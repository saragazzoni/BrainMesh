import argparse
import meshio
from dolfinx.io import XDMFFile
from dolfinx.mesh import create_mesh, MeshTags
from mpi4py import MPI
import numpy as np


def write_mesh_to_xdmf_single(meshfile, xdmf_file):
    # Leggi il file .mesh con meshio
    mesh = meshio.read(meshfile)

    # Estrai i dati
    points = mesh.points/10.0
    tetra  = {"tetra": mesh.cells_dict["tetra"]}
    subdomains = {"subdomains": [mesh.cell_data_dict["medit:ref"]["tetra"]]}

    if tetra is None:
        raise ValueError("The input mesh does not contain tetrahedral cells.")


    # Scrivi nel file XDMF
    xdmf_mesh = meshio.Mesh(points, tetra, cell_data=subdomains)
    meshio.write(xdmf_file, xdmf_mesh)
    print(f"Mesh salvata in {xdmf_file}")


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument("--meshfile", type=str, help="Path to the input .mesh file")
    # parser.add_argument("--xdmffile", type=str, help="Path to the output .xdmf file")
    # args = parser.parse_args()

    path = "Data/paz22/27-03/mesh"
    meshfile = f"{path}/brain_tumor.mesh"
    xdmffile = f"{path}/brain_tumor_adim.xdmf"
    write_mesh_to_xdmf_single(meshfile, xdmffile)
