# LLM Training Pipeline

This package implements the full training pipeline for the vertical-farm environmental control agent:

**Data synthesis → LLM augmentation → QLoRA SFT → QLoRA DPO → GGUF export**

Training data is aligned with inference code: prompts reuse [`llm/prompts/local.py`](../prompts/local.py), and JSON schemas reuse [`llm/models/output.py`](../models/output.py).

---

## Directory Layout

```
llm/training/
├── training_config.json    # Unified config (recommended entry point)
├── config_loader.py        # JSON config loader
├── run_pipeline.py         # One-command full pipeline
├── synthesize.py           # Data synthesis (random env + teacher annotation)
├── augment.py              # LLM augmentation from existing data
├── train_sft.py            # QLoRA supervised fine-tuning
├── train_dpo.py            # QLoRA preference optimization
├── export_gguf.py          # Merge LoRA + GGUF quantization export
├── evaluate.py             # JSON compliance and related metrics
├── docs/HUMAN_ANNOTATION.md
└── sample_data/            # Per-stage smoke-test fixtures
```

---

## Installation

```bash
# Base dependencies (LangChain, Pydantic, etc.)
uv sync

# Training dependencies (PyTorch, Transformers, PEFT, TRL, etc.)
uv sync --extra training
```

Training stages require an **NVIDIA GPU** (≥24 GB VRAM recommended; documented SFT setup uses a single L40S 48 GB).

---

## End-to-End Training Flow

```
Random env generation (state_generator)
        ↓
Teacher model annotation (GPT-4o, etc.)  ──→  SFT JSONL + DPO JSONL
        ↓                                        ↓
Human review (human_review.md)          LLM augmentation (augment)
        ↓                                        ↓
Merged dataset ──────────────────────→  sft_merged.jsonl
        ↓
QLoRA SFT (Qwen2.5-4B-Instruct)  →  output/sft_lora/
        ↓
QLoRA DPO (frozen SFT reference)  →  output/dpo_lora/
        ↓
Merge + GGUF Q4_K_M quantization   →  output/model-q4_k_m.gguf
        ↓
Edge deployment (Jetson Orin Nano)
```

### Five Workflow Stages (Independent SFT Samples)

| Stage | Output Schema | Description |
|-------|---------------|-------------|
| `diagnosis` | `Step1Output` | Environmental diagnosis |
| `planning` | `Step2Output` | Action plan + function calls |
| `side_effect` | `SideEffectEvaluation` | Side-effect assessment |
| `decision` | `Step3Output` | Solution selection |
| `final_command` | `ControlCommand` | MQTT control command |

Each stage is stored as a **separate** JSONL row (not a multi-turn conversation).

---

## Unified Configuration

All parameters live in [`training_config.json`](training_config.json):

| Section | Contents |
|---------|----------|
| `teacher_model` | External LLM for annotation/augmentation (provider, model_name, temperature, api_key, etc.) |
| `train_model` | Model being trained (base_model, 4-bit quantization, LoRA target modules) |
| `paths` | Data files and output directories |
| `synthesis` | Data synthesis scale parameters |
| `augment` | Augmentation strategies and variant counts |
| `sft` / `dpo` | Training hyperparameters |
| `export` | GGUF quantization format |
| `pipeline.run_stages` | Stages to run in one-command pipeline |

`api_key` supports environment variable references:

```json
"api_key": "${OPENAI_API_KEY}"
```

Set before running:

```bash
export OPENAI_API_KEY="sk-..."
# Or use a compatible API (e.g. DeepSeek):
export OPENAI_API_KEY="..."
# And update api_base / model_name under teacher_model
```

---

## CLI Usage

All subcommands support `--config` to load the unified JSON. Without `--config`, CLI defaults apply.

### Option 1: One-Command Pipeline (Recommended)

```bash
# Run all stages listed in pipeline.run_stages
python -m llm.training.run_pipeline \
  --config llm/training/training_config.json

# Run specific stages only
python -m llm.training.run_pipeline \
  --config llm/training/training_config.json \
  --stages synthesize,augment,sft

python -m llm.training.run_pipeline \
  --config llm/training/training_config.json \
  --stages dpo,export
```

