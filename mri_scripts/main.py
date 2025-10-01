import surface_to_mesh as stm
import json 

with open('params_config.json', 'r') as f:
    config = json.load(f)

path = config["patient_path"]
stm.remesh_surface(f"{path}/brain.stl", f"{path}/brain.stl", 1.0, 3)
stm.smoothen_surface(f"{path}/brain.stl", f"{path}/brain.stl", n=5, eps=0.7)
stm.create_volume_mesh(f"{path}/brain.stl", f"{path}/brain_mesh.vtk", resolution=16)