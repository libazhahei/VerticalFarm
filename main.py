import asyncio

from gateway import ControlMsg, MQTTServiceContext


async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext."""
    service_context = MQTTServiceContext(borker_host="localhost", broker_port=1883, client_id="test_client")
    await service_context.start()

    try:
        alive_devices = await service_context.alive_devices()
        print(f"Alive devices: {alive_devices}")

        is_alive = await service_context.is_alive(1)
        print(f"Is device 1 alive? {is_alive}")

        ctrl_msg = ControlMsg(board_id=1)
        await service_context.publish_control_command(ctrl_msg)
    finally:
        await service_context.stop()


if __name__ == "__main__":
    asyncio.run(main())
