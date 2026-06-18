from typing import Any, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from langchain_core.messages import BaseMessage
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.language_models import BaseChatModel


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

# Combined Output Model
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

def fix_and_validate_json(json_str: BaseMessage, expect_type: Any, fix_model: BaseChatModel, max_attempts: int = 3) -> str:
    """
    Fix and validate a JSON string using a provided model.
    Tries up to three times to fix the JSON, then returns the result.
    """
    json_fix_template = """
    ## Role
    You are a JSON converter and repair tool.

    ## Task
    Your task is to:
    - Parse the given content (which may contain syntax errors or be only partially structured like JSON)
    - Validate and convert it into a fully valid JSON that conforms to the following JSON Schema.
    - Fix formatting issues (e.g. unquoted strings, booleans like True/False, trailing commas).
    - Coerce compatible values (e.g. numbers in strings → numbers, if schema expects so).
    - Ensure all required fields are present, setting them to null if they cannot be inferred.

    ## JSON Schema (use this as the ground truth structure):
    {json_schema}

    ## Input:
    {error_json}
    ---
    ## Output:
    Return only the corrected JSON. Do not add comments or explanations. If any required fields are missing and cannot be inferred, set them to null.

    {{corrected_json}}
    """
    json_fix_prompt = PromptTemplate.from_template(json_fix_template)
    json_fix_chain = json_fix_prompt | fix_model | JsonOutputParser()
    attempts = 0
    content = json_str.content
    while attempts < max_attempts:
        try:
            fixed_json = json_fix_chain.invoke(
                input={
                    "error_json": content,
                    "json_schema": expect_type.model_json_schema()
                }
            )
            # Validate and return as JSON string
            return expect_type.model_validate(fixed_json).model_dump_json()
        except Exception as e:
            attempts += 1
            content = fixed_json if 'fixed_json' in locals() else content
    print(f"Error parsing JSON after {attempts} attempts.")
    print(f"Original content: {json_str.content}")
    return "{}"
