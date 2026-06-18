"""CLI entrypoint: same interface as llm/demo.py but proxies infer to vf-server."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from llm.clients.config import LLMClientConfig, LLMProvider
from llm.models.input import Esp32StateAdapter
from llm.utils.logging import WorkflowLogger, ansi_cprint
from vf_proxy.runner import run_workflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run llm/ LocalWorkflow via vf-server inference proxy.",
    )
    parser.add_argument("--input", type=str, default=None, help="ESP32/sensor state JSON path.")
    parser.add_argument("--playbook", type=str, default=None, help="Playbook JSON path.")
    parser.add_argument("--host", type=str, default=None, help="vf-server host override.")
    parser.add_argument("--port", type=int, default=None, help="vf-server port override.")
    parser.add_argument("--model", type=str, default=None, help="Model name sent to vf-server.")
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Run as local TCP proxy server instead of one-shot CLI.",
    )
    parser.add_argument(
        "--listen-host",
        type=str,
        default="127.0.0.1",
        help="Bind host when using --serve.",
    )
    parser.add_argument(
        "--listen-port",
        type=int,
        default=9600,
        help="Bind port when using --serve.",
    )
    return parser.parse_args()


def build_input(args: argparse.Namespace):
    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        return Esp32StateAdapter.from_sensor_json(data)
    return Esp32StateAdapter.sample_high_temp()


def load_vf_client(args: argparse.Namespace):
    config = LLMClientConfig.from_env()
    updates: dict = {"provider": LLMProvider.VF_SERVER}
    if args.host:
        updates["host"] = args.host
    if args.port:
        updates["port"] = args.port
    if args.model:
        updates["model_name"] = args.model
    config = config.model_copy(update=updates)
    client = create_llm_client(config)
    client.connect()
    return client


def main() -> None:
    args = parse_args()
    if args.serve:
        from vf_proxy.server import serve

        serve(host=args.listen_host, port=args.listen_port, playbook_path=args.playbook)
        return

    ansi_cprint("Starting vf proxy workflow (llm/ + vf-server)", fg="green", style="bold")
    client = load_vf_client(args)
    ansi_cprint(
        f"vf-server={client.config.host}:{client.config.port}, model={client.config.model_name}",
        fg="cyan",
    )

    user_input = build_input(args)
    logger = WorkflowLogger()
    result = run_workflow(client, user_input, playbook_path=args.playbook, logger=logger)

    ansi_cprint("\n=== Final Control Command ===", fg="magenta", style="bold")
    if result.control_command:
        ansi_cprint(result.control_command.model_dump_json(indent=2, ensure_ascii=False), fg="white")
    ansi_cprint("\n=== MQTT Command ===", fg="magenta", style="bold")
    if result.mqtt_command:
        ansi_cprint(result.mqtt_command.to_json(indent=2), fg="white")
    ansi_cprint("\n=== Planner Comments ===", fg="magenta", style="bold")
    ansi_cprint(result.comments, fg="white")

    client.close()


if __name__ == "__main__":
    main()
