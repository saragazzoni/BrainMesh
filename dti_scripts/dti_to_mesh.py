import vtk
import meshio 
import numpy as np

# Function to read the refined mesh file (VTK/VTU format)
def read_mesh(filename):
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

# Function to read the DTI tensor component from a .mhd file
def read_mhd_scalar_field(mhd_filename):
    reader = vtk.vtkMetaImageReader()
    reader.SetFileName(mhd_filename)
    reader.Update()
    return reader.GetOutput()

# Function to assign the scalar field to the mesh cells
def assign_scalar_to_mesh(mesh, scalar_field,label):
    num_cells = mesh.GetNumberOfCells()

    # Interpolate the scalar field to the mesh cells (we'll assume the field aligns spatially with the mesh)
    probe = vtk.vtkProbeFilter()
    probe.SetInputData(mesh)
    probe.SetSourceData(scalar_field)
    probe.Update()

    # Get the interpolated scalar values (cell data)
    probed_mesh = probe.GetOutput()

    # Extract the scalar field values and add them to the mesh cell data
    scalar_values = probed_mesh.GetPointData().GetScalars()

    # Create a new array to store scalar data for cells
    cell_scalar_array = vtk.vtkDoubleArray()
    cell_scalar_array.SetName(label)
    cell_scalar_array.SetNumberOfComponents(1)
    cell_scalar_array.SetNumberOfTuples(num_cells)

    # Loop through each cell and compute the average scalar value for the cell
    for i in range(num_cells):
        cell = mesh.GetCell(i)
        cell_points = cell.GetPoints()
        num_points = cell_points.GetNumberOfPoints()

        # Compute the average scalar value over the points of the cell
        avg_value = 0.0
        for j in range(num_points):
            point_id = cell.GetPointId(j)
            avg_value += scalar_values.GetValue(point_id)

        avg_value /= num_points
        cell_scalar_array.SetValue(i, avg_value)

    # Add the new scalar field to the mesh's cell data
    mesh.GetCellData().AddArray(cell_scalar_array)

# Function to write the modified mesh to a new file
def write_mesh(mesh, output_filename):
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(output_filename)
    writer.SetInputData(mesh)
    writer.Write()

def vtu_to_xdfm(meshfile, xdmf_file, comp, coef=1e6):

    mesh = meshio.read(meshfile)
    points = mesh.points/10.0
    # points = mesh.points
    tetra  = {"tetra": mesh.cells_dict["tetra"]}
    
    dti = {f"{comp}": [mesh.cell_data_dict[f"{comp}"]["tetra"]]}
    dti[f"{comp}"][0] = dti[f"{comp}"][0]*coef

    # Write the dti data to a .xdmf file 
    xdmf = meshio.Mesh(points, tetra, cell_data=dti)
    meshio.write(xdmf_file, xdmf)
    print(f"Mesh {comp} written successfully")


# Main workflow
def main(refined_mesh_file, scalar_field_file, output_file,label):
    # Read the refined mesh
    mesh = read_mesh(refined_mesh_file)
    
    # Read the scalar field (e.g., Dxx.mhd) corresponding to a tensor component
    scalar_field = read_mhd_scalar_field(scalar_field_file)
    
    # Assign the scalar field to the mesh cells
    assign_scalar_to_mesh(mesh, scalar_field,label)
    
    # Write the modified mesh to a new file
    write_mesh(mesh, output_file)

    vtu_to_xdfm(output_file, xdmf_file, label, coef=1e6)

    print(f"Mesh with {label} field written to {output_file}")

if __name__ == "__main__":
    # Example usage
    data_folder = "Data/paz1/2018-02-06"
    # data_folder = "Data/paz22/27-03"
    components = ["Dxx", "Dyy", "Dzz", "Dxy", "Dxz", "Dyz"]
    for component in components:
        mesh_file = f"{data_folder}/mesh/mesh_nobrain_final000000.vtu"  # Path to your refined mesh file
        dti_file = f"{data_folder}/dti/{component}.mhd"  # Path to the scalar field (e.g., Dxx.mhd)
        output_file = f"{data_folder}/dti/Mesh_{component}.vtu"  # Output file path
        xdmf_file = f"{data_folder}/dti/Mesh_{component}_nobrain_adim.xdmf"
        label = component

        main(mesh_file, dti_file, output_file,label)
