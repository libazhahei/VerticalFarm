import asyncio
import math
import os
import sys
from datetime import datetime, timedelta

from tortoise import Tortoise

from data.config import init_schema
from data.tables import BoardData, BoardDataBatchWriter
from gateway import ControlMsg, MQTTServiceContext
from gateway.msg import ControlMsg, Mode
from gateway.service import BLEServiceContext

BOARD_ID = [1]

async def get_current_data(timeout: timedelta = timedelta(seconds=5)) -> tuple[list[BoardData], int]:
    data_batch_writer = BoardDataBatchWriter.get_instance()
    start_time = datetime.now()
    all_latest_data = []
    num_latest_data = 0
    while datetime.now() - start_time < timeout:
        latest_data = await data_batch_writer.fetch_latest(BOARD_ID)
        if latest_data:
            all_latest_data.extend(latest_data)
            num_latest_data += len(latest_data)
            print(f"Fetched {len(latest_data)} latest data points.")
        else:
            print("No new data available.")
        await asyncio.sleep(1)
    return all_latest_data, num_latest_data

async def get_average_temperature(timeout: timedelta = timedelta(seconds=5)) -> float:
    curr_env, num_data = await get_current_data(timeout)
    if num_data == 0:
        print("No data available to calculate average temperature.")
        return 0.0
    total_temp = sum(data.temperature for data in curr_env)
    average_temp = total_temp / num_data
    print(f"Average temperature over {num_data} data points: {average_temp:.2f}°C")
    return average_temp

async def led_heating(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), led_level: int = 0) -> None:
    """
    Control the LED heating element.
    """
    light_abs = math.floor(led_level / 100.0 * 255)
    msg = ControlMsg(
        board_id=1,
        mode=Mode.ABSOLUTE,
        led=light_abs
    )
    await mqtt_service.publish_control_command(msg)
    await asyncio.sleep(timeout.total_seconds())

async def fan_control(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), fan_level: int = 0) -> None:
    """
    Control the fan speed.
    """
    fan_abs = math.floor(fan_level / 100.0 * 255)
    msg = ControlMsg(
        board_id=1,
        mode=Mode.ABSOLUTE,
        fan=fan_abs
    )
    await mqtt_service.publish_control_command(msg)
    await asyncio.sleep(timeout.total_seconds())

async def cooling(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), target_tmp: float = 25) -> None:
    msg = ControlMsg(
        board_id=1,
        mode=Mode.RELATIVE,
        temperature=target_tmp
    )
    await mqtt_service.publish_control_command(msg)
    await asyncio.sleep(timeout.total_seconds())

async def heating(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=10), target_tmp: float = 30) -> None:
    curr_tmp = await get_average_temperature()
    begin_time = datetime.now()
    while curr_tmp < target_tmp:
        await led_heating(mqtt_service, timeout=timedelta(minutes=1), led_level=100)
        print(f"Current temperature {curr_tmp:.2f}°C is still below target temperature {target_tmp:.2f}°C, heating up...")
        curr_tmp = await get_average_temperature()
        if datetime.now() - begin_time > timeout:
            raise TimeoutError("Heating operation timed out.")

async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext and BLEServiceContext."""
    mqtt_service_context = MQTTServiceContext(broker_host="localhost", broker_port=5001, client_id="test_client")
    await mqtt_service_context.start()
    await init_schema()
    ble_service_context = BLEServiceContext(BOARD_ID)
    await ble_service_context.start()
    os.makedirs("testdata", exist_ok=True)
    sys.stdout = open('testdata/board_data.log', 'w')
    sys.stderr = open('testdata/board_data_error.log', 'w')

    data_writer = BoardDataBatchWriter.get_instance()
    try:
        await get_current_data()
        init_temp = await get_average_temperature()
        # -------------- Varify LED Can Heat Up ----------------
        before_tmp = await get_average_temperature()
        print(f"Average temperature: {before_tmp:.2f}°C")
        print("Starting LED heating with varying levels...")
        await led_heating(mqtt_service_context, timeout=timedelta(minutes=5), led_level=100)
        after_tmp = await get_average_temperature()
        print(f"Average temperature after LED heating: {after_tmp:.2f}°C")
        if after_tmp > before_tmp:
            print("Temperature increased after LED heating.")
        else:
            raise ValueError("Temperature did not increase after LED heating.")
        await data_writer.backup("testdata/board_data_backup_light_100.json")
        await data_writer.clear_all()

        # -------------- Test Cooling ----------------
        print("Testing cooling...")
        before_tmp = await get_average_temperature()
        await cooling(mqtt_service_context, timeout=timedelta(minutes=5), target_tmp=init_temp)
        after_tmp = await get_average_temperature()

        print(f"Average temperature after cooling: {after_tmp:.2f}°C")
        if after_tmp - 0.5 < init_temp < after_tmp + 0.5:
            print("Temperature decreased after cooling.")
        else:
            raise ValueError("Temperature did not decrease after cooling.")

        # -------------- Test LED Levels ----------------
        await data_writer.clear_all()
        print("Testing LED levels...")
        print("Current average temperature:", after_tmp)
        for level in [20, 40, 50, 60, 80]:
            print(f"Setting LED level to {level}%")
            await led_heating(mqtt_service_context, led_level=level)
            current_temp = await get_average_temperature()
            await data_writer.backup(f"testdata/board_data_backup_light_{level}.json")
            await data_writer.clear_all()
            print(f"Average temperature after LED level {level}%: {current_temp:.2f}°C")


        # -------------- Test Fan Control ----------------
        for level in [0, 25, 50, 75, 100]:
            print(f"Testing fan control at level {level}%")
            await heating(mqtt_service_context, timeout=timedelta(minutes=10), target_tmp=init_temp + 2)
            await fan_control(mqtt_service_context, fan_level=level, timeout=timedelta(minutes=3))
            current_temp = await get_average_temperature()
            await data_writer.backup(f"testdata/board_data_backup_fan_{level}.json")
            await data_writer.clear_all()
            print(f"Average temperature after fan level {level}%: {current_temp:.2f}°C")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        await mqtt_service_context.stop()
        await ble_service_context.stop()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
