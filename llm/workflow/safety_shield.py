from llm.models.input import LocalLLMInput
from llm.models.output import ActionPlan, Step2Output
from llm.utils.logging import WorkflowLogger


class SafetyShield:
    def __init__(self, logger: WorkflowLogger | None = None) -> None:
        self.logger = logger

    def filter(self, user_input: LocalLLMInput, step2_output: Step2Output) -> Step2Output:
        filtered: list[ActionPlan] = []
        for plan in step2_output.action_plan:
            reject_reason = self._check_plan(user_input, plan)
            if reject_reason:
                if self.logger:
                    self.logger.warn(f"Rejecting {plan.solution_id}: {reject_reason}")
            else:
                if self.logger:
                    self.logger.detail(f"Accepting {plan.solution_id}", fg="green")
                filtered.append(plan)
        return Step2Output(action_plan=filtered)

    def _check_plan(self, user_input: LocalLLMInput, plan: ActionPlan) -> str | None:
        for call in plan.function_calls:
            name = call.name.lower()
            if "fan" in name:
                delta = float(call.arguments.get("fan_speed_change", 0))
                if delta > 70 or delta < -70:
                    return f"fan_speed_change {delta} exceeds ±70%"
            if "led" in name:
                delta = float(call.arguments.get("led_brightness_change", 0))
                if delta > 50 or delta < -50:
                    return f"led_brightness_change {delta} exceeds ±50%"
                if user_input.photoperiod_status.upper() == "OFF" and delta > 0:
                    return "LED increase not allowed during Lights OFF period"
        if user_input.photoperiod_status.upper() == "OFF":
            for call in plan.function_calls:
                if "led" in call.name.lower() and float(call.arguments.get("led_brightness_change", 0)) > 0:
                    return "photoperiod OFF forbids LED increases"
        return None
