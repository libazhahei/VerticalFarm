"""Integration tests for vf-server + llm/ workflow proxy."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / "inference" / "server"


@pytest.fixture(scope="module")
def server_port():
    port = 19500
    while port < 19600:
        try:
            sock = socket.socket()
            sock.bind(("127.0.0.1", port))
            sock.close()
            break
        except OSError:
            port += 1
    else:
        pytest.skip("no free port for test server")

    binary = SERVER_DIR / "target" / "debug" / "vf-server"
    if not binary.exists():
        subprocess.run(["cargo", "build", "-p", "vf-server"], cwd=SERVER_DIR, check=True)

    proc = subprocess.Popen(
        [
            str(binary),
            "--mode",
            "mock",
            "--port",
            str(port),
            "--fixtures-dir",
            str(REPO_ROOT / "fixtures" / "inference"),
            "--models-config",
            str(REPO_ROOT / "inference" / "models.json"),
            "--mock-prefill-ms",
            "1",
            "--mock-decode-ms",
            "1",
        ],
        cwd=SERVER_DIR,
        env={
            **os.environ,
            "VF_MODELS_CONFIG": str(REPO_ROOT / "inference" / "models.json"),
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.5)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


@pytest.fixture
def vf_client(server_port, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "vf_server")
    monkeypatch.setenv("VF_SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("VF_SERVER_PORT", str(server_port))
    monkeypatch.setenv("VF_MODEL_NAME", "qwen2.5-4b-agent-q4km")

    from llm.clients import create_llm_client_from_env

    client = create_llm_client_from_env()
    client.connect()
    yield client
    client.close()


def test_heartbeat(vf_client):
    response = vf_client.transport.heartbeat()
    assert response["type"] == "heartbeat_ack"
    assert response["model_ready"] is True


def test_infer_miss_then_hit(vf_client):
    from llm.clients.vf_context import vf_workflow_session
    from llm.models.input import Esp32StateAdapter
    from llm.prompts.local import diagnosis_output_prompt, diagnosis_prompt, role_and_task
    from langchain_core.prompts import PromptTemplate

    from llm.models.input import build_step_data

    user_input = Esp32StateAdapter.sample_high_temp()
    template = PromptTemplate.from_template(role_and_task + diagnosis_prompt + diagnosis_output_prompt)
    data = build_step_data(user_input)

    with vf_workflow_session(user_input):
        first = vf_client.run_chain(template, data)
        second = vf_client.run_chain(template, data)

    assert first.content
    assert second.content


def test_stage_detection():
    from llm.clients.vf_prompt import detect_stage
    from llm.prompts.local import diagnosis_prompt, final_command_prompt

    assert detect_stage(diagnosis_prompt) == "diagnosis"
    assert detect_stage(final_command_prompt) == "final_command"


def test_workflow_end_to_end(vf_client):
    from llm.models.input import Esp32StateAdapter
    from vf_proxy.runner import run_workflow

    fixture = REPO_ROOT / "fixtures" / "esp32_state.json"
    sensor_data = json.loads(fixture.read_text(encoding="utf-8"))
    user_input = Esp32StateAdapter.from_sensor_json(sensor_data)
    result = run_workflow(vf_client, user_input)
    assert result.solution_action.solution_id
    assert result.control_command is not None


@pytest.fixture
def oom_server_port():
    port = 19600
    while port < 19700:
        try:
            sock = socket.socket()
            sock.bind(("127.0.0.1", port))
            sock.close()
            break
        except OSError:
            port += 1
    else:
        pytest.skip("no free port for OOM test server")

    binary = SERVER_DIR / "target" / "debug" / "vf-server"
    if not binary.exists():
        subprocess.run(["cargo", "build", "-p", "vf-server"], cwd=SERVER_DIR, check=True)

    models_config = REPO_ROOT / "inference" / "models.json"
    proc = subprocess.Popen(
        [
            str(binary),
            "--mode",
            "mock",
            "--port",
            str(port),
            "--fixtures-dir",
            str(REPO_ROOT / "fixtures" / "inference"),
            "--models-config",
            str(models_config),
            "--mock-oom-models",
            "qwen2.5-4b-agent-q4km",
            "--mock-prefill-ms",
            "1",
            "--mock-decode-ms",
            "1",
        ],
        cwd=SERVER_DIR,
        env={
            **os.environ,
            "VF_MODELS_CONFIG": str(models_config),
            "VF_MOCK_OOM_MODELS": "qwen2.5-4b-agent-q4km",
        },
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(0.5)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def test_oom_fallback_to_smaller_model(oom_server_port):
    from llm.clients.vf_tcp import TcpInferenceTransport

    transport = TcpInferenceTransport(
        host="127.0.0.1",
        port=oom_server_port,
        model_name="qwen2.5-4b-agent-q4km",
    )
    transport.connect()
    try:
        response = transport.infer(
            stage="diagnosis",
            cycle_id="oom-test-cycle",
            prompt={
                "static_prefix": "system",
                "instruction": "diagnose",
                "sensor_state": "temp=30",
            },
            state_signature={
                "internal_temp_bucket": "hi",
                "external_temp_bucket": "mid",
                "humidity_bucket": "mid",
                "photoperiod": "ON",
                "temp_trend_sign": "+",
                "temp_trend_magnitude": "lo",
                "crop": "lettuce",
                "growth_stage": "vegetative",
            },
            allow_model_fallback=True,
        )
        assert response["type"] == "infer_response"
        assert response.get("model_fallback") is True
        assert response.get("oom_recovered") is True
        assert response.get("model_used") != "qwen2.5-4b-agent-q4km"
        assert response.get("output")
    finally:
        transport.close()
