import SVMTK as svmtk 

def create_gw_mesh(brain_stl, tumor_stl, output):
    # Load the surfaces into SVM-Tk and combine in list
    brain  = svmtk.Surface(brain_stl)
    tumor = svmtk.Surface(tumor_stl)
    surfaces = [brain, tumor]
    # Create a map for the subdomains with tags
    # 1 for inside the first and outside the second ("10")
    # 2 for inside the first and inside the second ("11")
    smap = svmtk.SubdomainMap()
    smap.add("10", 1)
    smap.add("11", 2)
    # Create a tagged domain from the list of surfaces
    # and the map
    domain = svmtk.Domain(surfaces, smap)
       
    # Create and save the volume mesh 
    resolution = 16
    domain.create_mesh(resolution)
    domain.save(output) 

#create_gw_mesh("lh.pial.smooth.stl", "lh.white.smooth.stl", "paz1-lh-gw.mesh")
#create_gw_mesh("rh.pial.smooth.stl", "rh.white.smooth.stl", "paz1-rh-gw.mesh")
# folder_path = "Data/paz1/2018-02-06"
folder_path = "Data/paz22/27-03"
create_gw_mesh(f"{folder_path}/surf/brain.smooth.stl", f"{folder_path}/surf/tumor.smooth.stl", f"{folder_path}/mesh/brain_tumor.mesh")

