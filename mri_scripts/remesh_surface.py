import SVMTK as svmtk
import trimesh
# path = "Data/paz22/27-03/surf"


path = "Data"
# Carica la mesh
# mesh = trimesh.load(f"{path}/brain.smooth.stl")

# # Scala tutte le coordinate (divide per 10)
# mesh.vertices /= 10.0

# # Salva la mesh scalata
# mesh.export(f"{path}/brain_scaled.stl")




def remesh_surface(stl_input, output, L, n,
                   do_not_move_boundary_edges=False):

    # Load input STL file
    surface = svmtk.Surface(stl_input)

    # Remesh surface
    surface.isotropic_remeshing(L, n,
                                do_not_move_boundary_edges)

    # Save remeshed STL surface 
    surface.save(output)                                      

# remesh_surface(f"{path}/lh.white.stl", f"{path}/lh.white.remesh.stl", 5.0, 3)
# remesh_surface(f"{path}/rh.white.stl", f"{path}/rh.white.remesh.stl", 5.0, 3)
# remesh_surface(f"{path}/lh.pial.stl", f"{path}/lh.pial.remesh.stl", 5.0, 3)
# remesh_surface(f"{path}/rh.pial.stl", f"{path}/rh.pial.remesh.stl", 5.0, 3)
remesh_surface(f"{path}/brain_scaled.stl", f"{path}/brain_final.stl", 1.0, 3)
# remesh_surface(f"{path}/tumor.stl", f"{path}/tumor.remesh.stl", 2.0, 3)