import autograd.numpy as np


def electrolyte_diffusivity_Nyman2008(c_e, T, T_inf, E_D_e, R_g):
    """
    Diffusivity of LiPF6 in EC:EMC (3:7) as a function of ion concentration. The data
    comes from [1]

    References
    ----------
    .. [1] A Nyman et al. Electrochemical characterisation and modelling of the mass
    transport phenomena in LiPF6-EC-EMC electrolyte. Electrochimica Acta 53 (2008):
    6356-6365.

    Parameters
    ----------
    c_e: :class: `numpy.Array`
        Dimensional electrolyte concentration
    T: :class: `numpy.Array`
        Dimensional temperature
    T_inf: double
        Reference temperature
    E_D_e: double
        Electrolyte diffusion activation energy
    R_g: double
        The ideal gas constant

    Returns
    -------
    :`numpy.Array`
        Solid diffusivity
    """

    D_c_e = (
        8.794E-11 * (c_e / 1000) ** 2
        - 3.972E-10 * (c_e / 1000)
        + 4.862E-10
    )
    arrhenius = np.exp(E_D_e / R_g * (1 / T_inf - 1 / T))

    return D_c_e * arrhenius
