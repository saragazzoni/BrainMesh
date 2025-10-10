import nibabel as nib
import numpy as np
import vtk
import meshio
from scipy.interpolate import RegularGridInterpolator

# -----------------------------------------------
# FUNZIONI DI BASE
# -----------------------------------------------

def read_mesh(vtu_file):
    """Legge una mesh VTU con VTK."""
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(vtu_file)
    reader.Update()
    return reader.GetOutput()

def assign_scalar_to_mesh_from_nifti(mesh, nifti_file, component_idx=0, label="Dxx"):
    """
    Assegna valori scalari dalla componente NIfTI alla mesh usando interpolazione.
    component_idx: indice della componente DTI (0=Dxx, 1=Dyy, ecc.)
    """
    # Carica NIfTI
    img = nib.load(nifti_file)
    data = img.get_fdata()
    affine = img.affine

    # Se il NIfTI ha più componenti, seleziona quella desiderata
    if data.ndim == 4:
        data = data[..., component_idx]

    nx, ny, nz = data.shape
    x = np.arange(nx)
    y = np.arange(ny)
    z = np.arange(nz)

    interpolator = RegularGridInterpolator((x, y, z), data, bounds_error=False, fill_value=0.0)

    num_cells = mesh.GetNumberOfCells()
    cell_values = np.zeros(num_cells)

    # Loop su tutte le celle della mesh
    for i in range(num_cells):
        cell = mesh.GetCell(i)
        pts = cell.GetPoints()
        avg_val = 0.0
        n_pts = pts.GetNumberOfPoints()

        for j in range(n_pts):
            pt = np.array(pts.GetPoint(j) + (1,))
            # Trasforma coordinate world -> voxel
            voxel_coord = np.linalg.inv(affine) @ pt
            avg_val += interpolator(voxel_coord[:3])
        cell_values[i] = avg_val / n_pts

    # Aggiungi l'array scalare alla mesh
    array = vtk.vtkDoubleArray()
    array.SetName(label)
    array.SetNumberOfComponents(1)
    array.SetNumberOfTuples(num_cells)
    for i in range(num_cells):
        array.SetValue(i, cell_values[i])

    mesh.GetCellData().AddArray(array)
    return mesh

def write_mesh_vtu(mesh, output_file):
    """Scrive la mesh in VTU."""
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(output_file)
    writer.SetInputData(mesh)
    writer.Write()

def write_mesh_xdmf(mesh_vtu_file, xdmf_file, label, coef=1e6):
    """Legge la VTU e scrive in XDMF usando meshio."""
    mesh = meshio.read(mesh_vtu_file)
    points = mesh.points
    tetra = {"tetra": mesh.cells_dict["tetra"]}
    dti = {label: [mesh.cell_data_dict[label]["tetra"] * coef]}
    meshio.write(xdmf_file, meshio.Mesh(points, tetra, cell_data=dti))
    print(f"Mesh XDMF scritta: {xdmf_file}")

# -----------------------------------------------
# MAIN
# -----------------------------------------------

def main(mesh_file, nifti_file, output_vtu, output_xdmf, label="Dxx", component_idx=0):
    mesh = read_mesh(mesh_file)
    mesh = assign_scalar_to_mesh_from_nifti(mesh, nifti_file, component_idx, label)
    write_mesh_vtu(mesh, output_vtu)
    write_mesh_xdmf(output_vtu, output_xdmf, label)
    print(f"Mesh con campo {label} salvata in {output_vtu} e {output_xdmf}")

# -----------------------------------------------
# ESEMPIO USO
# -----------------------------------------------

if __name__ == "__main__":
    data_folder = "Data/paz23"
    components = ["Dxx"]  # Puoi aggiungere Dyy, Dzz, Dxy, Dxz, Dyz
    for idx, comp in enumerate(components):
        mesh_file = f"{data_folder}/brain_tumor_refined.vtu"
        nifti_file = f"/Users/saragazzoni/Desktop/Data/Campanini_Maria_paz23/images/2018-02-26/processed/{comp}.nii.gz"
        output_vtu = f"{data_folder}/Mesh_{comp}.vtu"
        output_xdmf = f"{data_folder}/Mesh_{comp}.xdmf"
        main(mesh_file, nifti_file, output_vtu, output_xdmf, label=comp, component_idx=idx)
