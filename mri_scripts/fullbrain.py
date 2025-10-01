import SVMTK as svmtk

data_folder = "paz1"
path = "Data/paz1/2018-02-06/surf"

def create_brain_mesh(stls, output,
                      resolution=16, remove_ventricles=True):

    # Load each of the Surfaces
    surfaces = [svmtk.Surface(stl) for stl in stls]
    
    
    # Take the union of the left (#3) and right (#4)
    # white surface and put the result into
    # the (former left) white surface
    # ... and drop the right white surface from the list
    surfaces[3].union(surfaces[4])
    surfaces.pop(4)
    surfaces[4].union(surfaces[5])
    surfaces.pop(5)

    # Define identifying tags for the different regions 
    tags = {"pial": 1, "white": 2, "ventricle": 3, "tumor": 4, "brain": 5}

    # Label the different regions
    
    smap = svmtk.SubdomainMap()
    smap.set_number_of_surfaces(6)
    smap.add("100000", tags["brain"]) 
    smap.add("110000", tags["pial"]) 
    smap.add("010000", tags["pial"]) 
    smap.add("101000", tags["pial"]) 
    smap.add("001000", tags["pial"]) 
    smap.add("110100", tags["white"])
    smap.add("101100", tags["white"])
    smap.add("111100", tags["white"])
    smap.add("110110", tags["ventricle"])
    smap.add("101110", tags["ventricle"])
    smap.add("111110", tags["ventricle"])
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

# f,
stls = (f"{path}/brain.smooth.stl",f"{path}/lh.pial.smooth.stl", f"{path}/rh.pial.smooth.stl", \
        f"{path}/lh.white.smooth.stl", f"{path}/rh.white.smooth.stl", f"{path}/aseg-models/Left-Lateral-Ventricle.stl", \
        f"{path}/aseg-models/Right-Lateral-Ventricle.stl",f"{path}/tumor.smooth.stl")
create_brain_mesh(stls, f"{path}/paz1_ref16_final.mesh",remove_ventricles=False)

#create_brain_mesh(stls, "ernie-brain-32-wv.mesh", remove_ventricles=False) 
