from llm.models.output import ControlCommand
from gateway.msg import ControlMsg, Mode


def control_command_to_mqtt(command: ControlCommand, board_id: int) -> ControlMsg:
    fan = int(max(0, min(100, command.fan_pwm)) / 100 * 255)
    led = int(max(0, min(100, command.led_pwm)) / 100 * 255)
    return ControlMsg(
        board_id=board_id,
        mode=Mode.ABSOLUTE,
        fan=fan,
        led=led,
    )
