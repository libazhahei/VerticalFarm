from datetime import timedelta
import json
import time
from typing import Any

from control.model import ChangeModel, TemperatureModel
from gateway.msg import ControlMsg, Mode
from gateway.service import MQTTServiceContext
from gateway.subscriber import CommonDataRetriver # For remaining_light_period example

class FunctionCallHandler:
    def __init__(self, function_definitions_json: str):
        """
        Initializes the FunctionCallHandler with function definitions.

        Args:
            function_definitions_json (str): A JSON string containing a list of
                                             function definitions.
        """
        try:
            parsed_definitions = json.loads(function_definitions_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format for function definitions: {e}")

        if not isinstance(parsed_definitions, list):
            raise TypeError("Function definitions must be a JSON array.")

        self.functions = {}
        for func_def in parsed_definitions:
            if not isinstance(func_def, dict) or 'name' not in func_def:
                raise ValueError("Each function definition must be an object with a 'name'.")
            self.functions[func_def['name']] = func_def

    def _get_python_type(self, json_type: str):
        """Maps JSON schema types to Python types."""
        if json_type == "string":
            return str
        elif json_type == "number":
            return (int, float)
        elif json_type == "integer":
            return int
        elif json_type == "boolean":
            return bool
        elif json_type == "array":
            return list
        elif json_type == "object":
            return dict
        return None # For unknown types

    def validate_function_call(self, function_name: str, **kwargs):
        """
        Validates a function call against the loaded schema.

        Args:
            function_name (str): The name of the function to call.
            **kwargs: Keyword arguments representing the parameters for the function call.

        Returns:
            tuple: A tuple (function_name, validated_args) if validation passes.
                   validated_args will be a dictionary of the arguments.

        Raises:
            ValueError: If the function name is not found, or if arguments do not
                        match the schema (missing required, wrong type, unknown args,
                        or enum violations).
        """
        if function_name not in self.functions:
            raise ValueError(f"Function '{function_name}' not found in definitions.")

        func_def = self.functions[function_name]
        parameters_schema = func_def.get('parameters', {})
        properties = parameters_schema.get('properties', {})
        required_params = parameters_schema.get('required', [])
        for param_name in required_params:
            if param_name not in kwargs:
                raise ValueError(f"Missing required argument '{param_name}' for function '{function_name}'.")
        validated_args = {}
        for arg_name, arg_value in kwargs.items():
            if arg_name not in properties:
                raise ValueError(f"Unknown argument '{arg_name}' for function '{function_name}'.")

            param_spec = properties[arg_name]
            expected_json_type = param_spec.get('type')
            expected_python_type = self._get_python_type(expected_json_type)
            if expected_python_type and not isinstance(arg_value, expected_python_type):
                raise ValueError(
                    f"Argument '{arg_name}' for function '{function_name}' has "
                    f"incorrect type. Expected {expected_json_type}, got {type(arg_value).__name__}."
                )
            if 'enum' in param_spec:
                if arg_value not in param_spec['enum']:
                    raise ValueError(
                        f"Argument '{arg_name}' for function '{function_name}' has an "
                        f"invalid value '{arg_value}'. Must be one of {param_spec['enum']}."
                    )
            
            validated_args[arg_name] = arg_value
        
        return function_name, validated_args

all_function_calls_json = """
[
    { "name": "predict_temp_change_with_led_action", "description": "Predict the temperature change over the next 15 minutes given a change in LED brightness.", "parameters": { "type": "object", "properties": { "led_brightness_change": { "type": "number", "description": "Percentage change in LED brightness, if no fans open e.g., -15 for -15%" } }, "required": ["led_brightness_change"] } },
    { "name": "predict_temp_change_with_fan_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed.", "parameters": { "type": "object", "properties": { "fan_speed_change": { "type": "number", "description": "temperature target change in fan speed, if no leds open e.g., 14.5" } }, "required": ["fan_speed_change"] } },
    { "name": "predict_temp_change_with_action", "description": "Predict the temperature change over the next 15 minutes given a change in fan speed and LED brightness. This prediction is not accurate than others", "parameters": { "type": "object", "properties": { "fan_speed_change": { "type": "number", "description": "temperature target change in fan speed, if no leds open e.g., 14.5" }, "led_brightness_change": { "type": "number", "description": "Percentage change in LED brightness, if no fans open e.g., -15 for -15%" } }, "required": ["fan_speed_change", "led_brightness_change"] } },
    { "name": "remaining_light_period", "description": "Calculate the remaining time in the current light period.", "parameters": { "type": "object", "properties": {} } },
    { "name": "set_device_state_abs", "description": "Directly set the fan speed or LED brightness.", "parameters": { "type": "object", "properties": { "device": { "type": "string", "enum": ["fan", "led"] }, "value": { "type": "number", "description": "Target Value in percentage" } }, "required": ["device", "value"] } },
    { "name": "set_device_state_rel", "description": "Set temperature or brightness.", "parameters": { "type": "object", "properties": { "type": { "type": "string", "enum": ["temperature", "brightness"] }, "value": { "type": "number", "description": "Target Value in its range. temperature: environmental range +- 1, brightness: 0-4000 lux" } }, "required": ["type", "value"] } }
]
"""

class FunctionExecutor:
    def __init__(self, function_call_handler: FunctionCallHandler):
        self.handler = function_call_handler
        self.available_functions = {} 

    def register_function(self, name: str, func_obj):
        self.available_functions[name] = func_obj
        print(f"Registered function: '{name}'")

    async def execute_call(self, function_name: str, time: timedelta = timedelta(minutes=15), **kwargs) -> Any:
        try:
            args_for_validation = kwargs.copy()
            if 'time' in args_for_validation:
                print("Warning: 'time' argument provided in kwargs will be ignored in favor of explicit 'time' parameter.")
                del args_for_validation['time'] 

            validated_name, validated_args = self.handler.validate_function_call(function_name, **args_for_validation)
            print(f"\n--- Executing Validated Call: {validated_name} ---")
            print(f"  Validated Arguments (excluding time): {validated_args}")

            if validated_name not in self.available_functions:
                raise ValueError(f"Function '{validated_name}' is defined but not registered for execution.")

            func_to_execute = self.available_functions[validated_name]
            
            validated_args['time'] = time
            print(f"  Including implicit 'time' parameter: {time.total_seconds()/60:.0f} minutes")

            result = await func_to_execute(**validated_args)
            print(f"  Execution of '{validated_name}' completed. Result: {result}")
            return result

        except ValueError as e:
            print(f"\n--- Execution Error (Validation/Registration): {e} ---")
            raise 
        except Exception as e:
            print(f"\n--- Execution Error (Runtime): An unexpected error occurred during '{function_name}' execution: {e} ---")
            raise 

async def _predict_temp_change_with_led_action(led_brightness_change: float, time: timedelta = timedelta(minutes=15)) -> str:
    model = TemperatureModel()
    retriver = CommonDataRetriver.get_instance(2)
    latest_temp = retriver.latest_temperature
    led = min((retriver.latest_led + led_brightness_change) / 255.0, 1)
    result = model.evaluate(led, latest_temp, time.total_seconds())
    diff_temp = result - latest_temp
    return f"Predicted temperature will {'increase' if diff_temp > 0 else 'decrease'} by {abs(diff_temp):.2f}°C, reaching {result:.2f}°C."

async def _predict_temp_change_with_fan_action(fan_speed_change: float, time: timedelta = timedelta(minutes=15)) -> str:
    model = TemperatureModel()
    retriver = CommonDataRetriver.get_instance(2)
    latest_temp = retriver.latest_temperature
    fan = min((retriver.latest_fan + fan_speed_change) / 255.0, 1)
    result = model.evaluate(fan, latest_temp, time.total_seconds())
    diff_temp = result - latest_temp
    return f"Predicted temperature will {'increase' if diff_temp > 0 else 'decrease'} by {abs(diff_temp):.2f}°C, reaching {result:.2f}°C."

async def _predict_temp_change_with_action(fan_speed_change: float, led_brightness_change: float, time: timedelta = timedelta(minutes=15)) -> str:
    mode = ChangeModel()
    retriver = CommonDataRetriver.get_instance(2)
    latest_temp = retriver.latest_temperature
    fan = min((retriver.latest_fan + fan_speed_change) / 255.0, 1)
    led = min((retriver.latest_led + led_brightness_change) / 255.0, 1)
    result = mode.evaluate(fan, led, latest_temp, time.total_seconds())
    diff_temp = result - latest_temp
    return f"Predicted temperature will {'increase' if diff_temp > 0 else 'decrease'} by {abs(diff_temp):.2f}°C, reaching {result:.2f}°C."

def convert_set_device_state_abs_to_control_msg(device: str, value: float) -> ControlMsg:
    scaled_value = int(max(0, min(100, value)) / 100 * 255)
    msg_params = {
        "board_id": 0,
        "mode": Mode.ABSOLUTE,
        "fan": 0,
        "led": 0,
        "temperature": 0.0,
        "light_intensity": 0.0,
    }

    if device == "fan":
        msg_params["fan"] = scaled_value
    elif device == "led":
        msg_params["led"] = scaled_value
    else: 
        return ControlMsg(board_id=5)

    return ControlMsg(**msg_params)

def convert_set_device_state_rel_to_control_msg(type: str, value: float) -> ControlMsg:
    msg_params = {
        "board_id": 0,
        "mode": Mode.RELATIVE,
        "fan": 0,
        "led": 0,
        "temperature": 0.0,
        "light_intensity": 0.0,
    }

    if type == "temperature":
        msg_params["temperature"] = max(0.0, min(100.0, value))
    elif type == "brightness":
        msg_params["light_intensity"] = max(0.0, min(65535.0, value))
    else:
        return ControlMsg(board_id=5)

    # message_id 和 timestamp 将由 ControlMsg 的 default_factory 自动生成
    return ControlMsg(**msg_params)


def parse_time_string(time_str: str) -> timedelta:
    time_str = time_str.strip().lower()
    parts = time_str.split()
    if len(parts) != 2:
        raise ValueError(f"Invalid time format: {time_str}")
    value, unit = parts
    value = float(value)
    if unit in ["min", "mins", "minute", "minutes"]:
        return timedelta(minutes=value)
    elif unit in ["h", "hr", "hrs", "hour", "hours"]:
        return timedelta(hours=value)
    elif unit in ["s", "sec", "secs", "second", "seconds"]:
        return timedelta(seconds=value)
    elif unit in ["d", "day", "days"]:
        return timedelta(days=value)
    else:
        raise ValueError(f"Unknown time unit: {unit}")


class FunctionCallService:
    service : "FunctionCallService" 
    function_call_handler: FunctionCallHandler
    function_executor: FunctionExecutor
    mqtt_service_context: MQTTServiceContext

    @classmethod
    def initialize(cls, mqtt_service_context: MQTTServiceContext) -> None:
        """
        Initializes the FunctionCallService with the function call handler and executor.
        This method should be called once at application startup.
        """
        cls.service = cls.get_instance()
        cls.service.mqtt_service_context = mqtt_service_context

    @classmethod
    def get_instance(cls) -> "FunctionCallService":
        handler = FunctionCallHandler(all_function_calls_json)
        executor = FunctionExecutor(handler)
        executor.register_function("predict_temp_change_with_led_action", _predict_temp_change_with_led_action)
        executor.register_function("predict_temp_change_with_fan_action", _predict_temp_change_with_fan_action)
        executor.register_function("predict_temp_change_with_action", _predict_temp_change_with_action)
        executor.register_function("set_device_state_abs", convert_set_device_state_abs_to_control_msg)
        executor.register_function("set_device_state_rel", convert_set_device_state_rel_to_control_msg)

        service = cls()
        service.function_call_handler = handler
        service.function_executor = executor
        return service

    async def execute_function_call(self, function_name: str, time: timedelta, **kwargs) -> Any:
        """
        Executes a function call after validating the arguments.

        Args:
            function_name (str): The name of the function to call.
            time (timedelta): The time duration for the function call.
            **kwargs: Keyword arguments representing the parameters for the function call.

        Returns:
            any: The result of the function call.

        Raises:
            ValueError: If validation fails or if the function is not registered.
        """
        if not function_name.startswith("set_"):
            return self.function_executor.execute_call(function_name, time=time, **kwargs)
        else:
            msg = await self.function_executor.execute_call(function_name, **kwargs)
            prev_msg = await self.mqtt_service_context.get_current_command()
            if msg is None or prev_msg is None:
                return "Keep current command"  # No action needed, just return True
            if function_name == "set_device_state_abs":
                msg.board_id = prev_msg.board_id
                await self.mqtt_service_context.publish_control_command(msg)
            elif function_name == "set_device_state_rel":
                msg.board_id = prev_msg.board_id
                await self.mqtt_service_context.publish_control_command(msg)
            return f"Published control command: {msg}"
            