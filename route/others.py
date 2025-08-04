
import re
from fastapi.routing import APIRouter

from data.tables import BoardDataBatchWriter
from gateway.constants import DEVICE_MAX_ID, DEVICE_MIN_ID
from gateway.subscriber import CommonDataRetriver

other_router = APIRouter()


@other_router.get("/realtime")
async def get_realtime_data() -> dict:
    """Endpoint to fetch real-time data."""
    board_data = []
    for key in range(DEVICE_MIN_ID, DEVICE_MAX_ID):
        retriver = CommonDataRetriver.get_instance(key)
        board_data.append({
            "board_id": key,
            "temperature": retriver.latest_temperature,
            "humidity": retriver.latest_humidity,
            "light": retriver.latest_light_intensity,
            "fan": 1 if retriver.latest_fan_speed else 0,
            "led": 1 if retriver.latest_led else 0,
            "online": retriver.num_samples > 0,
            "timestamp": retriver.latest_timestamp,
        })

    return {
        "boards": board_data
    }



@other_router.get("/board/{board_id}/status")
async def get_board_status(board_id: int) -> dict:
    """Endpoint to fetch the status of a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    retriver = CommonDataRetriver.get_instance(board_id)
    if retriver.num_samples == 0:
        return {"error": "This device is offline or has no data."}
    return {
        "board_id": board_id,
        "temperature": retriver.latest_temperature,
        "humidity": retriver.latest_humidity,
        "light": retriver.latest_light_intensity,
        "fan": 1 if retriver.latest_fan_speed else 0,
        "led": 1 if retriver.latest_led else 0,
        "online": retriver.num_samples > 0,
        "timestamp": retriver.latest_timestamp,
    }

