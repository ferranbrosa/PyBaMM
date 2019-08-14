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
# interpolated_OCV_cathode = interpolate.PchipInterpolator(
#     data_cathode.to_numpy()[:,0], 
#     data_cathode.to_numpy()[:,1], 
#     extrapolate=True
# )
data_anode = pd.read_csv(
    pybamm.root_dir() + "/input/parameters/lithium-ion/graphite_LGM50_ocp_CC3.csv"
)
interpolated_OCV_anode = interpolate.interp1d(
    data_anode.to_numpy()[:,0], 
    data_anode.to_numpy()[:,1], 
    bounds_error=False, 
    fill_value="extrapolate"
)
# interpolated_OCV_anode = interpolate.PchipInterpolator(
#     data_anode.to_numpy()[:,0], 
#     data_anode.to_numpy()[:,1], 
#     extrapolate=True
# )

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


# param = model.default_parameter_values

param = pybamm.ParameterValues("input/parameters/lithium-ion/LGM50_parameters.csv")
param.update({
    "Electrolyte conductivity": "electrolyte_conductivity_Petibon2016.py",
    "Electrolyte diffusivity": "electrolyte_diffusivity_Stewart2008.py",
    # "Electrolyte conductivity": "electrolyte_conductivity_Capiglia1999.py",
    # "Electrolyte diffusivity": "electrolyte_diffusivity_Capiglia1999.py",
    "Negative electrode OCV": OCV_anode,
    "Positive electrode OCV": OCV_cathode,
    "Negative electrode diffusivity": "graphite_LGM50_diffusivity_CC3.py",
    "Positive electrode diffusivity": "nmc_LGM50_diffusivity_CC3.py",
    "Negative electrode OCV entropic change": "graphite_LGM50_entropic_change.py",
    "Positive electrode OCV entropic change": "nmc_LGM50_entropic_change.py",
    "Negative electrode reaction rate": "graphite_LGM50_electrolyte_reaction_rate.py",
    "Positive electrode reaction rate": "nmc_LGM50_electrolyte_reaction_rate.py",
    "Typical current [A]": 5,
    "Current function": pybamm.GetConstantCurrent()
})

cspmax = 48000
csnmax = 32000

param["Initial concentration in negative electrode [mol.m-3]"] = 0.98*csnmax
param["Initial concentration in positive electrode [mol.m-3]"] = 0.05*cspmax
param["Maximum concentration in negative electrode [mol.m-3]"] = csnmax
param["Maximum concentration in positive electrode [mol.m-3]"] = cspmax
param["Negative electrode reference exchange-current density [A.m-2(m3.mol)1.5]"] = 1.4E-6
param["Positive electrode reference exchange-current density [A.m-2(m3.mol)1.5]"] = 1.4E-6
param["Lower voltage cut-off [V]"] = 2.5
param["Upper voltage cut-off [V]"] = 4.4

param.process_model(model)
param.process_geometry(geometry)

# set mesh
mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)

# discretise model
disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
disc.process_model(model)

# solve model discharge
#model.use_jacobian = False
t_eval = np.linspace(0, 0.5, 2E3)
solution = model.default_solver.solve(model, t_eval)

# process variables discharge (the ones that use current)
voltage = pybamm.ProcessedVariable(
    model.variables['Terminal voltage [V]'], solution.t, solution.y, mesh=mesh
)
Ueq = pybamm.ProcessedVariable(
    model.variables['X-averaged battery open circuit voltage [V]'], solution.t, solution.y, mesh=mesh
)
etar = pybamm.ProcessedVariable(
    model.variables['X-averaged battery reaction overpotential [V]'], solution.t, solution.y, mesh=mesh
)
etac = pybamm.ProcessedVariable(
    model.variables['X-averaged battery concentration overpotential [V]'], solution.t, solution.y, mesh=mesh
)
Dphis = pybamm.ProcessedVariable(
    model.variables['X-averaged battery solid phase ohmic losses [V]'], solution.t, solution.y, mesh=mesh
)
Dphie = pybamm.ProcessedVariable(
    model.variables['X-averaged battery electrolyte ohmic losses [V]'], solution.t, solution.y, mesh=mesh
)

