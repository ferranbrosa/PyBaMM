import pybamm
import numpy as np
from scipy import interpolate
import pandas as pd
import matplotlib.pyplot as plt

pybamm.set_logging_level("INFO")

# load model
model = pybamm.lithium_ion.SPMe()

# create geometry
geometry = model.default_geometry

# load parameter values and process model and geometry
data_cathode = pd.read_csv(
        pybamm.root_dir() + "/input/parameters/lithium-ion/nmc_LGM50_ocp_CC3.csv"
)
interpolated_OCV_cathode = interpolate.interp1d(
    data_cathode.to_numpy()[:,0], 
    data_cathode.to_numpy()[:,1], 
    bounds_error=False, 
    fill_value="extrapolate"
)
data_anode = pd.read_csv(
    pybamm.root_dir() + "/input/parameters/lithium-ion/graphite_LGM50_ocp_CC3.csv"
)
interpolated_OCV_anode = interpolate.interp1d(
    data_anode.to_numpy()[:,0], 
    data_anode.to_numpy()[:,1], 
    bounds_error=False, 
    fill_value="extrapolate"
)

def OCV_cathode(sto):
    out = interpolated_OCV_cathode(sto)
    if np.size(out) == 1:
        out = np.array([out])[0]
    return out

def OCV_anode(sto):
    out = interpolated_OCV_anode(sto)
    if np.size(out) == 1:
        out = np.array([out])[0]
    return out

param = pybamm.ParameterValues("input/parameters/lithium-ion/LGM50_parameters.csv")
param.update({
    "Electrolyte conductivity": "electrolyte_conductivity_Petibon2016.py",
    "Electrolyte diffusivity": "electrolyte_diffusivity_Stewart2008.py",
    "Negative electrode OCV": OCV_anode,
    "Positive electrode OCV": OCV_cathode,
    "Negative electrode diffusivity": "graphite_LGM50_diffusivity_CC3.py",
    "Positive electrode diffusivity": "nmc_LGM50_diffusivity_CC3.py",
    "Negative electrode OCV entropic change": "graphite_entropic_change_Moura.py",
    "Positive electrode OCV entropic change": "lico2_entropic_change_Moura.py",
    "Negative electrode reaction rate": "graphite_electrolyte_reaction_rate.py",
    "Positive electrode reaction rate": "lico2_electrolyte_reaction_rate.py",
    "Typical current [A]": 5,
    "Current function": pybamm.GetConstantCurrent()
})
param["Initial concentration in negative electrode [mol.m-3]"] = 10000   #19155
param["Initial concentration in positive electrode [mol.m-3]"] = 1120
param["Maximum concentration in negative electrode [mol.m-3]"] = 29334
param["Maximum concentration in positive electrode [mol.m-3]"] = 30800

param.process_model(model)
param.process_geometry(geometry)

# set mesh
mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)

# discretise model
disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
disc.process_model(model)

# solve model
model.use_jacobian = False
t_eval = np.linspace(0, 0.1, 1000)
solution = model.default_solver.solve(model, t_eval)

param["Current function"] = pybamm.GetConstantCurrent(current=0)
model.concatenated_initial_conditions = solution.y[:,-1][:,np.newaxis]
#param.update_model(model, disc)
param.process_model(model)
disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
disc.process_model(model)
t_eval2 = np.linspace(solution.t[-1],solution.t[-1] + 0.1,1000)
solution2 = model.default_solver.solve(model,t_eval2)

# quick plot
plot = pybamm.QuickPlot(model, mesh, solution)
plot.dynamic_plot()

# other plots
voltage = pybamm.ProcessedVariable(
    model.variables['Terminal voltage [V]'], solution.t, solution.y, mesh=mesh
)
voltage2 = pybamm.ProcessedVariable(
    model.variables['Terminal voltage [V]'], solution2.t, solution2.y, mesh=mesh
)
c_s_n_surf = pybamm.ProcessedVariable(
    model.variables['Negative particle surface concentration [mol.m-3]'], solution.t, solution.y, mesh=mesh
)
c_s_p_surf = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration [mol.m-3]'], solution.t, solution.y, mesh=mesh
)
c_s_n_nd = pybamm.ProcessedVariable(
    model.variables['Negative particle surface concentration'], solution.t, solution.y, mesh=mesh
)
c_s_p_nd = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration'], solution.t, solution.y, mesh=mesh
)

plt.figure(2)
plt.plot(solution.t,voltage(solution.t))
plt.plot(solution2.t,voltage2(solution2.t))
plt.show()