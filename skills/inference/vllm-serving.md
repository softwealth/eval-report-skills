---
name: vllm
version: 0.7.3
category: inference
trigger: 'when the user needs to serve an LLM locally, deploy an OpenAI-compatible API, run batch inference at high throughput, or serve quantized/LoRA models'
updated: 2026-03-11
confidence: tested
eval_issue: 1
---

# vLLM v0.7.3

## When to Use

- You need to serve an LLM with an OpenAI-compatible HTTP API
- You want high-throughput batch inference with PagedAttention
- You need to serve quantized models (FP8, GPTQ, AWQ) to fit on fewer GPUs
- You want to serve multiple LoRA adapters on a single base model
- You need tensor-parallel serving across multiple GPUs
- You want prefix caching for repeated prompt prefixes (e.g., system prompts)

## When NOT to Use

- You just need a simple chat UI -> use Ollama or llama.cpp instead
- You need edge/mobile inference -> use llama.cpp or MLC-LLM instead
- You only have CPU -> use llama.cpp with GGUF quantization instead
- You want a managed API -> use Together AI, Fireworks, or direct provider APIs
- You need training or fine-tuning -> use Axolotl, torchtune, or unsloth instead

## Quick Start

```bash
# Install
pip install vllm==0.7.3

# Serve a model (one command)
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.90

# Test it (OpenAI-compatible)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 256
  }'
```

## Common Patterns

### Python client with OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed",  # vLLM doesn't require a key by default
)

response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain PagedAttention in one paragraph."},
    ],
    max_tokens=512,
    temperature=0.7,
)
print(response.choices[0].message.content)
```

### Offline batch inference

```python
from vllm import LLM, SamplingParams

llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct",
    tensor_parallel_size=2,
    gpu_memory_utilization=0.90,
)

sampling_params = SamplingParams(
    temperature=0.0,
    max_tokens=512,
    top_p=0.95,
    stop=["\n\n"],
)

prompts = [
    "Summarize the theory of relativity:",
    "Write a Python function to sort a list:",
    "Explain quantum computing:",
]

outputs = llm.generate(prompts, sampling_params)
for output in outputs:
    print(output.outputs[0].text)
```

### Serving with LoRA adapters

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --enable-lora \
  --lora-modules my-adapter=./path/to/lora/adapter \
  --max-lora-rank 64
```

Then request with the adapter name as the model:

```python
response = client.chat.completions.create(
    model="my-adapter",
    messages=[{"role": "user", "content": "Hello"}],
)
```

### Serving quantized models

```bash
# AWQ quantized model
vllm serve TheBloke/Llama-2-13B-AWQ \
  --quantization awq \
  --gpu-memory-utilization 0.90

# GPTQ quantized model
vllm serve TheBloke/Llama-2-13B-GPTQ \
  --quantization gptq

# FP8 quantized model
vllm serve neuralmagic/Llama-3.1-8B-Instruct-FP8 \
  --quantization fp8
```

### Enabling prefix caching

```bash
vllm serve meta-llama/Llama-3.1-8B-Instruct \
  --enable-prefix-caching
```

This dramatically speeds up workloads where many requests share the same system prompt or prefix.

## Configuration Reference

| Flag | Default | Description |
|------|---------|-------------|
| --model | required | HuggingFace model ID or local path |
| --tensor-parallel-size | 1 | Number of GPUs for tensor parallelism |
| --gpu-memory-utilization | 0.90 | Fraction of GPU memory to use (0.0-1.0) |
| --max-model-len | auto | Maximum sequence length |
| --host | localhost | Bind address |
| --port | 8000 | Bind port |
| --quantization | None | awq, gptq, fp8, squeezellm |
| --enable-lora | false | Enable LoRA adapter serving |
| --lora-modules | None | name=path pairs for LoRA adapters |
| --max-lora-rank | 16 | Max LoRA rank |
| --enable-prefix-caching | false | Enable automatic prefix caching |
| --dtype | auto | Data type: auto, float16, bfloat16, float32 |
| --max-num-seqs | 256 | Max number of sequences per iteration |
| --api-key | None | API key for authentication |
| --served-model-name | None | Override the model name in the API |

SamplingParams reference:

| Parameter | Default | Description |
|-----------|---------|-------------|
| temperature | 1.0 | Sampling temperature |
| top_p | 1.0 | Nucleus sampling |
| top_k | -1 | Top-k sampling (-1 = disabled) |
| max_tokens | 16 | Maximum tokens to generate |
| stop | None | Stop strings or token IDs |
| presence_penalty | 0.0 | Presence penalty |
| frequency_penalty | 0.0 | Frequency penalty |
| best_of | 1 | Number of sequences to generate, return best |

## Pitfalls & Gotchas

- **OOM on large models**: Lower --gpu-memory-utilization to 0.85 or reduce --max-model-len. vLLM pre-allocates KV cache at startup.
- **Tokenizer trust**: Many models require --trust-remote-code. Add it if you get tokenizer errors.
- **max-model-len too high**: vLLM tries to use the model's full context window by default. If you don't need 128K context, set --max-model-len 4096 to save GPU memory.
- **Slow first request**: The first request triggers CUDA graph compilation. Subsequent requests are fast.
- **LoRA + quantization**: Not all quantization methods are compatible with LoRA serving. AWQ + LoRA works; GPTQ + LoRA support is limited.
- **Model not found**: vLLM downloads from HuggingFace. Set HF_TOKEN env var for gated models (Llama, Mistral, etc.).
- **Multi-GPU but single GPU used**: Ensure --tensor-parallel-size matches the number of GPUs you want. Check CUDA_VISIBLE_DEVICES.
- **Port already in use**: Default port 8000 conflicts with many services. Use --port 8080 or similar.

## Compared To

| Feature | vLLM | llama.cpp | TGI | Ollama |
|---------|------|-----------|-----|--------|
| Throughput | Highest (PagedAttention) | Good | High | Moderate |
| OpenAI API compat | Yes | Yes (server) | No (own API) | Yes |
| Quantization | FP8/AWQ/GPTQ | GGUF (Q4/Q5/Q8) | AWQ/GPTQ | GGUF |
| Multi-GPU | Tensor parallel | Limited | Tensor parallel | No |
| LoRA serving | Yes (multi) | Yes (single) | Yes | No |
| CPU inference | No | Yes (primary) | No | Yes (via llama.cpp) |
| Ease of setup | Medium | Easy | Medium | Easiest |
| Prefix caching | Yes | No | No | No |
