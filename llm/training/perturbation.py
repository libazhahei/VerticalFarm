from __future__ import annotations

import copy
import json
import random
from typing import Any

from llm.training.schemas import DPOFlawCategory, SeedScenario

PERTURBATION_TYPES = [
    "temperature_offset",
    "humidity_offset",
    "delta_inversion",
    "photoperiod_flip",
    "trend_reversal",
    "sensor_anomaly",
]


def perturb_state(seed: SeedScenario, perturbation_type: str, rng: random.Random | None = None) -> SeedScenario:
    rng = rng or random.Random()
    mutated = copy.deepcopy(seed)
    sv = mutated.state_vector

    if perturbation_type == "temperature_offset":
        offset = rng.uniform(-3.0, 3.0)
        sv.internal_temp = round(sv.internal_temp + offset, 1)
    elif perturbation_type == "humidity_offset":
        offset = rng.uniform(-15.0, 15.0)
        sv.internal_humidity = round(max(30.0, min(95.0, sv.internal_humidity + offset)), 1)
    elif perturbation_type == "delta_inversion":
        delta = sv.internal_temp - sv.external_temp
        sv.internal_temp = round(sv.external_temp - delta, 1)
    elif perturbation_type == "photoperiod_flip":
        if sv.photoperiod_status == "Lights_ON":
            sv.photoperiod_status = "Lights_OFF"
            sv.led_pwm = 0.0
        else:
            sv.photoperiod_status = "Lights_ON"
            sv.led_pwm = round(rng.uniform(0.4, 0.8), 2)
    elif perturbation_type == "trend_reversal":
        sv.temp_trend_15min = _negate_trend(sv.temp_trend_15min)
        sv.humidity_trend_15min = _negate_trend(sv.humidity_trend_15min, unit="%")
    elif perturbation_type == "sensor_anomaly":
        field = rng.choice(["internal_temp", "internal_humidity", "fan_rpm"])
        if field == "internal_temp":
            sv.internal_temp = round(rng.uniform(35.0, 45.0), 1)
        elif field == "internal_humidity":
            sv.internal_humidity = round(rng.uniform(5.0, 20.0), 1)
        else:
            sv.fan_rpm = int(rng.choice([0, 5000, 9999]))

    mutated.seed_id = f"{seed.seed_id}_pert_{perturbation_type}"
    return mutated


def _negate_trend(trend: str, unit: str = "°C") -> str:
    value = trend.replace(unit, "").replace("+", "").replace("%", "").strip()
    try:
        num = float(value)
        sign = "+" if -num >= 0 else ""
        return f"{sign}{-num:.1f}{unit}"
    except ValueError:
        return trend


def augment_with_perturbation(
    seeds: list[SeedScenario],
    rng: random.Random | None = None,
) -> list[SeedScenario]:
    rng = rng or random.Random()
    augmented: list[SeedScenario] = []
    for seed in seeds:
        ptype = rng.choice(PERTURBATION_TYPES)
        augmented.append(perturb_state(seed, ptype, rng))
    return augmented


def adversarial_state(seed: SeedScenario, flaw: DPOFlawCategory) -> SeedScenario:
    """Construct edge-case state targeting a specific constraint violation."""
    mutated = copy.deepcopy(seed)
    sv = mutated.state_vector
    if flaw == DPOFlawCategory.PHYSICAL_CONTRADICTION:
        sv.internal_temp = max(sv.internal_temp, mutated.crop_context.ideal_temp_range[1] + 2.0)
        sv.led_pwm = 1.0
        sv.fan_rpm = 0
    elif flaw == DPOFlawCategory.CONSTRAINT_VIOLATION:
        sv.photoperiod_status = "Lights_OFF"
        sv.led_pwm = 0.85
    elif flaw == DPOFlawCategory.SAFETY_BYPASS:
        sv.internal_temp = mutated.crop_context.ideal_temp_range[1] + 1.5
    mutated.seed_id = f"{seed.seed_id}_adv_{flaw.value}"
    return mutated


def deduplicate_by_embedding_stub(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Placeholder for cosine-similarity dedup on output JSON embeddings."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for sample in samples:
        key = json.dumps(sample.get("messages", sample), sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        unique.append(sample)
    return unique
