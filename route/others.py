
from fastapi.routing import APIRouter

from data.tables import BoardData, BoardDataBatchWriter
from gateway.constants import DEVICE_MAX_ID, DEVICE_MIN_ID

other_router = APIRouter()


@other_router.get("/realtime")
async def get_realtime_data() -> dict:
    """Endpoint to fetch real-time data."""
    writer = BoardDataBatchWriter.get_instance()
    ids = writer.boards_ids
    # Filter out the latest data for each board_id
    latest_data: dict[int, BoardData] = {}
    lastest_timestamp = None
    for data in await writer.fetch():
        if data.board_id not in latest_data or data.timestamp > latest_data[data.board_id].timestamp:
            lastest_timestamp = data.timestamp
            latest_data[data.board_id] = data
    board_data = []
    for key in range(DEVICE_MIN_ID, DEVICE_MAX_ID):
        if key in latest_data:
            board_data.append({
                "board_id": key,
                "temperature": latest_data[key].temperature,
                "humidity": latest_data[key].humidity,
                "light": latest_data[key].light_intensity,
                "fan": 1,
                "led": 0,
                "online": key in ids
            })

    return {
        "timestamp": lastest_timestamp,
        "boards": board_data
    }



@other_router.get("/board/{board_id}/status")
async def get_board_status(board_id: int) -> dict:
    """Endpoint to fetch the status of a specific board."""
    if not (DEVICE_MIN_ID <= board_id <= DEVICE_MAX_ID):
        return {"error": "Invalid board ID"}

    writer = BoardDataBatchWriter.get_instance()
    # find the latest data in buffer for the given board_id
    for data in writer.buffer:
        if data.board_id == board_id:
            latest_data = data
            break
    else:
        return {"error": "This device is offline or has no data."}
    return {
        "board_id": latest_data.board_id,
        "temperature": latest_data.temperature,
        "humidity": latest_data.humidity,
        "light": latest_data.light_intensity,
        "fan": 1,
        "led": 0,
        "online": board_id in writer.boards_ids
    }

