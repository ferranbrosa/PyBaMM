import pybamm
import numpy as np
import matplotlib.pyplot as plt

## Define model

# 1. Initialise an empty model
model = pybamm.BaseModel()

# 2. Define your variables and parameters
R = pybamm.Parameter('Particle radius [m]')
D = pybamm.Parameter('Diffusion coefficient [m2.s-1]')
j = pybamm.Parameter('Interfacial current density [A.m-2]')
F = pybamm.Parameter('Faraday constant [C.mol-1]')
c0 = pybamm.Parameter('Initial concentration [mol.m-3]')

c = pybamm.Variable('Concentration', domain = ['negative particle'])
N = - D/R * pybamm.grad(c)

# 3. State the governing equations
model.rhs = {c: - 1/R * pybamm.div(N)}

# 4. State boundary conditions
model.boundary_conditions = {c: {'left': (0 , 'Neumann'), 'right': ( -j*R/(F*D*c0), 'Neumann')}}

# 5. State initial conditions
model.initial_conditions = {c: pybamm.Scalar(1)}

# 6. State output variables
model.variables = {
    'Concentration': c, 
    'Surface concentration': pybamm.surf(c), 
    'Flux': N, 
    'Concentration [mol.m-3]': c*c0, 
    'Surface concentration [mol.m-3]': c0*pybamm.surf(c), 
    'Flux [mol.m-2.s-1]': N*c0/R
}

## Solve model

# Define geometry
r = pybamm.SpatialVariable('r', domain = ['negative particle'], coord_sys = 'spherical polar')
geometry = {'negative particle': {'primary': {r: {'min': pybamm.Scalar(0), 'max': pybamm.Scalar(1)}}}}

# Define parameters
param = pybamm.ParameterValues(
    {
        'Particle radius [m]': 10e-6, 
        'Diffusion coefficient [m2.s-1]': 3.9e-14, 
        'Interfacial current density [A.m-2]': 1.4, 
        'Faraday constant [C.mol-1]': 96485, 
        'Initial concentration [mol.m-3]': 2.5e4
    }
)

param.process_geometry(geometry)
param.process_model(model)

# Define mesh
submesh_types = {'negative particle': pybamm.Uniform1DSubMesh}
var_pts = {r: 20}
mesh = pybamm.Mesh(geometry, submesh_types, var_pts)

# Define discretisation
spatial_methods = {'negative particle': pybamm.FiniteVolume}
disc = pybamm.Discretisation(mesh, spatial_methods)
disc.process_model(model)

# Define solver
solver = pybamm.ScipySolver()
t = np.linspace(0,3600,900)
solution = solver.solve(model, t)

# Postprocessing
c_surf = pybamm.ProcessedVariable(model.variables['Surface concentration [mol.m-3]'], solution.t, solution.y, mesh)

plt.plot(solution.t, c_surf(solution.t))
plt.xlabel("Time [s]")
plt.ylabel("Surface concentration [mol.m-3]")
plt.show()