"""Per-workflow execution context for vf-server proxy calls."""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Optional

from llm.models.input import LocalLLMInput

_cycle_id: ContextVar[Optional[str]] = ContextVar("vf_cycle_id", default=None)
_user_input: ContextVar[Optional[LocalLLMInput]] = ContextVar("vf_user_input", default=None)
_stage_override: ContextVar[Optional[str]] = ContextVar("vf_stage_override", default=None)


def get_cycle_id() -> str:
    cycle_id = _cycle_id.get()
    if cycle_id is None:
        cycle_id = str(uuid.uuid4())
        _cycle_id.set(cycle_id)
    return cycle_id


def get_user_input() -> Optional[LocalLLMInput]:
    return _user_input.get()


def get_stage_override() -> Optional[str]:
    return _stage_override.get()


@contextmanager
def vf_workflow_session(user_input: LocalLLMInput, cycle_id: Optional[str] = None) -> Iterator[str]:
    token_cycle = _cycle_id.set(cycle_id or str(uuid.uuid4()))
    token_input = _user_input.set(user_input)
    try:
        yield _cycle_id.get() or ""
    finally:
        _cycle_id.reset(token_cycle)
        _user_input.reset(token_input)
        _stage_override.set(None)


@contextmanager
def vf_stage_override(stage: str) -> Iterator[None]:
    token = _stage_override.set(stage)
    try:
        yield
    finally:
        _stage_override.reset(token)