# solve model rest
param["Current function"] = pybamm.GetConstantCurrent(current=pybamm.Scalar(0))
param.update_model(model, disc)
model.concatenated_initial_conditions = solution.y[:, -1][:, np.newaxis]

t_eval2 = np.linspace(solution.t[-1], solution.t[-1] + 0.65, 1000)
solution2 = model.default_solver.solve(model,t_eval2)

# quick plot
# plot = pybamm.QuickPlot(model, mesh, solution)
# plot.dynamic_plot()

# plot = pybamm.QuickPlot(model, mesh, solution2)
# plot.dynamic_plot()

# other plots
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
c_s_n_nd2 = pybamm.ProcessedVariable(
    model.variables['Negative particle surface concentration'], solution2.t, solution2.y, mesh=mesh
)
x_averaged_c_s_n_nd = pybamm.ProcessedVariable(
    model.variables['X-averaged negative particle surface concentration'], solution.t, solution.y, mesh=mesh
)
c_s_p_nd = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration'], solution.t, solution.y, mesh=mesh
)
c_s_p_nd2 = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration'], solution2.t, solution2.y, mesh=mesh
)
x_averaged_c_s_p_nd = pybamm.ProcessedVariable(
    model.variables['X-averaged positive particle surface concentration'], solution.t, solution.y, mesh=mesh
)
time = pybamm.ProcessedVariable(
    model.variables['Time [h]'], solution.t, solution.y, mesh=mesh
)
time2 = pybamm.ProcessedVariable(
    model.variables['Time [h]'], solution2.t, solution2.y, mesh=mesh
)

data_experiments = pd.read_csv(
        pybamm.root_dir() + "/results/LGM50/data/data1C.csv"
).to_numpy()

plt.figure(2)
plt.fill_between(
    data_experiments[:,0]/3600,
    data_experiments[:,1] + data_experiments[:,2],
    data_experiments[:,1] - data_experiments[:,2],
    color="#808080",
    label="experiments"
)
plt.plot(time(solution.t),voltage(solution.t),color="C1",label="model")
plt.plot(time2(solution2.t),voltage2(solution2.t),color="C1")
plt.plot(
    time(solution.t),
    OCV_cathode(c_s_p_nd(solution.t,x=1)) - OCV_anode(c_s_n_nd(solution.t,x=0)),
    color="black",linestyle="--",
    label="OCV"
)
plt.plot(
    time2(solution2.t),
    OCV_cathode(c_s_p_nd2(solution2.t,x=1)) - OCV_anode(c_s_n_nd2(solution2.t,x=0)),
    color="black",linestyle="--"
)
plt.xlabel("t [h]")
plt.ylabel("Voltage [V]")
plt.legend()

plt.figure(3)
plt.plot(time(solution.t),c_s_p_nd(solution.t,x=1),color="C1",label="positive")
plt.plot(time2(solution2.t),c_s_p_nd2(solution2.t,x=1),color="C1")
plt.plot(time(solution.t),c_s_n_nd(solution.t,x=0),color="C0",label="negative")
plt.plot(time2(solution2.t),c_s_n_nd2(solution2.t,x=0),color="C0")
plt.xlabel("t [h]")
plt.ylabel("Concentration surface")
plt.legend()

plt.figure(4)
plt.plot(time(solution.t),voltage(solution.t),color="C0")
plt.plot(time2(solution2.t),voltage2(solution2.t),color="C0")
plt.xlabel("t [h]")
plt.ylabel("Voltage [V]")

plt.figure(5)
plt.plot(np.linspace(0,1,1E4),OCV_cathode(np.linspace(0,1,1E4)),color="C0")
plt.plot(np.linspace(0,1,1E4),OCV_anode(np.linspace(0,1,1E4)),color="C1")
plt.xlabel("SoC")
plt.ylabel("OCP [V]")
plt.legend(("positive","negative"))

plt.figure(6)
plt.plot(solution.t,Ueq(solution.t),label="OCV")
plt.plot(solution.t,etar(solution.t),label="reaction op")
plt.plot(solution.t,etac(solution.t),label="concentration op")
plt.plot(solution.t,Dphis(solution.t),label="solid Ohmic")
plt.plot(solution.t,Dphie(solution.t),label="electrolyte Ohmic")
plt.xlabel("t")
plt.ylabel("Voltages [V]")
plt.legend()

plt.show()