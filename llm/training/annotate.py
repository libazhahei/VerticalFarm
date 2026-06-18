from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.output_parsers import JsonOutputParser

from llm.clients.base import BaseLLMClient
from llm.models.input import LocalLLMInput
from llm.models.output import (
    ActionPlan,
    ControlCommand,
    FunctionCall,
    SideEffectEvaluation,
    Step1Output,
    Step2Output,
    Step3Output,
)
from llm.training.config import SynthesisConfig
from llm.training.prompt_builder import build_prompt_for_stage, format_chat_messages
from llm.training.prompts.teacher import (
    STAGE_SCHEMAS,
    build_negative_prompt,
    build_teacher_prompt,
)
from llm.training.schemas import DPOFlawCategory, DPOPair, SeedScenario, SFTSample, WorkflowStage
from llm.training.state_generator import seed_to_local_llm_input
from llm.workflow.safety_shield import SafetyShield

STAGE_OUTPUT_KEY: dict[WorkflowStage, str] = {
    WorkflowStage.DIAGNOSIS: "diagnosis",
    WorkflowStage.PLANNING: "planning",
    WorkflowStage.SIDE_EFFECT: "side_effect",
    WorkflowStage.DECISION: "decision",
    WorkflowStage.FINAL_COMMAND: "final_command",
}

DPO_FLAW_CYCLE = list(DPOFlawCategory)


