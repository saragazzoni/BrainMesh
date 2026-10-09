import SVMTK as svmtk
import meshio

def remesh_surface(stl_input, output, L, n,
                   do_not_move_boundary_edges=False):

    # Load input STL file
    surface = svmtk.Surface(stl_input)

    # Remesh surface
    surface.isotropic_remeshing(L, n,
                                do_not_move_boundary_edges)

    # Save remeshed STL surface 
    surface.save(output)  

import time 
def smoothen_surface(stl_input, output,
                     n=1, eps=1.0, preserve_volume=True):
    # Load input STL file
    t = time.time()
    surface = svmtk.Surface(stl_input)
    print("caricata:", time.time() - t, "s |", surface.num_vertices(), "vertici")

    # Smooth using Taubin smoothing
    # if volume should be preserved,
    # otherwise use Laplacian smoothing
    if preserve_volume:
        surface.smooth_taubin(n)
        
    else:
        surface.smooth_laplacian(eps, n)
        
    # Save smoothened STL surface
    surface.save(output)



def create_brain_tumor_mesh(brain_stl, tumor_stl, output, resolution=16):
    # Load the surfaces into SVM-Tk and combine in list
    brain  = svmtk.Surface(brain_stl)
    tumor = svmtk.Surface(tumor_stl)
    surfaces = [brain, tumor]
    # Create a map for the subdomains with tags

    smap = svmtk.SubdomainMap()
    smap.add("10", 1)
    smap.add("11", 2)
    # Create a tagged domain from the list of surfaces
    # and the map
    domain = svmtk.Domain(surfaces, smap)
       
    # Create and save the volume mesh 
    domain.create_mesh(resolution)
    domain.save(output)

def from_mesh_to_adim_xdmf(meshfile, xdmf_file, L_car=1):
    # Leggi il file .mesh con meshio
    mesh = meshio.read(meshfile)

    # Estrai i dati
    points = mesh.points/L_car
    tetra  = {"tetra": mesh.cells_dict["tetra"]}
    subdomains = {"subdomains": [mesh.cell_data_dict["medit:ref"]["tetra"]]}

    if tetra is None:
        raise ValueError("The input mesh does not contain tetrahedral cells.")


    # Scrivi nel file XDMF
    xdmf_mesh = meshio.Mesh(points, tetra, cell_data=subdomains)
    meshio.write(xdmf_file, xdmf_mesh)
    print(f"Mesh salvata in {xdmf_file}")

def mesh_from_single_surface(stl_input, output_mesh):
    # Load input STL file
    surface = svmtk.Surface(stl_input)
    
    # Create volume mesh from single surface
    domain = svmtk.Domain(surface)
    domain.create_mesh(16)
    domain.save(output_mesh)

    return domain

def create_full_brain_mesh(brain_stl, tumor_stl, wm_stl, gm_stl, output, resolution=16):
    # Load the surfaces into SVM-Tk and combine in list
    brain  = svmtk.Surface(brain_stl)
    tumor = svmtk.Surface(tumor_stl)
    wm = svmtk.Surface(wm_stl)
    gm = svmtk.Surface(gm_stl)
    surfaces = [brain, gm, wm, tumor]
    # Create a map for the subdomains with tags

    smap = svmtk.SubdomainMap()
    smap.add("1000", 1)
    smap.add("1100", 2)
    smap.add("1110", 3)
    smap.add("1010", 3)
    smap.add("1111", 4)
    smap.add("1101", 4)
    smap.add("1001", 4)
    # Create a tagged domain from the list of surfaces
    # and the map
    domain = svmtk.Domain(surfaces, smap)
       
    # Create and save the volume mesh 
    domain.create_mesh(resolution)
    domain.save(output)

def create_pial_mesh(tumor_stl, wm_stl, gm_stl, output, resolution=16):
    # Load the surfaces into SVM-Tk and combine in list
    tumor = svmtk.Surface(tumor_stl)
    wm = svmtk.Surface(wm_stl)
    gm = svmtk.Surface(gm_stl)
    surfaces = [gm, wm, tumor]
    # Create a map for the subdomains with tags

    smap = svmtk.SubdomainMap()
    smap.add("100", 2)
    smap.add("110", 3)
    smap.add("010", 3)
    smap.add("111", 4)
    smap.add("101", 4)
    smap.add("001", 4)
    # Create a tagged domain from the list of surfaces
    # and the map
    domain = svmtk.Domain(surfaces, smap)
       
    # Create and save the volume mesh 
    domain.create_mesh(resolution)
    domain.save(output)