
import numpy as np

def exp_temperature_raise_model(p, t_env, t):
    """
    Exponential temperature model.
    - ΔT(t, P, T_env) = 7.9867 * P^0.2484 * exp(-0.0522 * T_env) * (1 - exp(-0.002564 * t))
    where:
    - P: Power factor (0.0 to 1.0)
    - T_env: Environmental temperature in Celsius
    - t: Time in seconds
    # """
    return 7.9867 * (p ** 0.2484) * np.exp(-0.0522 * t_env) * (1 - np.exp(-0.002564 * t))