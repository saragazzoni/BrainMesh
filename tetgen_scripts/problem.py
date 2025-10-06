import typing
import dolfinx.fem
from basix.ufl import element
from io_manager import IOManager
from mesh_adapter import MeshAdapter 
import json


class Problem(object):

    def __init__(self, parser) -> None:

        args = parser.parse_args()

        # Read parameters from JSON file
        with open(args.name_file, "r") as f:
            config = json.load(f)
        parameters = config["parameters"]

        output_dir = args.output_dir


        save_sol = parameters["Save_solution_xdmf"]["value"]

        self.save_mesh_xdmf = parameters["Save_mesh_xdmf"]["value"]
        self.filename = parameters["mesh_filename"]["value"]
        self.h_ub = parameters["h_ub"]["value"]
        self.h_lb = parameters["h_lb"]["value"]
        self.sigma = parameters["sigma"]["value"]
        self.io_manager = IOManager(output_dir, plot=save_sol)
        self.set_space(self.filename)

    def set_space(self, mesh_filename, timestep=0, iteration=0):
        
        self.mesh = self.io_manager.import_mesh(mesh_filename, timestep, iteration)
        elem = element("Lagrange", self.mesh.basix_cell(), 1)
        V_phi = dolfinx.fem.functionspace(self.mesh, elem)
        V_mu = dolfinx.fem.functionspace(self.mesh, elem)
        V_n = dolfinx.fem.functionspace(self.mesh, elem) 

        self.Vh0 = dolfinx.fem.functionspace(self.mesh, ("DG", 0))
        self._V = (V_phi,V_mu,V_n)
        self._function_space_phi=V_phi
        self._function_space_mu=V_mu
        self._function_space_n=V_n

    def refine_mesh(self) -> typing.Tuple[dolfinx.fem.Function, dolfinx.fem.Function,dolfinx.fem.Function]:

        filename = self.filename

        mesh_adapter = MeshAdapter(self.mesh, self._function_space_phi) 
        mesh_adapter.compute_size(h_ub=self.h_ub, h_lb=self.h_lb, sigma=self.sigma)
        mesh_adapter.compute_metric(file_name=filename, output_manager=self.io_manager)
        self.io_manager.write_tet_mesh(filename)
        mesh_adapter.create_mesh()
        if self.save_mesh_xdmf:
            self.io_manager.create_xdmf(filename)
        




