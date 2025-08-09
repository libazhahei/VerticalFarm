import datetime
import random

from fastapi.routing import APIRouter

from llm.cloud import CloudLLMCache
from llm.parser import CloudLLMOutput, StrategyDetail

ai_router = APIRouter(prefix="/ai")


@ai_router.get("/insights")
async def get_insights() -> dict:
    """Endpoint to get insights from the AI model."""
    # Placeholder for AI model insights logic
    # TODO: THIS IS A PLACEHOLDER FOR AI MODEL INSIGHTS LOGIC
    # TODO: THIS SHOULD BE REPLACED WITH ACTUAL AI MODEL INTEGRATION
    # llm_cache = await CloudLLMCache.get_instance()
    # plan = await llm_cache.get_plan()
    # if plan is None:
    #     return {"error": "No plan available"}
    # insights = plan.local.cases

    # if not insights:
        # return {"error": "No insights available"}
    return {
        "summary": "Critical Heat and High Humidity Stress",
        "reasoning": "Internal temperature exceeds upper ideal and humidity is above ideal during lights on",
        "risk_level": "High",
        "control_priority": "Rapidly reduce chamber temperature and humidity, then Stabilize environment and resume photosynthesis",
        "action_priority": "Maximize fan speed for cooling and moisture removal; dim LEDs to cut heat load, Maintain strong airflow for humidity control while restoring light for DLI.",
        "suggestion_time": datetime.datetime.now().timestamp()
    }


def summary_strategy(strategy: StrategyDetail) -> dict:
    """Helper function to summarize a strategy."""
    control_priority = ",".join([step.objective for step in strategy.control_sequence])
    action_priority = ",".join([step.justification for step in strategy.control_sequence])  # Limit to first 3 objectives

    return {
        "id": strategy.case_id,
        "summary": strategy.case_description,
        "reasoning": strategy.case_quantitative_description,
        "risk level": strategy.risk_level,
        "control_priority": control_priority,
        "action_priority": action_priority,
        "suggestion_time": datetime.datetime.now().timestamp()
    }


@ai_router.get("/strategies")
async def get_strategies() -> list[dict]:
    """Endpoint to get strategies from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")
    
    strategies = plan.local.strategy_playbook
    if not strategies:
        raise ValueError("No strategies available")
    
    return [
        summary_strategy(strategy) for strategy in strategies
    ]


@ai_router.get("/target")
async def get_target() -> dict:
    """Endpoint to get the target from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")

    target = plan.overall.lighting_strategy
    basic_knowledge = plan.online

    if not target or not basic_knowledge:
        raise ValueError("No target or basic knowledge available")
    night_photoperiod = 24 - target.photoperiod_hours
    return {
        "day_temperature": basic_knowledge.temperature_celsius.day_range,
        "night_temperature": basic_knowledge.temperature_celsius.night_range,
        "humidity": basic_knowledge.relative_humidity_percent.ideal_range,
        "PPFD": basic_knowledge.ppfd_umol_m2_s,
        "DLI": basic_knowledge.dli_mol_m2_day,
        "Photoperiod": [
            {"period": f"{target.photoperiod_hours}", "light": target.daytime_target_lux},
            {"period": f"{night_photoperiod}", "light": 0},
        ],
        "data_source": basic_knowledge.references,
    }

@ai_router.get("/human_task")
async def get_human_task() -> list[dict]:
    """Endpoint to get the human task from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")

    human_tasks = plan.overall.manual_check_recommendations
    if not human_tasks:
        raise ValueError("No human tasks available")
    return [{
        "task": human_task.task,
        "todo": human_task.todo,
    } for human_task in human_tasks]


@ai_router.get("/verification")
async def get_verification() -> list[dict]:
    """Endpoint to get the verification from the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")
    verifications = plan.overall.strategy_failure_escalation
    if not verifications:
        raise ValueError("No verifications available")
    return [{
        "task": f"if {verification.condition} {verification.detection_period}",
        "todo": f"Equipment Limitation Considered: {verification.equipment_limitation_considered}. \n"
                 f"Location Season Weather Considered: {verification.location_season_weather_factors}. \n"
                 f"Action Required: {verification.recovery_suggestion}. \n",
    } for verification in verifications]


@ai_router.put("/strategies/{strategy_id}")
async def update_strategy(strategy_id: int, strategy: dict) -> dict:
    """Endpoint to update a strategy in the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")

    # strategies = plan.local.cases
    # if not strategies or strategy_id < 1 or strategy_id > len(strategies):
    #     raise ValueError("Invalid strategy ID")

    # # Validate the incoming strategy data
    # strategy_case = StrategyDetail.model_validate({
    #     "Case_ID": strategy.get("id"),
    #     "Condition_IF": strategy.get("condition"),
    #     "Diagnosis_Tradeoff_Analysis": strategy.get("reasoning"),
    #     "Primary_Control_Priority": strategy.get("control_priority"),
    #     "Prioritized_Action_Chain": strategy.get("action_priority", []),
    #     "Risk_level": strategy.get("risk_level"),
    #     "15_min_Goal_and_Tradeoff": strategy.get("tradeoff", "")
    # })
    # if not strategy_case:
    #     raise ValueError("Invalid strategy data")
    # Update the strategy
    # strategies[strategy_id - 1] = strategy_case
    # await llm_cache.set_plan(plan)
    return {"message": "Strategy updated successfully"}


@ai_router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: int) -> dict:
    """Endpoint to delete a strategy in the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")

    strategies = plan.local.strategy_playbook
    if not strategies or strategy_id < 1 or strategy_id > len(strategies):
        raise ValueError("Invalid strategy ID")

    # Delete the strategy
    del strategies[strategy_id - 1]
    await llm_cache.set_plan(plan)
    return {"message": "Strategy deleted successfully"}

@ai_router.put("/target")
async def update_target(target: dict) -> dict:
    """Endpoint to update the target in the AI model."""
    llm_cache = await CloudLLMCache.get_instance()
    plan = await llm_cache.get_plan()
    if plan is None:
        raise ValueError("No plan available")

    # Validate the incoming target data
    lighting_strategy = plan.overall.lighting_strategy.model_validate(target)
    if not lighting_strategy:
        raise ValueError("Invalid target data")

    # Update the target
    plan.overall.lighting_strategy = lighting_strategy
    await llm_cache.set_plan(plan)
    return {"message": "Target updated successfully"}
