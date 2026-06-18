from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from datasets import Dataset


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def sft_rows_to_dataset(rows: list[dict[str, Any]]) -> "Dataset":
    """Convert SFT JSONL rows to HF Dataset with messages column."""
    from datasets import Dataset

    formatted = []
    for row in rows:
        messages = row.get("messages", [])
        formatted.append({"messages": messages, "stage": row.get("stage", ""), "metadata": row.get("metadata", {})})
    return Dataset.from_list(formatted)


def dpo_rows_to_dataset(rows: list[dict[str, Any]]) -> "Dataset":
    from datasets import Dataset

    formatted = []
    for row in rows:
        formatted.append(
            {
                "prompt": row["prompt"],
                "chosen": row["chosen"],
                "rejected": row["rejected"],
                "stage": row.get("stage", ""),
                "metadata": row.get("metadata", {}),
            }
        )
    return Dataset.from_list(formatted)


def apply_chat_template(dataset: "Dataset", tokenizer: Any, column: str = "messages") -> "Dataset":
    def _format(example: dict[str, Any]) -> dict[str, str]:
        text = tokenizer.apply_chat_template(example[column], tokenize=False, add_generation_prompt=False)
        return {"text": text}

    return dataset.map(_format)


def train_val_split(rows: list[dict[str, Any]], val_ratio: float = 0.12) -> tuple[list[dict], list[dict]]:
    split_idx = max(1, int(len(rows) * (1 - val_ratio)))
    return rows[:split_idx], rows[split_idx:]


def load_sft_datasets(train_file: str, val_file: str | None = None) -> "tuple[Dataset, Dataset | None]":
    train_rows = load_jsonl(train_file)
    train_ds = sft_rows_to_dataset(train_rows)
    val_ds = None
    if val_file and Path(val_file).exists():
        val_ds = sft_rows_to_dataset(load_jsonl(val_file))
    return train_ds, val_ds


def load_dpo_datasets(train_file: str, val_file: str | None = None) -> "tuple[Dataset, Dataset | None]":
    train_rows = load_jsonl(train_file)
    train_ds = dpo_rows_to_dataset(train_rows)
    val_ds = None
    if val_file and Path(val_file).exists():
        val_ds = dpo_rows_to_dataset(load_jsonl(val_file))
    return train_ds, val_ds
