"""Augment existing SFT/DPO training data using perturbation + LLM teacher."""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from langchain_core.output_parsers import JsonOutputParser

from llm.clients.base import BaseLLMClient
from llm.clients.factory import create_llm_client_from_env
from llm.training.annotate import TeacherAnnotator
from llm.training.config import AugmentConfig, SynthesisConfig
from llm.training.config_loader import add_config_argument, load_training_config
from llm.training.dataset import load_jsonl
from llm.training.perturbation import PERTURBATION_TYPES, deduplicate_by_embedding_stub, perturb_state
from llm.training.prompts.augment import build_augment_prompt, build_dpo_augment_prompt
from llm.training.schemas import DPOPair, SFTSample, WorkflowStage
from llm.training.state_generator import CROP_PROFILES, generate_seeds, seed_to_local_llm_input
from llm.training.synthesize import write_jsonl as synth_write_jsonl


def reconstruct_seed(seed_id: str, source_random_seed: int = 42) -> Any:
    """Reconstruct SeedScenario from seed_id (e.g. seed_00007) using original RNG."""
    match = re.search(r"(\d+)$", seed_id)
    if not match:
        seeds = generate_seeds(1, source_random_seed)
        return seeds[0]
    idx = int(match.group(1))
    seeds = generate_seeds(idx + 1, source_random_seed)
    return seeds[idx]


