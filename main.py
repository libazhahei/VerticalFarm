import asyncio
from datetime import datetime, timedelta
from time import sleep

from tortoise import Tortoise

from data.config import init_schema
from gateway import ControlMsg, MQTTServiceContext
from gateway.msg import Mode
from gateway.service import BLEServiceContext
from gateway.subscriber import CommonDataRetriver


async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext and BLEServiceContext."""
    mqtt_service_context = MQTTServiceContext(broker_host="localhost", broker_port=5001, client_id="test_client")
    await mqtt_service_context.start()
    await init_schema()
    ble_service_context = BLEServiceContext([1])
    await ble_service_context.start()

    try:
        alive_devices = await mqtt_service_context.alive_devices()
        print(f"Alive devices: {alive_devices}")

        is_alive = await mqtt_service_context.is_alive(1)
        print(f"Is device 1 alive? {is_alive}")
        await asyncio.sleep(20)
        print("Publishing control command to device 1...")
        retriver = CommonDataRetriver.get_instance(1)
        print(f"Data retriever for device 1: {retriver.get_moving_average()}")
        print(f"Data retriever for device 1: {retriver.get_lastest_data()}")
        ctrl_msg = ControlMsg(board_id=1, temperature=25, mode=Mode.RELATIVE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        await asyncio.sleep(120)  # Wait for the command to be processed
        print(f"Data retriever for device 1: {retriver.get_moving_average()}")
        print(f"Data retriever for device 1: {retriver.get_lastest_data()}")
        data = await ble_service_context.fetch_data(since=datetime.now() - timedelta(days=1), board_ids=[1])
        print(f"Fetched data: {data}")
    finally:
        await mqtt_service_context.stop()
        await ble_service_context.stop()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
