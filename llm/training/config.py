from __future__ import annotations

from dataclasses import dataclass, field

from llm.training.schemas import WorkflowStage


@dataclass
class SynthesisConfig:
    num_seeds: int = 5
    samples_per_stage: int = 2
    human_annotate_count: int = 3
    human_annotate_ratio: float = 0.0
    stages: list[WorkflowStage] = field(default_factory=WorkflowStage.all_stages)
    test_mode: bool = False
    enable_perturbation: bool = False
    dpo_pairs_per_seed: int = 1
    random_seed: int = 42
    output_dir: str = "data"
    teacher_temperature: float = 0.2
    skip_llm: bool = False

    def apply_test_mode(self) -> None:
        if not self.test_mode:
            return
        self.num_seeds = 2
        self.samples_per_stage = 1
        self.human_annotate_count = 2
        self.dpo_pairs_per_seed = 1

    def resolve_human_annotate_count(self, total_samples: int) -> int:
        if self.human_annotate_ratio > 0:
            return max(1, int(total_samples * self.human_annotate_ratio))
        return min(self.human_annotate_count, total_samples)


@dataclass
class SFTConfig:
    base_model: str = "Qwen/Qwen2.5-4B-Instruct"
    output_dir: str = "output/sft_lora"
    train_file: str = "data/sft_train.jsonl"
    val_file: str = "data/sft_val.jsonl"
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
    lora_target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    bf16: bool = True
    packing: bool = False


@dataclass
class DPOConfig:
    base_model: str = "Qwen/Qwen2.5-4B-Instruct"
    sft_adapter_path: str = "output/sft_lora"
    output_dir: str = "output/dpo_lora"
    train_file: str = "data/dpo_train.jsonl"
    val_file: str = "data/dpo_val.jsonl"
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
    lora_target_modules: list[str] = field(
        default_factory=lambda: ["q_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )
    bf16: bool = True
    use_8bit_optimizer: bool = True


@dataclass
class ExportConfig:
    base_model: str = "Qwen/Qwen2.5-4B-Instruct"
    adapter_path: str = "output/dpo_lora"
    merged_output_dir: str = "output/merged"
    gguf_output: str = "output/model-q4_k_m.gguf"
    quant: str = "q4_k_m"
    llama_cpp_dir: str = ""


@dataclass
class AugmentConfig:
    """Configuration for LLM-based augmentation of existing training data."""

    input_sft_file: str = "data/sft_all.jsonl"
    input_dpo_file: str = ""
    output_dir: str = "data/augmented"
    variants_per_sample: int = 2
    max_samples: int = 0
    strategies: list[str] = field(
        default_factory=lambda: ["perturbation", "paraphrase", "crop_context"]
    )
    stages: list[WorkflowStage] = field(default_factory=WorkflowStage.all_stages)
    random_seed: int = 42
    source_random_seed: int = 42
    teacher_temperature: float = 0.3
    skip_llm: bool = False
    merge_with_original: bool = True
    generate_dpo: bool = True
    dpo_variants_per_pair: int = 1

