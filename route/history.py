import datetime
from enum import Enum

from fastapi.routing import APIRouter
from pydantic import BaseModel

from data.tables import BoardData, BoardDataBatchWriter

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

    unit: UnitModel 
    start_from: int

def aggregate_data_by_unit(data: list[BoardData], unit: UnitModel, data_field: str) -> dict[int, list[BoardData]]:
    """
    Aggregates data by the specified unit and calculates the average for each board_id.

    Args:
        data (list[BoardData]): List of BoardData objects to aggregate.
        unit (UnitModel): The unit to aggregate by (day, hour, minute, second, ms).
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

@history_router.post("/temperature")
async def get_temperature_history(data: HistoryDataModel) -> list[dict]:
    """Endpoint to fetch temperature history data."""
    writer = BoardDataBatchWriter.get_instance()
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=None)
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
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=None)
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
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=None)
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
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=[board_id])
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
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=[board_id])
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
    history_data = await writer.fetch_since(since=datetime.datetime.fromtimestamp(data.start_from), board_ids=[board_id])
    if not history_data:
        return []

    agg_data = aggregate_data_by_unit(history_data, data.unit, "light_intensity")
    return [
        {"board_id": board_id, "data": values, "field": "light_intensity"} for board_id, values in agg_data.items()
    ]
