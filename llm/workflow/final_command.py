from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput, build_step_data
from llm.models.output import ActionPlan, ControlCommand
from llm.prompts.local import FINAL_COMMAND_PROMPT
from llm.utils.json import parse_json_with_fallback
from llm.utils.logging import WorkflowLogger


class FinalCommandGenerator:
    def __init__(self, client: BaseLLMClient, repair_client: BaseLLMClient | None = None, logger: WorkflowLogger | None = None) -> None:
        self.client = client
        self.repair_client = repair_client or client
        self.logger = logger

    def generate(self, user_input: LocalLLMInput, selected_plan: ActionPlan) -> ControlCommand:
        prompt_data = build_step_data(user_input)
        prompt_data.update(selected_plan.model_dump())
        raw = self.client.run_chain(FINAL_COMMAND_PROMPT, prompt_data, temperature=0.2)
        command = parse_json_with_fallback(raw, ControlCommand, self.repair_client.get_model(temperature=0.0))
        if self.logger:
            self.logger.detail(
                f"fan_pwm={command.fan_pwm}, led_pwm={command.led_pwm}, rationale={command.rationale[:80]}..."
            )
        return command
