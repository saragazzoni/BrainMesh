import surface_to_mesh as stm
import json 
import os

with open('mri_scripts/params_config.json', 'r') as f:
    config = json.load(f)

path = config["patient_path"]
surf_folder = f"{path}/surf"
mesh_folder = f"{path}/mesh"
if not os.path.exists(mesh_folder):
    os.makedirs(mesh_folder)

# Remesh and smoothen the surfaces
volume_mesh = config["volume_mesh"]

print("Remeshing Brain surface...")
stm.remesh_surface(f"{surf_folder}/brain_new.stl", f"{surf_folder}/brain_remeshed_new.stl", volume_mesh["remesh_length_brain"], volume_mesh["remesh_iterations_brain"])
print("Smoothing Brain surface...")
stm.smoothen_surface(f"{surf_folder}/brain_remeshed_new.stl", f"{surf_folder}/brain_smooth_new.stl", n=volume_mesh["smoothen_iterations_brain"], eps=volume_mesh["smoothen_epsilon_brain"])

print("Remeshing GM surface...")
# stm.remesh_surface(f"{surf_folder}/GM.stl", f"{surf_folder}/GM_remeshed.stl", volume_mesh["remesh_length_tumor"], volume_mesh["remesh_iterations_tumor"])
print("Smoothing GM surface...")
stm.smoothen_surface(f"{surf_folder}/GM_new.stl", f"{surf_folder}/GM_smooth_new.stl", n=volume_mesh["smoothen_iterations_tumor"], eps=volume_mesh["smoothen_epsilon_tumor"])

print("Remeshing WM surface...")
# stm.remesh_surface(f"{surf_folder}/WM.stl", f"{surf_folder}/WM_remeshed.stl", volume_mesh["remesh_length_tumor"], volume_mesh["remesh_iterations_tumor"])
print("Smoothing WM surface...")
stm.smoothen_surface(f"{surf_folder}/WM_new.stl", f"{surf_folder}/WM_smooth_new.stl", n=volume_mesh["smoothen_iterations_tumor"], eps=volume_mesh["smoothen_epsilon_tumor"])

print("Generating Volume mesh...")
stm.create_pial_mesh(f"{surf_folder}/tumor_smooth.stl", f"{surf_folder}/WM_smooth_new.stl", f"{surf_folder}/GM_smooth_new.stl", f"{mesh_folder}/pial.mesh")
print("Converting to XDMF...")
stm.from_mesh_to_adim_xdmf(f"{mesh_folder}/pial.mesh", f"{mesh_folder}/pial.xdmf", volume_mesh["characteristic_length"])


