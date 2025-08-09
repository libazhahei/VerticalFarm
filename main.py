import asyncio
from datetime import datetime, timedelta
from time import sleep
from turtle import home

from tortoise import Tortoise

from data.config import init_schema
from gateway import ControlMsg, MQTTServiceContext
from gateway.msg import Mode
from gateway.publisher import HomeAssistantDataPublisher
from gateway.service import BLEServiceContext
from gateway.subscriber import CommonDataRetriver, HomeAssistantDataSubscriber

ANSI_COLORS = {
    "black":   "30",
    "red":     "31",
    "green":   "32",
    "yellow":  "33",
    "blue":    "34",
    "magenta": "35",
    "cyan":    "36",
    "white":   "37",
    "reset":   "0"
}

ANSI_STYLES = {
    "bold":     "1",
    "dim":      "2",
    "underline":"4",
    "normal":   "22"
}

def ansi_cprint(text, fg="green", bg=None, style="normal", end="\n"):
    """
    ANSI 终端彩色打印
    :param text: 文本内容
    :param fg: 前景色名
    :param bg: 背景色名（可选）
    :param style: 样式（bold, underline, dim, normal）
    """
    fg_code = ANSI_COLORS.get(fg.lower(), "37")
    style_code = ANSI_STYLES.get(style.lower(), "0")
    bg_code = ""
    if bg:
        bg_code = ANSI_COLORS.get(bg.lower(), "")
        if bg_code:
            bg_code = str(int(bg_code) + 10)  

    ansi_sequence = f"\033[{style_code};{fg_code}"
    if bg_code:
        ansi_sequence += f";{bg_code}"
    ansi_sequence += "m"

    reset_sequence = "\033[0m"
    print(f"{ansi_sequence}{text}{reset_sequence}", end=end)

async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext and BLEServiceContext."""
    mqtt_service_context = MQTTServiceContext(broker_host="localhost", broker_port=5001, client_id="test_client")
    await mqtt_service_context.start()
    await init_schema()
    client = mqtt_service_context.get_client()
    home_ass_pub = HomeAssistantDataPublisher(client)
    home_ass_sub = HomeAssistantDataSubscriber(home_ass_pub.publish_message)
    ble_service_context = BLEServiceContext([1])
    ble_service_context.register_home_assistant_handler(home_ass_sub)
    await ble_service_context.start()

    try:
        alive_devices = await mqtt_service_context.alive_devices()
        ansi_cprint(f"Alive devices: {alive_devices}")

        is_alive = await mqtt_service_context.is_alive(1)
        ansi_cprint(f"Is device 1 alive? {is_alive}")
        
        await asyncio.sleep(5)
        # ansi_cprint("Publishing control command to device 1...")
        retriver = CommonDataRetriver.get_instance(1)
        ansi_cprint(f"Data retriever for device 1: {await retriver.get_moving_average()}")
        ansi_cprint(f"Data retriever for device 1: {await retriver.get_lastest_data()}")

        while True:
            await asyncio.sleep(1)
        ansi_cprint("Publishing control LED command 0 to device 1...")
        ctrl_msg = ControlMsg(board_id=1, led=255, mode=Mode.ABSOLUTE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        await asyncio.sleep(5)
        ansi_cprint("Publishing control command 1 to device 1...")
        ctrl_msg = ControlMsg(board_id=1, led=0, mode=Mode.ABSOLUTE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        ctrl_msg = ControlMsg(board_id=1, fan=255, mode=Mode.ABSOLUTE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        await asyncio.sleep(5)
        ctrl_msg = ControlMsg(board_id=1, fan=0, mode=Mode.ABSOLUTE)
        ctrl_msg = ControlMsg(board_id=1, temperature=15, mode=Mode.RELATIVE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        await asyncio.sleep(10)  
        ctrl_msg = ControlMsg(board_id=1, fan=0, mode=Mode.ABSOLUTE)
        await mqtt_service_context.publish_control_command(ctrl_msg)
        await asyncio.sleep(5)
        # ansi_cprint(f"Data retriever for device 1: {await retriver.get_moving_average()}")
        # ansi_cprint(f"Data retriever for device 1: {await retriver.get_lastest_data()}")
        # data = await ble_service_context.fetch_data(since=datetime.now() - timedelta(days=1), board_ids=[1])
        # ansi_cprint(f"Fetched data: {data}")
    finally:
        # exit(1)
        await mqtt_service_context.stop()
        await ble_service_context.stop()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
