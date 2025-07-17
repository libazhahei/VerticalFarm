import asyncio

from attr import dataclass
from langchain_core.output_parsers import JsonOutputParser

# import openai
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_perplexity import ChatPerplexity
from pydantic import SecretStr

system_prompt = """
You are an intelligent assistant specializing in environmental monitoring for indoor vertical farms.
Based on the provided daily sensor data, please generate a structured report with the following sections:

1. Summary Statistics: Average, min, and max values for temperature, humidity, and light (PAR).
2. Anomaly Detection: Identify any high-temperature (>30°C), low-humidity (<50%), or low-light (<100 PAR) conditions, along with affected sensor IDs and time ranges.
3. Recommended Actions: Suggest control adjustments (e.g., fan speed, humidity level, LED intensity) to correct problems.
4. Overall Assessment: Evaluate whether the farm's environment is healthy or needs manual intervention.

Format the output in clear sections with bullet points or labels.
"""

user_prompt = "Please analyze the attached sensor data and generate a report including summary statistics, anomaly detection, recommended control actions, and overall farm status"

# def get_daily_report():

    # # upload file
    # # TODO: generate daily sensor data file
    # file_response = openai.files.create(
    #     file=open("fake_data.csv", "rb"),
    #     purpose="assistants"
    # )
    # print("Uploaded file:", file_response.id)

    # # send the request to GPT-4o
    # response = openai.chat.completions.create(
    #     model="gpt-4o",
    #     messages=[
    #         {"role": "system", "content": system_prompt},
    #         {"role": "user", "content": user_prompt}
    #     ],
    #     file_ids=[file_response.id],
    #     temperature=0.4
    # )

    # return response["choices"][0]["message"]["content"]

@dataclass
class ChainPart1UserInput:
    """
    Represents the user input for the first part of the chain.
    """

    plant: str
    growth_stage: str
    target_orientation: str
    comments: str

    def to_dict(self) -> dict:
        return {
            "plant": self.plant,
            "growth_stage": self.growth_stage,
            "target_orientation": self.target_orientation,
            "comments": self.comments
        }

