from dolfin import *

folder_path = "Data/paz1/2018-02-06/mesh"
# folder_path = "Data/paz22/27-03/mesh"
filename = f"{folder_path}/mesh_nobrain_final.h5"
mesh = Mesh()
hdf = HDF5File(mesh.mpi_comm(),filename, "r")
hdf.read(mesh, "/mesh", False)  
print ("mesh num vertices ", mesh.num_vertices())
print ("mesh num cells", mesh.num_cells())
subdomains = MeshFunction("size_t", mesh, mesh.topology().dim())
hdf.read(subdomains, "/subdomains")
boundaries  = MeshFunction("size_t", mesh, mesh.topology().dim() - 1)
hdf.read(boundaries, "/boundaries")
dx = Measure("dx", domain=mesh, subdomain_data=subdomains)
ds = Measure("ds", domain=mesh, subdomain_data=boundaries)
# T = FunctionSpace(mesh, "DG",0)
# Kt = Function(T) 
# hdf.read(Kt, "/Dxx")
# hdf.close()

# Salvare la funzione tensoriale Kt in formato VTK
# vtkfile = File("paz1/final_surf/Dxx.pvd")  # Può essere anche .vtk
# vtkfile << Kt

# vtkfile_mesh = File(f"{folder_path}/brain_tumor_shiftcenter.pvd")
# vtkfile_mesh << mesh
vtkfile_mesh = File(f"{folder_path}/mesh_nobrain_final.pvd")
vtkfile_mesh << subdomains

print("Dati salvati in formato VTK per la visualizzazione in ParaView.")
