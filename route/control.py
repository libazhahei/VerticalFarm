from fastapi.routing import APIRouter

from gateway.constants import DEVICE_MAX_ID, DEVICE_MIN_ID

control_router = APIRouter(prefix="/control")

@control_router.get("/{board_id}")
async def control_board(board_id: int) -> dict:
    """Endpoint to control a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    return { "mode": "auto", "fan": 1, "led": 0 }

@control_router.post("/{board_id}")
async def update_board(board_id: int, command: dict) -> dict:
    """Endpoint to update the status of a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    return { "mode": "auto", "fan": 1, "led": 0 }
