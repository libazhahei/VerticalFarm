"""Local TCP server: accepts workflow requests and runs llm/ LocalWorkflow via vf-server."""

from __future__ import annotations

import json
import socket
import struct
import threading
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from llm.clients import create_llm_client
from llm.clients.config import LLMClientConfig, LLMProvider
from llm.models.input import Esp32StateAdapter
from vf_proxy.runner import run_workflow


def _read_frame(conn: socket.socket) -> Dict[str, Any]:
    header = _recv_exact(conn, 4)
    length = struct.unpack(">I", header)[0]
    body = _recv_exact(conn, length)
    return json.loads(body.decode("utf-8"))


def _write_frame(conn: socket.socket, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    conn.sendall(struct.pack(">I", len(body)) + body)


def _recv_exact(conn: socket.socket, nbytes: int) -> bytes:
    chunks = []
    received = 0
    while received < nbytes:
        chunk = conn.recv(nbytes - received)
        if not chunk:
            raise ConnectionError("client disconnected")
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


def handle_request(payload: Dict[str, Any], playbook_path: Optional[str]) -> Dict[str, Any]:
    request_type = payload.get("type")
    if request_type == "ping":
        return {"type": "pong"}

    if request_type != "run_workflow":
        return {"type": "error", "code": "unsupported_type", "message": f"unknown type: {request_type}"}

    sensor = payload.get("input")
    if not isinstance(sensor, dict):
        return {"type": "error", "code": "invalid_input", "message": "input must be a JSON object"}

    config = LLMClientConfig.from_env()
    config = config.model_copy(update={"provider": LLMProvider.VF_SERVER})
    client = create_llm_client(config)
    client.connect()
    try:
        user_input = Esp32StateAdapter.from_sensor_json(sensor)
        result = run_workflow(client, user_input, playbook_path=playbook_path)
        return {
            "type": "workflow_result",
            "result": json.loads(result.model_dump_json()),
        }
    finally:
        client.close()


def _client_handler(conn: socket.socket, playbook_path: Optional[str]) -> None:
    try:
        payload = _read_frame(conn)
        response = handle_request(payload, playbook_path=playbook_path)
    except Exception as error:
        response = {
            "type": "error",
            "code": "handler_failed",
            "message": str(error),
            "traceback": traceback.format_exc(),
        }
    _write_frame(conn, response)
    conn.close()


def serve(host: str = "127.0.0.1", port: int = 9600, playbook_path: Optional[str] = None) -> None:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((host, port))
    listener.listen(8)
    print(f"[vf-proxy] listening on {host}:{port}")

    while True:
        conn, addr = listener.accept()
        thread = threading.Thread(
            target=_client_handler,
            args=(conn, playbook_path),
            daemon=True,
        )
        thread.start()
        print(f"[vf-proxy] accepted {addr[0]}:{addr[1]}")
