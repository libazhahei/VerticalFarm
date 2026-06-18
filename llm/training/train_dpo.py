"""QLoRA DPO training with frozen 4-bit SFT reference model."""

from __future__ import annotations

import argparse

from llm.training.config import DPOConfig
from llm.training.config_loader import TrainModelConfig, add_config_argument, build_bnb_config_from_train_model, load_training_config
from llm.training.dataset import load_dpo_datasets


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


def build_lora_config(config: DPOConfig):
    from peft import LoraConfig

    return LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=config.lora_target_modules,
        bias="none",
        task_type="CAUSAL_LM",
    )


def load_model_with_adapter(
    base_model: str,
    adapter_path: str,
    trainable: bool = True,
    train_model: TrainModelConfig | None = None,
):
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM

    bnb_config = build_bnb_config(train_model)
    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, adapter_path, is_trainable=trainable)
    if not trainable:
        for param in model.parameters():
            param.requires_grad = False
        model.eval()
    return model


def train_dpo(config: DPOConfig, train_model: TrainModelConfig | None = None) -> None:
    from transformers import AutoTokenizer
    from trl import DPOConfig as TRLDPOConfig
    from trl import DPOTrainer

    train_ds, val_ds = load_dpo_datasets(config.train_file, config.val_file)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    policy_model = load_model_with_adapter(
        config.base_model, config.sft_adapter_path, trainable=True, train_model=train_model
    )
    ref_model = load_model_with_adapter(
        config.base_model, config.sft_adapter_path, trainable=False, train_model=train_model
    )

    dpo_config = TRLDPOConfig(
        output_dir=config.output_dir,
        beta=config.beta,
        learning_rate=config.learning_rate,
        num_train_epochs=config.num_epochs,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        max_length=config.max_length,
        max_prompt_length=config.max_prompt_length,
        bf16=config.bf16,
        logging_steps=10,
        save_strategy="epoch",
        loss_type="sigmoid",
    )

    trainer = DPOTrainer(
        model=policy_model,
        ref_model=ref_model,
        args=dpo_config,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        processing_class=tokenizer,
    )

    trainer.train()
    trainer.save_model(config.output_dir)
    tokenizer.save_pretrained(config.output_dir)
    print(f"DPO LoRA adapter saved to {config.output_dir}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QLoRA DPO training")
    add_config_argument(parser)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-4B-Instruct")
    parser.add_argument("--sft-adapter", default="output/sft_lora")
    parser.add_argument("--train-file", default="data/dpo_train.jsonl")
    parser.add_argument("--val-file", default="data/dpo_val.jsonl")
    parser.add_argument("--output-dir", default="output/dpo_lora")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=3e-5)
    parser.add_argument("--beta", type=float, default=0.1)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    pipeline = load_training_config(args.config) if args.config else None
    if pipeline:
        config = pipeline.to_dpo_config()
        train_model = pipeline.train_model
    else:
        config = DPOConfig(
            base_model=args.base_model,
            sft_adapter_path=args.sft_adapter,
            train_file=args.train_file,
            val_file=args.val_file,
            output_dir=args.output_dir,
            num_epochs=args.epochs,
            learning_rate=args.lr,
            beta=args.beta,
        )
        train_model = None
    train_dpo(config, train_model=train_model)


if __name__ == "__main__":
    main()
