import SVMTK as svmtk

data_folder = "paz1"
path = "Data/paz22/27-03/surf"

def smoothen_surface(stl_input, output,
                     n=1, eps=1.0, preserve_volume=True):
    # Load input STL file
    surface = svmtk.Surface(stl_input)

    # Smooth using Taubin smoothing
    # if volume should be preserved,
    # otherwise use Laplacian smoothing
    if preserve_volume:
        surface.smooth_taubin(n)
    else:
        surface.smooth_laplacian(eps, n)
        
    # Save smoothened STL surface
    surface.save(output)

# smoothen_surface(f"{path}/lh.white.remesh.stl", f"{path}/lh.white.smooth.stl", n=10, eps=0.7)
# smoothen_surface(f"{path}/rh.white.remesh.stl", f"{path}/rh.white.smooth.stl", n=10, eps=0.7)
# smoothen_surface(f"{path}/lh.pial.remesh.stl", f"{path}/lh.pial.smooth.stl", n=10, eps=0.7)
# smoothen_surface(f"{path}/rh.pial.remesh.stl", f"{path}/rh.pial.smooth.stl", n=10, eps=0.7)
smoothen_surface(f"{path}/brain.remesh.stl", f"{path}/brain.smooth.stl", n=10, eps=0.7)
smoothen_surface(f"{path}/tumor.remesh.stl", f"{path}/tumor.smooth.stl", n=10, eps=0.7)

# Try smoothing without not preserving volume
if False:
    smoothen_surface(f"{path}/lh.white.remesh.stl", f"{path}/lh.white.laplacian.stl",
                     n=10, eps=1.0, preserve_volume=False)

