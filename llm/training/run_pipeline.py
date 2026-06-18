"""Run training pipeline stages from unified JSON config."""

from __future__ import annotations

import argparse
from pathlib import Path

from llm.training.augment import run_augmentation
from llm.training.config_loader import load_training_config
from llm.training.export_gguf import export_gguf
from llm.clients.factory import create_llm_client
from llm.training.synthesize import run_synthesis
from llm.training.train_dpo import train_dpo
from llm.training.train_sft import train_sft


def run_pipeline(config_path: str, stages: list[str] | None = None) -> None:
    pipeline = load_training_config(config_path)
    to_run = stages or pipeline.pipeline.run_stages

    if "synthesize" in to_run:
        print("=== Stage: synthesize ===")
        synth_cfg = pipeline.to_synthesis_config()
        teacher = None
        if not synth_cfg.skip_llm:
            teacher = create_llm_client(pipeline.teacher_model.to_llm_client_config())
        paths = run_synthesis(synth_cfg, teacher_client=teacher)
        for name, path in paths.items():
            print(f"  {name}: {path}")

    if "augment" in to_run:
        print("=== Stage: augment ===")
        aug_cfg = pipeline.to_augment_config()
        teacher = None
        if not aug_cfg.skip_llm:
            teacher = create_llm_client(pipeline.teacher_model.to_llm_client_config())
        paths = run_augmentation(aug_cfg, teacher_client=teacher)
        for name, path in paths.items():
            print(f"  {name}: {path}")

    if "sft" in to_run:
        print("=== Stage: sft ===")
        train_sft(pipeline.to_sft_config(), train_model=pipeline.train_model)

    if "dpo" in to_run:
        print("=== Stage: dpo ===")
        train_dpo(pipeline.to_dpo_config(), train_model=pipeline.train_model)

    if "export" in to_run:
        print("=== Stage: export ===")
        export_gguf(pipeline.to_export_config())


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run training pipeline from JSON config")
    parser.add_argument(
        "--config",
        default="llm/training/training_config.json",
        help="Path to unified training_config.json",
    )
    parser.add_argument(
        "--stages",
        default=None,
        help="Comma-separated stages: synthesize,augment,sft,dpo,export (overrides config)",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    stages = [s.strip() for s in args.stages.split(",")] if args.stages else None
    config_path = Path(args.config)
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    run_pipeline(str(config_path), stages)


if __name__ == "__main__":
    main()
