import SVMTK as svmtk

def remesh_surface(stl_input, output, L, n,
                   do_not_move_boundary_edges=False):

    # Load input STL file
    surface = svmtk.Surface(stl_input)

    # Remesh surface
    surface.isotropic_remeshing(L, n,
                                do_not_move_boundary_edges)

    # Save remeshed STL surface 
    surface.save(output)  

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


def create_volume_mesh(stlfile, output, resolution=16):
    # Load input file
    surface = svmtk.Surface(stlfile)
    
    # Generate the volume mesh
    domain = svmtk.Domain(surface)
    domain.create_mesh(resolution)

    # Write the mesh to the output file
    domain.save(output)


