"""Load unified training pipeline configuration from JSON."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from llm.clients.config import LLMClientConfig, LLMProvider
from llm.clients.factory import create_llm_client
from llm.training.config import AugmentConfig, DPOConfig, ExportConfig, SFTConfig, SynthesisConfig
from llm.training.schemas import WorkflowStage


def resolve_env_value(value: str | None) -> str | None:
    if value is None:
        return None
    match = re.fullmatch(r"\$\{([^}]+)\}", value.strip())
    if match:
        return os.environ.get(match.group(1))
    return value


class TeacherModelConfig(BaseModel):
    provider: str = "openai"
    model_name: str = "gpt-4o"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float = 0.2
    max_retries: int = 3
    timeout: int = 120
    host: str = "localhost"
    port: int = 11434
    scheme: str = "http"
    api_path: str = "v1"

    def to_llm_client_config(self) -> LLMClientConfig:
        provider = LLMProvider(self.provider.lower())
        api_key = resolve_env_value(self.api_key)
        if provider == LLMProvider.OPENAI and not api_key:
            api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        api_base = resolve_env_value(self.api_base)
        if provider == LLMProvider.OLLAMA and not api_base:
            api_base = f"{self.scheme}://{self.host}:{self.port}"
        return LLMClientConfig(
            provider=provider,
            model_name=self.model_name,
            api_key=api_key,
            api_base=api_base,
            host=self.host,
            port=self.port,
            scheme=self.scheme,
            api_path=self.api_path,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )


class QuantizationConfig(BaseModel):
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_use_double_quant: bool = True
    bnb_4bit_compute_dtype: str = "bf16"


class TrainModelConfig(BaseModel):
    base_model: str = "Qwen/Qwen2.5-4B-Instruct"
    trust_remote_code: bool = True
    quantization: QuantizationConfig = Field(default_factory=QuantizationConfig)
    lora_target_modules: list[str] = Field(
        default_factory=lambda: ["q_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )


class PathsConfig(BaseModel):
    output_root: str = "data"
    sft_train: str = "data/sft_train.jsonl"
    sft_val: str = "data/sft_val.jsonl"
    sft_all: str = "data/sft_all.jsonl"
    dpo_train: str = "data/dpo_train.jsonl"
    dpo_val: str = "data/dpo_val.jsonl"
    sft_merged: str = "data/augmented/sft_merged.jsonl"
    dpo_merged: str = "data/augmented/dpo_merged.jsonl"
    human_review_md: str = "data/human_review.md"
    sft_lora_output: str = "output/sft_lora"
    dpo_lora_output: str = "output/dpo_lora"
    merged_hf_output: str = "output/merged"
    gguf_output: str = "output/model-q4_k_m.gguf"


class SynthesisSection(BaseModel):
    num_seeds: int = 5
    samples_per_stage: int = 2
    human_annotate_count: int = 3
    human_annotate_ratio: float = 0.0
    stages: list[str] = Field(
        default_factory=lambda: [s.value for s in WorkflowStage.all_stages()]
    )
    test_mode: bool = False
    enable_perturbation: bool = False
    dpo_pairs_per_seed: int = 1
    random_seed: int = 42
    skip_llm: bool = False


class AugmentSection(BaseModel):
    variants_per_sample: int = 2
    max_samples: int = 0
    strategies: list[str] = Field(default_factory=lambda: ["perturbation", "paraphrase", "crop_context"])
    random_seed: int = 42
    source_random_seed: int = 42
    merge_with_original: bool = True
    generate_dpo: bool = True
    dpo_variants_per_pair: int = 1
    skip_llm: bool = False


class SFTSection(BaseModel):
    learning_rate: float = 2e-4
    warmup_ratio: float = 0.03
    num_epochs: int = 3
    per_device_train_batch_size: int = 2
    gradient_accumulation_steps: int = 4
    weight_decay: float = 0.01
    max_seq_length: int = 1536
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    bf16: bool = True
    packing: bool = False


class DPOSection(BaseModel):
    learning_rate: float = 3e-5
    beta: float = 0.1
    num_epochs: int = 2
    per_device_train_batch_size: int = 1
    gradient_accumulation_steps: int = 8
    max_length: int = 1536
    max_prompt_length: int = 768
    lora_r: int = 16
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    bf16: bool = True
    use_8bit_optimizer: bool = True


class ExportSection(BaseModel):
    quant: str = "q4_k_m"
    llama_cpp_dir: str = ""


class PipelineSection(BaseModel):
    run_stages: list[str] = Field(default_factory=lambda: ["synthesize", "augment", "sft", "dpo", "export"])


class TrainingPipelineConfig(BaseModel):
    description: str = ""
    teacher_model: TeacherModelConfig = Field(default_factory=TeacherModelConfig)
    train_model: TrainModelConfig = Field(default_factory=TrainModelConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    synthesis: SynthesisSection = Field(default_factory=SynthesisSection)
    augment: AugmentSection = Field(default_factory=AugmentSection)
    sft: SFTSection = Field(default_factory=SFTSection)
    dpo: DPOSection = Field(default_factory=DPOSection)
    export: ExportSection = Field(default_factory=ExportSection)
    pipeline: PipelineSection = Field(default_factory=PipelineSection)

    def to_synthesis_config(self) -> SynthesisConfig:
        stages = [WorkflowStage(s) for s in self.synthesis.stages]
        return SynthesisConfig(
            num_seeds=self.synthesis.num_seeds,
            samples_per_stage=self.synthesis.samples_per_stage,
            human_annotate_count=self.synthesis.human_annotate_count,
            human_annotate_ratio=self.synthesis.human_annotate_ratio,
            stages=stages,
            test_mode=self.synthesis.test_mode,
            enable_perturbation=self.synthesis.enable_perturbation,
            dpo_pairs_per_seed=self.synthesis.dpo_pairs_per_seed,
            random_seed=self.synthesis.random_seed,
            output_dir=self.paths.output_root,
            teacher_temperature=self.teacher_model.temperature,
            skip_llm=self.synthesis.skip_llm,
        )

    def to_augment_config(self) -> AugmentConfig:
        return AugmentConfig(
            input_sft_file=self.paths.sft_all,
            input_dpo_file=self.paths.dpo_train,
            output_dir=str(Path(self.paths.output_root) / "augmented"),
            variants_per_sample=self.augment.variants_per_sample,
            max_samples=self.augment.max_samples,
            strategies=self.augment.strategies,
            stages=[WorkflowStage(s) for s in self.synthesis.stages],
            random_seed=self.augment.random_seed,
            source_random_seed=self.augment.source_random_seed,
            teacher_temperature=self.teacher_model.temperature,
            skip_llm=self.augment.skip_llm,
            merge_with_original=self.augment.merge_with_original,
            generate_dpo=self.augment.generate_dpo,
            dpo_variants_per_pair=self.augment.dpo_variants_per_pair,
        )

    def to_sft_config(self) -> SFTConfig:
        train_file = self.paths.sft_merged if Path(self.paths.sft_merged).exists() else self.paths.sft_train
        return SFTConfig(
            base_model=self.train_model.base_model,
            output_dir=self.paths.sft_lora_output,
            train_file=train_file,
            val_file=self.paths.sft_val,
            learning_rate=self.sft.learning_rate,
            warmup_ratio=self.sft.warmup_ratio,
            num_epochs=self.sft.num_epochs,
            per_device_train_batch_size=self.sft.per_device_train_batch_size,
            gradient_accumulation_steps=self.sft.gradient_accumulation_steps,
            weight_decay=self.sft.weight_decay,
            max_seq_length=self.sft.max_seq_length,
            lora_r=self.sft.lora_r,
            lora_alpha=self.sft.lora_alpha,
            lora_dropout=self.sft.lora_dropout,
            lora_target_modules=self.train_model.lora_target_modules,
            bf16=self.sft.bf16,
            packing=self.sft.packing,
        )

    def to_dpo_config(self) -> DPOConfig:
        train_file = self.paths.dpo_merged if Path(self.paths.dpo_merged).exists() else self.paths.dpo_train
        return DPOConfig(
            base_model=self.train_model.base_model,
            sft_adapter_path=self.paths.sft_lora_output,
            output_dir=self.paths.dpo_lora_output,
            train_file=train_file,
            val_file=self.paths.dpo_val,
            learning_rate=self.dpo.learning_rate,
            beta=self.dpo.beta,
            num_epochs=self.dpo.num_epochs,
            per_device_train_batch_size=self.dpo.per_device_train_batch_size,
            gradient_accumulation_steps=self.dpo.gradient_accumulation_steps,
            max_length=self.dpo.max_length,
            max_prompt_length=self.dpo.max_prompt_length,
            lora_r=self.dpo.lora_r,
            lora_alpha=self.dpo.lora_alpha,
            lora_dropout=self.dpo.lora_dropout,
            lora_target_modules=self.train_model.lora_target_modules,
            bf16=self.dpo.bf16,
            use_8bit_optimizer=self.dpo.use_8bit_optimizer,
        )

    def to_export_config(self) -> ExportConfig:
        return ExportConfig(
            base_model=self.train_model.base_model,
            adapter_path=self.paths.dpo_lora_output,
            merged_output_dir=self.paths.merged_hf_output,
            gguf_output=self.paths.gguf_output,
            quant=self.export.quant,
            llama_cpp_dir=self.export.llama_cpp_dir,
        )

    def create_teacher_client(self):
        if self.synthesis.skip_llm and self.augment.skip_llm:
            return None
        return create_llm_client(self.teacher_model.to_llm_client_config())


def load_training_config(path: str | Path) -> TrainingPipelineConfig:
    config_path = Path(path)
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return TrainingPipelineConfig.model_validate(data)


def save_training_config(config: TrainingPipelineConfig, path: str | Path) -> None:
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def build_bnb_config_from_train_model(train_model: TrainModelConfig):
    import torch
    from transformers import BitsAndBytesConfig

    dtype_map = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}
    compute_dtype = dtype_map.get(train_model.quantization.bnb_4bit_compute_dtype, torch.bfloat16)
    return BitsAndBytesConfig(
        load_in_4bit=train_model.quantization.load_in_4bit,
        bnb_4bit_quant_type=train_model.quantization.bnb_4bit_quant_type,
        bnb_4bit_use_double_quant=train_model.quantization.bnb_4bit_use_double_quant,
        bnb_4bit_compute_dtype=compute_dtype,
    )


def add_config_argument(parser) -> None:
    parser.add_argument(
        "--config",
        default=None,
        help="Path to unified training_config.json",
    )
