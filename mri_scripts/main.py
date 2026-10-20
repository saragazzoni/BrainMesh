import surface_to_mesh as stm
import json 
import os


with open('mri_scripts/params_config.json', 'r') as f:
    config = json.load(f)

folder_path = config["patient_path"]

for idx in range(17,18):
    print(f"Processing patient {idx}...")
    patient_folder = f"paz{idx}/postop"
    surf_folder = f"{folder_path}/{patient_folder}/stl"
    mesh_folder = f"{folder_path}/{patient_folder}/mesh"
    if not os.path.exists(mesh_folder):
        os.makedirs(mesh_folder)

    # Remesh and smoothen the surfaces
    volume_mesh = config["volume_mesh"]
    print("Smoothing Brain surface...")
    stm.remesh_surface(f"{surf_folder}/brain.stl", f"{surf_folder}/brain_remeshed.stl", volume_mesh["remesh_length_brain"], 
                       volume_mesh["remesh_iterations_brain"])
    stm.smoothen_surface(f"{surf_folder}/brain_remeshed.stl", f"{surf_folder}/brain_smooth.stl", 
                         n=volume_mesh["smoothen_iterations_brain"], eps=volume_mesh["smoothen_epsilon_brain"])

    print("Smoothing Tumor surface...")
    stm.remesh_surface(f"{surf_folder}/cavity.stl", f"{surf_folder}/tumor_remeshed.stl", volume_mesh["remesh_length_tumor"], 
                       volume_mesh["remesh_iterations_tumor"])
    stm.smoothen_surface(f"{surf_folder}/tumor_remeshed.stl", f"{surf_folder}/tumor_smooth.stl", 
                         n=volume_mesh["smoothen_iterations_tumor"], eps=volume_mesh["smoothen_epsilon_tumor"])

    print("Generating Volume mesh...")
    stm.create_brain_tumor_mesh(f"{surf_folder}/brain_smooth.stl", f"{surf_folder}/tumor_smooth.stl", 
                                            f"{mesh_folder}/brain_tumor.mesh", resolution=volume_mesh["mesh_resolution"])
    print("Converting to XDMF...")
    stm.from_mesh_to_adim_xdmf(f"{mesh_folder}/brain_tumor.mesh", f"{mesh_folder}/brain_tumor_adim.xdmf", 
                               volume_mesh["characteristic_length"])#, tumor_stl=f"{surf_folder}/tumor_smooth.stl")


# # single surface mesh example
# print("Generating Volume mesh from single surface...")
# domain = stm.mesh_from_single_surface(f"{path}/brain_smooth.stl", f"{mesh_folder}/brainRef.mesh")
# print("Converting to XDMF...")
# stm.from_mesh_to_adim_xdmf(f"{mesh_folder}/brainRef.mesh", f"{mesh_folder}/brainRef.xdmf")