import SVMTK as svmtk

folder_path = "Data/paz1/2018-02-06"

def create_brain_mesh(stls, output,
                      resolution=16, remove_ventricles=True):

    # Load each of the Surfaces
    surfaces = [svmtk.Surface(stl) for stl in stls]
    
    
    # Take the union of the left (#3) and right (#4)
    # white surface and put the result into
    # the (former left) white surface
    # ... and drop the right white surface from the list
    # surfaces[2].union(surfaces[3])
    # surfaces.pop(3)
    # surfaces[3].union(surfaces[4])
    # surfaces.pop(4)

    # Define identifying tags for the different regions 
    tags = {"pial": 1, "white": 2, "ventricle": 3, "tumor": 4}

    # Label the different regions
    
    smap = svmtk.SubdomainMap()
    smap.set_number_of_surfaces(3) 
    smap.add("100", tags["pial"]) 
    smap.add("010", tags["pial"])  
    # smap.add("10100", tags["white"])
    # smap.add("01100", tags["white"])
    # smap.add("11100", tags["white"])
    # smap.add("10110", tags["ventricle"])
    # smap.add("01110", tags["ventricle"])
    # smap.add("11110", tags["ventricle"])
    smap.add("*1", tags["tumor"])

    # Generate mesh at given resolution
    domain = svmtk.Domain(surfaces, smap)
    domain.create_mesh(resolution)

    # Remove ventricles perhaps
    if remove_ventricles:
        domain.remove_subdomain(tags["ventricle"])

    # Save mesh    
    domain.save(output)
    print("mesh saved")


# stls = (f"{folder_path}/surf/lh.pial.smooth.stl", f"{folder_path}/surf/rh.pial.smooth.stl", \
#         f"{folder_path}/surf/lh.white.smooth.stl", f"{folder_path}/surf/rh.white.smooth.stl", f"{folder_path}/surf/aseg-models/Left-Lateral-Ventricle.stl", \
#         f"{folder_path}/surf/aseg-models/Right-Lateral-Ventricle.stl",f"{folder_path}/surf/tumor.smooth.stl")
stls = (f"{folder_path}/surf/lh.pial.smooth.stl", f"{folder_path}/surf/rh.pial.smooth.stl", f"{folder_path}/surf/tumor.smooth.stl")
create_brain_mesh(stls, f"{folder_path}/mesh/pial_tumor.mesh",remove_ventricles=False)

