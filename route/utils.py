import asyncio
import math
import random
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

from bleak.backends.characteristic import BleakGATTCharacteristic

from gateway.constants import TIMEZONE, get_characteristic_uuid
from gateway.msg import MQTTMessageType, SensorDataMsg, SensorStatus
from gateway.service import BLEServiceContext, MQTTServiceContext

FAKE_LOWER_COMPUTER_COMMUNICATION = False  # Set to True for testing purposes

global exit_fake_loop 
exit_fake_loop = False

class RunningMode(int, Enum):
    """Enum to represent different running modes of the application."""

    AUTO = 0
    MANUAL = 1

    def __str__(self) -> str:
        return self.name.lower()

class GlobalContext:
    """
    Global context for the application.
    This class can be used to store global state or configuration.
    """

    # Singleton instance
    mqtt_service_context: MQTTServiceContext | None
    ble_service_context: BLEServiceContext | None
    running_mode: RunningMode = RunningMode.AUTO
    running_target: dict
    plant_settings: dict | None = None

    global_context: Optional["GlobalContext"] = None

    @classmethod
    def get_instance(cls, mqtt_service_context: MQTTServiceContext | None = None, ble_service_context: BLEServiceContext | None = None) -> "GlobalContext":
        """Get the singleton instance of GlobalContext."""
        if cls.global_context is not None:  
            return cls.global_context
        cls.global_context = cls()
        cls.global_context.mqtt_service_context = mqtt_service_context
        cls.global_context.ble_service_context = ble_service_context
        cls.global_context.running_target = {
            "auto": None,
            "manual": None
        }
        cls.global_context.plant_settings = None


        return cls.global_context

    def switch_running_mode(self, mode: RunningMode, target: dict | None = None) -> None:
        """Switch the running mode of the application."""
        self.running_mode = mode
        if self.running_mode == RunningMode.AUTO:
            self.running_target['auto'] = target if target else self.running_target['manual']
        elif self.running_mode == RunningMode.MANUAL:
            self.running_target['manual'] = target if target else self.running_target['manual']

        print(f"Running mode switched to: {self.running_mode}")

    def get_running_target(self) -> dict | None:
        """Get the current running target based on the running mode."""
        if self.running_mode == RunningMode.AUTO:
            return self.running_target['auto']
        elif self.running_mode == RunningMode.MANUAL:
            return self.running_target['manual']
        return None


def simulate_environment(seed: int, hour: float, board_id: int) -> tuple[float, float, int]:
    """Simulate environmental data based on the hour of the day and board ID.

    Args:
        seed (int): Seed for random number generation.
        hour (float): Hour of the day (0-23).
        board_id (int): ID of the board for which to generate data.

    Returns:
        tuple: A tuple containing temperature (float), humidity (float), and light intensity (int).
    Behavior:
        - The function uses a sine wave to simulate temperature and humidity variations throughout the day.
        - Light intensity is simulated to be higher during the day and lower at night.
        - Random noise is added to the temperature, humidity, and light intensity to simulate real-world variations.
        - The function uses the seed and hour to ensure consistent data generation for testing purposes.
    """
    random.seed(seed + int(hour * 1000) + board_id ** 2)

    temp_base = 22 + 6 * math.sin((2 * math.pi / 24) * (hour - 14))  
    humidity_base = 60 + 20 * math.sin((2 * math.pi / 24) * (hour - 5))  
    light_base = max(0, 10000 * math.sin((math.pi / 12) * (hour - 6))) 

    temp_noise = random.gauss(0, 0.3)  
    humidity_noise = random.gauss(0, 1.5)
    light_noise = random.gauss(0, 300)

    temperature = round(temp_base + temp_noise, 2)
    humidity = round(humidity_base + humidity_noise, 2)
    light_intensity = max(0, round(light_base + light_noise))

    return temperature, humidity, light_intensity

async def insert_one_fake_data(
    callable_func: Callable,
    seed: int,
    board_id: int,
    hour: int = 0
) -> SensorDataMsg:
    """Insert one fake sensor data for testing purposes.

    Args:
        callable_func (Callable): Function to call with the generated data.
        seed (int): Seed for random number generation.
        board_id (int): ID of the board for which to generate data.
        hour (int): Hour of the day for which to generate data.
    """
    temperature, humidity, light_intensity = simulate_environment(seed, hour, board_id)
    data = SensorDataMsg(
        board_id=board_id,
        temperature=temperature,
        light_intensity=light_intensity,
        fans_real=random.randint(0, 100),
        humidity=humidity,
        status=SensorStatus.IDLE,
        fans_abs=random.randint(0, 255),
        led_abs=random.randint(0, 255),
        timestamp=(datetime.now(tz=ZoneInfo(TIMEZONE)) - timedelta(seconds=1)).timestamp()
    )
    byte_array = data.to_byte_array()
    if callable_func:
        mock_service = MagicMock()  # Mocking BleakGATTService
        await callable_func(BleakGATTCharacteristic(obj=None, uuid=get_characteristic_uuid(board_id), handle=0, 
                                                    properties=[], max_write_without_response_size=lambda: 0, 
                                                    service=mock_service), byte_array)
    return data

