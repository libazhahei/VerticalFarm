import asyncio
from datetime import datetime, timedelta

from data.config import init_schema
from gateway import ControlMsg, MQTTServiceContext
from gateway.service import BLEServiceContext


async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext and BLEServiceContext."""
    mqtt_service_context = MQTTServiceContext(borker_host="localhost", broker_port=1883, client_id="test_client")
    await mqtt_service_context.start()
    await init_schema()
    ble_service_context = BLEServiceContext([1, 2, 3])
    await ble_service_context.start()

    try:
        alive_devices = await mqtt_service_context.alive_devices()
        print(f"Alive devices: {alive_devices}")

        is_alive = await mqtt_service_context.is_alive(1)
        print(f"Is device 1 alive? {is_alive}")

        ctrl_msg = ControlMsg(board_id=1)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        print("BLE connected devices:", ble_service_context.connected_devices())
        data = await ble_service_context.fetch_data(since=datetime.now() - timedelta(days=1), board_ids=[1])
        print(f"Fetched data: {data}")
    finally:
        await mqtt_service_context.stop()
        await ble_service_context.stop()


if __name__ == "__main__":
    asyncio.run(main())
