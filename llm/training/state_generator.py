from __future__ import annotations

from datetime import datetime
from typing import Any

import numpy as np

from llm.models.input import LocalLLMInput
from llm.training.schemas import (
    CropContext,
    OperatorAction,
    SeedScenario,
    StateVector,
)

CROP_PROFILES: list[dict[str, Any]] = [
    {
        "crop": "iceberg_lettuce",
        "growth_stage": "seedling",
        "ideal_temp_range": [15.0, 21.0],
        "ideal_humidity_range": [50.0, 70.0],
        "dli_target": 12.0,
    },
    {
        "crop": "butterhead_lettuce",
        "growth_stage": "vegetative",
        "ideal_temp_range": [18.0, 22.0],
        "ideal_humidity_range": [55.0, 75.0],
        "dli_target": 14.0,
    },
    {
        "crop": "romaine_lettuce",
        "growth_stage": "harvest",
        "ideal_temp_range": [16.0, 20.0],
        "ideal_humidity_range": [50.0, 65.0],
        "dli_target": 16.0,
    },
]


def _format_trend(value: float, unit: str = "°C") -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}{unit}"


def _derive_operator_action(
    state: StateVector,
    crop: CropContext,
) -> tuple[OperatorAction, str]:
    ideal_low, ideal_high = crop.ideal_temp_range
    t_int = state.internal_temp
    led_pct = state.led_pwm * 100
    fan_rpm = state.fan_rpm

    if t_int > ideal_high:
        new_fan = min(3400, fan_rpm + int(np.random.randint(400, 1200)))
        new_led = max(0.0, led_pct - np.random.uniform(10, 30)) / 100.0
        rationale = (
            f"Temperature at {t_int:.1f}°C exceeds upper bound {ideal_high}°C; "
            f"increased fan to {new_fan} RPM and reduced LED."
        )
    elif t_int < ideal_low:
        new_led = min(1.0, led_pct + np.random.uniform(10, 25)) / 100.0 if state.photoperiod_status == "Lights_ON" else 0.0
        new_fan = max(0, fan_rpm - int(np.random.randint(200, 600)))
        rationale = (
            f"Temperature at {t_int:.1f}°C below lower bound {ideal_low}°C; "
            f"increased LED and reduced fan for pre-heating."
        )
    else:
        new_led = led_pct / 100.0
        new_fan = fan_rpm
        rationale = f"Temperature within ideal range; maintaining LED {led_pct:.0f}% and fan {fan_rpm} RPM."

    return OperatorAction(new_led_pwm=round(new_led, 2), new_fan_rpm=new_fan), rationale


def generate_seed_scenario(rng: np.random.Generator, index: int) -> SeedScenario:
    profile = CROP_PROFILES[int(rng.integers(0, len(CROP_PROFILES)))]
    crop = CropContext(**profile)

    external_temp = float(rng.uniform(14.0, 28.0))
    photoperiod = "Lights_ON" if rng.random() > 0.25 else "Lights_OFF"
    led_pwm = float(rng.uniform(0.3, 0.85)) if photoperiod == "Lights_ON" else 0.0
    fan_rpm = int(rng.integers(800, 3200))

    ideal_mid = sum(crop.ideal_temp_range) / 2
    led_heat = led_pwm * 3.0 * (1.0 - fan_rpm / 3400.0)
    internal_temp = external_temp + led_heat + float(rng.normal(0, 0.5))
    internal_temp = max(external_temp - 1.0, min(external_temp + 5.0, internal_temp))

    temp_delta = (internal_temp - ideal_mid) * 0.3 + float(rng.normal(0, 0.2))
    humidity_delta = float(rng.normal(0, 3.0))

    internal_humidity = float(np.clip(rng.uniform(45.0, 80.0), 40.0, 85.0))
    external_humidity = float(np.clip(internal_humidity + rng.uniform(-15, 10), 30.0, 90.0))

    state = StateVector(
        internal_temp=round(internal_temp, 1),
        external_temp=round(external_temp, 1),
        internal_humidity=round(internal_humidity, 1),
        external_humidity=round(external_humidity, 1),
        led_pwm=round(led_pwm, 2),
        fan_rpm=fan_rpm,
        photoperiod_status=photoperiod,
        temp_trend_15min=_format_trend(temp_delta),
        humidity_trend_15min=_format_trend(humidity_delta, "%"),
    )
    operator_action, rationale = _derive_operator_action(state, crop)

    return SeedScenario(
        seed_id=f"seed_{index:05d}",
        state_vector=state,
        operator_action=operator_action,
        operator_rationale=rationale,
        crop_context=crop,
    )


def generate_seeds(count: int, random_seed: int = 42) -> list[SeedScenario]:
    rng = np.random.default_rng(random_seed)
    return [generate_seed_scenario(rng, i) for i in range(count)]


def seed_to_local_llm_input(seed: SeedScenario) -> LocalLLMInput:
    sv = seed.state_vector
    crop = seed.crop_context
    now = datetime.now()
    trend_vals = []
    try:
        trend_val = float(sv.temp_trend_15min.replace("°C", "").replace("+", ""))
        trend_vals = [trend_val * 0.5, trend_val * 0.8, trend_val]
    except ValueError:
        trend_vals = [0.2, 0.3, 0.2]

    photoperiod = "ON" if sv.photoperiod_status == "Lights_ON" else "OFF"
    fan_pct = int(np.clip(sv.fan_rpm / 3400 * 100, 0, 100))
    led_pct = int(np.clip(sv.led_pwm * 100, 0, 100))

    return LocalLLMInput(
        board_id=0,
        ideal_temp_range=list(crop.ideal_temp_range),
        internal_temp=sv.internal_temp,
        humidity=sv.internal_humidity,
        photoperiod_status=photoperiod,
        current_time=now,
        pred_env_temp_range=[sv.external_temp - 1.0, sv.external_temp + 2.0],
        pred_env_high_time=now.replace(hour=15, minute=0, second=0, microsecond=0),
        pred_env_low_time=now.replace(hour=6, minute=0, second=0, microsecond=0),
        history_temp_change=trend_vals,
        fan_status=fan_pct,
        led_light_status=led_pct,
        device_health="Nominal",
        plant_status="Healthy",
    )
