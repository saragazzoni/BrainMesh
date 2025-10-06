import numpy as np
import ufl
import dolfinx
import dolfinx.fem as fem
from mpi4py import MPI
from basix.ufl import element
import dolfinx.fem.petsc

# compute the outward normal to the face defined by the three nodes p1,p2,p3
def compute_triangle_normal(p1, p2, p3, p4):
    """
    Compute the normal to a triangle given its nodes' coordinates.

    Parameters:
    p1, p2, p3: numpy arrays or lists
        Coordinates of the three nodes of the triangle.

    Returns:
    normal: numpy array
        The unit normal vector to the triangle.
    """
    # Convert points to numpy arrays
    p1 = np.array(p1)
    p2 = np.array(p2)
    p3 = np.array(p3)
    p4 = np.array(p4)
    # Compute edge vectors
    edge1 = -p2 + p1
    edge2 = p3 - p1
    comm = MPI.COMM_WORLD
    rank = comm.rank
    # Compute the cross product of the edge vectors
    normal = np.cross(edge1, edge2)
    edge_test = p4 - p1
    if np.dot(normal, edge_test) > 0:
        normal = -normal
    # Normalize the normal vector
    normal_length = np.linalg.norm(normal)
    if normal_length == 0:
        raise ValueError("The points do not form a valid triangle.")
        
    normal = normal * 0.5

    return normal

def compute_element_volume(mesh):

    elem = element("DG", mesh.basix_cell(), 0)
    Ve = dolfinx.fem.functionspace(mesh, elem)
    q_degree = 3
    vol = fem.Function(Ve)
    fem.petsc.assemble_vector(vol.x.petsc_vec, fem.form(
        1*ufl.TestFunction(Ve)*ufl.dx(metadata={"quadrature_degree": q_degree})))
    
    vol.x.scatter_forward()

    return vol.x.array

def compute_face_area(A,B,C):

    A = np.array(A)
    B = np.array(B)
    C = np.array(C)

    # Vettori AB e AC
    AB = B - A
    AC = C - A

    # Calcoliamo il prodotto vettoriale tra AB e AC
    cross_product = np.cross(AB, AC)

    # Calcoliamo la norma del prodotto vettoriale
    area = 0.5 * np.linalg.norm(cross_product)
    
    return area