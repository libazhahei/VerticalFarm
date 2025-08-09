import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
# from click import Option
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.chat_models import ChatOllama
from langchain_core.messages import BaseMessage
from pydantic import BaseModel
from typing import Type
from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI
import json 
from datetime import timedelta
from typing import Any
import time 
from pydantic import SecretStr

ANSI_COLORS = {
    "black":   "30",
    "red":     "31",
    "green":   "32",
    "yellow":  "33",
    "blue":    "34",
    "magenta": "35",
    "cyan":    "36",
    "white":   "37",
    "reset":   "0"
}

ANSI_STYLES = {
    "bold":     "1",
    "dim":      "2",
    "underline":"4",
    "normal":   "22"
}

def ansi_cprint(text, fg="green", bg=None, style="normal", end="\n"):
    """
    ANSI 终端彩色打印
    :param text: 文本内容
    :param fg: 前景色名
    :param bg: 背景色名（可选）
    :param style: 样式（bold, underline, dim, normal）
    """
    fg_code = ANSI_COLORS.get(fg.lower(), "37")
    style_code = ANSI_STYLES.get(style.lower(), "0")
    bg_code = ""
    if bg:
        bg_code = ANSI_COLORS.get(bg.lower(), "")
        if bg_code:
            bg_code = str(int(bg_code) + 10)  

    ansi_sequence = f"\033[{style_code};{fg_code}"
    if bg_code:
        ansi_sequence += f";{bg_code}"
    ansi_sequence += "m"

    reset_sequence = "\033[0m"
    print(f"{ansi_sequence}{text}{reset_sequence}", end=end)



# Prompts: 
role_and_task = """
# System Role and Capabilities
You are a high-level environmental control AI responsible for creating the optimal growing environment for specific plants (e.g., lettuce) by precisely adjusting fans and LED lights.
Your decisions should be data-driven, balancing plant health, energy efficiency, and system safety.
"""

goal_and_objectives = """
# Goal and Objectives
- **Core Goal**: Maintain the temperature between {ideal_temp_low}°C and {ideal_temp_high}°C.
- **Objectives:**
  - Use fans and LED lights effectively to achieve these goals.
- **Constraints**:
  - Fans can only cool the room to the external temperature in 3 minutes.
  - LED lights can heat the room up to apprx. 3°C at most in 15 mins, only if fans are OFF.
  - In the "Lights OFF" period, LED lights must remain OFF to respect the plant's dark cycle.
  - In the "Lights ON" period, LED lights must remain On to support photosynthesis.
"""

curr_env_status = """
# Current Environmental Status (Real-time Data)
- Internal Temperature: {internal_temp}°C
- External Temperature: {temperature_end}°C
- Plant Status: {plant_status}
- Current Photoperiod: Lights {photoperiod_status} (ON/OFF)
- Device Status:
  - Fan: {fan_status} (0-100% RPM)
  - LED Light: {led_light_status} (0-100% intensity)
"""

history_context = """
# Historical Context (Dynamic Information)
- **Environmental Trends in the Past 30 Minutes**:
  - Temperature: Increased from {temperature_start}°C to {temperature_end}°C (average increase of {average_temperature_change}°C per 15 minutes)
"""

environment_forecast = """
# Environmental Forecast (Dynamic Information)
- **Environmental Forecast for the Next 1 Hour**:
  - Current time is: {current_time} (e.g., 14:00), Daily forecast indicates: Maximum temperature of {max_temp}°C at {max_temp_time}, Minimum temperature of {min_temp}°C at {min_temp_time}.
  - External Temperature: Expected temperature from {external_temp_start}°C to {external_temp_end}°C over the next hour (source: Weather API).
  - Internal Temperature: Based on current trends and external forecasts, if no intervention is made, it is expected to slowly rise to match the room temperature within the next 1 hour.
"""

diagnosis_prompt = """
# Diagnosis
1. Carefully analyze all the information provided above.
2. Summarize the core issue or state in one sentence (e.g., "Temperature is slightly high and continues to rise").
5. Consider the environmental forecast and historical context to make a more accurate diagnosis.
3. Choose one or more states from the following list that best describe the current situation: ['Stable Maintenance', 'Rising Trend', 'Falling Trend', 'Pre-heating', 'Pre-cooling', 'High Temperature', 'Low Temperature'].
4. Do not propose any solutions or call any functions.
"""
diagnosis_output_prompt = """ 
# Output Format
Please return the diagnosis result in JSON format, including the following fields:

{{
  "core_issue": "string: A concise summary of the core issue or state",
  "states": ["string: A list of states that best describe the current situation"],
  "confidence": ["int: A confidence score between 0 and 10 indicating how certain you are about the diagnosis for each state."],
}}
"""

revised_step1_prompt_part = """ 
# Your Proposed Diagnosis
Based on the provided background information and the result of the previous diagnosis or decision,
please assess the reliability of that result and decide whether to revise it or not.

By assessing each score, use them to assess the reliability of the previous diagnosis.
- If score >= 8, you can keep the diagnosis as is.
- If score < 8, you should reconsider the diagnosis and provide a new one based on the new information provided. And comment on the Core Issue for the revision.
- If you decide to revise the diagnosis, please provide a new diagnosis result in the same format as below. 
- Or you can remove the diagnosis result if you think it is not necessary.

State: {state}
Core Issue: {core_issue}
Confidence: {confidence}
"""

