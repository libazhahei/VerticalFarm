import asyncio
from datetime import timedelta

from control.llm_calls import FunctionCallService, parse_time_string
from gateway.subscriber import CommonDataRetriver
from llm.models.input import LocalLLMInput
from llm.models.output import ActionPlan, Step2Output
from llm.utils.logging import WorkflowLogger


def seed_retriever_from_input(user_input: LocalLLMInput) -> None:
    retriever = CommonDataRetriver.get_instance(user_input.board_id)
    retriever.latest_temperature = user_input.internal_temp
    retriever.latest_humidity = user_input.humidity
    retriever.latest_fan = int(user_input.fan_status / 100 * 255)
    retriever.latest_led = int(user_input.led_light_status / 100 * 255)
    retriever.latest_fan_speed = float(user_input.fan_status)


class Simulator:
    def __init__(self, fc_service: FunctionCallService | None = None, logger: WorkflowLogger | None = None) -> None:
        self.fc_service = fc_service
        self.logger = logger

    async def simulate(self, user_input: LocalLLMInput, step2_output: Step2Output) -> list[str]:
        seed_retriever_from_input(user_input)
        if self.fc_service is not None:
            self.fc_service.set_board_context(user_input.board_id)

        results: list[str] = []
        for plan in step2_output.action_plan:
            for call in plan.function_calls:
                try:
                    if self.fc_service is not None and call.name.startswith("predict_"):
                        time_delta = parse_time_string(call.simulating_time)
                        result = await self.fc_service.execute_function_call(
                            call.name,
                            time_delta,
                            **call.arguments,
                        )
                    else:
                        result = self._fallback_simulate(call.name, call.arguments, call.simulating_time)
                    results.append(f"{plan.solution_id}/{call.name}: {result}")
                    if self.logger:
                        self.logger.detail(result)
                except Exception as error:
                    message = f"Simulation error for {call.name}: {error}"
                    results.append(message)
                    if self.logger:
                        self.logger.error(message)
        if not results and self.logger:
            self.logger.warn("No function calls to simulate")
        return results

    def simulate_sync(self, user_input: LocalLLMInput, step2_output: Step2Output) -> list[str]:
        return asyncio.run(self.simulate(user_input, step2_output))

    @staticmethod
    def _fallback_simulate(name: str, arguments: dict, simulating_time: str) -> str:
        if "fan" in name.lower():
            speed_change = arguments.get("fan_speed_change", 0)
            return (
                f"Function {name} predicts a {'cooling' if speed_change > 0 else 'warming'} effect "
                f"of {abs(float(speed_change)):.1f} units over {simulating_time}."
            )
        if "led" in name.lower():
            brightness_change = arguments.get("led_brightness_change", 0)
            return (
                f"Function {name} predicts a {'warming' if brightness_change > 0 else 'cooling'} effect "
                f"of {abs(float(brightness_change)):.1f} units over {simulating_time}."
            )
        return f"Function {name} called with {arguments}"