def group_sft_by_seed(rows: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        seed_id = row.get("metadata", {}).get("seed_id", "unknown")
        grouped[seed_id][row["stage"]] = row
    return grouped


def build_prior_outputs(seed_rows: dict[str, dict[str, Any]], stage: WorkflowStage) -> dict[str, Any]:
    """Collect prior workflow stage outputs for a seed from existing data."""
    stage_order = [s.value for s in WorkflowStage.all_stages()]
    target_idx = stage_order.index(stage.value)
    prior: dict[str, Any] = {}
    key_map = {
        WorkflowStage.DIAGNOSIS.value: "diagnosis",
        WorkflowStage.PLANNING.value: "planning",
        WorkflowStage.SIDE_EFFECT.value: "side_effect",
        WorkflowStage.DECISION.value: "decision",
        WorkflowStage.FINAL_COMMAND.value: "final_command",
    }
    for stg in stage_order[:target_idx]:
        row = seed_rows.get(stg)
        if not row:
            continue
        content = row["messages"][-1]["content"]
        try:
            prior[key_map[stg]] = json.loads(content)
        except json.JSONDecodeError:
            pass
    return prior


def _describe_perturbation(original: Any, perturbed: Any) -> str:
    o, p = original.state_vector, perturbed.state_vector
    changes = []
    if o.internal_temp != p.internal_temp:
        changes.append(f"internal_temp: {o.internal_temp} → {p.internal_temp}")
    if o.external_temp != p.external_temp:
        changes.append(f"external_temp: {o.external_temp} → {p.external_temp}")
    if o.internal_humidity != p.internal_humidity:
        changes.append(f"humidity: {o.internal_humidity} → {p.internal_humidity}")
    if o.photoperiod_status != p.photoperiod_status:
        changes.append(f"photoperiod: {o.photoperiod_status} → {p.photoperiod_status}")
    if o.led_pwm != p.led_pwm:
        changes.append(f"led_pwm: {o.led_pwm} → {p.led_pwm}")
    if o.fan_rpm != p.fan_rpm:
        changes.append(f"fan_rpm: {o.fan_rpm} → {p.fan_rpm}")
    if o.temp_trend_15min != p.temp_trend_15min:
        changes.append(f"temp_trend: {o.temp_trend_15min} → {p.temp_trend_15min}")
    return "; ".join(changes) if changes else "minor state variation"


def apply_crop_context_swap(seed: Any, rng: random.Random) -> Any:
    import copy

    mutated = copy.deepcopy(seed)
    profile = rng.choice(CROP_PROFILES)
    from llm.training.schemas import CropContext

    mutated.crop_context = CropContext(**profile)
    mutated.seed_id = f"{seed.seed_id}_aug_crop"
    return mutated


class DatasetAugmentor:
    def __init__(self, client: BaseLLMClient | None, config: AugmentConfig) -> None:
        self.client = client
        self.config = config
        self.rng = random.Random(config.random_seed)
        synth_cfg = SynthesisConfig(skip_llm=config.skip_llm, teacher_temperature=config.teacher_temperature)
        self.annotator = TeacherAnnotator(client, synth_cfg)

    def _extract_content(self, response: Any) -> str:
        if hasattr(response, "content"):
            return str(response.content)
        return str(response)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return JsonOutputParser().parse(cleaned)

    def augment_sft_row(
        self,
        row: dict[str, Any],
        seed_rows: dict[str, dict[str, Any]],
        strategy: str,
        variant_idx: int,
    ) -> SFTSample | None:
        stage = WorkflowStage(row["stage"])
        if stage not in self.config.stages:
            return None

        seed_id = row.get("metadata", {}).get("seed_id", "seed_00000")
        seed = reconstruct_seed(seed_id, self.config.source_random_seed)
        original_user = row["messages"][0]["content"]
        original_assistant = row["messages"][-1]["content"]

        perturbation_desc = ""
        if strategy == "perturbation":
            ptype = PERTURBATION_TYPES[variant_idx % len(PERTURBATION_TYPES)]
            perturbed = perturb_state(seed, ptype, self.rng)
            perturbation_desc = _describe_perturbation(seed, perturbed)
            seed = perturbed
        elif strategy == "crop_context":
            seed = apply_crop_context_swap(seed, self.rng)
            perturbation_desc = f"crop → {seed.crop_context.crop}, stage → {seed.crop_context.growth_stage}"
        elif strategy == "paraphrase":
            perturbation_desc = "Same state; generate paraphrased/alternative valid output."
        elif strategy == "edge_case":
            ptype = self.rng.choice(["temperature_offset", "sensor_anomaly", "photoperiod_flip"])
            perturbed = perturb_state(seed, ptype, self.rng)
            perturbation_desc = f"edge_case via {ptype}: {_describe_perturbation(seed, perturbed)}"
            seed = perturbed

        prior = build_prior_outputs(seed_rows, stage)

        if self.client and not self.config.skip_llm:
            prompt = build_augment_prompt(
                stage, original_user, original_assistant, seed, strategy, perturbation_desc
            )
            output_json: dict[str, Any] | None = None
            try:
                response = self.client.run_messages(
                    [{"role": "user", "content": prompt}],
                    temperature=self.config.teacher_temperature,
                )
                output_json = self._parse_json(self._extract_content(response))
                user_input = seed_to_local_llm_input(seed)
                if not self.annotator.validate_output(stage, output_json, user_input):
                    output_json = None
            except Exception:
                output_json = None

            if output_json is None:
                sample = self.annotator.annotate_stage(stage, seed, prior or None)
                sample.metadata.update(
                    {
                        "source": "llm_augmentation_fallback",
                        "augment_strategy": strategy,
                        "parent_seed_id": seed_id,
                        "variant_idx": variant_idx,
                    }
                )
            else:
                from llm.training.prompt_builder import build_prompt_for_stage, format_chat_messages

                user_input = seed_to_local_llm_input(seed)
                inference_prompt = build_prompt_for_stage(stage, user_input, prior or None)
                sample = SFTSample(
                    stage=stage,
                    messages=format_chat_messages(inference_prompt, json.dumps(output_json, ensure_ascii=False)),
                    metadata={
                        "seed_id": seed.seed_id,
                        "source": "llm_augmentation",
                        "augment_strategy": strategy,
                        "parent_seed_id": seed_id,
                        "variant_idx": variant_idx,
                    },
                )
        else:
            sample = self.annotator.annotate_stage(stage, seed, prior or None)
            sample.metadata.update(
                {
                    "source": "stub_augmentation",
                    "augment_strategy": strategy,
                    "parent_seed_id": seed_id,
                    "variant_idx": variant_idx,
                }
            )

        return sample

    def augment_dpo_row(self, row: dict[str, Any], variant_idx: int) -> DPOPair | None:
        if self.client and not self.config.skip_llm:
            prompt = build_dpo_augment_prompt(
                row["prompt"], row["chosen"], row["rejected"], strategy="edge_case"
            )
            try:
                response = self.client.run_messages(
                    [{"role": "user", "content": prompt}],
                    temperature=self.config.teacher_temperature,
                )
                parsed = self._parse_json(self._extract_content(response))
                return DPOPair(
                    prompt=row["prompt"],
                    chosen=parsed.get("chosen", row["chosen"]),
                    rejected=parsed.get("rejected", row["rejected"]),
                    stage=WorkflowStage(row.get("stage", "planning")),
                    category=parsed.get("category", row.get("category", "augmented")),
                    rejection_source="llm_augmentation",
                    metadata={"parent": row.get("metadata", {}), "variant_idx": variant_idx},
                )
            except Exception:
                pass

        return DPOPair(
            prompt=row["prompt"],
            chosen=row["chosen"],
            rejected=row["rejected"],
            stage=WorkflowStage(row.get("stage", "planning")),
            category=row.get("category", "augmented"),
            rejection_source="stub_augmentation",
            metadata={"parent": row.get("metadata", {}), "variant_idx": variant_idx},
        )


def run_augmentation(config: AugmentConfig, teacher_client=None) -> dict[str, Path]:
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    original_rows = load_jsonl(config.input_sft_file)
    grouped = group_sft_by_seed(original_rows)

    client = None
    if not config.skip_llm:
        client = teacher_client if teacher_client is not None else create_llm_client_from_env()
    augmentor = DatasetAugmentor(client, config)

    rows_to_augment = original_rows
    if config.max_samples > 0:
        rows_to_augment = original_rows[: config.max_samples]

    augmented_samples: list[SFTSample] = []
    for row in rows_to_augment:
        seed_id = row.get("metadata", {}).get("seed_id", "seed_00000")
        seed_rows = grouped.get(seed_id, {row["stage"]: row})
        for v in range(config.variants_per_sample):
            strategy = config.strategies[v % len(config.strategies)]
            sample = augmentor.augment_sft_row(row, seed_rows, strategy, v)
            if sample:
                augmented_samples.append(sample)

    aug_sft_rows = [s.to_jsonl_dict() for s in augmented_samples]
    if not config.skip_llm:
        aug_sft_rows = deduplicate_by_embedding_stub(aug_sft_rows)

    if config.merge_with_original:
        merged_sft = original_rows + aug_sft_rows
    else:
        merged_sft = aug_sft_rows

    sft_aug_path = output_dir / "sft_augmented.jsonl"
    sft_merged_path = output_dir / "sft_merged.jsonl"
    synth_write_jsonl(sft_aug_path, aug_sft_rows)
    synth_write_jsonl(sft_merged_path, merged_sft)

    result_paths: dict[str, Path] = {"sft_augmented": sft_aug_path, "sft_merged": sft_merged_path}

    if config.generate_dpo and config.input_dpo_file and Path(config.input_dpo_file).exists():
        dpo_rows = load_jsonl(config.input_dpo_file)
        aug_dpo: list[dict] = []
        for row in dpo_rows:
            for v in range(config.dpo_variants_per_pair):
                pair = augmentor.augment_dpo_row(row, v)
                if pair:
                    aug_dpo.append(pair.to_jsonl_dict())
        dpo_aug_path = output_dir / "dpo_augmented.jsonl"
        dpo_merged_path = output_dir / "dpo_merged.jsonl"
        synth_write_jsonl(dpo_aug_path, aug_dpo)
        synth_write_jsonl(dpo_merged_path, dpo_rows + aug_dpo)
        result_paths["dpo_augmented"] = dpo_aug_path
        result_paths["dpo_merged"] = dpo_merged_path

    return result_paths


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Augment existing training data with LLM + perturbation")
    add_config_argument(parser)
    parser.add_argument("--input-sft", default="data/training_15x5/sft_all.jsonl")
    parser.add_argument("--input-dpo", default="data/training_15x5/dpo_train.jsonl")
    parser.add_argument("--output-dir", default="data/training_15x5/augmented")
    parser.add_argument("--variants-per-sample", type=int, default=2)
    parser.add_argument("--max-samples", type=int, default=0, help="0 = all samples")
    parser.add_argument(
        "--strategies",
        default="perturbation,paraphrase,crop_context",
        help="Comma-separated: perturbation,paraphrase,crop_context,edge_case",
    )
    parser.add_argument("--stages", default=None, help="Comma-separated workflow stages")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--source-seed", type=int, default=42, help="RNG seed used when original data was built")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--no-merge", action="store_true", help="Only output augmented rows, not merged")
    parser.add_argument("--no-dpo", action="store_true")
    parser.add_argument("--dpo-variants", type=int, default=1)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    pipeline = load_training_config(args.config) if args.config else None
    if pipeline:
        config = pipeline.to_augment_config()
        teacher_client = None if config.skip_llm else pipeline.create_teacher_client()
    else:
        stages = None
        if args.stages:
            stages = [WorkflowStage(s.strip()) for s in args.stages.split(",")]
        config = AugmentConfig(
            input_sft_file=args.input_sft,
            input_dpo_file=args.input_dpo,
            output_dir=args.output_dir,
            variants_per_sample=args.variants_per_sample,
            max_samples=args.max_samples,
            strategies=[s.strip() for s in args.strategies.split(",")],
            stages=stages or WorkflowStage.all_stages(),
            random_seed=args.seed,
            source_random_seed=args.source_seed,
            skip_llm=args.skip_llm,
            merge_with_original=not args.no_merge,
            generate_dpo=not args.no_dpo,
            dpo_variants_per_pair=args.dpo_variants,
        )
        teacher_client = None
    paths = run_augmentation(config, teacher_client=teacher_client)
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
