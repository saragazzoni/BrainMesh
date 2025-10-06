import surface_to_mesh as stm
import json 
import os

with open('params_config.json', 'r') as f:
    config = json.load(f)

path = config["patient_path"]
mesh_folder = config["mesh_folder_path"]
if not os.path.exists(mesh_folder):
    os.makedirs(mesh_folder)

# Remesh and smoothen the surfaces
volume_mesh = config["volume_mesh"]
print("Smoothing Brain surface...")
stm.remesh_surface(f"{path}/brain.stl", f"{mesh_folder}/brain_remeshed.stl", volume_mesh["remesh_length_brain"], volume_mesh["remesh_iterations_brain"])
stm.smoothen_surface(f"{mesh_folder}/brain_remeshed.stl", f"{mesh_folder}/brain_smooth.stl", n=volume_mesh["smoothen_iterations_brain"], eps=volume_mesh["smoothen_epsilon_brain"])

print("Smoothing Tumor surface...")
stm.remesh_surface(f"{path}/tumor.stl", f"{mesh_folder}/tumor_remeshed.stl", volume_mesh["remesh_length_tumor"], volume_mesh["remesh_iterations_tumor"])
stm.smoothen_surface(f"{mesh_folder}/tumor_remeshed.stl", f"{mesh_folder}/tumor_smooth.stl", n=volume_mesh["smoothen_iterations_tumor"], eps=volume_mesh["smoothen_epsilon_tumor"])

print("Generating Volume mesh...")
stm.create_brain_tumor_mesh(f"{mesh_folder}/brain_smooth.stl", f"{mesh_folder}/tumor_smooth.stl", f"{mesh_folder}/brain_tumor.mesh")
print("Converting to XDMF...")
stm.from_mesh_to_adim_xdmf(f"{mesh_folder}/brain_tumor.mesh", f"{mesh_folder}/brain_tumor_adim.xdmf", volume_mesh["characteristic_length"])

