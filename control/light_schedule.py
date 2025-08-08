from datetime import datetime, timedelta
import numpy as np
from typing import Any, Any, List, Optional,Dict
import requests
from .model import TemperatureModel

class LightScheduleOptimizer:
    def __init__(
        self,
        days: int = 7,
        hours_per_day: int = 24,
        light_hours: int = 16,
        day_temp_min: float = 15.0,
        day_temp_max: float = 21.0,
        night_temp_min: float = 10.0,
        night_temp_max: float = 15.0,
        stability_lambda: float = 2.5,
        window_size: int = 3,
        lat: float = -33.865143,
        lng: float = 151.2099,
        exp_temperature_raise_model: TemperatureModel = TemperatureModel()  # Default model with parameters [7.9867, 0.2484, -0.0522, -0.002564]
    ):
        self.days = days
        self.hours_per_day = hours_per_day
        self.light_hours = light_hours
        self.day_temp_min = day_temp_min
        self.day_temp_max = day_temp_max
        self.night_temp_min = night_temp_min
        self.night_temp_max = night_temp_max
        self.stability_lambda = stability_lambda
        self.window_size = window_size
        self.lat = lat
        self.lng = lng
        self.exp_temperature_raise_model = exp_temperature_raise_model

    def update_temperature_settings(self, day_temp_min: Optional[float] = None, day_temp_max: Optional[float] = None,
                                    night_temp_min: Optional[float] = None, night_temp_max: Optional[float] = None):
        if day_temp_min is not None:
            self.day_temp_min = day_temp_min
        if day_temp_max is not None:
            self.day_temp_max = day_temp_max
        if night_temp_min is not None:
            self.night_temp_min = night_temp_min
        if night_temp_max is not None:
            self.night_temp_max = night_temp_max

    def update_light_hours(self, light_hours: Optional[int] = None):
        if light_hours is not None:
            if 0 < light_hours <= self.hours_per_day:
                self.light_hours = light_hours
            else:
                raise ValueError(f"Light hours must be between 1 and {self.hours_per_day}.")

    def get_weather_forecast(self, forecast_days: Optional[int] = None) -> np.ndarray:
        if forecast_days is None:
            forecast_days = self.days
        url = (
            f'https://api.open-meteo.com/v1/forecast?latitude={self.lat}&longitude={self.lng}'
            f'&hourly=temperature_2m&forecast_days={forecast_days}'
        )
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if 'hourly' in data and 'temperature_2m' in data['hourly']:
                temp_data_flat = np.array(data['hourly']['temperature_2m'])
                if len(temp_data_flat) >= forecast_days * self.hours_per_day:
                    return temp_data_flat[: forecast_days * self.hours_per_day].reshape(forecast_days, self.hours_per_day)
                else:
                    print(f"Warning: Received fewer data than expected ({len(temp_data_flat)} hours).")
                    return temp_data_flat.reshape(-1, self.hours_per_day)
            else:
                print("Error: API response missing temperature data. Using simulated data (default 20°C).")
                return np.full((forecast_days, self.hours_per_day), 20.0)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching weather forecast: {e}")
            print("Using simulated weather data (default 20°C).")
            sim_data = 20 + 5 * np.sin(np.linspace(0, 2 * np.pi * forecast_days, forecast_days * self.hours_per_day))
            return sim_data.reshape(forecast_days, self.hours_per_day)

    def score_day(self, temp_vec: np.ndarray, start_hour: int) -> float:
        score = 0.0
        light_hours_indices = set([(start_hour + h) % self.hours_per_day for h in range(self.light_hours)])
        for h in range(self.hours_per_day):
            current_temp = temp_vec[h]
            if h in light_hours_indices:  # Light period
                min_target = self.day_temp_min
                max_target = self.day_temp_max
                effective_led_heat = self.exp_temperature_raise_model.evaluate(1.0, current_temp, 1800)
                effective_temp_for_min_check = current_temp + effective_led_heat

                if min_target <= current_temp <= max_target:
                    score += 2.0
                elif current_temp < min_target:
                    if effective_temp_for_min_check >= min_target:
                        score += 1.0
                    else:
                        score -= (min_target - effective_temp_for_min_check) * 2
                elif current_temp > max_target:
                    score -= (current_temp - max_target) * 2
            else:  # Dark period
                min_target = self.night_temp_min
                max_target = self.night_temp_max
                if min_target <= current_temp <= max_target:
                    score += 2.0
                elif current_temp < min_target:
                    score -= (min_target - current_temp) * 2.5
                elif current_temp > max_target:
                    score -= (current_temp - max_target) * 1.5
        return score

    def rolling_optimization(self, temp_data: np.ndarray) -> List[int]:
        total_days = temp_data.shape[0]
        selected_start_hours = []
        prev_start_hour = None

        for today in range(total_days):
            window_end = min(today + self.window_size, total_days)
            window_slice = temp_data[today:window_end]
            best_hour = None
            best_score = -np.inf

            for start_hour in range(self.hours_per_day):
                score_sum = sum(self.score_day(day_temp, start_hour) for day_temp in window_slice)
                if prev_start_hour is not None:
                    diff = abs(start_hour - prev_start_hour)
                    penalty_diff = min(diff, self.hours_per_day - diff)
                    penalty = self.stability_lambda * penalty_diff
                    score_sum -= penalty

                if score_sum > best_score:
                    best_score = score_sum
                    best_hour = start_hour

            selected_start_hours.append(best_hour)
            prev_start_hour = best_hour

        return selected_start_hours


    def eval(self) -> Dict[str, list[int]]:
        temp_data = self.get_weather_forecast()
        optimal_starts = self.rolling_optimization(temp_data)
        result_dict = {
            "day": [i for i in range(self.days)],
            "start_hour": optimal_starts
        }
        return result_dict



