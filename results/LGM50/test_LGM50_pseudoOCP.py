import pybamm
import numpy as np
from scipy import interpolate
import pandas as pd
import matplotlib.pyplot as plt
from autograd.extend import primitive, defvjp

pybamm.set_logging_level("INFO")

# load model
model = pybamm.lithium_ion.SPMe()

# create geometry
geometry = model.default_geometry

# define OCP functions
data_cathode = pd.read_csv(
    pybamm.root_dir() +
    "/results/LGM50/data/nmc_LGM50_pseudoocp_Chen2020.csv",
    comment="#", skip_blank_lines=True
)

interpolated_OCP_cathode = interpolate.PchipInterpolator(
    data_cathode.to_numpy()[:, 0],
    data_cathode.to_numpy()[:, 1],
    extrapolate=True
)

data_anode = pd.read_csv(
    pybamm.root_dir() +
    "/results/LGM50/data/graphite_LGM50_pseudoocp_Chen2020.csv",
    comment="#", skip_blank_lines=True
)

interpolated_OCP_anode = interpolate.PchipInterpolator(
    data_anode.to_numpy()[:, 0],
    data_anode.to_numpy()[:, 1],
    extrapolate=True
)

dOCP_cathode = interpolated_OCP_cathode.derivative()
dOCP_anode = interpolated_OCP_anode.derivative()


@primitive
def OCP_cathode(sto):
    b = - 0.012 / 1.5
    out = interpolated_OCP_cathode(sto + b)
    if np.size(out) == 1:
        out = np.array([out])[0]
    return out


@primitive
def OCP_anode(sto):
    b = - 0.05
    out = interpolated_OCP_anode(sto + b)
    if np.size(out) == 1:
        out = np.array([out])[0]
    return out


def OCP_cathode_vjp(ans, sto):
    sto_shape = sto.shape
    return lambda g: np.full(sto_shape, g) * dOCP_cathode(sto)


def OCP_anode_vjp(ans, sto):
    sto_shape = sto.shape
    return lambda g: np.full(sto_shape, g) * dOCP_anode(sto)


defvjp(OCP_cathode, OCP_cathode_vjp)
defvjp(OCP_anode, OCP_anode_vjp)

# load parameter values and process model and geometry
param = pybamm.ParameterValues(
    chemistry={
        "chemistry": "lithium-ion",
        "cell": "LGM50_Chen2020",
        "anode": "graphite_Chen2020",
        "separator": "separator_Chen2020",
        "cathode": "nmc_Chen2020",
        "electrolyte": "lipf6_Nyman2008",
        "experiment": "1C_discharge_from_full_Chen2020",
    }
)
param.update({
    "Negative electrode OCP [V]": OCP_anode,
    "Positive electrode OCP [V]": OCP_cathode,
})

data_experiments = pd.read_csv(
    pybamm.root_dir() + "/results/LGM50/data/data1C_rest.csv"
).to_numpy()

cspmax = 38000 * 1.1
csnmax = 29000

param["Initial concentration in negative electrode [mol.m-3]"] = 0.9 * csnmax
param["Initial concentration in positive electrode [mol.m-3]"] = 0.011 * cspmax
param["Maximum concentration in negative electrode [mol.m-3]"] = csnmax
param["Maximum concentration in positive electrode [mol.m-3]"] = cspmax
param["Lower voltage cut-off [V]"] = 2.5
param["Upper voltage cut-off [V]"] = 4.4
param["Current function"] = pybamm.GetConstantCurrent(current=pybamm.Scalar(5))

param.process_model(model)
param.process_geometry(geometry)

tau = param.process_symbol(pybamm.standard_parameters_lithium_ion.tau_discharge)

# set mesh
mesh = pybamm.Mesh(geometry, model.default_submesh_types, model.default_var_pts)

# discretise model
disc = pybamm.Discretisation(mesh, model.default_spatial_methods)
disc.process_model(model)

# solve model discharge
# model.use_jacobian = False
t_eval = np.linspace(0, 3 * 3600 / tau.evaluate(), 1000)
solver = pybamm.ScikitsOdeSolver()
# solver = pybamm.ScikitsDaeSolver()
solution = solver.solve(model, t_eval)

# process variables discharge (the ones that use current)
voltage = pybamm.ProcessedVariable(
    model.variables['Terminal voltage [V]'], solution.t, solution.y, mesh=mesh
)
phi_p = pybamm.ProcessedVariable(
    model.variables['Positive electrode potential [V]'], solution.t, solution.y, mesh=mesh
)
phi_n = pybamm.ProcessedVariable(
    model.variables['Negative electrode potential [V]'], solution.t, solution.y, mesh=mesh
)
phi_e = pybamm.ProcessedVariable(
    model.variables['Electrolyte potential [V]'], solution.t, solution.y, mesh=mesh
)


