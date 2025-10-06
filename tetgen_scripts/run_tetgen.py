import numpy as np
import subprocess
from mpi4py import MPI

def read_node_file(filename):
    with open(filename + ".node", "r") as f:
        lines = f.readlines()

    # Read number of nodes
    num_nodes = int(lines[0].split()[0])
    
    # Read node coordinates
    nodes = np.array([
        list(map(float, line.split()[1:4]))  # Extract x, y, z
        for line in lines[1:num_nodes + 1]
    ])

    return nodes

def read_ele_file(filename):
    with open(filename + ".ele", "r") as f:
        lines = f.readlines()

    # Read number of tetrahedra
    num_tetra = int(lines[0].split()[0])

    # Read tetrahedral elements
    elements = np.array([
        list(map(int, line.split()[1:5]))  # Extract 4 node indices
        for line in lines[1:num_tetra + 1]
    ])

    return elements

def read_mtr_file(filename):
    with open(filename + ".mtr", "r") as f:
        lines = f.readlines()

    # Read the number of elements
    num_values = int(lines[0].strip())

    # Read metric values
    values = np.array([float(line.strip()) for line in lines[1:num_values + 1]])

    return values

def adapt_mesh(filename):

    comm = MPI.COMM_WORLD
    rank = comm.rank

    if rank == 0:
        output = subprocess.run(["tetgen1.6.0/build/tetgen", "-rqm", filename], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        #subprocess.run(["rm", f"{filename}.mtr"])
        #subprocess.run(["rm", f"{filename}.edge"])
        #subprocess.run(["rm", f"{filename}.face"])
        if output.stderr:
            print("Tetgen Errors:")
            print(output.stderr)
        print(f"{filename}.mtr deleted")
    return 

def update_name(filename, new_filename):

    if MPI.COMM_WORLD.rank == 0:
        subprocess.run(["mv", f"{filename}.node", f"{new_filename}.node"])
        subprocess.run(["mv", f"{filename}.ele", f"{new_filename}.ele"])
    
# adapt_mesh("cube.2")





