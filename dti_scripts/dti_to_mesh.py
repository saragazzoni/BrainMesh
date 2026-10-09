import vtk
import meshio 
import argparse
import numpy as np

# Function to read the refined mesh file (VTK/VTU format)
def read_mesh(filename):
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

# Function to read the DTI tensor component from a .mhd file
def read_mhd_scalar_field(mhd_filename):
    print(f"Reading scalar field from {mhd_filename}")
    reader = vtk.vtkMetaImageReader()
    reader.SetFileName(mhd_filename)
    reader.Update()

    output = reader.GetOutput()
    return output

def scale_mesh(mesh, scale_factor):
    """Scala tutti i punti della mesh"""
    transform = vtk.vtkTransform()
    transform.Scale(scale_factor, scale_factor, scale_factor)
    
    transform_filter = vtk.vtkTransformFilter()
    transform_filter.SetInputData(mesh)
    transform_filter.SetTransform(transform)
    transform_filter.Update()
    
    return transform_filter.GetOutput()


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

def assign_scalar_to_mesh_log(mesh, scalar_field, label, use_log=True):
    num_cells = mesh.GetNumberOfCells()

    probe = vtk.vtkProbeFilter()
    probe.SetInputData(mesh)
    probe.SetSourceData(scalar_field)
    probe.Update()

    probed_mesh = probe.GetOutput()
    scalar_values = probed_mesh.GetPointData().GetScalars()

    cell_scalar_array = vtk.vtkDoubleArray()
    cell_scalar_array.SetName(label)
    cell_scalar_array.SetNumberOfComponents(1)
    cell_scalar_array.SetNumberOfTuples(num_cells)

    for i in range(num_cells):
        cell = mesh.GetCell(i)
        cell_points = cell.GetPoints()
        num_points = cell_points.GetNumberOfPoints()

        avg_value = 0.0
        for j in range(num_points):
            point_id = cell.GetPointId(j)
            value = scalar_values.GetValue(point_id)
            
            if use_log and value > 0:
                value = np.log(value)
            
            avg_value += value

        avg_value /= num_points
        
        if use_log:
            avg_value = np.exp(avg_value)
        
        cell_scalar_array.SetValue(i, avg_value)

    mesh.GetCellData().AddArray(cell_scalar_array)

# Function to write the modified mesh to a new file
def write_mesh(mesh, output_filename):
    print(f"Writing mesh to {output_filename}")
    writer = vtk.vtkXMLUnstructuredGridWriter()
    writer.SetFileName(output_filename)
    writer.SetInputData(mesh)
    writer.Write()
    print(f"Mesh written to {output_filename}")

def vtu_to_xdfm(meshfile, comp, coef=1e6, L_car=10.0):

    mesh = meshio.read(meshfile)
    points = mesh.points/L_car
    # points = mesh.points
    tetra  = {"tetra": mesh.cells_dict["tetra"]}
    
    dti = {f"{comp}": [mesh.cell_data_dict[f"{comp}"]["tetra"]]}
    dti[f"{comp}"][0] = dti[f"{comp}"][0]*coef

    # Write the dti data to a .xdmf file 
    xdmf = meshio.Mesh(points, tetra, cell_data=dti)
    xdmf_file = meshfile.replace(".vtu", ".xdmf")
    meshio.write(xdmf_file, xdmf)
    print(f"Mesh {comp} written successfully")


# Main workflow
def project_dti(refined_mesh_file, scalar_field_file, output_file,label):
    # Read the refined mesh
    mesh = read_mesh(refined_mesh_file)
    
    # Scala su di un fattore 10
    mesh_scaled = scale_mesh(mesh, 10.0)
    
    # Read the scalar field (e.g., Dxx.mhd) corresponding to a tensor component
    scalar_field = read_mhd_scalar_field(scalar_field_file)
    
    # Assign the scalar field to the mesh cells
    assign_scalar_to_mesh(mesh_scaled, scalar_field,label)

    # Write the modified mesh to a new file
    write_mesh(mesh_scaled, output_file)

    vtu_to_xdfm(output_file, label, coef=1e6)

    print(f"Mesh with {label} field written to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process mesh and DTI scalar components")
    
    parser.add_argument("--dti_folder", type=str, required=True,
                        help="Folder where the DTI .mhd files are located")
    parser.add_argument("--mesh_path", type=str, required=True,
                        help="Path to the refined mesh file (vtu)")
    parser.add_argument("--output_folder", type=str, required=True,
                        help="Folder where the output .vtu files will be located")


    args = parser.parse_args()

    mesh_file = args.mesh_path
    components = ["Dxx"]
    for comp in components:
        dti_file = f"{args.dti_folder}/{comp}_flipped.mhd"
        output_file = f"{args.output_folder}/{comp}_MNI.vtu"

        project_dti(mesh_file, dti_file, output_file, comp)

    