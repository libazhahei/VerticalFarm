import datetime
from enum import Enum
from zoneinfo import ZoneInfo

from fastapi.routing import APIRouter
from pydantic import BaseModel

from data.tables import BoardData, BoardDataBatchWriter
from gateway.constants import TIMEZONE

history_router = APIRouter(prefix="/history")

class UnitModel(str, Enum):
    """Enum to represent different time units for aggregation."""

    DAY = "day"
    HOUR = "hour"
    MINUTE = "min"
    SECOND = "sec"
    MS = "ms"

class HistoryDataModel(BaseModel):
    """Model for the history data request."""

    unit: UnitModel = UnitModel.MINUTE
    start_from: int = int((datetime.datetime.now(tz=ZoneInfo(TIMEZONE)) - datetime.timedelta(minutes=15)).timestamp())


def aggregate_data_by_unit(data: list[BoardData], unit: UnitModel, data_field: str, ignore_board: bool = False) -> dict[int, list[BoardData]]:
    """
    Aggregates data by the specified unit and calculates the average for each board_id.

    Args:
        data (list[BoardData]): List of BoardData objects to aggregate.
        unit (UnitModel): The unit to aggregate by (day, hour, minute, second, ms) every unit.
        data_field (str): The field in BoardData to aggregate (e.g., "temperature", "humidity", "light_intensity").

    Returns:
        Dict[int, list[BoardData]]: A dictionary where keys are board_ids and values
        are lists of aggregated BoardData objects.
    """
    aggregated_data = {}
    for entry in data:
        board_id = entry.board_id
        timestamp = entry.timestamp
        if unit == UnitModel.DAY:
            key = timestamp.date()
        elif unit == UnitModel.HOUR:
            key = timestamp.replace(minute=0, second=0, microsecond=0)
        elif unit == UnitModel.MINUTE:
            key = timestamp.replace(second=0, microsecond=0)
        elif unit == UnitModel.SECOND:
            key = timestamp.replace(microsecond=0)
        elif unit == UnitModel.MS:
            key = timestamp.replace(microsecond=timestamp.microsecond // 1000 * 1000)

        if key not in aggregated_data:
            aggregated_data[key] = {}
        if ignore_board:
            board_id = 0

        if board_id not in aggregated_data[key]:
            aggregated_data[key][board_id] = []
        field_value = getattr(entry, data_field)
        aggregated_data[key][board_id].append(field_value)

    result = {}
    for key, board_data in aggregated_data.items():
        for board_id, values in board_data.items():
            avg_value = sum(values) / len(values)
            if board_id not in result:
                result[board_id] = []
            result[board_id].append({"timestamp": key, "value": avg_value})
    return result


@history_router.get("/all")
async def get_all_history(unit: UnitModel, start_from: int) -> list:
    """Endpoint to fetch all history data."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(start_from, tz=ZoneInfo(TIMEZONE)), board_ids=None)
    temp_data = aggregate_data_by_unit(history_data, unit, "temperature", ignore_board=True).get(0, [])
    humidity_data = aggregate_data_by_unit(history_data, unit, "humidity", ignore_board=True).get(0, [])
    light_data = aggregate_data_by_unit(history_data, unit, "light_intensity", ignore_board=True).get(0, [])
    # Return something like :
    # [{timestamp: "2023-10-01T00:00:00", temperature: 25, humidity: 60, light_intensity: 300}, ...]
    return [
        {
            "timestamp": data[0]["timestamp"],
            "temperature": data[0]["value"] if data[0] is not None else None,
            "humidity": data[1]["value"] if data[1] is not None else None,
            "light_intensity": data[2]["value"] if data[2] is not None else None
        } for data in zip(temp_data, humidity_data, light_data) if data[0] is not None or data[1] is not None or data[2] is not None
    ]
    


@history_router.post("/temperature")
async def get_temperature_history(data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch temperature history data."""
    writer = BoardDataBatchWriter.get_instance()
    print(f"Fetching temperature history since {datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE))} with unit {data.unit}")
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=None)
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "temperature")
    return [
        {"board_id": board_id, "data": values, "field": "temperature"} for board_id, values in agg_data.items()
    ]

@history_router.post("/humidity")
async def get_humidity_history(data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch humidity history data."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=None)
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "humidity")
    return [
        {"board_id": board_id, "data": values, "field": "humidity"} for board_id, values in agg_data.items()
    ]

@history_router.post("/light")
async def get_light_history(data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch light intensity history data."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=None)
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "light_intensity")
    return [
        {"board_id": board_id, "data": values, "field": "light_intensity"} for board_id, values in agg_data.items()
    ]


@history_router.post("/{board_id}/temperature")
async def get_board_temperature_history(board_id: int, data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch temperature history for a specific board."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=[board_id])
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "temperature")
    return [
        {"board_id": board_id, "data": values, "field": "temperature"} for board_id, values in agg_data.items()
    ]

@history_router.post("/{board_id}/humidity")
async def get_board_humidity_history(board_id: int, data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch humidity history for a specific board."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=[board_id])
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "humidity")
    return [
        {"board_id": board_id, "data": values, "field": "humidity"} for board_id, values in agg_data.items()
    ]

@history_router.post("/{board_id}/light")
async def get_board_light_history(board_id: int, data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch light intensity history for a specific board."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from, tz=ZoneInfo(TIMEZONE)), board_ids=[board_id])
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "light_intensity")
    return [
        {"board_id": board_id, "data": values, "field": "light_intensity"} for board_id, values in agg_data.items()
    ]