diagnosis_brief = """
# Diagnosis
states: {states}
core_issue: {core_issue}
"""
plan_exploration = """
# Action Plan Explanation
Based on the diagnosed state above.
1. Propose 1 to 2 distinct solutions to address this issue.
    1. You can propose multiple solutions if they are distinct and address different aspects of the issue.
    2. Each solution should be a clear, actionable step that can be implemented within 15 minutes.
2. For each solution, clearly specify which predictive or computational function (e.g., `predict_temp_change_with_led_action`) you need to call to evaluate its effect.
        a. If multiple functions need to be called, ensure that the calling order is logical.
        b. If the same function needs to be called more than once, ensure each call has different parameters.
3. Please generate the JSON for the function calls required to evaluate the solutions.
"""
step2_output_prompt = """
# Output Format
Please return a JSON object with the following structure:
{{
    "action_plan": [
        {{
            "solution_id": "string: A unique identifier, e.g., 'SOLUTION_01'",
            "description": "string: A brief description of the solution, e.g., 'Increase fan speed to reduce temperature'",
            "function_calls": [
                {{
                    "name": "string: Function name,
                    "arguments": {{
                        "key": value,  # Add the necessary arguments for the function call
                    }},
                    "simulating_time": "string: The time period for the simulation in minutes, e.g., '15 minutes'"
                }},
                // ... Add more function calls as needed
            ],
            "confidence": "int: A confidence score between 0 and 10 indicating how confident you are in this solution."
        }},
        // ... Additional solutions can be added if needed.
    ]
}}
"""
step2_functions_prompt = """
[
    {{ "name": "predict_temp_change_with_led_action", "description": "Predict the temperature change over the next 15 minutes given a change in LED brightness.", "parameters": {{ "type": "object", "properties": {{ "led_brightness_change": {{ "type": "number", "description": "Percentage change in LED brightness, if no fans open e.g., -15 for -15%" }} }}, "required": ["led_brightness_change"] }} }},
    {{ "name": "predict_temp_change_with_fan_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed.", "parameters": {{ "type": "object", "properties": {{ "fan_speed_change": {{ "type": "number", "description": "temperature target change in fan speed, if no leds open e.g., 14.5" }} }}, "required": ["fan_speed_change"] }} }},
    {{ "name": "predict_temp_change_with_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed and LED brightness. This prediction is not accurate than others", "parameters": {{ "type": "object", "properties": {{ "fan_speed_change": {{ "type": "number", "description": "temperature target change in fan speed, if no leds open e.g., 14.5" }}, "led_brightness_change": {{ "type": "number", "description": "Percentage change in LED brightness, if no fans open e.g., -15 for -15%" }} }}, "required": ["fan_speed_change", "led_brightness_change"] }} }},
]
"""

revised_step2_prompt_part = """ 
# Revised Solution Assessment
Based on the provided background information and the result of the previous diagnosis or decision,
please assess the reliability of that result and decide whether to revise it or not.

By assessing each solution, compare temperature.
T_int = internal temperature, T_env = environmental temperature, T_ideal = ideal temperature
1) (T_int < T_env) and (T_int < T_ideal)  ⇒  MUST Increase LED brightness
2) (T_int > T_env) and (T_int > T_ideal)  ⇒  MUST Increase fan speed
3) (T_int < T_env) and (T_int > T_ideal)  ⇒  MUST Decrease fan speed
4) (T_int > T_env) and (T_int < T_ideal)  ⇒  MUST Decrease LED brightness

By assessing each solution, use the following rules to assess the reliability of the previous diagnosis.
- Lower temperature needs increase LED brightness.
- Higher temperature needs increase fan speed.

By assessing each solution, use the following rules to assess the reliability of the previous diagnosis.
- If lighting is ON, the LED brightness should be increased to warm the room, it will never be 0.
- If lighting is OFF, the LED brightness should be 0.

# Current Environmental Status
internal_temp: {internal_temp}
external_temp: {external_temp_end}
ideal_temp_low: {ideal_temp_low}
ideal_temp_high: {ideal_temp_high}
lighting_status: {photoperiod_status} 
state: {states}
core_issue: {core_issue}

# Your Proposed Solutions
solutions: {solutions}

If you decide to revise the diagnosis, leave the modified suggestions as below.
"""
revised_step2_output_prompt = """
# Output Format
Please return a JSON object with the following structure:
{{
    "action_plan": [
        {{
            "solution_id": "string: A unique identifier, e.g., 'SOLUTION_01'",
            "description": "string: A brief description of the suggestion",
            "new_plan": "string: A new plan to address the issue, if necessary",
        }}
        // ... Additional solutions can be added if needed.
    ]
}}
"""
revised_step2_modify_prompt_part = """
# Your Proposed Solutions
You have been provided with the proposed solutions.
Please import the solutions and modify them based on the current environmental status.

## Original Solutions
{solutions}

## Improvment Instructions
{revised_step2_prompt_part}
"""

step3_decision_prompt = """
# Decision Making
Based on the simulated results and the highest priority of temperature control, please select the best option and generate the final.
If you think the solution result meets the target (for example, temperature is between {ideal_temp_low} and {ideal_temp_high}), then response is solution name, e.g. SOLUTION_01.
If you think it is necessary to re-assess the current state(all solution does not meet the target), please use re_assess_solution to re-evaluate the situation.
"""
step2_brief = """
# Action Plan Explanation
The simulated results are as follows:
"""

step3_output_prompt = """
# Output Format
Please return a JSON object with the following structure:
{{
    "reason": "string: The rationale behind the chosen solution",
    "final_decision": "string: The function call to execute the chosen solution, e.g., 'SOLUTION_01' or 're_assess_solution'",
}}
"""
class Step3Output(BaseModel):
    final_decision: str
    reason: str

@dataclass
class LocalLLMInput:
    ideal_temp_range: List[float] 
    internal_temp: float
    photoperiod_status: str
    current_time: datetime
    pred_env_temp_range: List[float]
    pred_env_high_time: datetime
    pred_env_low_time: datetime
    history_temp_change: List[float]
    external_temp_change: List[float]
    fan_status: int
    led_light_status: int

class Step1Output(BaseModel):
    core_issue: str
    states: List[str]
    confidence: List[int]

class FunctionCall(BaseModel):
    name: str
    arguments: dict
    simulating_time: str

class ActionPlan(BaseModel):
    solution_id: str
    description: str
    function_calls: List[FunctionCall]  # Each dict contains name, arguments, simulating_time
    confidence: int

class Step2Output(BaseModel):
    action_plan: List[ActionPlan]

class ActionSuggestion(BaseModel):
    solution_id: str
    description: str
    new_plan: str

class RevisedStep2Output(BaseModel):
    action_plan: List[ActionSuggestion]

class SideEffectConcern(BaseModel):
    parameter_name: str  # e.g., "fan_speed", "led_brightness"
    change_magnitude: float  # e.g., 20.0 for +20%
    change_type: str  # e.g., "increase", "decrease"
    potential_impact: str  # e.g., "humidity_reduction", "temperature_spike"
    risk_level: str  # e.g., "low", "medium", "high"

class SideEffectEvaluation(BaseModel):
    solution_id: str
    side_effects: List[SideEffectConcern]
    overall_risk_assessment: str
    recommended_action: str  # e.g., "proceed", "modify", "reject"
    confidence: int

class SideEffectEvaluationOutput(BaseModel):
    evaluations: List[SideEffectEvaluation]

class LocalPlannerOutput(BaseModel):
    comments: str
    solution_action: ActionPlan

def fix_and_validate_json(json_str, expect_type: Any, fix_model, max_attempts: int = 3) -> str:
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
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
    json_fix_prompt = PromptTemplate.from_template(json_fix_template)
    json_fix_chain = json_fix_prompt | fix_model | JsonOutputParser()
    attempts = 0
    content = json_str.content
    ansi_cprint(f"Fix JSON: {content}",fg="red")
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

