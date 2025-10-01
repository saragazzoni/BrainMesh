import SVMTK as svmtk

data_folder = "paz1"
path = f"{data_folder}/final_surf"

# Import the STL surface
lpial = svmtk.Surface(f"{path}/lh.pial.smooth.stl") 
rpial = svmtk.Surface(f"{path}/rh.pial.smooth.stl") 
rwhite = svmtk.Surface(f"{path}/rh.white.smooth.stl") 
lwhite = svmtk.Surface(f"{path}/lh.white.smooth.stl") 
brain = svmtk.Surface(f"{path}/brain.smooth.stl")

# Find and fill holes 
lpial.fill_holes()
rpial.fill_holes()
rwhite.fill_holes()
lwhite.fill_holes()
brain.fill_holes()

# Separate narrow gaps
# Default argument is -0.33. 
lpial.separate_narrow_gaps(-0.2)
rpial.separate_narrow_gaps(-0.2)
rwhite.separate_narrow_gaps(-0.2)
lwhite.separate_narrow_gaps(-0.2)
brain.separate_narrow_gaps(-0.2)

