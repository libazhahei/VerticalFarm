from langchain_core.prompts import PromptTemplate

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
- Humidity: {humidity}%
- External Temperature: {temperature_end}°C
- Plant Status: {plant_status}
- Current Photoperiod: Lights {photoperiod_status} (ON/OFF)
- Device Status:
  - Fan: {fan_status} (0-100% RPM)
  - LED Light: {led_light_status} (0-100% intensity)
  - Device Health: {device_health}
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

playbook_context = """
# Recalled Operational Playbook (RAG)
The following strategy cases were retrieved from the daily playbook based on current conditions:
{playbook_context}
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
                        "key": value,
                    }},
                    "simulating_time": "string: The time period for the simulation in minutes, e.g., '15 minutes'"
                }}
            ],
            "confidence": "int: A confidence score between 0 and 10 indicating how confident you are in this solution."
        }}
    ]
}}
"""

step2_functions_prompt = """
[
    {{ "name": "predict_temp_change_with_led_action", "description": "Predict the temperature change over the next 15 minutes given a change in LED brightness.", "parameters": {{ "type": "object", "properties": {{ "led_brightness_change": {{ "type": "number", "description": "Percentage change in LED brightness, if no fans open e.g., -15 for -15%" }} }}, "required": ["led_brightness_change"] }} }},
    {{ "name": "predict_temp_change_with_fan_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed.", "parameters": {{ "type": "object", "properties": {{ "fan_speed_change": {{ "type": "number", "description": "temperature target change in fan speed, if no leds open e.g., 14.5" }} }}, "required": ["fan_speed_change"] }} }},
    {{ "name": "predict_temp_change_with_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed and LED brightness.", "parameters": {{ "type": "object", "properties": {{ "fan_speed_change": {{ "type": "number" }}, "led_brightness_change": {{ "type": "number" }} }}, "required": ["fan_speed_change", "led_brightness_change"] }} }}
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
            "new_plan": "string: A new plan to address the issue, if necessary"
        }}
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
Diagnosis summary: {summary}
"""

step3_output_prompt = """
# Output Format
Please return a JSON object with the following structure:
{{
    "reason": "string: The rationale behind the chosen solution",
    "final_decision": "string: The function call to execute the chosen solution, e.g., 'SOLUTION_01' or 're_assess_solution'"
}}
"""

final_command_prompt = """
# Command Generation
Based on the selected plan and the current environment, generate a structured MQTT control command JSON.
The output must include fields: fan_pwm, led_pwm, pid, and rationale.
fan_pwm and led_pwm are percentages from 0 to 100.
"""

FINAL_COMMAND_PROMPT = PromptTemplate.from_template(
    role_and_task + goal_and_objectives + curr_env_status + history_context + environment_forecast + final_command_prompt
)
