from mpi4py import MPI
import numpy as np
import dolfinx.mesh
import dolfinx.io
from dolfinx.mesh import refine, transfer_meshtag, RefinementOption
import gmsh
import meshio

def refine_tumor_mesh(xdmf_file: str, label_name: str, tumor_label: int, num_refinements: int = 1, output_file: str = "mesh_refined.xdmf"):

    # 1. Carica mesh e label
    with dolfinx.io.XDMFFile(MPI.COMM_WORLD, xdmf_file, "r") as xdmf:
        mesh = xdmf.read_mesh(name="Grid")
        cell_labels = xdmf.read_meshtags(mesh, name="Grid")

    # Cicli di raffinamento
    for _ in range(num_refinements):
        # Crea un array booleano per contrassegnare le celle da raffinare
        markers = np.zeros(mesh.topology.index_map(mesh.topology.dim).size_local, dtype=bool)
        markers[cell_labels.indices[cell_labels.values == tumor_label]] = True
        marked_cells = np.where(markers)[0]
       
        mesh.topology.create_connectivity(mesh.topology.dim,1)

        c_to_e  = mesh.topology.connectivity(mesh.topology.dim,1)

        edges=[]
        for cell in marked_cells:
            for e in c_to_e.links(cell):
                edges.append(e)
        mesh, parent_cell, _ = refine(mesh, np.array(edges), partitioner=None, option=RefinementOption.parent_cell_and_facet)
        cell_labels = transfer_meshtag(cell_labels, mesh, parent_cell)


    # 3. Salva mesh raffinata
    with dolfinx.io.XDMFFile(MPI.COMM_WORLD, output_file, "w") as xdmf_out:
        xdmf_out.write_mesh(mesh)
        xdmf_out.write_meshtags(cell_labels, mesh.geometry)

    # Stampa informazioni sulla mesh finale
    num_cells = mesh.topology.index_map(mesh.topology.dim).size_global
    num_points = mesh.geometry.x.shape[0]
    print(f"Mesh raffinata salvata in: {output_file}")
    print(f"Numero di celle nella mesh finale: {num_cells}")
    print(f"Numero di punti nella mesh finale: {num_points}")
    
    return mesh


def refine_tumor_area(input_xdmf: str, output_xdmf: str, tag: int, num_refinements: int = 1, radius: float=2.0, step_refinement=True):
    with dolfinx.io.XDMFFile(MPI.COMM_WORLD, input_xdmf, "r") as infile:
        mesh = infile.read_mesh(name="Grid")
        subdomains = infile.read_meshtags(mesh, name="Grid")

        print("Original mesh #cells:", mesh.topology.index_map(mesh.topology.dim).size_local)

        mesh.topology.create_connectivity(mesh.topology.dim, 0)
        c_to_v = mesh.topology.connectivity(mesh.topology.dim, 0)

        tumor_cells = np.where(subdomains.values == tag)[0]
        # baricentri di tutte le celle con quel tag
        tumor_centers = np.array([
            mesh.geometry.x[c_to_v.links(cell)].mean(axis=0)
            for cell in tumor_cells
        ])

        # centro medio (baricentro del tumore)
        center = tumor_centers.mean(axis=0)
        print("Computed tumor center:", center)
    
        for _ in range(num_refinements):
            print(f"Refinement iteration with radius: {radius}")
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

            if step_refinement:
                radius *= 0.6
            
        print("Refined mesh #cells:", mesh.topology.index_map(mesh.topology.dim).size_local)

        # Scrivi la mesh e i subdomains raffinati in un nuovo file XDMF
        with dolfinx.io.XDMFFile(MPI.COMM_WORLD, output_xdmf, "w") as outfile:
            outfile.write_mesh(mesh)
            outfile.write_meshtags(subdomains, mesh.geometry)

        print(f"Refined mesh salvata in {output_xdmf}")