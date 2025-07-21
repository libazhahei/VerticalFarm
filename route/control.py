from fastapi.routing import APIRouter
from pydantic import BaseModel

from gateway.constants import DEVICE_MAX_ID, DEVICE_MIN_ID
from gateway.msg import ControlMsg

from .utils import GlobalContext

control_router = APIRouter(prefix="/control")

class ControlMsgSchema(BaseModel):
    """Schema for control message."""

    board_id: int
    fan: int
    led: int
    temperature: float
    light_intensity: float


@control_router.get("/{board_id}")
async def control_board(board_id: int) -> dict:
    """Endpoint to control a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}
    # context = GlobalContext.get_instance()
    # ctrl_msg = ControlMsg(board_id=board_id, fan=1, led=0, temperature=25.0, light_intensity=50.0)


    return { "mode": "auto", "fan": 1, "led": 0 }

@control_router.post("/{board_id}")
async def update_board(board_id: int, data: ControlMsgSchema) -> dict:
    """Endpoint to update the status of a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    context = GlobalContext.get_instance()
    if context.mqtt_service_context is None:
        raise ValueError("MQTT service context is not initialized.")

    ctrl_msg = ControlMsg(
        board_id=board_id,
        fan=data.fan,
        led=data.led,
        temperature=data.temperature,
        light_intensity=data.light_intensity
    )

    await context.mqtt_service_context.publish_control_command(ctrl_msg)

    return { "mode": "auto", "fan": 1, "led": 0 }
