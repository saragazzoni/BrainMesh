import meshio
import numpy as np

# Read the .mesh file into meshio 
folder_path = "Data/paz1/2018-02-06/mesh"
# folder_path = "Data/paz22/27-03/mesh"

meshfile = f"{folder_path}/mesh_nobrain_final000000.vtu"

mesh = meshio.read(meshfile)
points = mesh.points/10.0
tetra  = {"tetra": mesh.cells_dict["tetra"]}

subdomains = {"subdomains": [mesh.cell_data_dict["f"]["tetra"]]}

# Write the dti data to a .xdmf file 
xdmf = meshio.Mesh(points, tetra, cell_data=subdomains)
meshio.write(f"{folder_path}/mesh_nobrain_final_labels_adim.xdmf", xdmf)
print(f"Mesh written successfully")