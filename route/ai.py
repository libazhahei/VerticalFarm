import datetime
import random

from fastapi.routing import APIRouter

from llm.cloud import CloudLLMCache

ai_router = APIRouter(prefix="/ai")


@ai_router.get("/insights")
async def get_insights() -> dict:
    """Endpoint to get insights from the AI model."""
    # Placeholder for AI model insights logic
    # TODO: THIS IS A PLACEHOLDER FOR AI MODEL INSIGHTS LOGIC
    # TODO: THIS SHOULD BE REPLACED WITH ACTUAL AI MODEL INTEGRATION
    llm_cache = await CloudLLMCache.get_instance()
    insights = await llm_cache.access(
        lambda x: x['p3_output']['cases'][0],
        default=None
    )
    if not insights:
        return {"error": "No insights available"}
    return {
        "summary": insights['Condition_IF'],
        "reasoning": insights['Diagnosis_Tradeoff_Analysis'],
        "risk level": random.choice(["Low", "Medium", "High"]),
        "control_priority": insights['Primary_Control_Priority'],
        "action_priority": ",".join(insights['Prioritized_Action_Chain']),
        "suggestion_time": datetime.datetime.now().timestamp()
    }


@ai_router.get("/strategies")
async def get_strategies() -> list[dict]:
    """Endpoint to get strategies from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    strategies: list[dict] = await llm_cache.access(
        lambda x: x['p3_output']['cases'],
        default=None
    )
    if not strategies:
        raise ValueError("No strategies available")
    return [{
            "id": id+1,
            "summary": strategie['Condition_IF'],
            "reasoning": strategie['Diagnosis_Tradeoff_Analysis'],
            "risk level": random.choice(["Low", "Medium", "High"]),
            "control_priority": strategie['Primary_Control_Priority'],
            "action_priority": ",".join(strategie['Prioritized_Action_Chain']),
            "suggestion_time": datetime.datetime.now().timestamp()
        } for id, strategie in enumerate(strategies)]


@ai_router.get("/target")
async def get_target() -> dict:
    """Endpoint to get the target from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    target = await llm_cache.access(
        lambda x: x['p2_output']['lighting_strategy'],
        default=None
    )
    basic_knowledge = await llm_cache.access(
        lambda x: x['p1_output'],
        default=None
    )
    if not target or not basic_knowledge:
        raise ValueError("No target or basic knowledge available")
    night_photoperiod = 24 - target['photoperiod_hours']
    return {
        "day_temperature": basic_knowledge['temperature_celsius']['day_range'],
        "night_temperature": basic_knowledge['temperature_celsius']['night_range'],
        "humidity": basic_knowledge['relative_humidity_percent']['ideal_range'],
        "PPFD": basic_knowledge['ppfd_umol_m2_s'],
        "DLI": basic_knowledge['dli_mol_m2_day'],
        "Photoperiod": [
            {"period": f"{target['photoperiod_hours']}", "light": target['daytime_target_lux']},
            {"period": f"{night_photoperiod}", "light": 0},
        ],
        "data_source": basic_knowledge['references'],
    }

@ai_router.get("/human_task")
async def get_human_task() -> list[dict]:
    """Endpoint to get the human task from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    human_tasks = await llm_cache.access(
        lambda x: x['p2_output']['manual_check_recommendations'],
        default=None
    )
    if not human_tasks:
        raise ValueError("No human tasks available")
    return [{
        "task": human_task[0],
        "todo": human_task[1],
    } for human_task in human_tasks]


@ai_router.get("/verification")
async def get_verification() -> list[dict]:
    """Endpoint to get the verification from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    verifications = await llm_cache.access(
        lambda x: x['p2_output']['strategy_failure_escalation'],
        default=None
    )
    if not verifications:
        raise ValueError("No verifications available")
    return [{
        "task": f"if {verification['condition']} {verification['detection_period']}",
        "todo": f"Equipment Limitation Considered: {verification['equipment_limitation_considered']}. \n"
                 f"Location Season Weather Considered: {verification['location_season_weather_considered']}. \n"
                 f"Action Required: {verification['recovery_suggestion']}. \n",
    } for verification in verifications]
