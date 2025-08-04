from typing import List, Optional, Union
from pydantic import BaseModel, Field, model_validator

# P1 Output Model
class Reference(BaseModel):
    name: str
    link: str

class TemperatureCelsius(BaseModel):
    day_range: List[float]
    night_range: List[float]

class RelativeHumidityPercent(BaseModel):
    ideal_range: List[float]

class OnlineResult(BaseModel):
    temperature_celsius: TemperatureCelsius
    relative_humidity_percent: RelativeHumidityPercent
    ppfd_umol_m2_s: Union[List[float], float, str]
    dli_mol_m2_day: Union[List[float], float, str]
    references: List[Reference]
    notes: str

# P2 Output Model
class LightingStrategy(BaseModel):
    photoperiod_hours: float
    daytime_target_lux: List[float]
    notes: str

class ClimateStrategyPeriod(BaseModel):
    temperature_celsius: List[float]
    humidity_percent: List[float]

class ClimateStrategy(BaseModel):
    day: ClimateStrategyPeriod
    night: ClimateStrategyPeriod
    control_logic: str

class ManualCheckRecommendation(BaseModel):
    task: str 
    todo: str

class StrategyFailureEscalation(BaseModel):
    condition: str
    detection_period: str
    equipment_limitation_considered: str
    location_season_weather_factors: str
    recovery_suggestion: str

class OverallTarget(BaseModel):
    lighting_strategy: LightingStrategy
    climate_strategy: ClimateStrategy
    manual_check_recommendations: List[ManualCheckRecommendation]
    strategy_failure_escalation: List[StrategyFailureEscalation]

    @model_validator(mode='before')
    @classmethod
    def convert_raw_list(cls, values):
        if isinstance(values.get("manual_check_recommendations"), list):
            values["manual_check_recommendations"] = [
                {"task": item, "todo": explanation}
                for item, explanation in values["manual_check_recommendations"]
            ]
        return values
    
# P3 Output Model
class TriggerCondition(BaseModel):
    description: str
    logic: str

class ControlAction(BaseModel):
    fan_setting: str
    led_setting: str

class ControlStep(BaseModel):
    step: int
    objective: str
    actions: ControlAction
    justification: str
    estimated_duration_minutes: int
    exit_condition: str

class StrategyDetail(BaseModel):
    case_id: str
    case_description: str
    case_quantitative_description: str
    risk_level: str
    trigger_condition: TriggerCondition
    diagnosis_and_strategy: str
    control_sequence: List[ControlStep]
    overall_15min_goal: str

class LocalStrategies(BaseModel):
    strategy_playbook: List[StrategyDetail]


class CloudLLMOutput(BaseModel):
    online: OnlineResult
    overall: OverallTarget
    local: LocalStrategies

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            OnlineResult: lambda v: v.model_dump(),
            OverallTarget: lambda v: v.model_dump(),
            LocalStrategies: lambda v: v.model_dump(),
        }