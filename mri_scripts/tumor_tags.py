"""
Assegna il tag del tumore ai tetraedri DOPO la generazione della mesh.
 
Un tetraedro riceve il tag del tumore se il suo baricentro cade dentro la superficie
del tumore (STL chiuso). Non dipende da cosa ha rilevato il mesher, quindi funziona
anche per tumori profondi. Il bordo del tumore segue gli elementi della mesh
(non e' una superficie conforme): piu' fine la mesh, piu' fedele il bordo.
 
IMPORTANTE: la mesh e lo STL devono essere nelle stesse coordinate (mm),
quindi applicalo PRIMA di eventuali adimensionalizzazioni.
 
Requisiti: pip install meshio trimesh rtree
"""
 
import meshio
import numpy as np
import trimesh
 
 
def tumor_tags(points, tets, tumor_stl, tag_brain=1, tag_tumor=2):
    """Restituisce un tag per ogni tetraedro e stampa i volumi per tag."""
    tumor = trimesh.load(tumor_stl, force="mesh")
    if not tumor.is_watertight:
        raise RuntimeError(f"{tumor_stl}: la superficie del tumore non e' chiusa")
 
    centroids = points[tets].mean(axis=1)
    tags = np.full(len(tets), tag_brain, dtype=np.int32)
 
    # test "dentro/fuori" solo per i baricentri nel riquadro del tumore (molto piu' veloce)
    lo, hi = tumor.bounds
    near = np.all((centroids >= lo) & (centroids <= hi), axis=1)
    tags[np.flatnonzero(near)[tumor.contains(centroids[near])]] = tag_tumor
 
    p = points[tets]
    vol = np.abs(np.einsum("ij,ij->i", p[:, 1] - p[:, 0],
                           np.cross(p[:, 2] - p[:, 0], p[:, 3] - p[:, 0]))) / 6
    v_tumor = vol[tags == tag_tumor].sum() / 1000
    print(f"   tumore nella mesh: {v_tumor:.2f} mL "
          f"(STL: {tumor.volume / 1000:.2f} mL), {np.sum(tags == tag_tumor)} tetraedri")
    if v_tumor == 0:
        print("   ATTENZIONE: nessun tetraedro dentro il tumore (coordinate diverse?)")
    return tags
 
 
def retag_mesh_file(mesh_in, tumor_stl, mesh_out):
    """Legge una mesh (.mesh, .xdmf, ...), riassegna i tag delle celle e la salva."""
    m = meshio.read(mesh_in)
    tets = m.cells_dict["tetra"]
    tags = tumor_tags(m.points, tets, tumor_stl)
    meshio.write(mesh_out, meshio.Mesh(m.points, [("tetra", tets)],
                                       cell_data={"subdomains": [tags]}))
    return tags