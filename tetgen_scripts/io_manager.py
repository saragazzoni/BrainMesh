import dolfinx
import dolfinx.io
from mpi4py import MPI
import meshio
import numpy as np
import meshio

class IOManager(object):
            
    def __init__(self, sol_folder, plot = True):
        self.sol_folder = sol_folder
        self.plot = plot

    def setup_output(self, filename):
        t = self.time_step
        print("writing solution at time step ", t)
        if self.plot:
            new_file = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{self.sol_folder}/{filename}_{t}.xdmf", "w")
            new_file.write_mesh(self.msh)
            self.file = new_file
         
    def write_output(self, solution, t):  

        if self.plot:      
            
            print(f"Writing output of {solution.name}")   
            self.file.write_function(solution, t)
    
    def close_file(self):

        if self.plot:
            self.file.close()

    def import_mesh(self, filename, tag, t, iteration):
        
        with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{self.sol_folder}/{filename}.xdmf", "r") as xdmf:
            self.msh=xdmf.read_mesh(name="Grid")
            self.tags=xdmf.read_meshtags(self.msh,"Grid")
        self.time_step = t
        self.iteration = iteration

        self.msh.topology.create_connectivity(self.msh.topology.dim, 0)
        c_to_v = self.msh.topology.connectivity(self.msh.topology.dim, 0)

        tumor_cells = np.where(self.tags.values == tag)[0]
        # baricentri di tutte le celle con quel tag
        tumor_centers = np.array([
            self.msh.geometry.x[c_to_v.links(cell)].mean(axis=0)
            for cell in tumor_cells
        ])

        # centro medio (baricentro del tumore)
        self.center = tumor_centers.mean(axis=0)
        print(f"Tumor center at {self.center}")

        return self.msh
    
    def write_tet_mesh(self, filename):
        
        comm = self.msh.comm
        rank = comm.rank

        geom_imap = self.msh.geometry.index_map()
        local_range = geom_imap.local_range
        num_nodes_local = local_range[1] - local_range[0]
        nodes = self.msh.geometry.x.reshape(-1, 3)[:num_nodes_local, :]
        all_nodes = self.msh.comm.gather(nodes, root=0)
        if rank == 0:
            all_nodes = np.vstack(all_nodes)
            # print(all_nodes.shape)

        num_cells_local = self.msh.topology.index_map(self.msh.topology.dim).size_local
        connectivity = self.msh.geometry.dofmap[:num_cells_local, :]
        global_connectivity = geom_imap.local_to_global(connectivity.flatten()).reshape(-1, connectivity.shape[1])

        all_connectivity = self.msh.comm.gather(global_connectivity, root=0)
        if rank == 0:
            all_connectivity = np.vstack(all_connectivity)

        # tags
        if self.tags is not None:
            local_tags = self.tags.values
            all_tags = comm.gather(local_tags, root=0)
            if rank == 0:
                all_tags = np.concatenate(all_tags)
        else:
            all_tags = None
        
        t = self.time_step
        iteration = self.iteration

        if rank == 0:
            
            with open(f"{self.sol_folder}/{filename}_{t}.{iteration}.node", "w") as file:
                file.write(f"{len(all_nodes)} 3 0 0\n")
                for i, node in enumerate(all_nodes):
                    file.write(f"{i+1} {node[0]} {node[1]} {node[2]}\n")
            with open(f"{self.sol_folder}/{filename}_{t}.{iteration}.ele", "w") as file:
                file.write(f"{len(all_connectivity)} 4 1\n")
                for i, cell in enumerate(all_connectivity):
                    tag = int(all_tags[i]) if all_tags is not None else 0
                    file.write(f"{i+1} {int(cell[0])+1} {int(cell[1])+1} {int(cell[2])+1} {int(cell[3])+1} {tag}\n")
        comm.barrier()
        return
    
    def create_xdmf(self, name_file):
        
        t = self.time_step
        iteration = self.iteration
        comm = self.msh.comm
        
        if comm.rank == 0:
            current_name = f"{self.sol_folder}/{name_file}_{t}.{iteration+1}"
            
            nodes = meshio.read(current_name + ".node")  # Node coordinates
            elements = meshio.read(current_name + ".ele")  # Tetrahedral elements

            # Lettura celle (tetra) e tag manualmente
            ele_file = current_name + ".ele"
            with open(ele_file, "r") as f:
                header = f.readline()  # es. "num_cells 4 1"
                parts = header.split()
                has_attribute = int(parts[2])  # se 1 -> c'è la colonna tag

                tetra_cells = []
                cell_markers = []
                lines = f.readlines()  # legge tutte le righe in una lista
                for line in lines[:-1]: 
                    values = [int(x) for x in line.split()]
                    # I primi 4 valori dopo l'indice sono i vertici
                    tetra_cells.append([v-1 for v in values[1:5]])  # 0-based indexing
                    if has_attribute:
                        cell_markers.append(values[5])
                    else:
                        cell_markers.append(1)  # default tag

            tetra_cells = np.array(tetra_cells, dtype=np.int32)
            cell_markers = np.array(cell_markers, dtype=np.int32)

            # Extract points and tetrahedra
            points = nodes.points
            tetra_cells = elements.cells_dict["tetra"]
            
            # Create mesh with tags
            msh = meshio.Mesh(
                points,
                [("tetra", tetra_cells)],
                cell_data={"gmsh:physical": [cell_markers]},
            )

            # Save to XDMF
            new_namefile = f"{self.sol_folder}/{name_file}_refined"
            meshio.write(new_namefile + ".xdmf", msh, file_format="xdmf")

            print(f"RANK {comm.rank}: created mesh xdmf {new_namefile}.xdmf")
            print(f"final mesh has {len(points)} nodes and {len(tetra_cells)} tetrahedra")
        comm.barrier()
        return
    
    def getFolder(self):

        return self.sol_folder
    
    def getTimeStep(self):

        return self.time_step
    
    def getIteration(self):

        return self.iteration
    

