import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Protocol

from llm.cloud.models import LocalStrategies, StrategyDetail
from llm.models.input import LocalLLMInput


class PlaybookRetrieverProtocol(Protocol):
    def retrieve(self, user_input: LocalLLMInput, top_k: int = 2) -> list[StrategyDetail]:
        ...

    def format_context(self, cases: list[StrategyDetail]) -> str:
        ...


class RuleBasedPlaybookRetriever:
    """Rule-based playbook retrieval from cloud strategy_playbook."""

    def __init__(self, playbook_path: str | Path | None = None, strategies: LocalStrategies | None = None) -> None:
        if strategies is not None:
            self._playbook = strategies.strategy_playbook
        elif playbook_path is not None:
            data = json.loads(Path(playbook_path).read_text(encoding="utf-8"))
            self._playbook = LocalStrategies.model_validate(data).strategy_playbook
        else:
            default = Path(__file__).resolve().parents[1] / "p3_output.json"
            data = json.loads(default.read_text(encoding="utf-8"))
            self._playbook = LocalStrategies.model_validate(data).strategy_playbook

    def retrieve(self, user_input: LocalLLMInput, top_k: int = 2) -> list[StrategyDetail]:
        scored: list[tuple[int, StrategyDetail]] = []
        for case in self._playbook:
            score = self._score_case(user_input, case)
            if score > 0:
                scored.append((score, case))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [case for _, case in scored[:top_k]]

    def format_context(self, cases: list[StrategyDetail]) -> str:
        if not cases:
            return "No matching playbook case was retrieved. Proceed using general control logic."
        blocks = []
        for case in cases:
            blocks.append(
                f"- {case.case_id}: {case.case_description}\n"
                f"  Strategy: {case.diagnosis_and_strategy}\n"
                f"  Goal: {case.overall_15min_goal}"
            )
        return "\n".join(blocks)

    def _score_case(self, user_input: LocalLLMInput, case: StrategyDetail) -> int:
        logic = case.trigger_condition.logic
        score = 0
        t_internal = user_input.internal_temp
        rh = user_input.humidity
        photoperiod = "Lights_ON" if user_input.photoperiod_status.upper() == "ON" else "Lights_OFF"

        if self._eval_logic(logic, t_internal, rh, photoperiod):
            score += 10
        if case.risk_level.lower() == "high" and t_internal > user_input.ideal_temp_range[1]:
            score += 3
        if "temperature" in case.case_description.lower() and (
            t_internal > user_input.ideal_temp_range[1] or t_internal < user_input.ideal_temp_range[0]
        ):
            score += 2
        return score

    def _eval_logic(self, logic: str, t_internal: float, rh: float, photoperiod: str) -> bool:
        expr = logic
        expr = expr.replace("T_internal", str(t_internal))
        expr = expr.replace("RH_internal", str(rh))
        expr = expr.replace("Photoperiod == 'Lights_ON'", f"'{photoperiod}' == 'Lights_ON'")
        expr = expr.replace("Photoperiod == 'Lights_OFF'", f"'{photoperiod}' == 'Lights_OFF'")
        expr = re.sub(r"\bAND\b", "and", expr)
        expr = re.sub(r"\bOR\b", "or", expr)
        try:
            return bool(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return False


class VectorPlaybookRetriever(ABC):
    """Future vector-RAG interface placeholder."""

    @abstractmethod
    def retrieve(self, user_input: LocalLLMInput, top_k: int = 2) -> list[StrategyDetail]:
        raise NotImplementedError

    @abstractmethod
    def format_context(self, cases: list[StrategyDetail]) -> str:
        raise NotImplementedError
