import asyncio
from datetime import datetime, timedelta
import time
from tortoise import Tortoise
import logging
import sys

from data.config import init_schema
from gateway import ControlMsg, MQTTServiceContext
from gateway.service import BLEServiceContext
from data.tables import BoardData, BoardDataBatchWriter
from gateway.msg import ControlMsg, Mode
import math
import os

from gateway.subscriber import CommonDataRetriver
BOARD_ID = [1]

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


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()  # 及时写入文件

    def flush(self):
        for f in self.files:
            f.flush()

async def get_latest_temperature(board_id: int = 1) -> float:
    retriver = CommonDataRetriver.get_instance(board_id)
    result = await retriver.get_lastest_data()
    return result['temperature'] if result else 0.0

async def get_average_temperature(timeout: timedelta = timedelta(seconds=5)) -> float:
    retriver = CommonDataRetriver.get_instance(1)
    result = await retriver.get_moving_average()
    return result['temperature'] if result else 0.0

async def led_heating(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), led_level: int = 0) -> None:
    """
    Control the LED heating element.
    """
    begin_time = datetime.now()
    light_abs = math.floor(led_level / 100.0 * 255)
    msg = ControlMsg(
        board_id=1,
        mode=Mode.ABSOLUTE,
        led=light_abs
    )
    await mqtt_service.publish_control_command(msg)
    while datetime.now() - begin_time < timeout:
        curr_temp = await get_average_temperature()
        ansi_cprint(f"Current temperature after LED heating: {curr_temp:.2f}°C, remaining time: {timeout - (datetime.now() - begin_time)}", fg="yellow")
        await asyncio.sleep(timedelta(seconds=30).total_seconds())

async def fan_control(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), fan_level: int = 0) -> None:
    """
    Control the fan speed.
    """
    begin_time = datetime.now()
    fan_abs = math.floor(fan_level / 100.0 * 255)
    msg = ControlMsg(
        board_id=1,
        mode=Mode.ABSOLUTE,
        fan=fan_abs
    )
    await mqtt_service.publish_control_command(msg)
    while datetime.now() - begin_time < timeout:
        curr_temp = await get_average_temperature()
        ansi_cprint(f"Current temperature after fan control: {curr_temp:.2f}°C, remaining time: {timeout - (datetime.now() - begin_time)}", fg="yellow")
        await asyncio.sleep(timedelta(seconds=10).total_seconds())

async def cooling(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=5), target_tmp: float = 25) -> None:
    begin_time = datetime.now()
    msg = ControlMsg(
        board_id=1,
        mode=Mode.RELATIVE,
        temperature=target_tmp
    )
    await mqtt_service.publish_control_command(msg)
    while datetime.now() - begin_time < timeout:
        curr_temp = await get_average_temperature()
        ansi_cprint(f"Current temperature after LED heating: {curr_temp:.2f}°C, remaining time: {timeout - (datetime.now() - begin_time)}", fg="yellow")
        await asyncio.sleep(timedelta(seconds=30).total_seconds())

async def heating(mqtt_service: MQTTServiceContext, timeout: timedelta = timedelta(minutes=10), target_tmp: float = 30) -> None:
    curr_tmp = await get_average_temperature()
    begin_time = datetime.now()
    while curr_tmp < target_tmp:
        await led_heating(mqtt_service, timeout=timedelta(minutes=1), led_level=100)
        ansi_cprint(f"Current temperature {curr_tmp:.2f}°C is still below target temperature {target_tmp:.2f}°C, heating up... ")
        ansi_cprint(f"elapsed time: {datetime.now() - begin_time}")
        curr_tmp = await get_average_temperature()
        if datetime.now() - begin_time > timeout:
            ansi_cprint(f"Timeout reached after {timeout}, stopping heating.")
            break

