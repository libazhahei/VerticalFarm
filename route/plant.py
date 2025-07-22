from fastapi.routing import APIRouter
from pydantic import BaseModel

from .utils import GlobalContext


class PlantSettingsSchema(BaseModel):
    """Schema for user settings."""

    plant_name: str = "Tomato"
    growth_stage: str = "Seedling"
    notes: str = ""


plant_router = APIRouter(prefix="/plant")

@plant_router.get("/plant-settings")
async def get_plant_settings() -> dict:
    """Endpoint to get plant settings."""
    context = GlobalContext.get_instance()
    if context.plant_settings is None:
        return {"error": "Plant settings not found."}
    return {
        "plant_name": context.plant_settings.get("plant_name", ""),
        "growth_stage": context.plant_settings.get("growth_stage", ""),
        "notes": context.plant_settings.get("comments", ""),
    }

@plant_router.post("/plant-settings")
async def update_plant_settings(settings: PlantSettingsSchema) -> dict:
    """Endpoint to update plant settings."""
    context = GlobalContext.get_instance()
    context.plant_settings = {
        "plant_name": settings.plant_name,
        "growth_stage": settings.growth_stage,
        "comments": settings.notes,
        "target_orientation": "Keep the plants healthy and growing"
    }
    return {"status": "success"}