# Ueq = pybamm.ProcessedVariable(
#     model.variables['X-averaged battery open circuit voltage [V]'], solution.t,
#     solution.y, mesh=mesh
# )
etar = pybamm.ProcessedVariable(
    model.variables['X-averaged battery reaction overpotential [V]'], solution.t,
    solution.y, mesh=mesh
)
etap = pybamm.ProcessedVariable(
    model.variables['X-averaged positive electrode reaction overpotential [V]'], solution.t,
    solution.y, mesh=mesh
)
etan = pybamm.ProcessedVariable(
    model.variables['X-averaged negative electrode reaction overpotential [V]'], solution.t,
    solution.y, mesh=mesh
)
# etac = pybamm.ProcessedVariable(
#     model.variables['X-averaged battery concentration overpotential [V]'], solution.t,
#     solution.y, mesh=mesh
# )
# Dphis = pybamm.ProcessedVariable(
#     model.variables['X-averaged battery solid phase ohmic losses [V]'], solution.t,
#     solution.y, mesh=mesh
# )
# Dphie = pybamm.ProcessedVariable(
#     model.variables['X-averaged battery electrolyte ohmic losses [V]'], solution.t,
#     solution.y, mesh=mesh
# )

# solve model rest
param["Current function"] = pybamm.GetConstantCurrent(current=pybamm.Scalar(0))
param.update_model(model, disc)
model.concatenated_initial_conditions = solution.y_event
t_eval2 = np.linspace(
    solution.t_event[0], solution.t_event[0] + 2 * 3600 / tau.evaluate(), 200
)
solution2 = solver.solve(model, t_eval2)

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
    model.variables['Negative particle surface concentration [mol.m-3]'], solution.t,
    solution.y, mesh=mesh
)
c_s_p_surf = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration [mol.m-3]'], solution.t,
    solution.y, mesh=mesh
)
c_s_n_nd = pybamm.ProcessedVariable(
    model.variables['Negative particle surface concentration'], solution.t, solution.y,
    mesh=mesh
)
c_s_n_nd2 = pybamm.ProcessedVariable(
    model.variables['Negative particle surface concentration'], solution2.t,
    solution2.y, mesh=mesh
)
# x_averaged_c_s_n_nd = pybamm.ProcessedVariable(
#     model.variables['X-averaged negative particle surface concentration'], solution.t,
#     solution.y, mesh=mesh
# )
c_s_p_nd = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration'], solution.t, solution.y,
    mesh=mesh
)
c_s_p_nd2 = pybamm.ProcessedVariable(
    model.variables['Positive particle surface concentration'], solution2.t,
    solution2.y, mesh=mesh
)
# x_averaged_c_s_p_nd = pybamm.ProcessedVariable(
#     model.variables['X-averaged positive particle surface concentration'], solution.t,
#     solution.y, mesh=mesh
# )
time = pybamm.ProcessedVariable(
    model.variables['Time [h]'], solution.t, solution.y, mesh=mesh
)
time2 = pybamm.ProcessedVariable(
    model.variables['Time [h]'], solution2.t, solution2.y, mesh=mesh
)

phi_p2 = pybamm.ProcessedVariable(
    model.variables['Positive electrode potential [V]'], solution2.t, solution2.y, mesh=mesh
)
phi_n2 = pybamm.ProcessedVariable(
    model.variables['Negative electrode potential [V]'], solution2.t, solution2.y, mesh=mesh
)
phi_e2 = pybamm.ProcessedVariable(
    model.variables['Electrolyte potential [V]'], solution2.t, solution2.y, mesh=mesh
)

data_discharge = np.transpose(np.vstack((
    time(solution.t), voltage(solution.t), c_s_p_nd(solution.t, x=1), c_s_n_nd(solution.t, x=0), etap(solution.t), etan(solution.t)
)))
data_rest = np.transpose(np.vstack((
    time2(solution2.t), voltage2(solution2.t), c_s_p_nd2(solution2.t, x=1), c_s_n_nd2(solution2.t, x=0), 0 * time2(solution2.t), 0 * time2(solution2.t)
)))
data_full = np.vstack((data_discharge, data_rest))
# np.savetxt(
#     "results/LGM50/data/data_SPMe.csv",
#     data_full,
#     delimiter=",",
#     header="Time [h], Voltage[V], Concentration Positive Electrode (ND), Concentration Negative Electrode (ND), Overpotential Positive Electrode [V], Overpotential Negative Electrode[V]"
# )

# plt.figure(1)
# plt.plot(
#     data_full[:, 0], data_full[:,1]
# )
# plt.xlabel("t [h]")
# plt.ylabel("Voltage [V]")

