from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LocalLLMInput(BaseModel):
    board_id: int = 0
    ideal_temp_range: list[float]
    internal_temp: float
    humidity: float = 0.0
    photoperiod_status: str
    current_time: datetime
    pred_env_temp_range: list[float]
    pred_env_high_time: datetime
    pred_env_low_time: datetime
    history_temp_change: list[float]
    external_temp_change: list[float] = Field(default_factory=list)
    fan_status: int
    led_light_status: int
    device_health: str = "Nominal"
    plant_status: str = "Healthy"


class Esp32StateAdapter:
    @staticmethod
    def from_sensor_json(data: dict[str, Any], defaults: dict[str, Any] | None = None) -> LocalLLMInput:
        defaults = defaults or {}
        now = datetime.now()
        fan_abs = int(data.get("fans_abs", data.get("fan_pwm", defaults.get("fan_status", 60))))
        led_abs = int(data.get("led_abs", data.get("led_pwm", defaults.get("led_light_status", 180))))
        if fan_abs > 100:
            fan_abs = int(fan_abs / 255 * 100)
        if led_abs > 100:
            led_abs = int(led_abs / 255 * 100)

        ideal = defaults.get("ideal_temp_range", [20.0, 24.0])
        pred_range = defaults.get("pred_env_temp_range", [18.0, 22.0])
        photoperiod = defaults.get("photoperiod_status", "ON")
        if "photoperiod_status" in data:
            photoperiod = data["photoperiod_status"]
        elif data.get("lights_on") is False:
            photoperiod = "OFF"

        return LocalLLMInput(
            board_id=int(data.get("board_id", defaults.get("board_id", 0))),
            ideal_temp_range=list(ideal),
            internal_temp=float(data.get("temperature", data.get("internal_temp", defaults.get("internal_temp", 22.0)))),
            humidity=float(data.get("humidity", defaults.get("humidity", 55.0))),
            photoperiod_status=str(photoperiod),
            current_time=now,
            pred_env_temp_range=list(pred_range),
            pred_env_high_time=defaults.get("pred_env_high_time", now.replace(hour=15, minute=0, second=0, microsecond=0)),
            pred_env_low_time=defaults.get("pred_env_low_time", now.replace(hour=6, minute=0, second=0, microsecond=0)),
            history_temp_change=list(data.get("history_temperature_change", defaults.get("history_temp_change", [0.2, 0.3, 0.2]))),
            external_temp_change=list(data.get("external_temp_change", defaults.get("external_temp_change", []))),
            fan_status=fan_abs,
            led_light_status=led_abs,
            device_health=str(data.get("device_health", defaults.get("device_health", "Nominal"))),
            plant_status=str(data.get("plant_status", defaults.get("plant_status", "Healthy"))),
        )

    @staticmethod
    def sample_high_temp() -> LocalLLMInput:
        now = datetime.now()
        return LocalLLMInput(
            board_id=0,
            ideal_temp_range=[20.0, 24.0],
            internal_temp=26.5,
            humidity=65.0,
            photoperiod_status="ON",
            current_time=now,
            pred_env_temp_range=[18.0, 22.0],
            pred_env_high_time=now.replace(hour=15, minute=0, second=0, microsecond=0),
            pred_env_low_time=now.replace(hour=6, minute=0, second=0, microsecond=0),
            history_temp_change=[0.2, 0.4, 0.3],
            fan_status=60,
            led_light_status=70,
            device_health="Nominal",
        )


def build_step_data(user_input: LocalLLMInput) -> dict[str, Any]:
    temperature_start = (
        user_input.history_temp_change[0] + user_input.internal_temp
        if user_input.history_temp_change
        else user_input.internal_temp - 1.0
    )
    temperature_end = user_input.internal_temp
    average_temperature_change = (
        sum(user_input.history_temp_change) / len(user_input.history_temp_change)
        if user_input.history_temp_change
        else 0.0
    )
    external_temp_start = user_input.pred_env_temp_range[0]
    external_temp_end = user_input.pred_env_temp_range[1]
    min_temp = min(user_input.pred_env_temp_range)
    max_temp = max(user_input.pred_env_temp_range)

    return {
        "ideal_temp_low": user_input.ideal_temp_range[0],
        "ideal_temp_high": user_input.ideal_temp_range[1],
        "internal_temp": user_input.internal_temp,
        "humidity": user_input.humidity,
        "photoperiod_status": user_input.photoperiod_status,
        "current_time": user_input.current_time.strftime("%H:%M"),
        "external_temp_start": external_temp_start,
        "external_temp_end": external_temp_end,
        "external_temp_min": external_temp_start,
        "external_temp_max": external_temp_end,
        "max_temp": max_temp,
        "max_temp_time": user_input.pred_env_high_time.strftime("%H:%M"),
        "min_temp": min_temp,
        "min_temp_time": user_input.pred_env_low_time.strftime("%H:%M"),
        "temperature_start": temperature_start,
        "temperature_end": temperature_end,
        "average_temperature_change": average_temperature_change,
        "plant_status": user_input.plant_status,
        "fan_status": user_input.fan_status,
        "led_light_status": user_input.led_light_status,
        "fan_rpm": user_input.fan_status,
        "led_pwm": user_input.led_light_status,
        "device_health": user_input.device_health,
        "history_temperature_change": user_input.history_temp_change,
    }
