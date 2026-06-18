"""Shared workflow runner used by the vf proxy CLI and request server."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from control.llm_calls import FunctionCallService
from llm.clients.base import BaseLLMClient
from llm.clients.vf_context import vf_workflow_session
from llm.models.input import LocalLLMInput
from llm.models.output import LocalPlannerOutput
from llm.utils.logging import WorkflowLogger
from llm.workflow.orchestrator import LocalWorkflow


def build_workflow(
    client: BaseLLMClient,
    playbook_path: str | Path | None = None,
    logger: WorkflowLogger | None = None,
) -> LocalWorkflow:
    return LocalWorkflow(
        client=client,
        repair_client=client,
        playbook_path=playbook_path,
        fc_service=FunctionCallService.get_instance(),
        logger=logger or WorkflowLogger(),
    )


def run_workflow(
    client: BaseLLMClient,
    user_input: LocalLLMInput,
    playbook_path: str | Path | None = None,
    logger: WorkflowLogger | None = None,
) -> LocalPlannerOutput:
    workflow = build_workflow(client, playbook_path=playbook_path, logger=logger)
    with vf_workflow_session(user_input) as cycle_id:
        try:
            return workflow.execute(user_input)
        finally:
            pass
