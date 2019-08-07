import pybamm
import numpy as np
from scipy import interpolate
import pandas as pd

# load model
model = pybamm.lithium_ion.DFN()

# create geometry
geometry = model.default_geometry

# load parameter values and process model and geometry
def OCV_cathode(soc):
    data = pd.read_csv("/home/ferranbrosa/PyBaMM/input/parameters/lithium-ion/nmc_LGM50_ocp_CC3.csv")
    interpolated_OCV_cathode = interpolate.interp1d(
        data.to_numpy()[:,0], 
        data.to_numpy()[:,1], 
        bounds_error=False, 
        fill_value="extrapolate"
    )
    return float(interpolated_OCV_cathode(soc))

def OCV_anode(sto):
    data = pd.read_csv("/home/ferranbrosa/PyBaMM/input/parameters/lithium-ion/graphite_LGM50_ocp_CC3.csv")
    interpolated_OCV_anode = interpolate.interp1d(
        data.to_numpy()[:,0], 
        data.to_numpy()[:,1], 
        bounds_error=False, 
        fill_value="extrapolate"
    )
    return float(interpolated_OCV_anode(sto))

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
    "Current function": pybamm.GetConstantCurrent(current=5)
})
param.process_model(model)
param.process_geometry(geometry)

# set mesh
mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)

# discretise model
disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
disc.process_model(model)

# solve model
t_eval = np.linspace(0, 0.2, 100)
solution = model.default_solver.solve(model, t_eval)

# plot
plot = pybamm.QuickPlot(model, mesh, solution)
plot.dynamic_plot()