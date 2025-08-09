import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from tortoise import Tortoise
from uvicorn import run

from data.config import init_schema
from data.tables import BoardDataBatchWriter
from gateway.service import BLEServiceContext, MQTTServiceContext
from llm.cloud import ChainPart1UserInput, CloudLLMCache, DailyPlanner
from route.ai import ai_router
from route.control import control_router
from route.history import history_router
from route.others import other_router
from route.plant import plant_router
from route.utils import GlobalContext, fake_lower_computer_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d in %(funcName)s: %(message)s",
)
logger = logging.getLogger(__name__)

MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 5001
MQTT_CLIENT_ID = "test_client"
BLE_DEVICES = [1]  # Example BLE devices


# async def init_lower_computer_services() -> tuple[MQTTServiceContext, BLEServiceContext]:
#     """Initialize MQTT and BLE service contexts."""

#     return mqtt_service, ble_service

@asynccontextmanager # type: ignore
async def lifespan(app: FastAPI) -> Any:
    """Lifespan context manager to initialize the database schema."""
    # logger.debug("🌟 This is a debug message")
    await init_schema()
    logger.info("Database schema initialized.")
    # TODO: Initialize MQTT and BLE services
    # cache = await CloudLLMCache.get_instance()
    # planner = DailyPlanner("123", "123")
    # user_setting = ChainPart1UserInput(
    #     plant= "Tomato",
    #     growth_stage= "Seedling",
    #     target_orientation= "Keep the plants healthy and growing",
    #     comments= "",
    # )
    # await cache.refresh_plan(planner, user_setting, demo=True)
    mqtt_service = MQTTServiceContext(
        broker_host=MQTT_BROKER_HOST,
        broker_port=MQTT_BROKER_PORT,
        client_id=MQTT_CLIENT_ID
    )
    ble_service = BLEServiceContext(BLE_DEVICES)
    mqtt_service, ble_service = await fake_lower_computer_services(mqtt_service, ble_service, BLE_DEVICES)
    GlobalContext.get_instance(mqtt_service_context=mqtt_service, ble_service_context=ble_service)

    yield

    await mqtt_service.stop()
    await ble_service.stop()
    await Tortoise.close_connections()
    logger.info("FastAPI application shutdown complete.")

app = FastAPI(lifespan=lifespan)
app.include_router(other_router, prefix="/api", tags=["others"])
app.include_router(history_router, prefix="/ap", tags=["history"])
app.include_router(ai_router, prefix="/api", tags=["ai"])
app.include_router(control_router, prefix="/api", tags=["control"])
app.include_router(plant_router, prefix="/api", tags=["plant"])
# CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_index(request: Request) -> Any:
    """Hello World endpoint."""
    return RedirectResponse(url="/docs")


@app.get("/api/devices")
async def get_devices() -> list:
    """Endpoint to fetch the list of devices."""
    global_context = GlobalContext.get_instance()
    if global_context.ble_service_context is None:
        return []
    devices = await global_context.mqtt_service_context.alive_devices() if global_context.mqtt_service_context else []
    ble_latest = await BoardDataBatchWriter.get_instance().fetch_latest(devices)

    result = []
    for ble_data in ble_latest:
        if ble_data is not None:
            result.append({
                "board_id": ble_data.board_id,
                "last_seen": ble_data.timestamp.timestamp() if ble_data.timestamp else None,
                "ip_address": "127.0.0.1",
                "status": "online" if ble_data.board_id in devices else "offline",
            })
    return result


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception)-> dict:
    """Handle uncaught exceptions globally."""
    return {"error": str(exc), "message": "An unexpected error occurred."}


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = "./test.db"

    print("Starting FastAPI application...")

    logger.info("Starting FastAPI application with lifespan context manager.")
    # run(app, host="127.0.0.1", port=8000, log_level="info", reload=True)
    run(app, host="127.0.0.1", port=8000, log_level="info")