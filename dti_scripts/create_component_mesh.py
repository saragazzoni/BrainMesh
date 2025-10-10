import os
import vtk
import pyvista as pv
import meshio
import numpy as np

# =============================================
# Funzione: legge un file .mhd e ritorna VTK image
# =============================================
def read_mhd_image(mhd_file):
    reader = vtk.vtkMetaImageReader()
    reader.SetFileName(mhd_file)
    reader.Update()
    return reader.GetOutput()

# =============================================
# Funzione: interpola l'immagine scalare sulla mesh XDMF
# =============================================
def probe_scalar_to_mesh(mesh_pv, scalar_image, label):
    # Wrap VTK image in PyVista
    pv_image = pv.wrap(scalar_image)
    
    # Prova a mappare i valori dell'immagine sui punti della mesh
    sampled = pv_image.sample(mesh_pv)
    
    # Aggiungi i dati interpolati alla mesh
    mesh_pv[label] = sampled[label]
    return mesh_pv

# =============================================
# Funzione: scrive la mesh finale in XDMF
# =============================================
def write_mesh_xdmf(mesh_pv, output_file):
    # Estrai punti e celle
    points = mesh_pv.points
    cells = {}
    for cell_type, conn in mesh_pv.cells_dict.items():
        cells[cell_type] = conn
    
    # Estrai i dati dei punti (scalari)
    point_data = {}
    for name in mesh_pv.point_data.keys():
        point_data[name] = [mesh_pv.point_data[name]]
    
    # Crea meshio.Mesh e salva
    meshio_mesh = meshio.Mesh(points=points, cells=cells, point_data=point_data)
    meshio.write(output_file, meshio_mesh)
    print(f"Mesh scritta correttamente in {output_file}")

# =============================================
# Funzione principale
# =============================================
def main(mesh_xdmf_file, dti_folder, components, output_file):
    # Leggi la mesh XDMF con meshio
    mesh_mio = meshio.read(mesh_xdmf_file)
    
    if "tetra" in mesh_mio.cells_dict:
        tetra = mesh_mio.cells_dict["tetra"]
        cell_types = np.full(len(tetra), 10, dtype=np.uint8)
        cells_array = np.hstack([np.array([4, *cell]) for cell in tetra])
        mesh_pv = pv.UnstructuredGrid(cells_array, cell_types, mesh_mio.points)
    else:
        raise ValueError("La mesh deve contenere celle tetraedriche")

    
    # Loop sui componenti DTI
    for comp in components:
        mhd_file = os.path.join(dti_folder, f"{comp}.mhd")
        if not os.path.exists(mhd_file):
            print(f"Attenzione: {mhd_file} non trovato, salto {comp}")
            continue
        
        scalar_image = read_mhd_image(mhd_file)

        print("Array scalari disponibili nell'immagine:", scalar_image.GetPointData().GetArrayName(0))

        mesh_pv = probe_scalar_to_mesh(mesh_pv, scalar_image, 'MetaImage')
        print(f"{comp} interpolato sulla mesh")
    
    # Scrivi la mesh finale
    write_mesh_xdmf(mesh_pv, output_file)

# =============================================
# Esempio di utilizzo
# =============================================
if __name__ == "__main__":
    # Cartella con DTI .mhd
    dti_folder = "/Users/saragazzoni/Desktop/Data/Campanini_Maria_paz23/images/2018-02-26/processed/"
    
    # Mesh iniziale in XDMF/EMSH
    mesh_xdmf_file = "Data/paz23/brain_tumor_adim_refined.xdmf"
    
    # Componenti DTI da interpolare
    components = ["Dxx"]
    
    # Output finale
    output_file = "Data/paz23/brain_mesh_with_DTI.xdmf"
    
    main(mesh_xdmf_file, dti_folder, components, output_file)
