---
name: axolotl
version: 0.6.0
category: training
trigger: 'when the user needs to fine-tune an LLM, create a LoRA/QLoRA adapter, do full fine-tuning, or train on instruction/chat datasets'
updated: 2026-03-11
confidence: reviewed
eval_issue: 1
---

# Axolotl v0.6+

## When to Use

- You need to fine-tune Llama, Mistral, Qwen, or other popular LLMs
- You want LoRA or QLoRA fine-tuning (parameter-efficient, fits on consumer GPUs)
- You need full fine-tuning with DeepSpeed or FSDP across multiple GPUs
- You have data in common formats (Alpaca, ShareGPT, completion) and want minimal preprocessing
- You want flash attention, gradient checkpointing, sample packing out of the box
- You want a YAML-driven config (no Python training loop to write)

## When NOT to Use

- You want to fine-tune via a pure Python API -> use HuggingFace TRL or torchtune instead
- You only need simple LoRA on a single file -> use unsloth for fastest single-GPU training
- You need to train from scratch (pretraining) -> use Megatron-LM or NanoGPT instead
- You want a UI/no-code fine-tuning -> use Predibase, Together, or OpenPipe instead
- You're fine-tuning vision or multimodal models -> use LLaVA or dedicated frameworks

## Quick Start

```bash
# Install
pip install axolotl[flash-attn]
# Or from source for latest:
git clone https://github.com/axolotl-ai-cloud/axolotl.git
cd axolotl
pip install -e ".[flash-attn]"

# Fine-tune with a YAML config
accelerate launch -m axolotl.cli.train config.yml

# Or use the CLI shorthand
axolotl train config.yml
```

Minimal LoRA config (config.yml):

```yaml
base_model: meta-llama/Llama-3.1-8B-Instruct
model_type: LlamaForCausalLM
load_in_8bit: false
load_in_4bit: true

adapter: qlora
lora_r: 16
lora_alpha: 32
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

datasets:
  - path: my_data.jsonl
    type: alpaca

dataset_prepared_path: last_run_prepared
output_dir: ./output

sequence_len: 2048
sample_packing: true
pad_to_sequence_len: true

micro_batch_size: 2
gradient_accumulation_steps: 4
num_epochs: 3
learning_rate: 2e-4
optimizer: adamw_bnb_8bit
lr_scheduler: cosine
warmup_ratio: 0.1

bf16: auto
flash_attention: true
gradient_checkpointing: true

wandb_project: my-finetune
wandb_run_id:
```

## Common Patterns

### Alpaca format dataset

Your data file (my_data.jsonl) — one JSON object per line:

```json
{"instruction": "Summarize the following text.", "input": "Long article text here...", "output": "Brief summary here."}
{"instruction": "Translate to French.", "input": "Hello, how are you?", "output": "Bonjour, comment allez-vous?"}
{"instruction": "Write a haiku about coding.", "input": "", "output": "Fingers on the keys\nLogic flows like morning streams\nBugs hide in the mist"}
```

Config:
```yaml
datasets:
  - path: my_data.jsonl
    type: alpaca
```

### ShareGPT format (multi-turn chat)

```json
{"conversations": [
  {"from": "human", "value": "What is Python?"},
  {"from": "gpt", "value": "Python is a high-level programming language..."},
  {"from": "human", "value": "Show me a hello world example"},
  {"from": "gpt", "value": "```python\nprint('Hello, World!')\n```"}
]}
```

Config:
```yaml
datasets:
  - path: chat_data.jsonl
    type: sharegpt
```

### Completion format (raw text, no instruction structure)

```json
{"text": "Full document text that the model should learn to generate..."}
```

Config:
```yaml
datasets:
  - path: completions.jsonl
    type: completion
```

### QLoRA on a single GPU (24GB VRAM)