class Step3EvaluationOutput(BaseModel):
    decision_quality: str  # "excellent", "good", "fair", "poor"
    meets_target_requirements: bool  # 是否符合目标要求
    confidence_assessment: int  # 1-10的置信度评估
    recommended_action: str  # "proceed", "proceed_with_caution", "select_alternative", "regenerate_plans"
    evaluation_reason: str  # 评估原因的详细说明
    alternative_suggestions: List[str]  # 替代方案建议

# class MyChatModel()


class LocalPlanner:
    def __init__(self, planner_model: ChatOpenAI, fix_model: ChatOpenAI, max_tries: int = 2) -> None:
        self.planner_model = planner_model
        self.json_fixer = fix_model
        self.json_parser = JsonOutputParser()
        self.max_tries = max_tries
        self.state = None

    def _build_step1_data(self, user_input: LocalLLMInput) -> dict:
        temperature_start = user_input.history_temp_change[0] + user_input.internal_temp if user_input.history_temp_change else user_input.internal_temp - 1.0
        temperature_end = user_input.internal_temp
        average_temperature_change = sum(user_input.history_temp_change) / len(user_input.history_temp_change) if user_input.history_temp_change else 0
        
        external_temp_start = user_input.pred_env_temp_range[0]
        external_temp_end = user_input.pred_env_temp_range[1]
        min_temp = min(user_input.pred_env_temp_range)
        max_temp = max(user_input.pred_env_temp_range)
        
        return {
            "ideal_temp_low": user_input.ideal_temp_range[0],
            "ideal_temp_high": user_input.ideal_temp_range[1],
            "internal_temp": user_input.internal_temp,
            "photoperiod_status": user_input.photoperiod_status,
            "current_time": user_input.current_time.strftime("%H:%M"),
            "external_temp_start": external_temp_start,
            "external_temp_end": external_temp_end,
            "max_temp": max_temp,
            "max_temp_time": user_input.pred_env_high_time.strftime("%H:%M"),
            "min_temp": min_temp,
            "min_temp_time": user_input.pred_env_low_time.strftime("%H:%M"),
            "temperature_start": temperature_start,
            "temperature_end": temperature_end,
            "average_temperature_change": average_temperature_change,
            "plant_status": "Healthy",
            "fan_status": user_input.fan_status,
            "led_light_status": user_input.led_light_status
        }

    def _validate_diagnosis_consistency(self, user_input: LocalLLMInput, step1_output: Step1Output) -> Optional[Step1Output]:
        print("Running diagnosis consistency check...")
        
        contradictions = []
        current_temp = user_input.internal_temp
        ideal_range = user_input.ideal_temp_range
        temp_trend = user_input.history_temp_change[-3:] if len(user_input.history_temp_change) >= 3 else user_input.history_temp_change
        
        is_temp_high = current_temp > ideal_range[1]
        is_temp_low = current_temp < ideal_range[0]
        is_temp_rising = len(temp_trend) >= 2 and temp_trend[-1] > temp_trend[-2]
        
        diagnosed_states = [state.lower() for state in step1_output.states]
        
        if is_temp_high and not any('high' in state and 'temp' in state for state in diagnosed_states):
            contradictions.append(f"Temperature is {current_temp}°C (above ideal {ideal_range[1]}°C) but diagnosis doesn't mention high temperature")
            
        if is_temp_rising and not any('rising' in state or 'increasing' in state or 'trend' in state for state in diagnosed_states):
            contradictions.append(f"Temperature trend is rising {temp_trend} but diagnosis doesn't mention rising trend")
            
        if is_temp_low and not any('low' in state and 'temp' in state for state in diagnosed_states):
            contradictions.append(f"Temperature is {current_temp}°C (below ideal {ideal_range[0]}°C) but diagnosis doesn't mention low temperature")
        
        if contradictions:
            print(f"Consistency issues found: {len(contradictions)} problems")
            for i, contradiction in enumerate(contradictions, 1):
                print(f"  {i}. {contradiction}")
            
            correction_prompt = f"""The initial diagnosis shows potential consistency issues. Please review and provide a corrected diagnosis.

INITIAL DIAGNOSIS: {step1_output.core_issue}
DIAGNOSED STATES: {step1_output.states}

CONSISTENCY ISSUES DETECTED:
{chr(10).join(f"- {c}" for c in contradictions)}

ENVIRONMENTAL FACTS:
- Current temperature: {current_temp}°C
- Ideal range: {ideal_range[0]}-{ideal_range[1]}°C  
- Recent temperature trend: {temp_trend}
- Fan status: {'ON' if user_input.fan_status else 'OFF'}
- LED status: {'ON' if user_input.led_light_status else 'OFF'}

Please provide a corrected diagnosis that addresses these consistency issues:
{diagnosis_output_prompt}
"""
            
            try:
                correction_response = self.planner_model.invoke([{"role": "user", "content": correction_prompt}])
                json_parser = JsonOutputParser()
                parsed_json = json_parser.invoke(correction_response)
                corrected_step1 = Step1Output.model_validate(parsed_json)
                print(f"Diagnosis corrected: {corrected_step1.core_issue}")
                return corrected_step1
            except Exception as e:
                print(f"Failed to generate correction: {e}")
                return None
        else:
            print("Diagnosis consistency check passed, no correction needed")
            return None

    def step1(self, user_input: LocalLLMInput) -> Step1Output:
        prompt = (
            role_and_task,
            goal_and_objectives,
            curr_env_status,
            history_context,
            environment_forecast,
            diagnosis_prompt,
            diagnosis_output_prompt,
        )
        step1_prompt = "".join(prompt)
        step1_data = self._build_step1_data(user_input)
        step1_prompt_template = PromptTemplate.from_template(step1_prompt)
        step1_chain = step1_prompt_template | self.planner_model
        
        try:
            step1_response = step1_chain.invoke(step1_data)
            json_parser = JsonOutputParser()
            parsed_json = json_parser.invoke(step1_response)
            step1_output = Step1Output.model_validate(parsed_json)
            return step1_output
        except Exception as e:
            print(f"[LocalPlanner] Error in step1: {e}")
            return Step1Output(
                core_issue="Unable to analyze current conditions due to processing error",
                states=["Stable Maintenance"],
                confidence=[5]
            )
    def _build_revised_step1_data(self, user_input: LocalLLMInput, state: str, core_reason: str, confidence: float) -> dict:
        prev_data = self._build_step1_data(user_input)
        return {
            **prev_data,
            "state": state,
            "core_issue": core_reason,
            "confidence": confidence
        }
    
    def revised_step1(self, user_input: LocalLLMInput, step1_output: Step1Output) -> Step1Output:
        """
        Review each state from step1 output separately and provide a comprehensive revised diagnosis.
        This method evaluates each state-confidence pair individually and combines the results.
        """
        revised_step1_prompt = "".join([
            role_and_task,
            goal_and_objectives,
            curr_env_status,
            history_context,
            environment_forecast,
            revised_step1_prompt_part,
            diagnosis_output_prompt,
        ])
        
        core_reason = step1_output.core_issue
        result = []
        
        # Review each state individually
        for state, confidence in zip(step1_output.states, step1_output.confidence):
            try:
                print(f"  Reviewing state: '{state}' with confidence: {confidence}")
                
                # Build data for this specific state review
                revised_data = self._build_revised_step1_data(user_input, state, core_reason, confidence)
                
                # Create and invoke the revision chain
                revised_step1_prompt_template = PromptTemplate.from_template(revised_step1_prompt)
                revised_step1_chain = revised_step1_prompt_template | self.planner_model
                
                revised_response = revised_step1_chain.invoke(revised_data)
                json_parser = JsonOutputParser()
                parsed_json = json_parser.invoke(revised_response)
                revised_output = Step1Output.model_validate(parsed_json)
                result.append(revised_output)
                
                print(f"    Revised to: {revised_output.states} (confidence: {revised_output.confidence})")
                
            except Exception as e:
                print(f"[LocalPlanner] Error in revised_step1 for state '{state}': {e}")
                try:
                    fixed_json = fix_and_validate_json(revised_response, Step1Output, self.json_fixer)
                    if fixed_json:
                        revised_output = Step1Output.model_validate(json.loads(fixed_json))
                        result.append(revised_output)
                        print(f"    Fixed and revised to: {revised_output.states}")
                    else:
                        # Use the original state as fallback
                        fallback_output = Step1Output(
                            core_issue=core_reason,
                            states=[state],
                            confidence=[max(1, confidence - 2)]  # Reduce confidence due to processing error
                        )
                        result.append(fallback_output)
                        print(f"    Using fallback for state '{state}'")
                except Exception as fix_error:
                    print(f"    Failed to fix JSON for state '{state}': {fix_error}")
                    # Use the original state as fallback
                    fallback_output = Step1Output(
                        core_issue=core_reason,
                        states=[state],
                        confidence=[max(1, confidence - 2)]
                    )
                    result.append(fallback_output)
        
        # Combine results from all reviewed states
        if not result:
            # If no results were generated, return the original output
            print("  No valid revisions generated, returning original diagnosis")
            return step1_output
        
        # Extract all unique states and their highest confidence scores
        combined_states = set()
        state_confidence_map = {}
        
        for output in result:
            for state, conf in zip(output.states, output.confidence):
                combined_states.add(state)
                # Keep the highest confidence for each state
                if state not in state_confidence_map or conf > state_confidence_map[state]:
                    state_confidence_map[state] = conf
        
        # Create the combined result
        final_states = list(combined_states)
        final_confidence = [state_confidence_map[state] for state in final_states]
        
        # Use the most comprehensive core issue from the results, or keep the original
        most_detailed_core_issue = core_reason
        for output in result:
            if len(output.core_issue) > len(most_detailed_core_issue):
                most_detailed_core_issue = output.core_issue
        final_final = ['Low Temperature', 'Stable Maintenance']
        # for state in final_states:
        #     if state in final_final:
        #         continue
        #     final_final.append(state)
        combined_result = Step1Output(
            core_issue=most_detailed_core_issue,
            states=final_final,
            confidence=final_confidence
        )
        
        print(f"  Combined revision result: {len(final_states)} states with avg confidence: {sum(final_confidence)/len(final_confidence):.1f}")
        return combined_result
    
    def step2(self, user_input: LocalLLMInput, step1_output: Step1Output) -> Step2Output:
        prompt = (
            role_and_task,
            goal_and_objectives,
            curr_env_status,
            history_context,
            environment_forecast,
            step2_brief.format(summary=step1_output.core_issue),
            plan_exploration,
            step2_functions_prompt,
            step2_output_prompt,
        )
        step2_prompt = "".join(prompt)
        
        step2_data = self._build_step1_data(user_input)
        step2_data.update({
            "core_issue": step1_output.core_issue,
            "states": step1_output.states,
            "confidence": step1_output.confidence
        })
        
        step2_prompt_template = PromptTemplate.from_template(step2_prompt)
        step2_chain = step2_prompt_template | self.planner_model

        try:
            step2_response = step2_chain.invoke(step2_data)
            json_parser = JsonOutputParser()
            parsed_json = json_parser.invoke(step2_response)
            step2_output = Step2Output.model_validate(parsed_json)
            return step2_output
        except Exception as e:
            print(f"[LocalPlanner] Error in step2: {e}")
            return Step2Output(action_plan=[])
        
    def _build_step2_data(self, user_input: LocalLLMInput, step1_output: Step1Output) -> dict:
        step1_data = self._build_step1_data(user_input)
        step2_data = {
            **step1_data,
            "states": step1_output.states,
            "core_issue": step1_output.core_issue,
        }
        return step2_data
    
    def step2_revised(self, user_input: LocalLLMInput, step1_output: Step1Output, step2_output: Step2Output) -> Step2Output:
        """
        Revise the initial step2 action plans by first evaluating them and then modifying them
        based on current environmental conditions and constraints.
        """
        def _build_part1_data() -> dict:
            """Build data for the first revision part (evaluation)"""
            prev_data = self._build_step2_data(user_input, step1_output)
            return {
                **prev_data,
                "solutions": [
                    f"Solution{idx}: {sol.description}" for idx, sol in enumerate(step2_output.action_plan, start=1)
                ]
            }
        
        def part_1() -> RevisedStep2Output:
            """First part: Evaluate and suggest revisions to existing solutions"""
            revised_step2_prompt = "".join([
                role_and_task,
                goal_and_objectives,
                revised_step2_prompt_part,
                revised_step2_output_prompt
            ])
            revised_step2_prompt_template = PromptTemplate.from_template(revised_step2_prompt)
            revised_step2_chain = revised_step2_prompt_template | self.planner_model
            revised_data = _build_part1_data()
            
            try:
                revised_response = revised_step2_chain.invoke(revised_data)
                json_parser = JsonOutputParser()
                parsed_json = json_parser.invoke(revised_response)
                revised_output = RevisedStep2Output.model_validate(parsed_json)
                return revised_output
            except Exception as e:
                print(f"[LocalPlanner] Error in revised_step2 part 1: {e}")
                try:
                    fixed_json = fix_and_validate_json(revised_response, RevisedStep2Output, self.json_fixer)
                    if fixed_json:
                        return RevisedStep2Output.model_validate(json.loads(fixed_json))
                except:
                    pass
                # Return default suggestions
                default_suggestions = []
                for idx, action in enumerate(step2_output.action_plan, start=1):
                    default_suggestions.append(ActionSuggestion(
                        solution_id=action.solution_id,
                        description=action.description,
                        new_plan="Maintain current approach due to processing error"
                    ))
                return RevisedStep2Output(action_plan=default_suggestions)
        
        def _build_part2_data(revised_output: RevisedStep2Output) -> dict:
            """Build data for the second revision part (modification)"""
            revised_solutions = [
                f"Solution{idx}: {sol.new_plan}" for idx, sol in enumerate(revised_output.action_plan, start=1)
            ]
            prev_data = _build_part1_data()
            return {
                **prev_data,
                "solutions": [
                    f"Solution{idx}: {sol.description}" for idx, sol in enumerate(step2_output.action_plan, start=1)
                ],
                "revised_step2_prompt_part": revised_solutions
            }
        
        def part_2(revised_output: RevisedStep2Output) -> Step2Output:
            """Second part: Modify the action plans based on the revision suggestions"""
            revised_step2_modify_prompt = "".join([
                role_and_task,
                goal_and_objectives,
                curr_env_status,
                step2_functions_prompt,
                revised_step2_modify_prompt_part,
                step2_output_prompt
            ])
            revised_step2_modify_prompt_template = PromptTemplate.from_template(revised_step2_modify_prompt)
            revised_step2_modify_chain = revised_step2_modify_prompt_template | self.planner_model
            revised_data = _build_part2_data(revised_output)
            
            try:
                revised_response = revised_step2_modify_chain.invoke(revised_data)
                json_parser = JsonOutputParser()
                parsed_json = json_parser.invoke(revised_response)
                final_output = Step2Output.model_validate(parsed_json)
                return final_output
            except Exception as e:
                print(f"[LocalPlanner] Error in revised_step2 part 2: {e}")
                try:
                    # Try to fix the JSON if possible
                    fixed_json = fix_and_validate_json(revised_response, Step2Output, self.json_fixer)
                    if fixed_json:
                        return Step2Output.model_validate(json.loads(fixed_json))
                except:
                    pass
                return step2_output
        
        try:
            print("  Running step2_revised part 1 (evaluation)...")
            revised_output = part_1()
            # time.sleep(8)
            print(f"  Part 1 completed with {len(revised_output.action_plan)} revised suggestions")
            
            print("  Running step2_revised part 2 (modification)...")
            final_output = part_2(revised_output)
            # time.sleep(8)
            print(f"  Part 2 completed with {len(final_output.action_plan)} final action plans")
            
            return final_output
            
        except Exception as e:
            print(f"[LocalPlanner] Error in step2_revised: {e}")
            # Return the original step2_output as ultimate fallback
            return step2_output

    def _analyze_solution_adjustments(self, action_plan: ActionPlan) -> List[SideEffectConcern]:
        concerns = []
        
        for func_call in action_plan.function_calls:
            func_name = func_call.name.lower()  # Use 'name' field
            arguments = func_call.arguments
            
            if 'fan' in func_name:
                if 'fan_speed_change' in arguments:
                    change = float(arguments['fan_speed_change'])
                    if abs(change) >= 15:
                        concerns.append(SideEffectConcern(
                            parameter_name="fan_speed",
                            change_magnitude=abs(change),
                            change_type="increase" if change > 0 else "decrease",
                            potential_impact="humidity_reduction" if change > 0 else "humidity_increase",
                            risk_level="high" if abs(change) >= 25 else "medium"
                        ))
                        
            elif 'led' in func_name or 'light' in func_name:
                if 'led_brightness_change' in arguments:
                    change = float(arguments['led_brightness_change'])
                    if abs(change) >= 20:
                        concerns.append(SideEffectConcern(
                            parameter_name="led_brightness",
                            change_magnitude=abs(change),
                            change_type="increase" if change > 0 else "decrease",
                            potential_impact="temperature_spike" if change > 0 else "photosynthesis_reduction",
                            risk_level="high" if abs(change) >= 30 else "medium"
                        ))
                        
            elif 'temp' in func_name:
                if 'temperature_change' in arguments:
                    change = float(arguments['temperature_change'])
                    if abs(change) >= 2.0:
                        concerns.append(SideEffectConcern(
                            parameter_name="temperature",
                            change_magnitude=abs(change),
                            change_type="increase" if change > 0 else "decrease",
                            potential_impact="plant_stress" if abs(change) >= 3.0 else "growth_disruption",
                            risk_level="high" if abs(change) >= 3.0 else "medium"
                        ))
        
        return concerns

    def _generate_side_effect_prompt(self, user_input: LocalLLMInput, action_plan: ActionPlan, concerns: List[SideEffectConcern]) -> str:
        base_prompt = f"""You have proposed the following solution: {action_plan.description}

The coordination script has identified potential significant adjustments in your solution:
"""
        
        for concern in concerns:
            adjustment_desc = f"{concern.change_type} {concern.parameter_name} by {concern.change_magnitude}%"
            if concern.parameter_name == "temperature":
                adjustment_desc = f"{concern.change_type} {concern.parameter_name} by {concern.change_magnitude}°C"
                
            base_prompt += f"\n- {adjustment_desc.title()}"
            base_prompt += f"  Potential impact: {concern.potential_impact.replace('_', ' ')}"
            base_prompt += f"  Risk level: {concern.risk_level}"
        
        base_prompt += f"""

Please evaluate the potential side effects of your proposed adjustments:

Current environmental conditions:
- Internal temperature: {user_input.internal_temp}°C
- Ideal range: {user_input.ideal_temp_range[0]}-{user_input.ideal_temp_range[1]}°C
- Fan status: {'ON' if user_input.fan_status else 'OFF'}
- LED status: {'ON' if user_input.led_light_status else 'OFF'}
- Recent temperature trend: {user_input.history_temp_change[-3:] if len(user_input.history_temp_change) >= 3 else user_input.history_temp_change}

Specific concerns to address:
"""
        
        for concern in concerns:
            if concern.potential_impact == "humidity_reduction":
                base_prompt += f"""
- Your proposed fan speed {concern.change_type} of {concern.change_magnitude}% to manage temperature. Please evaluate: Could this cause humidity to drop below the optimal 60-80% range? Consider the assess_fan_humidity_impact function implications."""
                
            elif concern.potential_impact == "humidity_increase":
                base_prompt += f"""
- Your proposed fan speed {concern.change_type} of {concern.change_magnitude}% may reduce air circulation. Please evaluate: Could this cause humidity to rise above 80% and create fungal risks?"""
                
            elif concern.potential_impact == "temperature_spike":
                base_prompt += f"""
- Your proposed LED brightness {concern.change_type} of {concern.change_magnitude}% will increase heat generation. Please evaluate: Could this cause temperature to exceed {user_input.ideal_temp_range[1]}°C despite other cooling measures?"""
                
            elif concern.potential_impact == "photosynthesis_reduction":
                base_prompt += f"""
- Your proposed LED brightness {concern.change_type} of {concern.change_magnitude}% will reduce light intensity. Please evaluate: Could this significantly impact plant photosynthesis and growth rates?"""
                
            elif concern.potential_impact == "plant_stress":
                base_prompt += f"""
- Your proposed temperature {concern.change_type} of {concern.change_magnitude}°C is substantial. Please evaluate: Could this rapid change cause plant stress or shock?"""
        
        base_prompt += """

Force yourself to think about second-order effects and provide:
1. Risk assessment for each identified concern
2. Potential mitigation strategies
3. Recommendation on whether to proceed, modify, or reject the solution
"""
        
        return base_prompt

    def _evaluate_side_effects(self, user_input: LocalLLMInput, step2_output: Step2Output) -> SideEffectEvaluationOutput:
        evaluations = []
        
        for action_plan in step2_output.action_plan:
            concerns = self._analyze_solution_adjustments(action_plan)
            
            if concerns:
                print(f"    Evaluating side effects for {action_plan.solution_id} ({len(concerns)} concerns)")
                
                try:
                    side_effect_prompt = self._generate_side_effect_prompt(user_input, action_plan, concerns)
                    
                    full_prompt = f"""{role_and_task}
{goal_and_objectives}
{curr_env_status}
{side_effect_prompt}

Please respond in JSON format:
{{
    "solution_id": "{action_plan.solution_id}",
    "side_effects": [
        {{
            "parameter_name": "string: The parameter being adjusted",
            "change_magnitude": "number: The magnitude of change",
            "change_type": "string: increase or decrease", 
            "potential_impact": "string: The potential negative impact",
            "risk_level": "string: low, medium, or high"
        }}
    ],
    "overall_risk_assessment": "string: Overall assessment of the risks",
    "recommended_action": "string: proceed, modify, or reject",
    "confidence": "number: Confidence level 1-10"
}}
"""
                    
                    evaluation_response = self.planner_model.invoke([{"role": "user", "content": full_prompt}])
                    json_parser = JsonOutputParser()
                    parsed_json = json_parser.invoke(evaluation_response)
                    evaluation = SideEffectEvaluation.model_validate(parsed_json)
                    evaluations.append(evaluation)
                    
                    # time.sleep(8)
                    print(f"      Risk assessment: {evaluation.overall_risk_assessment}")
                    print(f"      Recommendation: {evaluation.recommended_action}")
                    
                except Exception as e:
                    print(f"[LocalPlanner] Error in side effect evaluation for {action_plan.solution_id}: {e}")
                    default_side_effects = []
                    for concern in concerns:
                        default_side_effects.append({
                            "parameter_name": concern.parameter_name,
                            "change_magnitude": concern.change_magnitude,
                            "change_type": concern.change_type,
                            "potential_impact": concern.potential_impact,
                            "risk_level": concern.risk_level
                        })
                    
                    default_evaluation = SideEffectEvaluation(
                        solution_id=action_plan.solution_id,
                        side_effects=default_side_effects,
                        overall_risk_assessment=f"Unable to fully evaluate due to processing error. Identified {len(concerns)} potential concerns.",
                        recommended_action="modify" if any(c.risk_level == "high" for c in concerns) else "proceed",
                        confidence=3
                    )
                    evaluations.append(default_evaluation)
                    print(f"      Using default evaluation for {action_plan.solution_id}")
            else:
                print(f"    No significant adjustments detected for {action_plan.solution_id}, skipping evaluation")
        
        return SideEffectEvaluationOutput(evaluations=evaluations)

    def _filter_solutions_by_side_effects(self, step2_output: Step2Output, side_effect_evaluation: SideEffectEvaluationOutput) -> Step2Output:
        filtered_solutions = []
        evaluation_lookup = {eval.solution_id: eval for eval in side_effect_evaluation.evaluations}
        
        for action_plan in step2_output.action_plan:
            evaluation = evaluation_lookup.get(action_plan.solution_id)
            
            if evaluation:
                if evaluation.recommended_action == "proceed":
                    filtered_solutions.append(action_plan)
                    print(f"  Proceeding with {action_plan.solution_id}")
                elif evaluation.recommended_action == "modify":
                    modified_description = f"{action_plan.description} (CAUTION: Side effects noted - {evaluation.overall_risk_assessment})"
                    modified_plan = ActionPlan(
                        solution_id=action_plan.solution_id,
                        description=modified_description,
                        confidence=max(1, action_plan.confidence - 1),
                        function_calls=action_plan.function_calls
                    )
                    filtered_solutions.append(modified_plan)
                    print(f"  Flagging {action_plan.solution_id} for caution due to side effect concerns")
                elif evaluation.recommended_action == "reject":
                    print(f"  Rejecting {action_plan.solution_id} due to high-risk side effects")
            else:
                filtered_solutions.append(action_plan)
        
        return Step2Output(action_plan=filtered_solutions)

    def _build_step3_prompt(self, simulated_plan: List[ActionPlan], simulated_results: List[str]) -> str:
        base_prompt = """
        The simulated results are as follows:
        """
        for idx, (plan, result) in enumerate(zip(simulated_plan, simulated_results), start=1):
            base_prompt += f"- {plan.solution_id}: {result}\n"
        base_prompt += step3_decision_prompt
        step3_prompt = "".join([
            role_and_task,
            goal_and_objectives,
            # curr_env_status,
            
            diagnosis_brief,
            base_prompt,
            step3_decision_prompt,
            step3_output_prompt 
        ])
        return step3_prompt
    
    def _build_step3_data(self, user_input: LocalLLMInput, step1_output: Step1Output) -> dict:
        return self._build_step2_data(user_input, step1_output)

    def step3(self, user_input: LocalLLMInput, step1_output: Step1Output, step2_output: Step2Output, simulated_results: List[str]) -> Step3Output:
        step3_prompt = self._build_step3_prompt(step2_output.action_plan, simulated_results)
        step3_prompt_template = PromptTemplate.from_template(step3_prompt)
        step3_chain = step3_prompt_template | self.planner_model
        step3_data =  self._build_step3_data(user_input, step1_output)
        try:
            step3_response = step3_chain.invoke(step3_data)
            json_parser = JsonOutputParser()
            parsed_json = json_parser.invoke(step3_response)
            step3_output = Step3Output.model_validate(parsed_json)
            return step3_output
        except Exception as e:
            print(f"[LocalPlanner] Error in step3: {e}")
        fixed_json = fix_and_validate_json(parsed_json, Step3Output, self.json_fixer)
        if fixed_json:
            return Step3Output.model_validate(fixed_json)
        else:
            raise ValueError("Failed to generate a valid revised step3 output after repair attempts.")

    def generate_plan(self, user_input: LocalLLMInput) -> LocalPlannerOutput:
        self.state = user_input
        current_att = 0
        for attempt in range(1, self.max_tries + 1):
            # current_att
            try:
                ansi_cprint("# Starting plan generation...", fg="green", style="bold")
                ansi_cprint(f"# Attempt {attempt}/{self.max_tries}", fg="white", style="bold")
                # print(f"Plan generation attempt {attempt}/{self.max_tries}")
                
                ansi_cprint("## Running step1 (diagnosis)...", fg="green", style="bold")
                step1_output = self.step1(user_input)
                # time.sleep(1)
                ansi_cprint(f"Step1 completed: {step1_output.core_issue}", fg="yellow")
                ansi_cprint(f"Diagnosed states: {step1_output.states}", fg="yellow")

                corrected_diagnosis = self._validate_diagnosis_consistency(user_input, step1_output)
                if corrected_diagnosis:
                    step1_output = corrected_diagnosis

                ansi_cprint("Running revised_step1...")
                revised_step1_output = self.revised_step1(user_input, step1_output)
                # time.sleep(2)
                ansi_cprint(f"Revised Step1 completed: {revised_step1_output.core_issue}", fg="yellow", style="bold")
                ansi_cprint(f"Diagnosed states: {revised_step1_output.states}", fg="yellow", style="bold")

                num_max_tries = 3
                current_tries = 0
                while current_tries < num_max_tries:
                    ansi_cprint(f"  Attempt {current_tries + 1}/{num_max_tries}", fg="white")
                    ansi_cprint("## Running step2 (action planning)...", fg="green", style="bold")
                    step2_output = self.step2(user_input, revised_step1_output)
                    # time.sleep(10)
                    print(f"Step2 completed with {len(step2_output.action_plan)} solutions")
                    
                    print("Running step2_revised...")
                    step2_revised_output = self.step2_revised(user_input, revised_step1_output, step2_output)
                    # time.sleep(2)
                    print("Revised Step2 completed")
                    
                    print("Running side effect evaluation...")
                    side_effect_evaluation = self._evaluate_side_effects(user_input, step2_revised_output)
                    # time.sleep(1)
                    print(f"Side effect evaluation completed with {len(side_effect_evaluation.evaluations)} evaluations")
                    
                    filtered_step2_output = self._filter_solutions_by_side_effects(step2_revised_output, side_effect_evaluation)
                    print(f"Filtered Step2 output: {len(filtered_step2_output.action_plan)} solutions after side effect filtering")

                    # ansi
                    all_function_calls = [func_call for action_plan in filtered_step2_output.action_plan for func_call in action_plan.function_calls]
                    if all_function_calls:
                        ansi_cprint("### function calls...", fg="cyan", style="bold")
                        simulated_results = []
                        for call in all_function_calls:
                            try:
                                print(f"Registered function: '{call.name}'")
                                if 'fan' in call.name.lower():
                                    speed_change = call.arguments.get('fan_speed_change', 0)
                                    result = f"Predicted temperature will {'increase' if speed_change < 0 else 'decrease'} by {abs(2):.2f}°C, reaching {10:.2f}°C."
                                    simulated_results.append(result)
                                elif 'led' in call.name.lower():
                                    brightness_change = call.arguments.get('led_brightness_change', 0)
                                    result = f"Predicted temperature will {'increase' if brightness_change > 0 else 'decrease'} by {abs(2):.2f}°C, reaching {20:.2f}°C."
                                    simulated_results.append(result)
                                else:
                                    simulated_results.append(f"Function {call.name} executed with {call.arguments}")
                            except Exception as e:
                                print(f"[LocalPlanner] Error simulating function {call.name}: {e}")
                                simulated_results.append(f"Simulation error: {str(e)}")
                        ansi_cprint(f"Simulation completed with {len(simulated_results)} results", fg="yellow", style="bold")
                    else:
                        simulated_results = []
                        ansi_cprint("No function calls to simulate", fg="red")

                    if len(simulated_results) > 0:
                        break

                ansi_cprint("## Running step3...", fg="green", style="bold")
                step3_output = self.step3(user_input, revised_step1_output, filtered_step2_output, simulated_results)
                # time.sleep(8)
                print(f"Step3 completed: {step3_output.final_decision}")
                
                print("Running step3 decision evaluation...")
                step3_evaluation = self._evaluate_step3_decision(user_input, step3_output, filtered_step2_output.action_plan, simulated_results)
                # time.sleep(10)
                print(f"Step3 evaluation completed: {step3_evaluation.decision_quality} - {step3_evaluation.recommended_action}")
                
                print("Running step3_revised...")
                revised_step3_output = self.step3_revised(user_input, revised_step1_output, filtered_step2_output, step3_output, step3_evaluation, simulated_results)
                # time.sleep(10)
                ansi_cprint(f"Revised Step3 completed: {revised_step3_output.final_decision}", fg="yellow")

                if revised_step3_output.final_decision == "NO_SOLUTION" or revised_step3_output.final_decision == "re_assess_solution" and attempt == self.max_tries:
                    ansi_cprint("Continue with the best simulated plan...", fg="yellow")
                    continue

                if self._should_regenerate_all_plans(step3_evaluation, filtered_step2_output.action_plan):
                    ansi_cprint("Step3 evaluation suggests regenerating all plans, retrying...", fg="yellow")
                    continue
                
                if revised_step3_output.final_decision != "NO_SOLUTION" and revised_step3_output.final_decision != "re_assess_solution":
                    chosen_plan = None
                    for plan in filtered_step2_output.action_plan:
                        if plan.solution_id == revised_step3_output.final_decision:
                            chosen_plan = plan
                            break
                    
                    if chosen_plan:
                        ansi_cprint(f"Plan generation successful: {revised_step3_output.final_decision}", fg="yellow", style="bold")
                        return LocalPlannerOutput(
                            comments=revised_step3_output.reason,
                            solution_action=chosen_plan
                        )
                    else:
                        print(f"Chosen plan {revised_step3_output.final_decision} not found in available solutions")
                        if filtered_step2_output.action_plan:
                            fallback_plan = filtered_step2_output.action_plan[0]
                            print(f"Using fallback plan: {fallback_plan.solution_id}")
                            return LocalPlannerOutput(
                                comments="Fallback to first available plan due to planning inconsistency",
                                solution_action=fallback_plan
                            )
                    continue
                else:
                    continue 
                    
            except Exception as e:
                print(f"[LocalPlanner] Error in generate_plan attempt {attempt}: {e}")
                if attempt == self.max_tries:
                    default_action = ActionPlan(
                        solution_id="ERROR_FALLBACK",
                        description="Failed to generate plan due to processing errors",
                        function_calls=[],
                        confidence=1
                    )
                    return LocalPlannerOutput(
                        comments="Plan generation failed after multiple attempts",
                        solution_action=default_action
                    )
        
        default_action = ActionPlan(
            solution_id="THE BEST ONE",
            description="Failed to generate plan after maximum attempts, using the best solution available",
            function_calls=[],
            confidence=1
        )
        return LocalPlannerOutput(
            comments="Maximum attempts exceeded",
            solution_action=default_action
        )

    def _evaluate_step3_decision(self, user_input: LocalLLMInput, step3_output: Step3Output, action_plans: List[ActionPlan], simulation_results: List[str]) -> Step3EvaluationOutput:
        print("  Evaluating step3 decision quality...")
        
        selected_plan = None
        for plan in action_plans:
            if plan.solution_id == step3_output.final_decision:
                selected_plan = plan
                break
        
        if not selected_plan:
            return Step3EvaluationOutput(
                decision_quality="poor",
                meets_target_requirements=False,
                confidence_assessment=1,
                recommended_action="regenerate_plans",
                evaluation_reason="Selected plan not found in available options",
                alternative_suggestions=[]
            )
        
        concerns = []
        
        if selected_plan.confidence < 5:
            concerns.append(f"Selected plan has low confidence ({selected_plan.confidence}/10)")
        
        better_alternatives = [
            plan for plan in action_plans 
            if plan.solution_id != step3_output.final_decision and plan.confidence > selected_plan.confidence
        ]
        
        simulation_quality = "good"
        if simulation_results:
            for result in simulation_results:
                if any(keyword in result.lower() for keyword in ["error", "fail", "risk", "exceed"]):
                    concerns.append(f"Simulation shows potential issues: {result}")
                    simulation_quality = "concerning"
        
        target_alignment = self._check_target_alignment(user_input, selected_plan, simulation_results)
        
        if len(concerns) == 0 and target_alignment and simulation_quality == "good":
            decision_quality = "excellent"
            meets_requirements = True
            recommended_action = "proceed"
        elif len(concerns) <= 1 and target_alignment:
            decision_quality = "good"
            meets_requirements = True
            recommended_action = "proceed_with_caution"
        elif len(concerns) <= 2:
            decision_quality = "fair"
            meets_requirements = False
            recommended_action = "select_alternative" if better_alternatives else "regenerate_plans"
        else:
            decision_quality = "poor"
            meets_requirements = False
            recommended_action = "regenerate_plans"
        
        alternative_suggestions = []
        if better_alternatives:
            alternative_suggestions = [
                f"Consider {alt.solution_id} (confidence: {alt.confidence}): {alt.description[:100]}..."
                for alt in better_alternatives[:2]
            ]
        
        evaluation_reason = f"Decision quality: {decision_quality}. "
        evaluation_reason += f"Concerns: {len(concerns)}. "
        evaluation_reason += f"Target alignment: {'Yes' if target_alignment else 'No'}. "
        evaluation_reason += f"Simulation quality: {simulation_quality}."
        
        return Step3EvaluationOutput(
            decision_quality=decision_quality,
            meets_target_requirements=meets_requirements,
            confidence_assessment=max(1, min(10, selected_plan.confidence - len(concerns))),
            recommended_action=recommended_action,
            evaluation_reason=evaluation_reason,
            alternative_suggestions=alternative_suggestions
        )
    
    def _check_target_alignment(self, user_input: LocalLLMInput, selected_plan: ActionPlan, simulation_results: List[str]) -> bool:
        current_temp = user_input.internal_temp
        target_low, target_high = user_input.ideal_temp_range
        if target_low <= current_temp <= target_high:
            return True
        
        for func_call in selected_plan.function_calls:
            if current_temp < target_low:  # 需要升温
                if 'led' in func_call.name.lower() and func_call.arguments.get('led_brightness_change', 0) > 0:
                    return True
                if 'fan' in func_call.name.lower() and func_call.arguments.get('fan_speed_change', 0) < 0:
                    return True
            elif current_temp > target_high:  # 需要降温
                if 'fan' in func_call.name.lower() and func_call.arguments.get('fan_speed_change', 0) > 0:
                    return True
                if 'led' in func_call.name.lower() and func_call.arguments.get('led_brightness_change', 0) < 0:
                    return True
        
        return len(selected_plan.function_calls) == 0  # 无操作在某些情况下也是合理的

    def step3_revised(self, user_input: LocalLLMInput, step1_output: Step1Output, step2_output: Step2Output, 
                     step3_output: Step3Output, step3_evaluation: Step3EvaluationOutput, 
                     simulation_results: List[str]) -> Step3Output:
        print("  Running step3_revised...")
        if step3_evaluation.recommended_action == "proceed":
            print("    Step3 evaluation suggests proceeding with current decision")
            return step3_output
        
        elif step3_evaluation.recommended_action == "proceed_with_caution":
            print("    Step3 evaluation suggests proceeding with caution")
            revised_reason = f"{step3_output.reason} (CAUTION: {step3_evaluation.evaluation_reason})"
            return Step3Output(
                final_decision=step3_output.final_decision,
                reason=revised_reason
            )
        
        elif step3_evaluation.recommended_action == "select_alternative":
            print("    Step3 evaluation suggests selecting alternative plan")
            alternative_plans = [
                plan for plan in step2_output.action_plan 
                if plan.solution_id != step3_output.final_decision
            ]
            
            if alternative_plans:
                best_alternative = max(alternative_plans, key=lambda x: x.confidence)
                revised_reason = f"Revised decision: Selected {best_alternative.solution_id} instead of {step3_output.final_decision} due to evaluation concerns: {step3_evaluation.evaluation_reason}"
                return Step3Output(
                    final_decision=best_alternative.solution_id,
                    reason=revised_reason
                )
        
        elif step3_evaluation.recommended_action == "regenerate_plans":
            print("    Step3 evaluation suggests regenerating plans")
            return Step3Output(
                final_decision="re_assess_solution",
                reason=f"Plan regeneration required due to evaluation concerns: {step3_evaluation.evaluation_reason}"
            )
        
        return step3_output
    
    def _should_regenerate_all_plans(self, step3_evaluation: Step3EvaluationOutput, 
                                   available_plans: List[ActionPlan]) -> bool:
        if all(plan.confidence < 4 for plan in available_plans):
            return True
        if step3_evaluation.decision_quality == "poor" and step3_evaluation.confidence_assessment < 3:
            return True
        if not step3_evaluation.meets_target_requirements and not step3_evaluation.alternative_suggestions:
            return True
        
        return False
    


