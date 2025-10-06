import refinement_functions as rf
import json
import os


with open('params_config.json', 'r') as f:
    config = json.load(f)

path = config["patient_path"]
mesh_folder = config["mesh_folder_path"]


## Choose this refinnement method to refine only the cells with the tumor tag
# rf.refine_tumor_mesh(f"{mesh_folder}/brain_tumor_adim.xdmf", "Grid", 2, config["mesh_refinement"]["refinement_iterations"], 
#                      f"{mesh_folder}/brain_tumor_refined.xdmf")

## Choose this refinement method to refine the area around the center of the tumor
rf.refine_tumor_area(f"{mesh_folder}/brain_tumor_adim.xdmf", f"{mesh_folder}/brain_tumor_refined_area.xdmf", config["mesh_refinement"]["refinement_tag"], 
                     config["mesh_refinement"]["refinement_iterations"], radius=config["mesh_refinement"]["refinement_radius"], 
                     step_refinement=config["mesh_refinement"]["step_refinement"])