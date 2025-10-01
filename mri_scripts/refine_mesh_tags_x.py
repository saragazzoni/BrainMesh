from dolfinx import mesh, io
from dolfinx.mesh import refine, transfer_meshtag, RefinementOption
from mpi4py import MPI
import numpy as np


def refine_mesh_by_tag(input_xdmf: str, output_xdmf: str, tag: int, num_refinements: int = 1):
    """
    Raffina una mesh solo nelle celle con un determinato tag.

    Parameters:
    -----------
    input_xdmf : str
        File XDMF di input contenente la mesh e i subdomains.
    output_xdmf : str
        File XDMF di output per salvare la mesh raffinata.
    tag : int
        Il valore del tag nei `subdomains` per cui effettuare il raffinamento.
    num_refinements : int, optional
        Numero di iterazioni di raffinamento da applicare (default: 1).
    """

    # Leggi la mesh e i subdomains
    with io.XDMFFile(MPI.COMM_WORLD, input_xdmf, "r") as infile:
        mesh = infile.read_mesh(name="Grid")
        subdomains = infile.read_meshtags(mesh, name="Grid")

    print("Original mesh #cells:", mesh.topology.index_map(mesh.topology.dim).size_local)

    # Raffinamento iterativo
    # for _ in range(num_refinements):
    #     # Crea un array booleano per contrassegnare le celle da raffinare
    #     markers = np.zeros(mesh.topology.index_map(mesh.topology.dim).size_local, dtype=bool)
    #     markers[subdomains.indices[subdomains.values == tag]] = True
    #     marked_cells = np.where(markers)[0]
       
    #     mesh.topology.create_connectivity(mesh.topology.dim,1)

    #     c_to_e  = mesh.topology.connectivity(mesh.topology.dim,1)

    #     edges=[]
    #     for cell in marked_cells:
    #         for e in c_to_e.links(cell):
    #             edges.append(e)
    #     mesh, parent_cell, _ = refine(mesh, np.array(edges), partitioner=None, option=RefinementOption.parent_cell_and_facet)
    #     subdomains = transfer_meshtag(subdomains, mesh, parent_cell)

    for _ in range(num_refinements):
        # Coordinate del punto centrale e raggio di raffinamento
        center = np.array([2.5, 0.4, 3.0])  # <-- inserisci qui le tue coordinate
        radius = 2.0                  # <-- scegli il raggio desiderato

        # Trova le celle vicine al punto
        # Ottieni la connettività cella-vertice
        mesh.topology.create_connectivity(mesh.topology.dim, 0)
        c_to_v = mesh.topology.connectivity(mesh.topology.dim, 0)

        # Calcola i baricentri delle celle
        cell_centers = np.array([mesh.geometry.x[c_to_v.links(cell)].mean(axis=0)
        for cell in range(mesh.topology.index_map(mesh.topology.dim).size_local)])
        distances = np.linalg.norm(cell_centers - center, axis=1)
        markers = distances < radius
        marked_cells = np.where(markers)[0]

        mesh.topology.create_connectivity(mesh.topology.dim, 1)
        c_to_e = mesh.topology.connectivity(mesh.topology.dim, 1)

        edges = []
        for cell in marked_cells:
            for e in c_to_e.links(cell):
                edges.append(e)
        mesh, parent_cell, _ = refine(mesh, np.array(edges), partitioner=None, option=RefinementOption.parent_cell_and_facet)
        subdomains = transfer_meshtag(subdomains, mesh, parent_cell)
        
    print("Refined mesh #cells:", mesh.topology.index_map(mesh.topology.dim).size_local)

    # Scrivi la mesh e i subdomains raffinati in un nuovo file XDMF
    with io.XDMFFile(MPI.COMM_WORLD, output_xdmf, "w") as outfile:
        outfile.write_mesh(mesh)
        outfile.write_meshtags(subdomains, mesh.geometry)

    print(f"Refined mesh salvata in {output_xdmf}")

    with io.XDMFFile(MPI.COMM_WORLD, output_xdmf, "r") as infile:
        mesh = infile.read_mesh(name="mesh")
        subdomains = infile.read_meshtags(mesh,name="mesh_tags")
    print(subdomains.values)

# Esempio d'uso
if __name__ == "__main__":
    # path = "Data/paz22/27-03/mesh"
    path = "."
    input_xdmf = "brain_final.2.xdmf"
    output_xdmf = "brain_final_ref.xdmf"
    refine_mesh_by_tag(input_xdmf, output_xdmf, tag=4, num_refinements=4)