### Option 2: Step-by-Step

#### 1. Data Synthesis — `synthesize`

Generate SFT / DPO training data from random environmental states, with optional teacher LLM annotation.

```bash
# Using unified config
python -m llm.training.synthesize \
  --config llm/training/training_config.json

# Standalone CLI flags (no JSON)
python -m llm.training.synthesize \
  --num-seeds 15 \
  --samples-per-stage 1 \
  --human-annotate-count 5 \
  --dpo-pairs 1 \
  --output-dir data/training_15x5

python -m llm.training.synthesize --test-mode --skip-llm

python -m llm.training.synthesize \
  --config llm/training/training_config.json
```

**Outputs:**

| File | Description |
|------|-------------|
| `sft_all.jsonl` | All SFT samples |
| `sft_train.jsonl` / `sft_val.jsonl` | Train / validation split |
| `dpo_train.jsonl` / `dpo_val.jsonl` | DPO preference pairs |
| `human_review.md` | Human review template |

**Key flags:**

| Flag | Meaning | Default |
|------|---------|---------|
| `--num-seeds` | Number of random env states | 5 |
| `--samples-per-stage` | Samples per seed per stage | 2 |
| `--human-annotate-count` | Samples exported for human review | 3 |
| `--dpo-pairs` | DPO pairs per seed | 1 |
| `--test-mode` | Minimal-scale test run | false |
| `--skip-llm` | Skip LLM; use stub annotations | false |
| `--perturb` | Enable env perturbation during synthesis | false |

#### 2. Human Annotation

1. Open `data/.../human_review.md`
2. Mark each sample: Accept / Needs Revision / Reject; add corrected JSON if needed
3. Import back into the pipeline:

```bash
python -m llm.training.synthesize \
  --import-human-md data/training_15x5/human_review_completed.md \
  --output-dir data/training_15x5
```

This writes `sft_human.jsonl`, which can be merged into the training set.

#### 3. Data Augmentation — `augment`

Generate variants from existing JSONL via perturbation + teacher LLM.

```bash
python -m llm.training.augment \
  --config llm/training/training_config.json

# Standalone flags
python -m llm.training.augment \
  --input-sft data/training_15x5/sft_all.jsonl \
  --input-dpo data/training_15x5/dpo_train.jsonl \
  --output-dir data/training_15x5/augmented \
  --variants-per-sample 2 \
  --skip-llm
```

**Augmentation strategies (`--strategies`):**

- `perturbation` — Perturb temperature/humidity/photoperiod, then re-annotate
- `paraphrase` — Same state, different wording or alternative valid plan
- `crop_context` — Swap crop variety or growth stage
- `edge_case` — Push toward boundary scenarios

**Outputs:**

| File | Description |
|------|-------------|
| `sft_augmented.jsonl` | Augmented samples only |
| `sft_merged.jsonl` | Original + augmented (preferred for SFT) |
| `dpo_merged.jsonl` | Merged DPO pairs |

#### 4. QLoRA SFT — `train_sft`

```bash
python -m llm.training.train_sft \
  --config llm/training/training_config.json

# Standalone flags
python -m llm.training.train_sft \
  --base-model Qwen/Qwen2.5-4B-Instruct \
  --train-file data/training_15x5/augmented/sft_merged.jsonl \
  --val-file data/training_15x5/sft_val.jsonl \
  --output-dir output/sft_lora \
  --epochs 3 --lr 2e-4 --batch-size 2 --grad-accum 4
```


Output: `output/sft_lora/` (LoRA adapter + tokenizer)

#### 5. QLoRA DPO — `train_dpo`

Preference optimization on top of the SFT adapter, with a frozen 4-bit SFT reference policy.

```bash
python -m llm.training.train_dpo \
  --config llm/training/training_config.json

# Standalone flags
python -m llm.training.train_dpo \
  --sft-adapter output/sft_lora \
  --train-file data/training_15x5/augmented/dpo_merged.jsonl \
  --output-dir output/dpo_lora \
  --epochs 2 --lr 3e-5 --beta 0.1
```

