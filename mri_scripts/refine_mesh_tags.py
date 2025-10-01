import argparse
from dolfin import * 
import numpy as np

cpp_code = """
#include<pybind11/pybind11.h>
#include<dolfin/adaptivity/adapt.h>
#include<dolfin/mesh/Mesh.h>
#include<dolfin/mesh/MeshFunction.h>

namespace py = pybind11;

PYBIND11_MODULE(SIGNATURE, m) {
  m.def("adapt", (std::shared_ptr<dolfin::MeshFunction<std::size_t>> (*)(const dolfin::MeshFunction<std::size_t>&, std::shared_ptr<const dolfin::Mesh>)) &dolfin::adapt, py::arg("mesh_function"), py::arg("adapted_mesh"));
  m.def("adapt", (std::shared_ptr<dolfin::Mesh> (*)(const dolfin::Mesh&)) &dolfin::adapt );
  m.def("adapt", (std::shared_ptr<dolfin::Mesh> (*)(const dolfin::Mesh&,const dolfin::MeshFunction<bool>&)) &dolfin::adapt );
}
"""
adapt = compile_cpp_code(cpp_code).adapt

folder_path = "."
# folder_path = "Data/paz22/27-03/mesh"

def refine_mesh_tags(in_hdf5, out_hdf5, tags=None, num_refinements=1):
    # Read the mesh from file. The mesh coordinates define 
    # the Surface RAS space.
    mesh = Mesh()
    hdf = HDF5File(mesh.mpi_comm(), in_hdf5, "r")
    hdf.read(mesh, "/mesh", False)  
    
    # Read subdomains and boundary markers
    d = mesh.topology().dim()
    subdomains = MeshFunction("size_t", mesh, d)
    hdf.read(subdomains, "/subdomains")
    boundaries = MeshFunction("size_t", mesh, d-1)
    hdf.read(boundaries, "/boundaries")
    hdf.close()

    # Initialize connections between all mesh entities, and 
    # use a refinement algorithm that remember parent facets
    mesh.init()
    print("Original mesh #cells: ", mesh.num_cells()) 
    parameters["refinement_algorithm"] = \
        "plaza_with_parent_facets"
    # Refine globally if no tags given
    if not tags: 
        # Refine all cells in the mesh 
        new_mesh = adapt(mesh)
        
        # Update the subdomain and boundary markers
        adapted_subdomains = adapt(subdomains, new_mesh) 
        adapted_boundaries = adapt(boundaries, new_mesh)      

    else:   
        # tag = tags[0]  # Assuming a single tag for simplicity
        # cells_with_tag = [cell for cell in cells(mesh) if subdomains[cell] == tag]
        center = Point(np.array([2.5, 0.4, 3.0]))
        # for cell in cells_with_tag:
        #     center += cell.midpoint()
        # center /= len(cells_with_tag)
        #Perform multiple refinements
        threshold = 2.0
        for _ in range(num_refinements):
            
            # Create markers for local refinement
            markers = MeshFunction("bool", mesh, d, False)
            # for tag in tags:
            #     markers.array()[(subdomains.array() == tag)] = True

            # Iterate over given tags, label all cells
            # with this subdomain tag for refinement:
            for cell in cells(mesh):
                distance = cell.midpoint().distance(center)
                # if subdomains[cell] == tag and distance < threshold:
                if distance < threshold:
                    markers[cell] = True

            # Refine mesh according to the markers
            new_mesh = adapt(mesh, markers)

            # Update subdomain and boundary markers
            adapted_subdomains = adapt(subdomains, new_mesh) 
            adapted_boundaries = adapt(boundaries, new_mesh)  

            # Update the mesh and subdomains for the next iteration
            mesh = new_mesh
            subdomains = adapted_subdomains
            boundaries = adapted_boundaries
            # threshold /= 2.0

    
    print("Refined mesh #cells: ", new_mesh.num_cells())  

    hdf = HDF5File(new_mesh.mpi_comm(), out_hdf5, "w")
    hdf.write(new_mesh, "/mesh")            
    hdf.write(adapted_subdomains, "/subdomains")
    hdf.write(adapted_boundaries, "/boundaries")
    hdf.close() 

if __name__ == "__main__":
    adapt = compile_cpp_code(cpp_code).adapt
    parser = argparse.ArgumentParser()
    parser.add_argument("--in_hdf5", type=str)      
    parser.add_argument("--out_hdf5", type=str) 
    parser.add_argument("--refine_tag",  type=int, nargs="+") 
    Z = parser.parse_args() 
    
    refine_mesh_tags(f"{folder_path}/brain_final.2.h5", f"{folder_path}/brain_final_ref.h5", [4], 3)

  