async def generate_fake_data(callable_func: Callable, seed: int, board_id: int, mins: int = 1, hour: int = 0) -> list[SensorDataMsg]:
    """Generate fake sensor data for testing purposes.

    Args:
        callable_func (Callable): Function to call with the generated data.
        seed (int): Seed for random number generation.
        board_id (int): ID of the board for which to generate data.
        mins (int): Number of minutes of data to generate.
        hour (int): Hour of the day for which to generate data.
    """
    data = []
    try:
        print(f"Generating fake data for board {board_id} for {mins} minutes starting at hour {hour} with seed {seed}")
        for i in range(mins):
            for minute in range(30):
                if exit_fake_loop:
                    print("Exiting fake data generation loop.")
                    return data
                time = minute / 30.0 + i + hour
                temperature, humidity, light_intensity = simulate_environment(seed, time, board_id)
                data.append(SensorDataMsg(
                    board_id=board_id,
                    temperature=temperature,
                    light_intensity=light_intensity,
                    fans_real=random.randint(0, 100),
                    humidity=humidity,
                    status=SensorStatus.IDLE,
                    fans_abs=random.randint(0, 255),
                    led_abs=random.randint(0, 255),
                    timestamp=(datetime.now(tz=ZoneInfo(TIMEZONE)) - timedelta(seconds=1)).timestamp()
                ))
                await asyncio.sleep(0.1)  # Simulate a delay of 1 minute between data points
                byte_array = data[-1].to_byte_array()
                if callable_func:
                    mock_service = MagicMock()  # Mocking BleakGATTService
                    await callable_func(BleakGATTCharacteristic(obj=None, uuid=get_characteristic_uuid(board_id), handle=0, 
                                                                properties=[], max_write_without_response_size=lambda: 0, 
                                                                service=mock_service), byte_array)
        print(f"Generated {len(data)} data points for board {board_id}")
    except asyncio.CancelledError:
        raise 
    return data


async def stop_tasks(tasks: list[asyncio.Task]) -> None:
    """Stop all tasks."""
    print("Stopping all tasks...")
    global exit_fake_loop
    exit_fake_loop = True
    for task in tasks:
        if not task.done():
            task.cancel()
    try:
        await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=1.0)
    except TimeoutError:
        pass

async def fake_lower_computer_services(mqtt: MQTTServiceContext, ble: BLEServiceContext, ble_device_ids: list[int], data_inserter: Callable = generate_fake_data) -> tuple[MQTTServiceContext, BLEServiceContext]:
    """
    Fake lower computer services for testing purposes.
    This function simulates the behavior of MQTT and BLE services without actual hardware communication.

    Args:
        mqtt (MQTTServiceContext): The MQTT service context to be faked.
        ble (BLEServiceContext): The BLE service context to be faked.
        ble_device_ids (List[int]): List of BLE device IDs to simulate.
        data_inserter (Callable): Function to insert fake data into the BLE service.

    Returns:
        tuple[MQTTServiceContext, BLEServiceContext]: The faked MQTT and BLE service contexts.

    Behavior:
        - If `FAKE_LOWER_COMPUTER_COMMUNICATION` is True, it simulates the behavior of MQTT and BLE services.
        - If False, it starts the actual MQTT and BLE services.

    What's happening here:
    - The function creates fake BLE devices and simulates their behavior.
    - It mocks the MQTT service methods to return predefined values.
    - It generates fake sensor data and simulates BLE notifications.
    - This allows testing of the application without needing actual hardware.    
    """
    if FAKE_LOWER_COMPUTER_COMMUNICATION:
        await ble.ble_client.dispatcher.start()
        await mqtt.msg_dispatcher.start()
        # MQTT Simulation
        fake_devices = []
        for id in ble_device_ids:
            fake_device = MagicMock()
            fake_device.name = f"CropWaifu-Board-{id}"
            fake_device.address = f"00:11:22:33:44:{id:02d}"
            fake_devices.append(fake_device)

        ble.ble_client.ble_devices = dict(zip(ble_device_ids, fake_devices, strict=False))
        ble.ble_client.is_running = True
        ble.ble_client.connection_tasks = {id: MagicMock() for id in ble_device_ids}
        ble.ble_client.ble_clients = {id: MagicMock(is_connected=True) for id in ble_device_ids}
        ble.ble_client.device_id_lists = set(ble_device_ids)
        send_tasks = [asyncio.create_task(
            data_inserter(callable_func=ble.ble_client.on_ble_notification, seed=42, board_id=board_id, mins=120, hour=12)
        ) for board_id in ble_device_ids]
        ble.ble_client.start = AsyncMock(
            lambda: asyncio.gather(*send_tasks)
        )
        ble.ble_client.stop = AsyncMock(
            lambda: stop_tasks(send_tasks)
        )
        ble.is_running = True
        async def mock_safe_publish(message: MQTTMessageType, topic: str, ack_func: Callable[[int], None]) -> MQTTMessageType:
            """Mock method to simulate safe publish.
            it wait 10ms to acknowledge the message.

            Args:
                message (MQTTMessageType): The message to be published.
                topic (str): The topic to which the message is published.
                ack_func (Callable[[int], None]): Acknowledgment function to call with the message ID.

            Returns:
                MQTTMessageType: The message that was published.
            """
            await asyncio.sleep(0.01)
            ack_func(message.get_message_id())  # Simulate acknowledgment with a dummy message ID
            return message

        mqtt.control_cmd_pub.safe_publish = MagicMock(side_effect=mock_safe_publish, return_value=True)
        mqtt.heartbeat_sub.get_alive_devices = AsyncMock(return_value=ble_device_ids)
        mqtt.heartbeat_sub.is_alive = AsyncMock(lambda board_id: True if board_id in ble_device_ids else False)
        mqtt.is_connected = MagicMock(return_value=True)
        mqtt.start = AsyncMock()
        mqtt.stop = AsyncMock(lambda: mqtt.msg_dispatcher.stop())
        # pass
    else:
        await mqtt.start()
        await ble.start()
    return mqtt, ble