interpolated_voltage = interpolate.PchipInterpolator(
    data_full[:, 0],
    data_full[:, 1],
    extrapolate=True
)

error = np.absolute(
    interpolated_voltage(data_experiments[60:-1, 0] / 3600) - data_experiments[60:-1, 1]
)

rmse = np.sqrt(np.mean(np.square(error)))

print("RMSE: ", rmse)

plt.figure(10)
plt.plot(data_experiments[60:-1, 0] / 3600, error)
plt.xlabel("t [h]")
plt.ylabel("Voltage error [V]")

plt.figure(2)
plt.fill_between(
    data_experiments[:, 0] / 3600,
    data_experiments[:, 1] + data_experiments[:, 2],
    data_experiments[:, 1] - data_experiments[:, 2],
    color="#808080",
    label="experiments"
)
plt.plot(
    np.array([data_experiments[0, 0] / 3600, 0]),
    (OCP_cathode(c_s_p_nd(0, x=1)) - OCP_anode(c_s_n_nd(0, x=0))) * np.ones(2),
    color="C1"
)
plt.plot(time(solution.t), voltage(solution.t), color="C1", label="model")
plt.plot(time2(solution2.t), voltage2(solution2.t), color="C1")
plt.plot(
    time(solution.t),
    OCP_cathode(c_s_p_nd(solution.t, x=1)) - OCP_anode(c_s_n_nd(solution.t, x=0)),
    color="black", linestyle="--", label="OCV"
)
plt.plot(
    time2(solution2.t),
    OCP_cathode(c_s_p_nd2(solution2.t, x=1)) - OCP_anode(c_s_n_nd2(solution2.t, x=0)),
    color="black", linestyle="--"
)
plt.xlabel("t [h]")
plt.ylabel("Voltage [V]")
plt.legend()

plt.figure(3)
plt.plot(time(solution.t), c_s_p_nd(solution.t, x=1), color="C1", label="positive")
plt.plot(time2(solution2.t), c_s_p_nd2(solution2.t, x=1), color="C1")
plt.plot(time(solution.t), c_s_n_nd(solution.t, x=0), color="C0", label="negative")
plt.plot(time2(solution2.t), c_s_n_nd2(solution2.t, x=0), color="C0")
plt.xlabel("t [h]")
plt.ylabel("Concentration surface")
plt.legend()

plt.figure(4)
plt.plot(
    time(solution.t), phi_p(solution.t, x=1) - phi_e(solution.t, x=1),
    color="C1", label="positive"
)
plt.plot(
    time2(solution2.t), phi_p2(solution2.t, x=1) - phi_e2(solution2.t, x=1), color="C1"
)
plt.plot(
    time(solution.t), phi_n(solution.t, x=0) - phi_e(solution.t, x=0),
    color="C0", label="negative"
)
plt.plot(
    time2(solution2.t), phi_n2(solution2.t, x=0) - phi_e2(solution2.t, x=0), color="C0"
)
plt.xlabel("t [h]")
plt.ylabel("Potential [V]")
plt.legend()

plt.figure(5)
plt.plot(np.linspace(0.1, 1, 1E3), OCP_cathode(np.linspace(0.1, 1, 1E3)), color="C0")
plt.plot(np.linspace(0, 1, 1E3), OCP_anode(np.linspace(0, 1, 1E3)), color="C1")
plt.plot(
    np.array([c_s_p_nd(solution.t[-1], x=1), c_s_n_nd(solution.t[-1], x=0)]),
    np.array([
        OCP_cathode(c_s_p_nd(solution.t[-1], x=1)),
        OCP_anode(c_s_n_nd(solution.t[-1], x=0))
    ]), 'ko'
)
plt.plot(
    np.array([c_s_p_nd2(solution2.t[-1], x=1), c_s_n_nd2(solution2.t[-1], x=0)]),
    np.array([
        OCP_cathode(c_s_p_nd2(solution2.t[-1], x=1)),
        OCP_anode(c_s_n_nd2(solution2.t[-1], x=0))
    ]), 'kx'
)
plt.xlabel("SoC")
plt.ylabel("OCP [V]")
plt.legend(("positive", "negative"))

plt.figure(6)
# plt.plot(solution.t, Ueq(solution.t), label="OCV")
plt.plot(solution.t, etar(solution.t), label="reaction op")
# plt.plot(solution.t, etac(solution.t), label="concentration op")
# plt.plot(solution.t, Dphis(solution.t), label="solid Ohmic")
# plt.plot(solution.t, Dphie(solution.t), label="electrolyte Ohmic")
# plt.plot(solution.t, etap(solution.t), label="positive overpotential")
# plt.plot(solution.t, etan(solution.t), label="negative overpotential")
plt.xlabel("t")
plt.ylabel("Voltages [V]")
plt.legend()

plt.show()