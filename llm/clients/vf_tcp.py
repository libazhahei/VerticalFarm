"""Low-level TCP transport for the vf Rust inference server."""

from __future__ import annotations

import json
import os
import socket
import struct
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def encode_message(payload: Dict[str, Any]) -> bytes:
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return struct.pack(">I", len(body)) + body


def read_frame_from_socket(sock: socket.socket) -> Dict[str, Any]:
    header = _recv_exact(sock, 4)
    length = struct.unpack(">I", header)[0]
    if length > 16 * 1024 * 1024:
        raise ValueError("frame exceeds 16MB limit")
    body = _recv_exact(sock, length)
    return json.loads(body.decode("utf-8"))


def write_frame_to_socket(sock: socket.socket, payload: Dict[str, Any]) -> None:
    sock.sendall(encode_message(payload))


def _recv_exact(sock: socket.socket, nbytes: int) -> bytes:
    chunks = []
    received = 0
    while received < nbytes:
        chunk = sock.recv(nbytes - received)
        if not chunk:
            raise ConnectionError("socket closed while reading frame")
        chunks.append(chunk)
        received += len(chunk)
    return b"".join(chunks)


class TcpInferenceTransport:
    """Thread-safe TCP client for vf-server infer / heartbeat / cache control."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        client_id: Optional[str] = None,
        model_name: Optional[str] = None,
        connect_timeout: float = 10.0,
        request_timeout: float = 120.0,
    ) -> None:
        self.host = host or os.environ.get("VF_SERVER_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("VF_SERVER_PORT", "9500"))
        self.client_id = client_id or f"vf-proxy-{uuid.uuid4().hex[:8]}"
        self.model_name = model_name or os.environ.get("VF_MODEL_NAME", "qwen2.5-4b-agent-q4km")
        self.connect_timeout = connect_timeout
        self.request_timeout = request_timeout
        self._sock: Optional[socket.socket] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop = threading.Event()
        self._lock = threading.Lock()
        self._last_photoperiod: Optional[str] = None

    def connect(self) -> None:
        self.close()
        sock = socket.create_connection((self.host, self.port), timeout=self.connect_timeout)
        sock.settimeout(self.request_timeout)
        self._sock = sock

    def close(self) -> None:
        self.stop_heartbeat()
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None

    def _ensure_connected(self) -> socket.socket:
        if self._sock is None:
            self.connect()
        assert self._sock is not None
        return self._sock

    def _send_and_receive(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            sock = self._ensure_connected()
            try:
                write_frame_to_socket(sock, payload)
                return read_frame_from_socket(sock)
            except (OSError, ValueError) as error:
                self._sock = None
                raise ConnectionError(f"vf-server tcp request failed: {error}") from error

    def heartbeat(self) -> Dict[str, Any]:
        return self._send_and_receive(
            {
                "type": "heartbeat",
                "client_id": self.client_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def start_heartbeat(self, interval_sec: Optional[float] = None) -> None:
        interval = interval_sec or float(os.environ.get("VF_HEARTBEAT_SEC", "10"))
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return
        self._heartbeat_stop.clear()

        def _loop() -> None:
            while not self._heartbeat_stop.wait(interval):
                try:
                    response = self.heartbeat()
                    if not response.get("model_ready", True):
                        time.sleep(1.0)
                except Exception as error:
                    print(f"[TcpInferenceTransport] heartbeat failed: {error}")
                    try:
                        self.connect()
                    except Exception as reconnect_error:
                        print(f"[TcpInferenceTransport] reconnect failed: {reconnect_error}")

        self._heartbeat_thread = threading.Thread(target=_loop, name="vf-heartbeat", daemon=True)
        self._heartbeat_thread.start()

    def stop_heartbeat(self) -> None:
        self._heartbeat_stop.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        self._heartbeat_thread = None

    def flush_cache(self, reason: str) -> Dict[str, Any]:
        return self._send_and_receive({"type": "flush_cache", "reason": reason})

    def cycle_end(self, cycle_id: str) -> Dict[str, Any]:
        return self._send_and_receive({"type": "cycle_end", "cycle_id": cycle_id})

    def preload_models(self, models: List[str]) -> Dict[str, Any]:
        if not models:
            return {"type": "preload_ack", "loaded_models": []}
        return self._send_and_receive({"type": "preload", "models": models})

    def maybe_flush_on_photoperiod(self, photoperiod: str) -> None:
        normalized = "ON" if photoperiod.upper() in {"ON", "LIGHTS_ON"} else "OFF"
        if self._last_photoperiod is not None and self._last_photoperiod != normalized:
            self.flush_cache("photoperiod_transition")
        self._last_photoperiod = normalized

    def infer(
        self,
        *,
        stage: str,
        cycle_id: str,
        prompt: Dict[str, str],
        state_signature: Dict[str, Any],
        model_name: Optional[str] = None,
        max_tokens: int = 256,
        temperature: float = 0.2,
        invalidate_reason: Optional[str] = None,
        allow_model_fallback: bool = True,
        preload_models: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        photoperiod = str(state_signature.get("photoperiod", "ON"))
        self.maybe_flush_on_photoperiod(photoperiod)
        request_id = str(uuid.uuid4())
        payload: Dict[str, Any] = {
            "type": "infer",
            "request_id": request_id,
            "cycle_id": cycle_id,
            "stage": stage,
            "model_name": model_name or self.model_name,
            "prompt": prompt,
            "state_signature": state_signature,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "allow_model_fallback": allow_model_fallback,
            "preload_models": preload_models or [],
        }
        if invalidate_reason:
            payload["invalidate_reason"] = invalidate_reason

        response = self._send_and_receive(payload)
        if response.get("type") == "error":
            raise RuntimeError(f"{response.get('code')}: {response.get('message')}")
        return response
