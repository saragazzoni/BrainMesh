import dolfinx.fem
import dolfinx.mesh
import numpy as np
from mpi4py import MPI
from ufl.tensors import as_matrix
from basix.ufl import element, mixed_element
import meshio

paz ="paz1"
date = "2018-02-06"
folder_path = f"Data/{paz}/{date}/dti"
coef = 1e6
dtiname ="brainref2"
folder_path_labels = f"Data/{paz}/{date}/mesh"
meshname = "brain_tumor_centerref2"
tumor_tag = 2

# get diffusion tensor values from xmdf files
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dxx_{dtiname}.xdmf", "r") as xdmf:
    mesh=xdmf.read_mesh(name="Grid")
    tag11=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dxy_{dtiname}.xdmf", "r") as xdmf:
    tag12=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dxz_{dtiname}.xdmf", "r") as xdmf:
    tag13=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dyy_{dtiname}.xdmf", "r") as xdmf:
    tag22=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dyz_{dtiname}.xdmf", "r") as xdmf:
    tag23=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path}/Mesh_Dzz_{dtiname}.xdmf", "r") as xdmf:
    tag33=xdmf.read_meshtags(mesh,"Grid")
with dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{folder_path_labels}/{meshname}.xdmf", "r") as xdmf:
    labels = xdmf.read_meshtags(mesh,"Grid")

n_cells = mesh.topology.index_map(mesh.topology.dim).size_local
print(f"Processo n_cells = {n_cells}")

conversion_factor = 86400
valuesD11=tag11.values/coef*conversion_factor
valuesD12=tag12.values/coef*conversion_factor
valuesD13=tag13.values/coef*conversion_factor
valuesD22=tag22.values/coef*conversion_factor
valuesD23=tag23.values/coef*conversion_factor
valuesD33=tag33.values/coef*conversion_factor

# compute eigenvalues and eigenvectors of D for each cell

ncells = len(valuesD11)
lambdas = np.zeros((ncells, 3))
v = np.zeros((ncells, 3, 3))
for i in range(ncells):
    matrixD = np.array([[valuesD11[i] , valuesD12[i], valuesD13[i] ],
                        [valuesD12[i] , valuesD22[i], valuesD23[i]],
                        [valuesD13[i] , valuesD23[i], valuesD33[i] ]])
    
    eigenval, eigenvec = np.linalg.eigh(matrixD)
    lambdas[i, :] = eigenval
    v[i, :, :] = eigenvec

# D_reconstructed = np.zeros((3, 3))
# # Somma i contributi di ogni autovalore-autovettore
# for i in range(3):
#     D_reconstructed += lambdas[0,i] * np.outer(v[0,:, i], v[0,:,i])
# print(D_reconstructed)

cl = (lambdas[:, 2] - lambdas[:, 1]) / (lambdas[:, 0] + lambdas[:, 1] + lambdas[:, 2])
cp = 2*(lambdas[:, 1] - lambdas[:, 0]) / (lambdas[:, 0] + lambdas[:, 1] + lambdas[:, 2])
cs = 3*lambdas[:, 0] / (lambdas[:, 0] + lambdas[:, 1] + lambdas[:, 2])
cvec = np.array([cl, cp, cs])

r = 3
A = np.array([[r, r, 1], [1, r, 1], [1, 1, 1]])
avec = np.zeros_like(cvec)
matrixT = np.zeros((3, 3, ncells))
That = np.zeros((3, 3, ncells))
for i in range(ncells):
    avec[:,i] = np.dot(A,cvec[:,i])
    That = avec[0,i]*lambdas[i,2]*np.outer(v[i,:,2], v[i,:,2]) + avec[1,i]*lambdas[i,1]*np.outer(v[i,:,1], v[i,:,1]) + avec[2,i]*lambdas[i,0]*np.outer(v[i,:,0], v[i,:,0])
    trT = avec[0,i]*lambdas[i,2] + avec[1,i]*lambdas[i,1] + avec[2,i]*lambdas[i,0]
    matrixT[:,:,i] = 3*That/trT
    matrixT[:,:,i] = np.nan_to_num(matrixT[:,:,i], nan=0)

# Get indices of tumor cells
cell_indices = np.where(labels.values == tumor_tag)[0]

# # get indeces of cells in a sphere of a specific radius centered in a point
# center = np.array([25.0, 4.0, 30.0])
# threshold = 10.0
# cell_indices = []
# cell_midpoints = dolfinx.mesh.compute_midpoints(mesh, 3, np.arange(n_cells, dtype=np.int32))
# for i,midpoint in enumerate(cell_midpoints):
#     distance = np.linalg.norm(midpoint - center)
#     if distance < threshold:
#         cell_indices.append(i)


lambda_tumor = np.zeros(3)
for i in range(3):
    lambda_tumor[i] = np.mean(lambdas[cell_indices,i])
print(f"lambda_tumor = {lambda_tumor}")
cl_tumor = (lambda_tumor[2] - lambda_tumor[1]) / (lambda_tumor[0] + lambda_tumor[1] + lambda_tumor[2])
cp_tumor = 2*(lambda_tumor[1] - lambda_tumor[0]) / (lambda_tumor[0] + lambda_tumor[1] + lambda_tumor[2])
cs_tumor = 3*lambda_tumor[0] / (lambda_tumor[0] + lambda_tumor[1] + lambda_tumor[2])
print(f"cl = {cl_tumor}, cp = {cp_tumor}, cs = {cs_tumor}")


# Save tensor T in xdmf file
# elem = element("DG", mesh.basix_cell(), 0)
# PD = mixed_element([elem,elem,elem,elem,elem,elem])
# MD = dolfinx.fem.functionspace(mesh,PD)
# Pd11, Pd11_to_P1 = MD.sub(0).collapse()
# Pd12, Pd12_to_P1 = MD.sub(1).collapse()
# Pd13, Pd13_to_P1 = MD.sub(2).collapse()
# Pd22, Pd22_to_P1 = MD.sub(3).collapse()
# Pd23, Pd23_to_P1 = MD.sub(4).collapse()
# Pd22, Pd33_to_P1 = MD.sub(5).collapse()
# D = dolfinx.fem.Function(MD)
# D11,D12,D13,D22,D23,D33=D.split()
# T = dolfinx.fem.Function(MD)

# D.x.array[Pd11_to_P1]=valuesD11
# D.x.array[Pd12_to_P1]=valuesD12
# D.x.array[Pd13_to_P1]=valuesD13
# D.x.array[Pd22_to_P1]=valuesD22
# D.x.array[Pd23_to_P1]=valuesD23
# D.x.array[Pd33_to_P1]=valuesD33

# T.x.array[Pd11_to_P1]=matrixT[0,0,:]
# T.x.array[Pd12_to_P1]=matrixT[0,1,:]
# T.x.array[Pd13_to_P1]=matrixT[0,2,:]
# T.x.array[Pd22_to_P1]=matrixT[1,1,:]
# T.x.array[Pd23_to_P1]=matrixT[1,2,:]
# T.x.array[Pd33_to_P1]=matrixT[2,2,:]
# T11,T12,T13,T22,T23,T33=T.split()
# tensor_folder = "dti_scripts/tensors"
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D11.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D11)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D12.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D12)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D13.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D13)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D22.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D22)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D23.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D23)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/D33.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(D33)

# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T11.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T11)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T12.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T12)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T13.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T13)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T22.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T22)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T23.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T23)
# fd = dolfinx.io.XDMFFile(MPI.COMM_WORLD, f"{tensor_folder}/T33.xdmf", "w")
# fd.write_mesh(mesh)
# fd.write_function(T33)

