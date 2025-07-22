from fastapi.routing import APIRouter
from pydantic import BaseModel

from gateway.constants import DEVICE_MAX_ID, DEVICE_MIN_ID
from gateway.msg import ControlMsg, Mode

from .utils import GlobalContext, RunningMode

control_router = APIRouter(prefix="/control")

class ControlMsgSchema(BaseModel):
    """Schema for control message."""

    running_mode: RunningMode = RunningMode.AUTO
    humidity: float
    temperature: float
    light_intensity: float


@control_router.get("/{board_id}")
async def control_board(board_id: int) -> dict:
    """Endpoint to control a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}
    curr_running_mode = GlobalContext.get_instance().running_mode
    running_target = GlobalContext.get_instance().get_running_target()

    return { "mode": str(curr_running_mode), **(running_target or {}) }

@control_router.post("/{board_id}")
async def update_board(board_id: int, data: ControlMsgSchema) -> dict:
    """Endpoint to update the status of a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    context = GlobalContext.get_instance()
    if context.mqtt_service_context is None:
        raise ValueError("MQTT service context is not initialized.")
    if data.running_mode == RunningMode.AUTO:
        print("Switching to auto mode")
        context.switch_running_mode(RunningMode.AUTO)
        return { "mode": str(context.running_mode) }
    print(f"Switching to manual mode with data: {data}")
    ctrl_msg = ControlMsg(
        board_id=board_id,
        fan=0,  # Placeholder for fan control
        led=0,  # Placeholder for LED control
        temperature=data.temperature,
        light_intensity=data.light_intensity,
        mode=Mode.ABSOLUTE
    )
    await context.mqtt_service_context.publish_control_command(ctrl_msg)

    GlobalContext.get_instance().switch_running_mode(RunningMode.MANUAL, {
        "humidity": data.humidity,
        "temperature": data.temperature,
        "light_intensity": data.light_intensity
    })

    return { "mode": str(GlobalContext.get_instance().running_mode)}
