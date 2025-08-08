
from abc import ABC
import numpy as np
from typing import List

class PhysicalModel(ABC):
    """
    Abstract base class for physical models.
    All physical models should inherit from this class.
    """
    def __init__(self, params: List[float]):
        if not params:
            raise ValueError("Parameters list cannot be empty.")
        self.params = params

    def evaluate(self, *args) -> float:
        """
        Evaluate the model with given parameters.
        This method should be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses should implement this method.")

class TemperatureModel(PhysicalModel):
    params: List[float]

    def __init__(self, params: List[float] = [7.9867, 0.2484, -0.0522, -0.002564]):
        if len(params) != 4:
            raise ValueError("TemperatureModel requires exactly 4 parameters.")
        self.params = params

    def evaluate(self, p: float, t_env: float, t_seconds: float) -> float:
        return self.__call__(p, t_env, t_seconds)

    def __call__(self, p: float, t_env: float, t_seconds: float) -> float:
        """
            Exponential temperature model.
            - ΔT(t, P, T_env) = 7.9867 * P^0.2484 * exp(-0.0522 * T_env) * (1 - exp(-0.002564 * t))
            where:
            - P: Power factor (0.0 to 1.0)
            - T_env: Environmental temperature in Celsius
            - t: Time in seconds
        """
        return self.params[0] * (p ** self.params[1]) * np.exp(self.params[2] * t_env) * (1 - np.exp(self.params[3] * t_seconds))
    
class CoolingModel(PhysicalModel):
    def __init__(self, params: List[float] = [0.1, 0.05, 0.01]):
        if len(params) != 3:
            raise ValueError("CoolingModel requires exactly 3 parameters.")
        self.params = params    

    def evaluate(self, p: float, t_env: float, t_seconds: float) -> float:
        return self.__call__(p, t_env, t_seconds)

    def __call__(self, p: float, t_env: float, t_seconds: float) -> float:
        """
            Cooling model based on environmental temperature and time.
            - ΔT_cooling = 0.1 * T_env + 0.05 * t_seconds + 0.01
            where:
            - T_env: Environmental temperature in Celsius
            - t_seconds: Time in seconds
        """
        return self.params[0] * t_env + self.params[1] * t_seconds + self.params[2]

class ChangeModel(PhysicalModel):
    def __init__(self, params: List[float] = [0.1, 0.05]):
        if len(params) != 2:
            raise ValueError("ChangeModel requires exactly 2 parameters.")
        self.params = params

    def evaluate(self, p_fan: float, p_led: float, t_env: float, t_seconds: float) -> float:
        return self.__call__(p_fan, p_led, t_env, t_seconds)

    def __call__(self, p_fan: float, p_led: float, t_env: float, t_seconds: float) -> float:
        """
            Change model based on environmental temperature and time.
            - ΔT_change = 0.1 * T_env + 0.05 * t_seconds
            where:
            - T_env: Environmental temperature in Celsius
            - t_seconds: Time in seconds
        """
        return self.params[0] * t_env + self.params[1] * t_seconds


class LuxToPPFD(PhysicalModel):
    def __init__(self, params: List[float] = [0.0473]):
        if len(params) != 1:
            raise ValueError("LuxToPPFD requires exactly 1 parameter.")
        self.params = params

    def evaluate(self, lux: float) -> float:
        return self.__call__(lux)
    
    def reverse(self, ppfd: float) -> float:
        """
            Convert PPFD back to Lux.
            - Lux = PPFD / 0.0473
        """
        return ppfd / self.params[0]

    def __call__(self, lux: float) -> float:
        """
            Convert Lux to PPFD (Photosynthetic Photon Flux Density).
            - PPFD = 0.0473 * Lux
        """
        return self.params[0] * lux