class DailyPlan:
    def __init__(self, openai_key: str, preplexity_key: str) -> None:
        self.preplexity_key = preplexity_key
        self.openai_key = openai_key

    def _search_knowledge(self, curr_status: ChainPart1UserInput) -> dict:
        P1_prompt_template = """
        ## Role and Task
        You are an agricultural science research assistant. 
        Based on authoritative scientific literature and open-access agricultural databases. 
        your task is to provide optimal environmental parameters for plant cultivation.

        ## Input Information:
        - Plant: {plant}
        - Growth Stage: {growth_stage}
        - Target Orientation: {target_orientation} (e.g., "maximize yield", "accelerate growth", "enhance flavor", etc.)

        ## Output Format (Strict JSON):

        {{
        "temperature_celsius": {{
            "day_range": [min, max],
            "night_range": [min, max]
        }},
        "relative_humidity_percent": {{
            "ideal_range": [min, max]
        }},
        "ppfd_umol_m2_s": "optimal_value_or_range",
        "dli_mol_m2_day": "optimal_value_or_range",
        "references": [
            {{
            "name": "Source Title or Dataset Name",
            "link": "https://source-link"
            }}
        ],
        "notes": "Concise notes on key considerations for this stage of growth, such as nutrient uptake sensitivity, light period preferences, CO2 enrichment compatibility, or temperature stress thresholds."
        }}

        ## Additional Guidelines:
        - Ensure that values are evidence-based, ideally from peer-reviewed papers, government guidelines, or reputable horticultural sources.
        - If data is not available for the exact growth stage, return best estimates with clarification in notes.
        - For "ppfd_umol_m2_s" and "dli_mol_m2_day", provide either a single optimal value or a scientifically recommended range.
        - "references" must include at least one valid citation in the format: {{ "name": ..., "link": ... }}.

        """

        P1_prompt = PromptTemplate.from_template(P1_prompt_template)
        perplexity_llm = ChatPerplexity(model="sonar", 
                                        temperature=0.5, 
                                        timeout=30, 
                                        api_key=SecretStr(self.preplexity_key))


        json_parser_p1 = JsonOutputParser()

        chain_part1 = P1_prompt | perplexity_llm 
        response_1 = chain_part1.invoke(
            curr_status.to_dict(),
        )
        response_1_json = json_parser_p1.invoke(response_1)
        return response_1_json

    def _prepare_input(self, original_input_json: dict, p1_output: dict) -> dict:
        return {
        "plant": original_input_json["plant"],
        "growth_stage": original_input_json["growth_stage"],
        "target_orientation": original_input_json["target_orientation"],
        "temperature_celsius": p1_output["temperature_celsius"],
        "relative_humidity_percent": p1_output["relative_humidity_percent"],
        "ppfd_umol_m2_s": p1_output["ppfd_umol_m2_s"],
        "dli_mol_m2_day": p1_output["dli_mol_m2_day"],
        "light_lux": [15000, 20000],  # Example value, adjust as needed
        "notes": p1_output["notes"],
        "fan_type": "exhaust",
        "fan_capacity": "3400 RPM",
        "LED_light_type": "full spectrum",
        "LED_light_highest": "23000 lux", 
        "LED_light_minimum": "10 lux",
        "LED_light_color": "4000K",
        "Room_type": "Vertical Farm, closed system",
        "Room_size": "25 cm x 20 cm x 25 cm each layer",
        "Room_layers": 2,
        "location": "Sydney, Indoor",
        "season": "Winter",
        "environmental_temperature_min": 7,  # Example value, adjust as needed
        "environmental_temperature_max": 14,  # Example value, adjust as needed
        "environmental_humidity": 51  # Example value, adjust as needed
    }

    async def _generate_general_target(self, curr_status: ChainPart1UserInput, p1_output: dict) -> dict:
        P2_prompt_template = """

        ## Role & Context
        You are a world-class Controlled Environment Agriculture (CEA) AI expert. 
        You have been provided with all necessary background information and scientific objectives. 
        Your task is to develop a comprehensive, actionable environmental control strategy for a minimalistic vertical farm setup.

        ## Global Information Provided
        - **Original Request:** {plant}, Growth Stage: {growth_stage}, Orientation: {target_orientation}
        - **Scientific Ideal Environment:**  
        - Temperature (°C): {temperature_celsius}
        - Relative Humidity (%): {relative_humidity_percent}
        - PPFD (µmol/m²/s): {ppfd_umol_m2_s}
        - DLI (mol/m²/day): {dli_mol_m2_day}
        - Notes: {notes}
        - **Available Equipment:**  
        - Fan: {fan_type}, {fan_capacity}
        - LED Light: {LED_light_type}, Max: {LED_light_highest}, Min: {LED_light_minimum}, Color: {LED_light_color}
        - **Room Specifications:**  
        - Type: {Room_type}
        - Size: {Room_size}
        - Layers: {Room_layers}
        - ""Location & Season:**
        - Location: {location}
        - Season: {season}
        - Environmental temprature: from {environmental_temperature_min} to {environmental_temperature_max}
        - Environmental humidity: {environmental_humidity}
        ---

        ## Output Instructions

        You must output only a JSON object in the following structure. Do not include any explanation or commentary. 
        Fill in all fields with specific, concise, and actionable content based on the provided parameters and your expert knowledge.

        {{
        "lighting_strategy": {{
            "photoperiod_hours": <number: Recommended daily light hours>,
            "daytime_target_lux": [<number: min>, <number: max>],
            "notes": "<string: Notes or rationale for lighting choices>"
        }},
        "climate_strategy": {{
            "day": {{
            "temperature_celsius": [<number:min>, <number:max>],
            "humidity_percent": [<number:min>, <number:max>]
            }},
            "night": {{
            "temperature_celsius": [<number:min>, <number:max>],
            "humidity_percent": [<number:min>, <number:max>]
            }},
            "control_logic": "<string: Describe how to use only the fan and LED light to achieve the above targets, referencing equipment specs and room size.>"
        }},
        "manual_check_recommendations": [
            {{task: <string: Check Item #1>, todo: <string: Visual indicator to check #1>}},
            {{task: <string: Check Item #2>, todo: <string: Visual indicator to check #2>}},
            // ...add more as needed
        ],
        "strategy_failure_escalation": [{{
            "condition": "<string: any condition that would indicate the strategy is failing>",
            "detection_period": "<string: any period of time that would indicate the condition is failing>",
            "equipment_limitation_considered": "<string: any limitation of the equipment that would cause the condition to fail>",
            "location_season_weather_factors": "<string: any location, season, or weather factors that would cause the condition to fail>",
            "recovery_suggestion": "<string: any suggestion to recover from the condition>",'>"
        }}, ... add more as needed],
        }}

        ---

        ## Requirements:
        - Strictly follow the above JSON structure.
        - Reference all parameters appropriately.
        - Do not include any extra text before or after the JSON object.
        - Ensure all values are concrete and actionable.
        - If a value is a range, use an array (e.g., [15000, 20000]).
        - Use clear, concise English.
        - “strategy_failure_escalation” must include at least two detailed failure conditions, each with specific detection period, equipment limitation, location/season/weather factors, alert action, and recovery suggestion.


        """
        P2_prompt = PromptTemplate.from_template(P2_prompt_template)
        task2_llm = ChatOpenAI(
            model="gpt-4.1",
            api_key=SecretStr(self.openai_key),
        )
        json_parser_p2 = JsonOutputParser()
        chain_part2 = P2_prompt | task2_llm | json_parser_p2
        p2_input = self._prepare_input(curr_status.to_dict(), p1_output)
        response_2 = chain_part2.ainvoke(
            p2_input
        )
        return await response_2

    async def _generate_strategy(self, curr_status: ChainPart1UserInput, p1_output: dict) -> dict:
        P3_prompt_template = """
        ## Core Task & Role

        You are an intelligent environmental control agent responsible for managing the microclimate within a closed vertical farm chamber.  
        Your core task is: Based on the global parameters provided below, **generate a comprehensive, state-based 15-minute control strategy set**. This strategy set should function as an "operational playbook" that covers all key environmental variations throughout the day (including both "lights-on" daytime and "lights-off" nighttime periods).

        Your only available controls are: 1) a variable-speed fan, and 2) dimmable LED lights. No other equipment (heaters, coolers, dehumidifiers, etc.) may be used.

        ## Global Information Provided

        - **Original Request:** {plant}, Growth Stage: {growth_stage}, Orientation: {target_orientation}
        - **Scientific Ideal Environment:**  
        - Temperature (°C): {temperature_celsius}
        - Relative Humidity (%): {relative_humidity_percent}
        - PPFD (µmol/m²/s): {ppfd_umol_m2_s}
        - DLI (mol/m²/day): {dli_mol_m2_day}
        - Notes: {notes}
        - **Available Equipment:**  
        - Fan: {fan_type}, {fan_capacity}
        - LED Light: {LED_light_type}, Max: {LED_light_highest}, Min: {LED_light_minimum}, Color: {LED_light_color}
        - **Room Specifications:**  
        - Type: {Room_type}
        - Size: {Room_size}
        - Layers: {Room_layers}
        - **Location & Season:**
        - Location: {location}
        - Season: {season}
        - Environmental temprature: from {environmental_temperature_min} to {environmental_temperature_max}
        - Environmental humidity: {environmental_humidity}

        ---

        ## Core Instructions

        1.  **State-Space Analysis:**
            Your primary task is not to wait for real-time data, but to **anticipate and define key environmental states**. Systematically consider all major combinations in which "temperature" and "relative humidity" deviate from the "scientific ideal". You must at least cover these core scenarios:
            - **High Temp & High Humidity:** Both exceed ideal upper limits.
            - **High Temp & Low Humidity:** Temperature too high, humidity too low.
            - **Ideal Temp & High Humidity:** Temperature within range, humidity too high.
            - **Low Temp & High Humidity:** Temperature too low (often at night), humidity too high.
            - **All Ideal Conditions:** All parameters within optimal range.
            - **Night Mode:** Lights off, no photosynthesis, but temperature and humidity still need management.

        2.  **Dynamic Trade-off Analysis:**
            In your analysis, clearly state the physiological risks and interlinked effects of each control action. For example:
            - **Increase fan speed:** Promotes transpiration, may reduce leaf surface temperature and chamber humidity, but increases energy use.
            - **Dim LED:** Reduces PPFD and DLI, directly decreases photosynthesis, but also reduces heat load.
            - **LED Off (Night):** Stops heat input and photosynthesis; fan is the only tool left for humidity and condensation prevention.

        3.  **Generate 5-7 Key Decision Cases:**
            Based on the above, generate 5 to 7 **most representative, critical, or high-risk** environmental state combinations. For each, provide a control solution following the output format below, with precise, quantitative, and actionable content.

        ## Output Instructions

        - Your answer **must be and only be** a JSON object. Do not add any explanation or comments outside the JSON object.
        - Every instruction must be strictly quantitative.
        - All logic must be IF-THEN conditional, and applicable to a tactical 15-minute time window.
        - All trade-offs and risks must be explicitly described in the analysis.
        - For each case, fill in the following five fields:

        1.  **Condition_IF:**
            - Clearly describe a specific environmental state using explicit, quantitative thresholds or ranges.
            - Example: "Temperature > 25°C AND Humidity > 80% (Lights ON)"

        2.  **Diagnosis_Tradeoff_Analysis:**
            - Analyze the physiological risks for plants under these conditions (e.g., heat stress, disease risk, light deficiency).
            - State trade-offs between possible actions (e.g., reducing light lowers temperature but sacrifices photosynthesis).
            - Be concise and professional.

        3.  **Primary_Control_Priority:**
            - Select the **single most important control goal** for this 15-minute period from the list below:
                - `Prevent heat/cold damage`
                - `Avoid disease risk`
                - `Maximize photosynthesis`
                - `Energy saving/rest`

        4.  **Prioritized_Action_Chain:**
            - List 1-3 strictly quantified, sequenced control actions using ONLY the fan and LED lights.
            - Each action must be explicit and measurable (e.g., "Set fan to 100%", "Set LED to 8,000 Lux").
            - Actions should be ordered by priority.

        5.  **15 min_Goal_and_Tradeoff:**
            - State the precise environmental target(s) for this cycle (e.g., "Achieve T ≤ 24°C and RH ≤ 75%").
            - Explicitly mention any temporarily sacrificed parameter(s) (e.g., "DLI accumulation is temporarily reduced to control heat.").

        ---
        ### **JSON Output Structure Example**

        {{
        [
        "Case_ID": "<string: Unique identifier for this 15-minute case>",
        "Condition_IF": "<string: Current scenario with explicit thresholds>",
        "Diagnosis_Tradeoff_Analysis": "<string: Analysis of physiological risks and trade-offs>",
        "Primary_Control_Priority": "<string: Single control goal from the list>",
        "Prioritized_Action_Chain": [
            "<string: Action #1>",
            "<string: Action #2>", 
            // ...add more as needed
        ],
        "15 min_Goal_and_Tradeoff": "<string: Environmental target(s) and any sacrificed parameters>"
        ], 
        ... add more distinct and critical cases as needed
        }}

        """
        P3_prompt = PromptTemplate.from_template(P3_prompt_template)
        task3_llm = ChatOpenAI(
            model="gpt-4.1",
            api_key=SecretStr(self.openai_key),
        )
        json_parser_p3 = JsonOutputParser()
        chain_part3 = P3_prompt | task3_llm | json_parser_p3
        p3_input = self._prepare_input(curr_status.to_dict(), p1_output)
        response_3 = chain_part3.ainvoke(
            p3_input
        )
        return await response_3

    async def generate_daily_plan(self, curr_status: ChainPart1UserInput) -> dict:
        """
        Generate a daily plan based on the current status and user input.
        
        :param curr_status: ChainPart1UserInput object containing the current status and user input.
        :return: A dictionary containing the daily plan with all necessary information.
        """
        p1_output = self._search_knowledge(curr_status)
        p2_output, p3_output = asyncio.gather(
            self._generate_general_target(curr_status, p1_output),
            self._generate_strategy(curr_status, p1_output)
        )
        return {
            "p1_output": p1_output,
            "p2_output": p2_output,
            "p3_output": p3_output
        }
