import meshio
import numpy as np

# Read the .mesh file into meshio 
folder_path = "Data/paz1/2018-02-06/dti"
# folder_path = "Data/paz22"
components = ["Dxx", "Dyy", "Dzz", "Dxy", "Dxz", "Dyz"]
coef = 1e6
for comp in components:
    meshfile = f"{folder_path}/Mesh_{comp}_nobrain.vtu"

    mesh = meshio.read(meshfile)
    points = mesh.points/10.0
    # points = mesh.points
    tetra  = {"tetra": mesh.cells_dict["tetra"]}
    
    dti = {f"{comp}": [mesh.cell_data_dict[f"{comp}"]["tetra"]]}
    dti[f"{comp}"][0] = dti[f"{comp}"][0]*coef

    # Write the dti data to a .xdmf file 
    xdmf = meshio.Mesh(points, tetra, cell_data=dti)
    meshio.write(f"{folder_path}/Mesh_{comp}_nobrain_adim.xdmf", xdmf)
    print(f"Mesh {comp} written successfully")
