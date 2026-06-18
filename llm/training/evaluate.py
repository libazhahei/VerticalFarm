"""Evaluation metrics for training pipeline ablation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llm.models.output import (
    ActionPlan,
    ControlCommand,
    SideEffectEvaluation,
    Step1Output,
    Step2Output,
    Step3Output,
)
from llm.training.schemas import WorkflowStage
from llm.workflow.safety_shield import SafetyShield


def _load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

STAGE_VALIDATORS: dict[str, type] = {
    WorkflowStage.DIAGNOSIS.value: Step1Output,
    WorkflowStage.PLANNING.value: Step2Output,
    WorkflowStage.SIDE_EFFECT.value: SideEffectEvaluation,
    WorkflowStage.DECISION.value: Step3Output,
    WorkflowStage.FINAL_COMMAND.value: ControlCommand,
}

VALID_FUNCTION_NAMES = {
    "predict_temp_change_with_led_action",
    "predict_temp_change_with_fan_action",
    "predict_temp_change_with_action",
}


def evaluate_json_compliance(predictions: list[dict[str, Any]], stage: str | None = None) -> float:
    if not predictions:
        return 0.0
    passed = 0
    for pred in predictions:
        stg = stage or pred.get("stage", "")
        validator = STAGE_VALIDATORS.get(stg)
        if validator is None:
            continue
        content = pred.get("content") or pred.get("assistant") or ""
        if isinstance(content, dict):
            raw = content
        else:
            try:
                raw = json.loads(content)
            except json.JSONDecodeError:
                continue
        try:
            validator.model_validate(raw)
            passed += 1
        except Exception:
            pass
    return passed / len(predictions) if predictions else 0.0


def evaluate_tool_call_success(predictions: list[dict[str, Any]]) -> float:
    planning_preds = [p for p in predictions if p.get("stage") == WorkflowStage.PLANNING.value]
    if not planning_preds:
        return 0.0
    passed = 0
    for pred in planning_preds:
        content = pred.get("content", pred.get("assistant", "{}"))
        try:
            raw = json.loads(content) if isinstance(content, str) else content
            step2 = Step2Output.model_validate(raw)
            ok = True
            for plan in step2.action_plan:
                for fc in plan.function_calls:
                    if fc.name not in VALID_FUNCTION_NAMES:
                        ok = False
                    if not fc.arguments:
                        ok = False
            if ok:
                passed += 1
        except Exception:
            pass
    return passed / len(planning_preds)


def evaluate_physical_consistency(prediction: dict[str, Any], user_input: Any) -> bool:
    shield = SafetyShield()
    try:
        content = prediction.get("content", prediction.get("assistant", "{}"))
        raw = json.loads(content) if isinstance(content, str) else content
        step2 = Step2Output.model_validate(raw)
        filtered = shield.filter(user_input, step2)
        return len(filtered.action_plan) == len(step2.action_plan)
    except Exception:
        return False


def collect_sft_failures(model: Any, val_set: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stub: collect SFT checkpoint failures for DPO rejected-source pipeline."""
    failures: list[dict[str, Any]] = []
    for sample in val_set:
        stage = sample.get("stage", "")
        if stage != WorkflowStage.PLANNING.value:
            continue
        content = sample.get("messages", [{}])[-1].get("content", "")
        try:
            raw = json.loads(content)
            Step2Output.model_validate(raw)
        except Exception:
            failures.append(sample)
    return failures


def run_ablation_report(checkpoint_paths: dict[str, str], val_file: str | None = None) -> dict[str, float]:
    """Run ablation metrics on validation set (stub without live model inference)."""
    sample_path = val_file or str(Path(__file__).parent / "sample_data" / "sft_per_stage.jsonl")
    if not Path(sample_path).exists():
        return {}
    rows = _load_jsonl(sample_path)
    preds = []
    for row in rows:
        assistant = row["messages"][-1]["content"]
        preds.append({"stage": row.get("stage"), "content": assistant})

    return {
        "json_compliance": evaluate_json_compliance(preds),
        "tool_call_success": evaluate_tool_call_success(preds),
        "checkpoint_stage": list(checkpoint_paths.keys())[-1] if checkpoint_paths else "base",
    }


def main() -> None:
    report = run_ablation_report({"sft": "output/sft_lora", "dpo": "output/dpo_lora"})
    print("Ablation Report:")
    for metric, value in report.items():
        print(f"  {metric}: {value:.2%}" if isinstance(value, float) and value <= 1 else f"  {metric}: {value}")


if __name__ == "__main__":
    main()