```yaml
base_model: meta-llama/Llama-3.1-8B-Instruct
load_in_4bit: true
adapter: qlora

lora_r: 32
lora_alpha: 64
lora_dropout: 0.05
lora_target_modules:
  - q_proj
  - v_proj
  - k_proj
  - o_proj
  - gate_proj
  - up_proj
  - down_proj

datasets:
  - path: data/train.jsonl
    type: alpaca

sequence_len: 4096
sample_packing: true
pad_to_sequence_len: true

micro_batch_size: 1
gradient_accumulation_steps: 8
num_epochs: 3
learning_rate: 2e-4
optimizer: adamw_bnb_8bit
lr_scheduler: cosine
warmup_ratio: 0.1

bf16: auto
flash_attention: true
gradient_checkpointing: true
gradient_checkpointing_kwargs:
  use_reentrant: false

output_dir: ./qlora-output
```

### Full fine-tune with DeepSpeed (multi-GPU)

```yaml
base_model: meta-llama/Llama-3.1-8B-Instruct
load_in_4bit: false
adapter:  # empty = full fine-tune

datasets:
  - path: data/train.jsonl
    type: sharegpt

sequence_len: 4096
sample_packing: true
pad_to_sequence_len: true

micro_batch_size: 1
gradient_accumulation_steps: 4
num_epochs: 3
learning_rate: 2e-5
optimizer: adamw_torch
lr_scheduler: cosine
warmup_ratio: 0.1

bf16: auto
flash_attention: true
gradient_checkpointing: true

deepspeed: deepspeed_configs/zero3_bf16.json

output_dir: ./full-ft-output
```

Launch with:
```bash
accelerate launch --num_processes 4 -m axolotl.cli.train config.yml
```

### Full fine-tune with FSDP

```yaml
base_model: meta-llama/Llama-3.1-8B-Instruct
adapter:

fsdp:
  - full_shard
  - auto_wrap
fsdp_config:
  fsdp_transformer_layer_cls_to_wrap: LlamaDecoderLayer
  fsdp_state_dict_type: SHARDED_STATE_DICT

# ... rest of training config
```

### Multiple datasets with mixing

```yaml
datasets:
  - path: data/instruct.jsonl
    type: alpaca
    split: train
  - path: data/chat.jsonl
    type: sharegpt
    split: train
  - path: tatsu-lab/alpaca
    type: alpaca
    split: train
```

Axolotl automatically concatenates and shuffles. You can also use HuggingFace Hub dataset names directly.

### Merging LoRA adapter after training

```bash
# Merge adapter back into base model
axolotl merge config.yml --lora-model-dir ./qlora-output
# Or with Python:
python -m axolotl.cli.merge_lora config.yml --lora_model_dir=./qlora-output
```

### Inference after training

```bash
# Interactive inference
axolotl inference config.yml --lora-model-dir ./qlora-output
```

Or serve with vLLM:
```bash
# After merging, serve the merged model
vllm serve ./merged-output --tensor-parallel-size 1

# Or serve the LoRA adapter directly (without merging)
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --enable-lora \
  --lora-modules my-lora=./qlora-output
```

## Configuration Reference

### Model settings

| Key | Values | Description |
|-----|--------|-------------|
| base_model | HF model ID or path | Base model to fine-tune |
| model_type | LlamaForCausalLM, etc. | Model class (usually auto-detected) |
| load_in_4bit | true/false | Load base model in 4-bit (for QLoRA) |
| load_in_8bit | true/false | Load base model in 8-bit |
| bf16 | true/false/auto | Use bfloat16 training |

### LoRA settings

| Key | Default | Description |
|-----|---------|-------------|
| adapter | qlora/lora/null | Adapter type (null = full fine-tune) |
| lora_r | 8 | LoRA rank (8, 16, 32, 64 common) |
| lora_alpha | 16 | LoRA alpha (typically 2x lora_r) |
| lora_dropout | 0.05 | Dropout on LoRA layers |
| lora_target_modules | varies | Which layers to apply LoRA to |

### Training settings

