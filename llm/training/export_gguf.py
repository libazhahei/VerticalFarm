"""Merge LoRA adapter and export to GGUF via llama.cpp."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from llm.training.config import ExportConfig
from llm.training.config_loader import add_config_argument, load_training_config

QUANT_MAP = {
    "f16": "F16",
    "q8_0": "Q8_0",
    "q4_k_m": "Q4_K_M",
    "q4_0": "Q4_0",
    "q2_k": "Q2_K",
}


def merge_lora(config: ExportConfig) -> Path:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    merged_dir = Path(config.merged_output_dir)
    merged_dir.mkdir(parents=True, exist_ok=True)

    base = AutoModelForCausalLM.from_pretrained(
        config.base_model,
        torch_dtype=torch.bfloat16,
        device_map="cpu",
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, config.adapter_path)
    model = model.merge_and_unload()
    model.save_pretrained(merged_dir)
    tokenizer = AutoTokenizer.from_pretrained(config.base_model, trust_remote_code=True)
    tokenizer.save_pretrained(merged_dir)
    print(f"Merged model saved to {merged_dir}")
    return merged_dir


def convert_to_gguf(merged_dir: Path, llama_cpp_dir: str, output_gguf: Path) -> Path:
    llama_cpp = Path(llama_cpp_dir) if llama_cpp_dir else None
    convert_script = None
    if llama_cpp:
        for candidate in ["convert_hf_to_gguf.py", "examples/convert_legacy_llama.py"]:
            path = llama_cpp / candidate
            if path.exists():
                convert_script = path
                break
    if convert_script is None:
        print(
            "llama.cpp convert script not found. Install llama.cpp and pass --llama-cpp-dir.\n"
            "Manual steps:\n"
            f"  python convert_hf_to_gguf.py {merged_dir} --outfile {output_gguf.with_suffix('.f16.gguf')}\n"
            f"  ./quantize <f16.gguf> {output_gguf} Q4_K_M",
            file=sys.stderr,
        )
        return output_gguf

    f16_path = output_gguf.with_suffix(".f16.gguf")
    subprocess.run(
        [sys.executable, str(convert_script), str(merged_dir), "--outfile", str(f16_path)],
        check=True,
    )
    return f16_path


def quantize_gguf(f16_path: Path, output_path: Path, quant: str, llama_cpp_dir: str) -> None:
    quant_type = QUANT_MAP.get(quant.lower(), "Q4_K_M")
    if quant.lower() == "f16":
        f16_path.rename(output_path)
        return
    quantize_bin = Path(llama_cpp_dir) / "quantize" if llama_cpp_dir else Path("quantize")
    if not quantize_bin.exists():
        print(
            f"quantize binary not found at {quantize_bin}. "
            f"Run manually: ./quantize {f16_path} {output_path} {quant_type}",
            file=sys.stderr,
        )
        return
    subprocess.run([str(quantize_bin), str(f16_path), str(output_path), quant_type], check=True)
    print(f"Quantized GGUF saved to {output_path}")


def export_gguf(config: ExportConfig) -> None:
    merged_dir = merge_lora(config)
    output_path = Path(config.gguf_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    f16_path = convert_to_gguf(merged_dir, config.llama_cpp_dir, output_path)
    if f16_path.exists():
        quantize_gguf(f16_path, output_path, config.quant, config.llama_cpp_dir)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export merged LoRA model to GGUF")
    add_config_argument(parser)
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-4B-Instruct")
    parser.add_argument("--adapter", default="output/dpo_lora")
    parser.add_argument("--merged-dir", default="output/merged")
    parser.add_argument("--output", default="output/model-q4_k_m.gguf")
    parser.add_argument("--quant", default="q4_k_m", choices=list(QUANT_MAP.keys()))
    parser.add_argument("--llama-cpp-dir", default="", help="Path to llama.cpp repo")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.config:
        config = load_training_config(args.config).to_export_config()
    else:
        config = ExportConfig(
            base_model=args.base_model,
            adapter_path=args.adapter,
            merged_output_dir=args.merged_dir,
            gguf_output=args.output,
            quant=args.quant,
            llama_cpp_dir=args.llama_cpp_dir,
        )
    export_gguf(config)


if __name__ == "__main__":
    main()
