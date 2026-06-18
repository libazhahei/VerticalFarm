from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from collections import defaultdict

from llm.training.config_loader import add_config_argument, load_training_config
from llm.clients.factory import create_llm_client_from_env
from llm.training.annotate import DPO_FLAW_CYCLE, TeacherAnnotator
from llm.training.config import SynthesisConfig
from llm.training.perturbation import augment_with_perturbation, deduplicate_by_embedding_stub
from llm.training.schemas import AnnotationStatus, SFTSample, WorkflowStage
from llm.training.state_generator import generate_seeds

HUMAN_ANNOTATION_TEMPLATE = """# Vertical Farm Control — Human Annotation Guide

## Review Criteria (3-point scale)
- **Accept** — physically plausible, JSON schema compliant, crop-biology aligned, cross-stage consistent
- **Needs Revision** — minor fixable issues (fan PWM range, DLI calc, photoperiod misclassification)
- **Reject** — physically implausible, schema-breaking, or logically inconsistent

## Annotation Instructions
1. Read the input state vector and LLM-generated output for each sample below.
2. Mark one score: Accept / Needs Revision / Reject.
3. If **Needs Revision**, write corrected JSON in the Correction field.
4. Return completed file to pipeline:
   `python -m llm.training.synthesize --import-human-md human_review_completed.md`

## Samples for Review

"""


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def export_human_review_md(samples: list[SFTSample], output_path: Path, count: int) -> None:
    """Export stratified samples for human expert review."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    selected = _stratified_select(samples, count)
    lines = [HUMAN_ANNOTATION_TEMPLATE]
    for idx, sample in enumerate(selected, start=1):
        user_msg = next((m["content"] for m in sample.messages if m["role"] == "user"), "")
        assistant_msg = next((m["content"] for m in sample.messages if m["role"] == "assistant"), "")
        seed_id = sample.metadata.get("seed_id", "unknown")
        lines.append(
            f"### Sample HR-{idx:03d} | Stage: {sample.stage.value} | Seed: {seed_id}\n\n"
            f"**Input State / Prompt:**\n```\n{user_msg[:2000]}\n```\n\n"
            f"**LLM Output:**\n```json\n{assistant_msg}\n```\n\n"
            f"**Reviewer Score:** [ ] Accept  [ ] Needs Revision  [ ] Reject\n\n"
            f"**Correction (if needed):**\n```json\n\n```\n\n"
            f"**Reviewer Notes:**\n\n\n---\n\n"
        )
    output_path.write_text("".join(lines), encoding="utf-8")


def _stratified_select(samples: list[SFTSample], count: int) -> list[SFTSample]:
    if count >= len(samples):
        return samples
    by_stage: dict[str, list[SFTSample]] = {}
    for s in samples:
        by_stage.setdefault(s.stage.value, []).append(s)
    selected: list[SFTSample] = []
    stages = list(by_stage.keys())
    idx = 0
    while len(selected) < count and any(by_stage.values()):
        stage = stages[idx % len(stages)]
        if by_stage[stage]:
            selected.append(by_stage[stage].pop(0))
        idx += 1
    return selected


def import_human_annotations(md_path: Path, output_jsonl: Path) -> list[dict]:
    """Parse completed human annotation MD and merge corrections into JSONL."""
    text = md_path.read_text(encoding="utf-8")
    blocks = re.split(r"### Sample HR-\d+", text)[1:]
    rows: list[dict] = []
    for block in blocks:
        stage_match = re.search(r"Stage:\s*(\w+)", block)
        seed_match = re.search(r"Seed:\s*(\S+)", block)
        output_match = re.search(r"\*\*LLM Output:\*\*\s*```json\s*(.*?)\s*```", block, re.DOTALL)
        correction_match = re.search(r"\*\*Correction.*?\*\*\s*```json\s*(.*?)\s*```", block, re.DOTALL)
        accept = "[x] Accept" in block or "[X] Accept" in block
        revision = "[x] Needs Revision" in block or "[X] Needs Revision" in block
        reject = "[x] Reject" in block or "[X] Reject" in block

        if not stage_match or not output_match:
            continue
        stage = stage_match.group(1)
        seed_id = seed_match.group(1) if seed_match else "unknown"
        content = output_match.group(1).strip()
        source = "human_authored"
        if revision and correction_match and correction_match.group(1).strip():
            content = correction_match.group(1).strip()
            source = "human_corrected"
        if reject:
            continue

        status = AnnotationStatus.ACCEPT if accept else AnnotationStatus.NEEDS_REVISION if revision else AnnotationStatus.PENDING
        rows.append(
            {
                "stage": stage,
                "messages": [{"role": "user", "content": ""}, {"role": "assistant", "content": content}],
                "metadata": {"seed_id": seed_id, "source": source, "annotation_status": status.value},
            }
        )
    if rows:
        write_jsonl(output_jsonl, rows)
    return rows


def stratified_train_val_split(
    rows: list[dict],
    val_per_stage: int = 3,
) -> tuple[list[dict], list[dict]]:
    """Split each stage independently. val_per_stage=0 puts all samples in train."""
    by_stage: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_stage[row["stage"]].append(row)
    train_rows: list[dict] = []
    val_rows: list[dict] = []
    if val_per_stage <= 0:
        return rows, []
    for items in by_stage.values():
        if len(items) <= val_per_stage:
            train_rows.extend(items[:-1] if len(items) > 1 else [])
            val_rows.extend(items[-1:])
        else:
            val_rows.extend(items[-val_per_stage:])
            train_rows.extend(items[:-val_per_stage])
    return train_rows, val_rows


def run_synthesis(config: SynthesisConfig, teacher_client=None) -> dict[str, Path]:
    config.apply_test_mode()
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    seeds = generate_seeds(config.num_seeds, config.random_seed)
    if config.enable_perturbation:
        import random

        seeds.extend(augment_with_perturbation(seeds, random.Random(config.random_seed)))

    client = None
    if not config.skip_llm:
        client = teacher_client if teacher_client is not None else create_llm_client_from_env()
    annotator = TeacherAnnotator(client, config)

    sft_samples: list[SFTSample] = []
    dpo_pairs = []
    for seed in seeds:
        sft_samples.extend(annotator.annotate_full_trace(seed))
        for i in range(config.dpo_pairs_per_seed):
            flaw = DPO_FLAW_CYCLE[i % len(DPO_FLAW_CYCLE)]
            dpo_pairs.append(annotator.generate_dpo_pair(seed, flaw))

    sft_rows = [s.to_jsonl_dict() for s in sft_samples]
    if not config.skip_llm:
        sft_rows = deduplicate_by_embedding_stub(sft_rows)
    dpo_rows = [p.to_jsonl_dict() for p in dpo_pairs]

    sft_train_rows, sft_val_rows = stratified_train_val_split(sft_rows, val_per_stage=0)
    dpo_split = max(1, int(len(dpo_rows) * 0.9))

    sft_all_path = output_dir / "sft_all.jsonl"
    write_jsonl(sft_all_path, sft_rows)

    sft_train_path = output_dir / "sft_train.jsonl"
    sft_val_path = output_dir / "sft_val.jsonl"
    write_jsonl(sft_train_path, sft_train_rows)
    write_jsonl(sft_val_path, sft_val_rows)
    dpo_train_path = output_dir / "dpo_train.jsonl"
    dpo_val_path = output_dir / "dpo_val.jsonl"
    write_jsonl(dpo_train_path, dpo_rows[:dpo_split])
    write_jsonl(dpo_val_path, dpo_rows[dpo_split:])

    human_count = config.resolve_human_annotate_count(len(sft_samples))
    human_md_path = output_dir / "human_review.md"
    export_human_review_md(sft_samples, human_md_path, human_count)

    return {
        "sft_all": sft_all_path,
        "sft_train": sft_train_path,
        "sft_val": sft_val_path,
        "dpo_train": dpo_train_path,
        "dpo_val": dpo_val_path,
        "human_review": human_md_path,
    }


def parse_stages(stages_str: str | None) -> list[WorkflowStage]:
    if not stages_str:
        return WorkflowStage.all_stages()
    return [WorkflowStage(s.strip()) for s in stages_str.split(",")]


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Synthesize SFT/DPO training data")
    add_config_argument(parser)
    parser.add_argument("--num-seeds", type=int, default=5)
    parser.add_argument("--samples-per-stage", type=int, default=2)
    parser.add_argument("--human-annotate-count", type=int, default=3)
    parser.add_argument("--human-annotate-ratio", type=float, default=0.0)
    parser.add_argument("--stages", type=str, default=None)
    parser.add_argument("--test-mode", action="store_true")
    parser.add_argument("--perturb", action="store_true")
    parser.add_argument("--dpo-pairs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output-dir", type=str, default="data")
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--export-human-md", type=str, default=None, help="Only export human MD to this path")
    parser.add_argument("--import-human-md", type=str, default=None, help="Import completed human MD")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.import_human_md:
        output_dir = args.output_dir
        if args.config:
            output_dir = load_training_config(args.config).paths.output_root
        rows = import_human_annotations(Path(args.import_human_md), Path(output_dir) / "sft_human.jsonl")
        print(f"Imported {len(rows)} human-annotated samples to {output_dir}/sft_human.jsonl")
        return

    pipeline = load_training_config(args.config) if args.config else None
    if pipeline:
        config = pipeline.to_synthesis_config()
        teacher_client = None if config.skip_llm else pipeline.create_teacher_client()
    else:
        config = SynthesisConfig(
            num_seeds=args.num_seeds,
            samples_per_stage=args.samples_per_stage,
            human_annotate_count=args.human_annotate_count,
            human_annotate_ratio=args.human_annotate_ratio,
            stages=parse_stages(args.stages),
            test_mode=args.test_mode,
            enable_perturbation=args.perturb,
            dpo_pairs_per_seed=args.dpo_pairs,
            random_seed=args.seed,
            output_dir=args.output_dir,
            skip_llm=args.skip_llm,
        )
        teacher_client = None

    if args.export_human_md and config.skip_llm:
        seeds = generate_seeds(config.num_seeds, config.random_seed)
        annotator = TeacherAnnotator(None, config)
        samples: list[SFTSample] = []
        for seed in seeds:
            samples.extend(annotator.annotate_full_trace(seed))
        export_human_review_md(samples, Path(args.export_human_md), config.human_annotate_count)
        print(f"Exported human review MD to {args.export_human_md}")
        return

    paths = run_synthesis(config, teacher_client=teacher_client)
    for name, path in paths.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
