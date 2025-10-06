import numpy as np
import compute_triangle as ct
import time
from run_tetgen import adapt_mesh

class MeshAdapter(object):

    def __init__(self, mesh, f_space_sol):
        self.msh = mesh
        self.f_space_sol = f_space_sol
        self.num_cells = len(self.f_space_sol.dofmap.list)
        self.h_new_vect = np.zeros(self.num_cells)
        self.num_nodes = len(self.msh.geometry.x)

        
    def compute_size(self, h_ub=0.1, h_lb=1e-2, sigma=5.0):

        comm = self.msh.comm
        rank = comm.rank
        init_time=time.time()

        self.volume_vect = ct.compute_element_volume(self.msh)

        for (ii,k) in enumerate(self.f_space_sol.dofmap.list):
            
            p0 = self.msh.geometry.x[k[0]]
            p1 = self.msh.geometry.x[k[1]]
            p2 = self.msh.geometry.x[k[2]]
            p3 = self.msh.geometry.x[k[3]]
                  

            center_x = (p0[0]+p1[0]+p2[0]+p3[0])/4
            center_y = (p0[1]+p1[1]+p2[1]+p3[1])/4
            center_z = (p0[2]+p1[2]+p2[2]+p3[2])/4
            point = np.array([center_x, center_y, center_z])
            center = np.array([-1.5, 6.1, 0.4])
            distances = np.linalg.norm(point - center)
            h_new = h_lb + (h_ub - h_lb) * (1-np.exp(-(distances**2)/sigma**2))
            if h_new > h_ub:
                self.h_new_vect[ii] = h_ub
            elif h_new < h_lb:
                self.h_new_vect[ii] = h_lb
            else:
                self.h_new_vect[ii] = h_new
             
            
        end_time=time.time()

        print(f"RANK {rank}: Time to compute h_new:  {end_time-init_time}")
    
    def compute_metric(self, file_name, output_manager):

        comm = self.msh.comm
        rank = comm.rank

        self.file_name = f"{output_manager.getFolder()}/{file_name}_{output_manager.getTimeStep()}.{output_manager.getIteration()}"

        hN_vect = np.zeros(self.num_nodes)
        delta_N_vect = np.zeros(self.num_nodes)
        init_time=time.time()
        for ii in range(len(hN_vect)):
            k = np.where(np.array(self.f_space_sol.dofmap.list)==ii)
            delta_N = np.sum(self.volume_vect[k[0]])
            delta_N_vect[ii] = delta_N
            hN = np.sum(self.h_new_vect[k[0]]*self.volume_vect[k[0]])/delta_N
            hN_vect[ii] = hN     
        
        
        geom_imap = self.msh.geometry.index_map()
        local_range = geom_imap.local_range
        num_nodes_local = local_range[1] - local_range[0]
        local_hN_vect = hN_vect[:num_nodes_local]
        hN_vect_ghosts = hN_vect[num_nodes_local:]
        
        ghosts_index = self.msh.geometry.index_map().ghosts

        global_hN_vect = self.msh.comm.gather(local_hN_vect.reshape(-1,1), root=0)
        global_hN_vect_ghosts = self.msh.comm.gather(hN_vect_ghosts.reshape(-1,1), root=0)
        global_ghosts_index = self.msh.comm.gather(ghosts_index.reshape(-1,1), root=0)
        global_delta_N_ghosts = self.msh.comm.gather(delta_N_vect[num_nodes_local:].reshape(-1,1), root=0)
        global_delta_N_local = self.msh.comm.gather(delta_N_vect[:num_nodes_local].reshape(-1,1), root=0)

        if rank == 0:
            global_hN_vect = np.vstack(global_hN_vect)
            global_delta_N_local = np.vstack(global_delta_N_local)
        

            for i in range(len(global_hN_vect_ghosts)):
                for j in range(len(global_hN_vect_ghosts[i])):
                    index = int(global_ghosts_index[i][j])
                    global_hN_vect[index] = global_hN_vect[index]*global_delta_N_local[index] + global_hN_vect_ghosts[i][j]*global_delta_N_ghosts[i][j]
                    global_hN_vect[index] = global_hN_vect[index]/(global_delta_N_local[index]+global_delta_N_ghosts[i][j])
                    global_delta_N_local[index] += global_delta_N_ghosts[i][j]


            print(f"RANK {rank}: Writing metric file... {self.file_name}.mtr")
            with open(self.file_name + ".mtr", "w") as file:
                file.write(f"{len(global_hN_vect)} 1\n")
                for hN in global_hN_vect:
                    file.write(f"{hN}\n")
        end_time=time.time()
        print(f"RANK {rank}: Time to compute metric: ", end_time-init_time)
        comm.barrier()

    def create_mesh(self): 
        comm = self.msh.comm

        init_time=time.time()
        
        print(f"Rank {comm.rank}: Running tetgen with metric file... ")
        adapt_mesh(self.file_name)

        end_time=time.time()
        print(f"RANK {comm.rank}: Time to run tetgen: ", end_time-init_time)
        comm.barrier()
        return