async def main() -> None:
    """Main function to demonstrate the usage of MQTTServiceContext and BLEServiceContext."""
    mqtt_service_context = MQTTServiceContext(broker_host="192.168.8.164", broker_port=5001, client_id="test_client")
    await mqtt_service_context.start()
    await init_schema()
    ble_service_context = BLEServiceContext(BOARD_ID)
    await ble_service_context.start()
    os.makedirs("testdata", exist_ok=True)
    log_file = open('testdata/board_data.log', 'w')
    err_file = open('testdata/board_data_error.log', 'w')

    # 让 stdout 同时写到终端和 log 文件
    sys.stdout = Tee(sys.__stdout__, log_file)

    # 让 stderr 同时写到终端和 error 文件
    sys.stderr = Tee(sys.__stderr__, err_file)

    data_writer = BoardDataBatchWriter.get_instance()
    ansi_cprint("Database writer OK.")
    ansi_cprint("Waiting for Collecting data...")
    try:
        await asyncio.sleep(10)  # 等待服务启动
        init_temp = 22
        # -------------- Varify LED Can Heat Up ----------------
        before_tmp = await get_average_temperature()
        ansi_cprint(f"Average temperature: {before_tmp:.2f}°C")
        ansi_cprint("Starting LED heating with varying levels...")
        await led_heating(mqtt_service_context, timeout=timedelta(minutes=15), led_level=100)
        after_tmp = await get_average_temperature()
        ansi_cprint(f"Average temperature after LED heating: {after_tmp:.2f}°C")
        if after_tmp > before_tmp:
            ansi_cprint("Temperature increased after LED heating.")
        else:
            raise ValueError("Temperature did not increase after LED heating.")
        # await led_heating(mqtt_service_context, timeout=timedelta(minutes=10), led_level=0)
        # await data_writer.backup(f"testdata/board_data_backup_light_100.db")
        await data_writer.clear_all()

        # -------------- Test Cooling ----------------
        # ansi_cprint("Testing cooling...")
        # before_tmp = await get_average_temperature()
        # await cooling(mqtt_service_context, timeout=timedelta(minutes=5), target_tmp=init_temp)
        # after_tmp = await get_average_temperature()

        # ansi_cprint(f"Average temperature after cooling: {after_tmp:.2f}°C")
        # if after_tmp - 0.5 < init_temp < after_tmp + 0.5:
        #     ansi_cprint("Temperature decreased after cooling.")
        # else:
        #     raise ValueError("Temperature did not decrease after cooling.")

        # # -------------- Test LED Levels ----------------
        # await data_writer.clear_all()
        # ansi_cprint("Testing LED levels...")
        # ansi_cprint(f"Current average temperature: {after_tmp:.2f}°C")
        # for level in [20, 40, 50, 60, 80]:
        #     ansi_cprint(f"Setting LED level to {level}%")
        #     await led_heating(mqtt_service_context, led_level=level)
        #     current_temp = await get_average_temperature()

        #     await data_writer.backup(f"testdata/board_data_backup_light_{level}.db")
        #     await data_writer.clear_all()
        #     ansi_cprint(f"Average temperature after LED level {level}%: {current_temp:.2f}°C")


        # # -------------- Test Fan Control ----------------
        # for level in [0, 25, 50, 75, 100]:
        #     ansi_cprint(f"Testing fan control at level {level}%")
        #     await heating(mqtt_service_context, timeout=timedelta(minutes=10), target_tmp=init_temp + 2)
        #     await fan_control(mqtt_service_context, fan_level=level, timeout=timedelta(minutes=3))
        #     current_temp = await get_average_temperature()

        #     await data_writer.backup(f"testdata/board_data_backup_fan_{level}.db")
        #     await data_writer.clear_all()
        #     ansi_cprint(f"Average temperature after fan level {level}%: {current_temp:.2f}°C")

    except Exception as e:
        ansi_cprint(f"An error occurred: {e}")
    finally:
        await mqtt_service_context.stop()
        await ble_service_context.stop()
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