| Key | Default | Description |
|-----|---------|-------------|
| num_epochs | 1 | Number of training epochs |
| micro_batch_size | 1 | Per-device batch size |
| gradient_accumulation_steps | 1 | Steps before optimizer update |
| learning_rate | 2e-5 | Peak learning rate |
| optimizer | adamw_torch | adamw_torch, adamw_bnb_8bit, paged_adamw_8bit |
| lr_scheduler | cosine | cosine, linear, constant |
| warmup_ratio | 0.0 | Fraction of steps for warmup |
| weight_decay | 0.0 | L2 regularization |

### Performance & memory

| Key | Default | Description |
|-----|---------|-------------|
| flash_attention | false | Use Flash Attention 2 |
| sample_packing | false | Pack multiple samples into one sequence |
| gradient_checkpointing | false | Trade compute for memory |
| sequence_len | 2048 | Max sequence length |
| pad_to_sequence_len | false | Pad all sequences to max length |

### Dataset types

| Type | Format | Description |
|------|--------|-------------|
| alpaca | instruction/input/output | Standard instruct format |
| sharegpt | conversations array | Multi-turn chat |
| completion | text field | Raw text completion |
| context_qa | context/question/answer | QA with context |

## Pitfalls & Gotchas

- **VRAM estimation**: QLoRA 4-bit on Llama-3.1-8B needs ~16GB VRAM with sequence_len=2048 and micro_batch_size=1. Full fine-tune needs 4-8x more. Always start with micro_batch_size=1 and increase.
- **sample_packing + pad_to_sequence_len**: Use BOTH together. Sample packing alone without padding can cause training instability with some models.
- **Flash Attention install**: flash-attn requires CUDA and can be painful to install. Use `pip install axolotl[flash-attn]` or install flash-attn separately first. Requires Ampere+ GPU (A100, 3090, 4090, H100).
- **gradient_checkpointing_kwargs**: For modern PyTorch, set `use_reentrant: false` to avoid warnings and potential correctness issues.
- **Tokenizer padding side**: Axolotl handles this automatically, but if you write custom dataset code, ensure padding is on the right side for causal LMs.
- **Eval during training**: Add `val_set_size: 0.05` to split 5% of data for validation. Without this, you can't detect overfitting.
- **HuggingFace token**: For gated models (Llama, Mistral), set `HF_TOKEN` environment variable or run `huggingface-cli login`.
- **WandB integration**: Set `wandb_project` in config and ensure `wandb` is installed. Axolotl automatically logs to W&B if configured.
- **LoRA rank selection**: Higher rank (32, 64) = more capacity but more memory and slower. Start with r=16 for most tasks. Use r=64 only if r=16 underfits.
- **Learning rate**: QLoRA typically needs higher LR (1e-4 to 3e-4). Full fine-tune needs lower LR (1e-5 to 5e-5). Too high = instability, too low = underfitting.
- **Reproducibility**: Set `seed: 42` in config. Without a fixed seed, runs are not reproducible.
- **dataset_prepared_path**: Set this to cache tokenized datasets. Without it, Axolotl re-tokenizes every run, which is slow for large datasets.

## Compared To

| Feature | Axolotl | unsloth | TRL/SFTTrainer | torchtune | LLaMA-Factory |
|---------|---------|---------|----------------|-----------|---------------|
| Config-driven | YAML (primary) | Python | Python | YAML+Python | YAML+UI |
| LoRA/QLoRA | Yes | Yes (2x faster) | Yes | Yes | Yes |
| Full fine-tune | Yes | No | Yes | Yes | Yes |
| DeepSpeed | Yes | No | Yes | No | Yes |
| FSDP | Yes | No | Yes | Yes | Yes |
| Dataset formats | Many built-in | Manual | Manual | Manual | Many built-in |
| Sample packing | Yes | Yes | Yes | No | Yes |
| Flash Attention | Yes | Automatic | Manual | Yes | Yes |
| Multi-GPU | Yes | No (single GPU) | Yes | Yes | Yes |
| Speed (single GPU) | Good | Fastest | Good | Good | Good |
| Model support | Wide | Llama/Mistral/Gemma | Wide | Limited | Wide |
| Ease of use | Easy (YAML) | Easiest | Medium (code) | Medium | Easy (has UI) |