Output: `output/dpo_lora/`

#### 6. GGUF Export — `export_gguf`

```bash
python -m llm.training.export_gguf \
  --config llm/training/training_config.json

# Standalone flags
python -m llm.training.export_gguf \
  --adapter output/dpo_lora \
  --quant q4_k_m \
  --output output/model-q4_k_m.gguf \
  --llama-cpp-dir /path/to/llama.cpp
```

Steps: merge LoRA → save HF weights → convert via llama.cpp → quantize.


***Requires!!!: *** [llama.cpp](https://github.com/ggerganov/llama.cpp) installed; set path via `export.llama_cpp_dir` or `--llama-cpp-dir`.

#### 7. Evaluation — `evaluate`

```bash
python -m llm.training.evaluate
```

Computes JSON schema compliance, tool-call success rate, etc. on `sample_data/sft_per_stage.jsonl`.

---

## Example Workflows

### Local Test 

```bash
# 1. Synthesize minimal dataset
python -m llm.training.synthesize --test-mode --skip-llm \
  --output-dir data/smoke_test

# 2. Augment
python -m llm.training.augment \
  --input-sft data/smoke_test/sft_all.jsonl \
  --variants-per-sample 1 --skip-llm \
  --output-dir data/smoke_test/augmented --no-dpo

# 3. Evaluate
python -m llm.training.evaluate
```

### Sample Production Training

```bash
# 1. Edit training_config.json:
#    - synthesis.num_seeds = 15
#    - synthesis.skip_llm = false  (requires API key)
#    - augment.skip_llm = false

# 2. Synthesize + augment
python -m llm.training.run_pipeline \
  --config llm/training/training_config.json \
  --stages synthesize,augment

# 3. Human review of human_review.md, then import (optional)
python -m llm.training.synthesize \
  --import-human-md data/training_15x5/human_review_completed.md \
  --output-dir data/training_15x5

# 4. SFT → DPO → export
python -m llm.training.run_pipeline \
  --config llm/training/training_config.json \
  --stages sft,dpo,export
```

---

## How Config Relates to CLI

```
training_config.json
       │
       ├── run_pipeline.py
       ├── synthesize.py   --config
       ├── augment.py      --config
       ├── train_sft.py    --config
       ├── train_dpo.py    --config
       └── export_gguf.py  --config
```

- With `--config`: loads the relevant section from JSON; paths are managed under `paths`
- Without `--config`: uses per-command CLI defaults
- SFT training prefers `paths.sft_merged` if the file exists, else `paths.sft_train`
- DPO training prefers `paths.dpo_merged` if the file exists, else `paths.dpo_train`

---

## Data Formats

### SFT Sample (one JSON object per JSONL line)

```json
{
  "stage": "diagnosis",
  "messages": [
    {"role": "user", "content": "...inference prompt..."},
    {"role": "assistant", "content": "{\"core_issue\": \"...\", \"states\": [...], \"confidence\": [...]}"}
  ],
  "metadata": {"seed_id": "seed_00000", "source": "llm_synthesis"}
}
```

### DPO Preference Pair (one JSON object per JSONL line)

```json
{
  "prompt": "...",
  "chosen": "{...safe output JSON...}",
  "rejected": "{...unsafe output JSON...}",
  "stage": "planning",
  "category": "safety_bypass"
}
```

---

## FAQ

**Q: What is the difference between `skip_llm: true` and `false`?**

`true` uses stub annotations derived from random env states (no API needed; good for pipeline validation). 
`false` calls the LLM configured under `teacher_model` for higher-quality labels.

**Q: Training fails with `No module named 'datasets'`?**

Run `uv sync --extra training` to install training dependencies.

**Q: OpenAI API errors?**

Check the `OPENAI_API_KEY` environment variable:

---

## Related Code

- Inference workflow: [`llm/workflow/`](../workflow/)
- Prompt templates: [`llm/prompts/local.py`](../prompts/local.py)
- Output schemas: [`llm/models/output.py`](../models/output.py)
- Human annotation guide: [`docs/HUMAN_ANNOTATION.md`](docs/HUMAN_ANNOTATION.md)