class LightScheduleManager:
    optimizer: LightScheduleOptimizer
    _schedule: Optional[Dict[str, List[int]]] = None
    _schedule_generation_date: Optional[datetime] = None

    def __init__(self, optimizer: LightScheduleOptimizer):
        self.optimizer = optimizer
        self._schedule: Optional[Dict[str, List[int]]] = None
        self._schedule_generation_date: Optional[datetime] = None

    @property
    def schedule(self) -> Optional[Dict[str, List[int]]]:
        return self._schedule

    @property
    def schedule_generation_date(self) -> Optional[datetime]:
        return self._schedule_generation_date

    def calculate_schedule(self) -> Dict[str, List[int]]:
        self._schedule = self.optimizer.eval()
        self._schedule_generation_date = datetime.now()
        print(f"Schedule calculated for {self.optimizer.days} days, starting from {self._schedule_generation_date.strftime('%Y-%m-%d %H:%M:%S')}")
        return self._schedule

    def get_remaining_light_hours(self, current_time: datetime) -> float:
        """
        Queries the remaining light hours for a given time based on the stored schedule.

        Args:
            current_time: The datetime object representing the current time to query.

        Returns:
            The number of remaining light hours (float) for the current light period.
            Returns 0.0 if lights are currently off or if the schedule is not available/valid.

        Raises:
            RuntimeError: If the schedule has not been calculated yet.
            ValueError: If the current_time is outside the calculated schedule's range.
        """
        if self._schedule is None or self._schedule_generation_date is None:
            raise RuntimeError("Light schedule has not been calculated yet. Call 'calculate_schedule()' first.")

        days_since_generation = (current_time.date() - self._schedule_generation_date.date()).days

        if not (0 <= days_since_generation < self.optimizer.days):
            raise ValueError(
                f"Provided time ({current_time.strftime('%Y-%m-%d')}) "
                f"is out of the calculated schedule range. "
                f"Schedule covers {self.optimizer.days} days starting from "
                f"{self._schedule_generation_date.strftime('%Y-%m-%d')}."
            )

        current_day_start_hour = self._schedule['start_hour'][days_since_generation]

        light_start_dt = current_time.replace(
            hour=current_day_start_hour, minute=0, second=0, microsecond=0
        )
        light_end_hour_raw = current_day_start_hour + self.optimizer.light_hours
        light_end_hour = light_end_hour_raw % self.optimizer.hours_per_day
        
        light_end_dt = current_time.replace(
            hour=light_end_hour, minute=0, second=0, microsecond=0
        )

        if light_end_hour_raw >= self.optimizer.hours_per_day:
            light_end_dt += timedelta(days=1)

        if light_start_dt <= current_time < light_end_dt:
            time_difference = light_end_dt - current_time
            remaining_hours = time_difference.total_seconds() / 3600.0
            return max(0.0, remaining_hours) 
        else:
            return 0.0

    def get_light_status(self, current_time: datetime) -> Dict[str, Any]:
        """
        Provides a detailed status of the light schedule for the given time.

        Args:
            current_time: The datetime object representing the current time to query.

        Returns:
            A dictionary containing:
            - 'is_light_on': True if lights are on, False otherwise.
            - 'remaining_light_hours': Float, hours until lights turn off (0 if off).
            - 'light_start_hour_today': Integer, the scheduled start hour for today.
            - 'light_end_hour_today': Integer, the scheduled end hour for today (actual hour, not wrapped).
            - 'next_light_on_in_hours': Float, hours until next light period starts (0 if currently on).
        """
        if self._schedule is None or self._schedule_generation_date is None:
            raise RuntimeError("Light schedule has not been calculated yet. Call 'calculate_schedule()' first.")

        days_since_generation = (current_time.date() - self._schedule_generation_date.date()).days

        if not (0 <= days_since_generation < self.optimizer.days):
            raise ValueError(
                f"Provided time ({current_time.strftime('%Y-%m-%d')}) "
                f"is out of the calculated schedule range. "
                f"Schedule covers {self.optimizer.days} days starting from "
                f"{self._schedule_generation_date.strftime('%Y-%m-%d')}."
            )

        current_day_start_hour = self._schedule['start_hour'][days_since_generation]
        
        light_start_dt = current_time.replace(
            hour=current_day_start_hour, minute=0, second=0, microsecond=0
        )
        
        light_end_hour_raw = current_day_start_hour + self.optimizer.light_hours
        light_end_hour = light_end_hour_raw % self.optimizer.hours_per_day
        
        light_end_dt = current_time.replace(
            hour=light_end_hour, minute=0, second=0, microsecond=0
        )
        if light_end_hour_raw >= self.optimizer.hours_per_day:
            light_end_dt += timedelta(days=1)

        next_light_on_dt = light_start_dt
        if current_time >= light_end_dt: # If current time is after today's light period ends
            next_light_on_dt += timedelta(days=1)
            if days_since_generation + 1 < self.optimizer.days:
                tomorrow_start_hour = self._schedule['start_hour'][days_since_generation + 1]
                next_light_on_dt = next_light_on_dt.replace(hour=tomorrow_start_hour, minute=0, second=0, microsecond=0)
            else:
                next_light_on_dt = None # Indicate no future schedule in this window

        is_light_on = False
        remaining_light_hours = 0.0
        next_light_on_in_hours = 0.0

        if light_start_dt <= current_time < light_end_dt:
            is_light_on = True
            time_difference = light_end_dt - current_time
            remaining_light_hours = max(0.0, time_difference.total_seconds() / 3600.0)
            next_light_on_in_hours = 0.0 # Already on
        else:
            is_light_on = False
            remaining_light_hours = 0.0
            if next_light_on_dt and current_time < next_light_on_dt:
                time_difference = next_light_on_dt - current_time
                next_light_on_in_hours = max(0.0, time_difference.total_seconds() / 3600.0)
            elif next_light_on_dt is None:
                next_light_on_in_hours = float('inf') # No more schedule within window

        return {
            "is_light_on": is_light_on,
            "remaining_light_hours": remaining_light_hours,
            "light_start_hour_today": current_day_start_hour,
            "light_end_hour_today": light_end_hour, # This is the hour of the day, not necessarily next day
            "next_light_on_in_hours": next_light_on_in_hours
        }
