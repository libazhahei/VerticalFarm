"""QLoRA supervised fine-tuning for Qwen2.5-4B-Instruct."""

from __future__ import annotations

import argparse

from llm.training.config import SFTConfig
from llm.training.config_loader import TrainModelConfig, add_config_argument, build_bnb_config_from_train_model, load_training_config
from llm.training.dataset import load_sft_datasets


def build_bnb_config(train_model: TrainModelConfig | None = None):
    if train_model is not None:
        return build_bnb_config_from_train_model(train_model)
    import torch
    from transformers import BitsAndBytesConfig

    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )


def build_lora_config(config: SFTConfig):
    from peft import LoraConfig

    return LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.lora_target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )


def train_sft(config: SFTConfig, train_model: TrainModelConfig | None = None) -> None:
    import torch
    from peft import get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments
    from trl import SFTConfig as TRLSFTConfig
    from trl import SFTTrainer

    train_ds, val_ds = load_sft_datasets(config.train_file, config.val_file)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = build_bnb_config(train_model)
    model = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, build_lora_config(config))

    sft_config = TRLSFTConfig(
        output_dir=config.output_dir,
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=config.warmup_ratio,
        weight_decay=config.weight_decay,
        bf16=config.bf16,
        logging_steps=10,
        save_strategy="epoch",
        max_length=config.max_seq_length,
        packing=config.packing,
        dataset_text_field=None,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    print(f"SFT LoRA adapter saved to {config.output_dir}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QLoRA SFT training")
    add_config_argument(parser)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-4B-Instruct")
    parser.add_argument("--train-file", default="data/sft_train.jsonl")
    parser.add_argument("--val-file", default="data/sft_val.jsonl")
    parser.add_argument("--output-dir", default="output/sft_lora")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    pipeline = load_training_config(args.config) if args.config else None
    if pipeline:
        config = pipeline.to_sft_config()
        train_model = pipeline.train_model
    else:
        config = SFTConfig(
            base_model=args.base_model,
            train_file=args.train_file,
            val_file=args.val_file,
            output_dir=args.output_dir,
            num_epochs=args.epochs,
            learning_rate=args.lr,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=args.grad_accum,
        )
        train_model = None
    train_sft(config, train_model=train_model)


if __name__ == "__main__":
    main()
