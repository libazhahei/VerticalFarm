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
class StrategyDetail(BaseModel):
    id: str = Field(..., alias="Case_ID")
    condition: str = Field(..., alias="Condition_IF")
    reasoning: str = Field(..., alias="Diagnosis_Tradeoff_Analysis")
    control_priority: str = Field(..., alias="Primary_Control_Priority")
    action_priority: List[str] = Field(..., alias="Prioritized_Action_Chain")
    risk_level: str = Field(..., alias="Risk_level")
    tradeoff: str = Field(..., alias="15 min_Goal_and_Tradeoff")

class LocalStrategies(BaseModel):
    cases: List[StrategyDetail]


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