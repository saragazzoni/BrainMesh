from dolfin import *

mesh = Mesh()
folder_path = "Data/paz1/2018-02-06/mesh"
filename = f"{folder_path}/mesh_nobrain_final.h5"
hdf = HDF5File(mesh.mpi_comm(),filename, "r")
hdf.read(mesh, "/mesh", False)  
subdomains = MeshFunction("size_t", mesh, mesh.topology().dim())
hdf.read(subdomains, "/subdomains")
file = XDMFFile(f'{folder_path}/mesh_nobrain_final_labels.xdmf')
file.write(subdomains)
 