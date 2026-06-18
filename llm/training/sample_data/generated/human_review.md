# Vertical Farm Control — Human Annotation Guide

## Review Criteria (3-point scale)
- **Accept** — physically plausible, JSON schema compliant, crop-biology aligned, cross-stage consistent
- **Needs Revision** — minor fixable issues (fan PWM range, DLI calc, photoperiod misclassification)
- **Reject** — physically implausible, schema-breaking, or logically inconsistent

## Annotation Instructions
1. Read the input state vector and LLM-generated output for each sample below.
2. Mark one score: Accept / Needs Revision / Reject.
3. If **Needs Revision**, write corrected JSON in the Correction field.
4. Return completed file to pipeline:
   `python -m llm.training.synthesize --import-human-md human_review_completed.md`

## Samples for Review

### Sample HR-001 | Stage: diagnosis | Seed: seed_00000

**Input State / Prompt:**
```

# System Role and Capabilities
You are a high-level environmental control AI responsible for creating the optimal growing environment for specific plants (e.g., lettuce) by precisely adjusting fans and LED lights.
Your decisions should be data-driven, balancing plant health, energy efficiency, and system safety.

# Goal and Objectives
- **Core Goal**: Maintain the temperature between 15.0°C and 21.0°C.
- **Objectives:**
  - Use fans and LED lights effectively to achieve these goals.
- **Constraints**:
  - Fans can only cool the room to the external temperature in 3 minutes.
  - LED lights can heat the room up to apprx. 3°C at most in 15 mins, only if fans are OFF.
  - In the "Lights OFF" period, LED lights must remain OFF to respect the plant's dark cycle.
  - In the "Lights ON" period, LED lights must remain On to support photosynthesis.

# Current Environmental Status (Real-time Data)
- Internal Temperature: 19.6°C
- Humidity: 72.5%
- External Temperature: 19.6°C
- Plant Status: Healthy
- Current Photoperiod: Lights ON (ON/OFF)
- Device Status:
  - Fan: 78 (0-100% RPM)
  - LED Light: 68 (0-100% intensity)
  - Device Health: Nominal

# Historical Context (Dynamic Information)
- **Environmental Trends in the Past 30 Minutes**:
  - Temperature: Increased from 19.700000000000003°C to 19.6°C (average increase of 0.15333333333333335°C per 15 minutes)

# Environmental Forecast (Dynamic Information)
- **Environmental Forecast for the Next 1 Hour**:
  - Current time is: 14:40 (e.g., 14:00), Daily forecast indicates: Maximum temperature of 22.1°C at 15:00, Minimum temperature of 19.1°C at 06:00.
  - External Temperature: Expected temperature from 19.1°C to 22.1°C over the next hour (source: Weather API).
  - Internal Temperature: Based on current trends and external forecasts, if no intervention is made, it is expected to slowly rise to match the room temperature within the next 1 hour.

# Diagnosis
1. Carefully analyze all the information provided above.
2. Summarize the 
```

**LLM Output:**
```json
{"core_issue": "Stable environmental conditions", "states": ["Stable Maintenance"], "confidence": [7]}
```
 
**Reviewer Score:** [ ] Accept  [x] Needs Revision  [ ] Reject
 
**Correction (if needed):**
```json
{
  "core_issue": "Approaching temperature ceiling with rising external heat",
  "states": ["Stable Maintenance", "Impending Overheating Risk"],
  "confidence": [5]
}
```
 
**Reviewer Notes:** Current internal temperature (19.6°C) is within the target range and short-term conditions appear stable. However, the forecast shows external temperature reaching 22.1°C by 15:00 — exceeding the 21°C upper limit — and the internal trend is already rising at +0.15°C per 15 min. The diagnosis must capture both the current stable state and the imminent overheating risk so the planning stage can act preemptively. The `states` field should include "Impending Overheating Risk" alongside "Stable Maintenance", and `core_issue` should identify rising external heat as the root driver. Confidence reduced from 7 to 5 to reflect uncertainty in the external temperature forecast.
 
---

### Sample HR-002 | Stage: planning | Seed: seed_00000

**Input State / Prompt:**
```

# System Role and Capabilities
You are a high-level environmental control AI responsible for creating the optimal growing environment for specific plants (e.g., lettuce) by precisely adjusting fans and LED lights.
Your decisions should be data-driven, balancing plant health, energy efficiency, and system safety.

# Goal and Objectives
- **Core Goal**: Maintain the temperature between 15.0°C and 21.0°C.
- **Objectives:**
  - Use fans and LED lights effectively to achieve these goals.
- **Constraints**:
  - Fans can only cool the room to the external temperature in 3 minutes.
  - LED lights can heat the room up to apprx. 3°C at most in 15 mins, only if fans are OFF.
  - In the "Lights OFF" period, LED lights must remain OFF to respect the plant's dark cycle.
  - In the "Lights ON" period, LED lights must remain On to support photosynthesis.

# Current Environmental Status (Real-time Data)
- Internal Temperature: 19.6°C
- Humidity: 72.5%
- External Temperature: 19.6°C
- Plant Status: Healthy
- Current Photoperiod: Lights ON (ON/OFF)
- Device Status:
  - Fan: 78 (0-100% RPM)
  - LED Light: 68 (0-100% intensity)
  - Device Health: Nominal

# Historical Context (Dynamic Information)
- **Environmental Trends in the Past 30 Minutes**:
  - Temperature: Increased from 19.700000000000003°C to 19.6°C (average increase of 0.15333333333333335°C per 15 minutes)

# Environmental Forecast (Dynamic Information)
- **Environmental Forecast for the Next 1 Hour**:
  - Current time is: 14:40 (e.g., 14:00), Daily forecast indicates: Maximum temperature of 22.1°C at 15:00, Minimum temperature of 19.1°C at 06:00.
  - External Temperature: Expected temperature from 19.1°C to 22.1°C over the next hour (source: Weather API).
  - Internal Temperature: Based on current trends and external forecasts, if no intervention is made, it is expected to slowly rise to match the room temperature within the next 1 hour.

# Action Plan Explanation
Diagnosis summary: Stable environmental conditions

# Action
```

**LLM Output:**
```json
{"action_plan": [{"solution_id": "SOLUTION_01", "description": "Maintain current settings", "function_calls": [], "confidence": 6}]}
```

**Reviewer Score:** [ ] Accept  [x] Needs Revision  [ ] Reject
 
**Correction (if needed):**
```json
{
  "action_plan": [
    {
      "solution_id": "SOLUTION_01",
      "description": "Preemptive cooling: increase fan speed to counteract forecasted external temperature rise to 22.1°C at 15:00",
      "function_calls": [
        {"device": "fan", "action": "set_pwm", "value": 90},
        {"device": "led", "action": "set_intensity", "value": 68}
      ],
      "confidence": 7
    },
    {
      "solution_id": "SOLUTION_02",
      "description": "Maintain current settings and monitor; intervene only if internal temperature exceeds 20.5°C",
      "function_calls": [],
      "confidence": 4
    }
  ]
}
```


**Reviewer Notes:** The empty list of function_calls is the most serious problem - in the scenario where the temperature is predicted to exceed the limit, the planning phase must output specific device instructions. The LED must not be turned off during Lights ON (the constraint is met and remains at 68). The fan is the only legal active cooling method and should be increased from 78 to 90 for preventive cooling. After the correction, two solutions are provided: SOLUTION_01 is an active pre-cooling solution (confidence 7); SOLUTION_02 retains the passive monitoring strategy for comparison (confidence 4). A single air-conditioning application plan is not acceptable in scenarios where the forecast exceeds the standard.


---

