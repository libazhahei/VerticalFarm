import logging
import os
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from uvicorn import run

from data.config import init_schema
from gateway.service import BLEServiceContext, MQTTServiceContext
from llm.cloud import ChainPart1UserInput, CloudLLMCache, DailyPlan
from route.ai import ai_router
from route.control import control_router
from route.history import history_router
from route.others import other_router
from route.utils import GlobalContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d in %(funcName)s: %(message)s",
)
logger = logging.getLogger(__name__)

MQTT_BROKER_HOST = "localhost"
MQTT_BROKER_PORT = 1883
MQTT_CLIENT_ID = "test_client"
BLE_DEVICES = [1, 2, 3]  # Example BLE devices
FAKE_LOWER_COMPUTER_COMMUNICATION = True  # Set to True for testing purposes

async def fake_lower_computer_services(mqtt: MQTTServiceContext, ble: BLEServiceContext) -> tuple[MQTTServiceContext, BLEServiceContext]:
    """Simulate lower computer communication for testing purposes."""
    if FAKE_LOWER_COMPUTER_COMMUNICATION:
        logger.info("Simulating lower computer communication.")
        # MQTT Simulation
        fake_device = MagicMock()
        fake_device.name = "CropWaifu-Board-1"
        fake_device.address = "00:11:22:33:44:55"
        ble.ble_client.ble_devices = {1: fake_device}
        ble.ble_client.is_running = True
        ble.ble_client.connection_tasks = {1: MagicMock()}
        ble.ble_client.ble_clients = {1: MagicMock(is_connected=True)}
        ble.ble_client.start = AsyncMock()
        ble.ble_client.stop = AsyncMock()


        # MQTT Simulation
        mqtt.control_cmd_pub.safe_publish = MagicMock(return_value=True)
        mqtt.heartbeat_sub.get_alive_devices = AsyncMock(return_value=[1])
        mqtt.heartbeat_sub.is_alive = AsyncMock(lambda board_id: True if board_id == 1 else False)
        mqtt.is_connected = MagicMock(return_value=True)
    else:   
        await mqtt.start()
        await ble.start()
    return mqtt, ble

@asynccontextmanager # type: ignore
async def lifespan(app: FastAPI) -> Any:
    """Lifespan context manager to initialize the database schema."""
    logger.debug("🌟 This is a debug message")
    await init_schema()
    logger.info("Database schema initialized.")
    cache = await CloudLLMCache.get_instance()
    planner = DailyPlan("123", "123")
    user_setting = ChainPart1UserInput(
        plant= "Tomato",
        growth_stage= "Seedling",
        target_orientation= "Keep the plants healthy and growing",
        comments= "",
    )
    await cache.refresh_plan(planner, user_setting, demo=True)
    mqtt_service = MQTTServiceContext(
        broker_host=MQTT_BROKER_HOST,
        broker_port=MQTT_BROKER_PORT,
        client_id=MQTT_CLIENT_ID
    )
    # await mqtt_service.start()
    ble_service = BLEServiceContext(BLE_DEVICES)
    # await ble_service.start()
    mqtt_service, ble_service = await fake_lower_computer_services(mqtt_service, ble_service)
    GlobalContext.get_instance(mqtt_service_context=mqtt_service, ble_service_context=ble_service)
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(other_router, prefix="/api", tags=["others"])
app.include_router(history_router, prefix="/ap", tags=["history"])
app.include_router(ai_router, prefix="/api", tags=["ai"])
app.include_router(control_router, prefix="/api", tags=["control"])
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


@app.get("/devices")
async def get_devices() -> dict:
    """Endpoint to fetch the list of devices."""
    return {"devices": ["device1", "device2", "device3"]}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception)-> dict:
    """Handle uncaught exceptions globally."""
    return {"error": str(exc), "message": "An unexpected error occurred."}


if __name__ == "__main__":
    os.environ["DATABASE_URL"] = "./test.db"

    print("Starting FastAPI application...")

    logger.info("Starting FastAPI application with lifespan context manager.")
    run(app, host="127.0.0.1", port=8000, log_level="info", reload=True)
