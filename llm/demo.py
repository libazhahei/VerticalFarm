import argparse
import json
from pathlib import Path

from control.llm_calls import FunctionCallService
from llm.clients import LLMProvider, create_llm_client, create_llm_client_from_env
from llm.clients.config import LLMClientConfig
from llm.models.input import Esp32StateAdapter
from llm.utils.logging import WorkflowLogger, ansi_cprint
from llm.workflow.orchestrator import LocalWorkflow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local LLM agent workflow demo.")
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        help="Path to ESP32/sensor state JSON (default: built-in high-temp sample).",
    )
    parser.add_argument(
        "--playbook",
        type=str,
        default=None,
        help="Path to strategy playbook JSON (default: llm/p3_output.json).",
    )
    parser.add_argument(
        "--provider",
        type=str,
        choices=[item.value for item in LLMProvider],
        default=None,
        help="LLM provider override (default: LLM_PROVIDER env or openai). Use vf_server for edge proxy.",
    )
    parser.add_argument("--host", type=str, default=None, help="LLM host for ollama/custom.")
    parser.add_argument("--port", type=int, default=None, help="LLM port for ollama/custom.")
    parser.add_argument("--model", type=str, default=None, help="Model name override.")
    parser.add_argument("--api-base", type=str, default=None, help="Full API base URL override.")
    return parser.parse_args()


def build_input(args: argparse.Namespace):
    if args.input:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        return Esp32StateAdapter.from_sensor_json(data)
    return Esp32StateAdapter.sample_high_temp()


def load_client(args: argparse.Namespace):
    if any([args.provider, args.host, args.port, args.model, args.api_base]):
        config = LLMClientConfig.from_env()
        updates: dict = {}
        if args.provider:
            updates["provider"] = LLMProvider(args.provider)
        if args.host:
            updates["host"] = args.host
        if args.port:
            updates["port"] = args.port
        if args.model:
            updates["model_name"] = args.model
        if args.api_base:
            updates["api_base"] = args.api_base
        config = config.model_copy(update=updates)
        client = create_llm_client(config)
    else:
        client = create_llm_client_from_env()
    if client.provider == LLMProvider.VF_SERVER:
        client.connect()
    return client


def main() -> None:
    args = parse_args()
    ansi_cprint("Starting llm demo workflow", fg="green", style="bold")

    client = load_client(args)
    ansi_cprint(
        f"LLM provider={client.provider.value}, model={client.config.model_name}, base={client.config.build_base_url()}",
        fg="cyan",
    )

    fc_service = FunctionCallService.get_instance()
    logger = WorkflowLogger()
    workflow = LocalWorkflow(
        client=client,
        playbook_path=args.playbook,
        fc_service=fc_service,
        logger=logger,
    )

    user_input = build_input(args)
    ansi_cprint(f"Input board_id={user_input.board_id}, temp={user_input.internal_temp}°C", fg="cyan")

    from llm.clients.vf_context import vf_workflow_session

    with vf_workflow_session(user_input):
        result = workflow.execute(user_input)

    if client.provider == LLMProvider.VF_SERVER:
        client.close()

    ansi_cprint("\n=== Final Control Command ===", fg="magenta", style="bold")
    if result.control_command:
        ansi_cprint(result.control_command.model_dump_json(indent=2, ensure_ascii=False), fg="white")
    ansi_cprint("\n=== MQTT Command ===", fg="magenta", style="bold")
    if result.mqtt_command:
        ansi_cprint(result.mqtt_command.to_json(indent=2), fg="white")
    ansi_cprint("\n=== Planner Comments ===", fg="magenta", style="bold")
    ansi_cprint(result.comments, fg="white")


if __name__ == "__main__":
    main()