class TeacherAnnotator:
    def __init__(self, client: BaseLLMClient | None, config: SynthesisConfig) -> None:
        self.client = client
        self.config = config
        self.safety_shield = SafetyShield()

    def _extract_content(self, response: Any) -> str:
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return JsonOutputParser().parse(cleaned)

    def validate_output(self, stage: WorkflowStage, raw_json: dict[str, Any], user_input: LocalLLMInput | None = None) -> bool:
        schema = STAGE_SCHEMAS[stage]
        try:
            validated = schema.model_validate(raw_json)
        except Exception:
            return False
        if stage == WorkflowStage.PLANNING and user_input is not None:
            step2 = Step2Output.model_validate(validated.model_dump() if hasattr(validated, "model_dump") else validated)
            filtered = self.safety_shield.filter(user_input, step2)
            if len(filtered.action_plan) < len(step2.action_plan):
                return False
        return True

    def _default_output(self, stage: WorkflowStage, seed: SeedScenario | None = None) -> dict[str, Any]:
        sv = seed.state_vector if seed else None
        crop = seed.crop_context if seed else None
        if stage == WorkflowStage.DIAGNOSIS:
            if sv and crop:
                issue = (
                    f"Internal temperature at {sv.internal_temp}°C "
                    f"(ideal {crop.ideal_temp_range[0]}–{crop.ideal_temp_range[1]}°C), "
                    f"trend {sv.temp_trend_15min}."
                )
                states = (
                    ["High Temperature", "Rising Trend"]
                    if sv.internal_temp > crop.ideal_temp_range[1]
                    else ["Stable Maintenance"]
                )
            else:
                issue, states = "Stable environmental conditions", ["Stable Maintenance"]
            return Step1Output(core_issue=issue, states=states, confidence=[8, 7]).model_dump()
        if stage == WorkflowStage.PLANNING:
            desc = (
                f"Adjust fan to {seed.operator_action.new_fan_rpm} RPM and LED to "
                f"{int(seed.operator_action.new_led_pwm * 100)}% for {seed.seed_id}."
                if seed
                else "Maintain current settings"
            )
            return Step2Output(
                action_plan=[
                    ActionPlan(
                        solution_id="SOLUTION_01",
                        description=desc,
                        function_calls=[
                            FunctionCall(
                                name="predict_temp_change_with_action",
                                arguments={
                                    "fan_speed_change": seed.operator_action.new_fan_rpm if seed else 2000,
                                    "led_brightness_change": int(seed.operator_action.new_led_pwm * 100) if seed else 50,
                                },
                                simulating_time="15 minutes",
                            )
                        ],
                        confidence=7,
                    )
                ]
            ).model_dump()
        if stage == WorkflowStage.SIDE_EFFECT:
            return SideEffectEvaluation(
                solution_id="SOLUTION_01",
                side_effects=[
                    {
                        "parameter_name": "fan_speed",
                        "change_magnitude": 15.0,
                        "change_type": "increase",
                        "potential_impact": "humidity_reduction",
                        "risk_level": "medium",
                    }
                ],
                overall_risk_assessment=f"Moderate risk for {seed.seed_id if seed else 'scenario'}",
                recommended_action="proceed",
                confidence=7,
            ).model_dump()
        if stage == WorkflowStage.DECISION:
            return Step3Output(
                reason=seed.operator_rationale if seed else "Maintain current plan",
                final_decision="SOLUTION_01",
            ).model_dump()
        fan = int(seed.operator_action.new_fan_rpm / 3400 * 100) if seed else 50
        led = int(seed.operator_action.new_led_pwm * 100) if seed else 50
        return ControlCommand(
            fan_pwm=fan,
            led_pwm=led,
            rationale=seed.operator_rationale if seed else "Maintain settings",
        ).model_dump()

    def annotate_stage(
        self,
        stage: WorkflowStage,
        seed: SeedScenario,
        prior_outputs: dict[str, Any] | None = None,
        needs_human_review: bool = False,
    ) -> SFTSample:
        user_input = seed_to_local_llm_input(seed)
        inference_prompt = build_prompt_for_stage(stage, user_input, prior_outputs)

        if self.client is None or self.config.skip_llm:
            output_json = self._default_output(stage, seed)
            source = "stub"
        else:
            teacher_prompt = build_teacher_prompt(stage, seed, prior_outputs)
            response = self.client.run_messages(
                [{"role": "user", "content": teacher_prompt}],
                temperature=self.config.teacher_temperature,
            )
            raw = self._extract_content(response)
            try:
                output_json = self._parse_json(raw)
                if not self.validate_output(stage, output_json, user_input):
                    output_json = self._default_output(stage, seed)
                    source = "llm_synthesis_fallback"
                else:
                    source = "llm_synthesis"
            except Exception:
                output_json = self._default_output(stage, seed)
                source = "llm_synthesis_fallback"

        assistant_json = json.dumps(output_json, ensure_ascii=False)
        return SFTSample(
            stage=stage,
            messages=format_chat_messages(inference_prompt, assistant_json),
            metadata={
                "seed_id": seed.seed_id,
                "source": source,
                "needs_human_review": needs_human_review,
            },
        )

    def annotate_full_trace(self, seed: SeedScenario) -> list[SFTSample]:
        prior: dict[str, Any] = {}
        samples: list[SFTSample] = []
        for stage in self.config.stages:
            key = STAGE_OUTPUT_KEY[stage]
            for _ in range(self.config.samples_per_stage):
                sample = self.annotate_stage(stage, seed, prior or None)
                samples.append(sample)
                if key not in prior:
                    try:
                        prior[key] = json.loads(sample.messages[-1]["content"])
                    except json.JSONDecodeError:
                        prior[key] = self._default_output(stage)
        return samples

    def generate_dpo_pair(
        self,
        seed: SeedScenario,
        flaw_category: DPOFlawCategory,
        prior_outputs: dict[str, Any] | None = None,
    ) -> DPOPair:
        stage = WorkflowStage.PLANNING
        user_input = seed_to_local_llm_input(seed)
        prior = prior_outputs or {"diagnosis": self._default_output(WorkflowStage.DIAGNOSIS, seed)}
        prompt = build_prompt_for_stage(stage, user_input, prior)

        chosen_json = self._default_output(stage, seed)
        if self.client and not self.config.skip_llm:
            teacher_prompt = build_teacher_prompt(stage, seed, prior)
            response = self.client.run_messages(
                [{"role": "user", "content": teacher_prompt}],
                temperature=self.config.teacher_temperature,
            )
            try:
                chosen_json = self._parse_json(self._extract_content(response))
            except Exception:
                pass

        rejected_json: dict[str, Any]
        if self.client and not self.config.skip_llm:
            neg_prompt = build_negative_prompt(stage, seed, flaw_category, prior)
            response = self.client.run_messages(
                [{"role": "user", "content": neg_prompt}],
                temperature=0.3,
            )
            try:
                rejected_json = self._parse_json(self._extract_content(response))
            except Exception:
                rejected_json = self._flawed_fallback(flaw_category)
        else:
            rejected_json = self._flawed_fallback(flaw_category)

        return DPOPair(
            prompt=prompt,
            chosen=json.dumps(chosen_json, ensure_ascii=False),
            rejected=json.dumps(rejected_json, ensure_ascii=False),
            stage=stage,
            category=flaw_category.value,
            rejection_source="teacher_flaw",
            metadata={"seed_id": seed.seed_id},
        )

    def _flawed_fallback(self, flaw: DPOFlawCategory) -> dict[str, Any]:
        if flaw == DPOFlawCategory.JSON_FORMAT:
            return {"action_plan": [{"solution_id": "SOLUTION_01", "confidence": 8}]}
        if flaw == DPOFlawCategory.PHYSICAL_CONTRADICTION:
            return {
                "action_plan": [
                    {
                        "solution_id": "SOLUTION_REJECTED",
                        "description": "Max LED and zero fan to maximize DLI",
                        "function_calls": [
                            {
                                "name": "predict_temp_change_with_action",
                                "arguments": {"led_brightness_change": 100, "fan_speed_change": 0},
                                "simulating_time": "15 minutes",
                            }
                        ],
                        "confidence": 8,
                    }
                ]
            }
        if flaw == DPOFlawCategory.SAFETY_BYPASS:
            return {"mqtt_command": {"fan_pwm": 255, "led_pwm": 255}, "skip_simulation": True}
        return {
            "action_plan": [
                {
                    "solution_id": "SOLUTION_REJECTED",
                    "description": "Increase LED during Lights OFF",
                    "function_calls": [
                        {
                            "name": "predict_temp_change_with_led_action",
                            "arguments": {"led_brightness_change": 80},
                            "simulating_time": "15 minutes",
                        }
                    ],
                    "confidence": 7,
                }
            ]
        }
