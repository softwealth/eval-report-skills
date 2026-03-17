# MoE Inference Deployment Guide

> Practical guide for deploying Mixture-of-Experts models (Llama 4 Scout/Maverick, DeepSeek-V3, Mixtral) across inference engines. Covers engine selection, memory planning, and optimization techniques.

**Source:** EVAL #007 — The Great MoE Shift  
**Updated:** 2026-03-17  
**Category:** inference

---

## Key Concept: MoE Flips the Bottleneck

MoE models activate only a fraction of total parameters per token. The bottleneck shifts from **compute** to **memory capacity and bandwidth**. All experts must be memory-resident even though only a few activate per forward pass.

---

## Memory Requirements (Llama 4)

| Precision | Scout (109B total, 17B active) | Maverick (400B total, 17B active) |
|-----------|-------------------------------|----------------------------------|
| FP16      | ~220GB                        | ~800GB                           |
| FP8       | ~115GB                        | ~400GB                           |
| Q4 (GGUF) | ~62GB                        | ~230GB                           |
| Q2 (GGUF) | ~35GB                        | ~130GB                           |

---

## Engine Selection Matrix

### Server / Datacenter GPUs (H100, A100, MI300X)

| Engine | Llama 4 Scout (4×H100) | Best For | Key Feature |
|--------|----------------------|----------|-------------|
| **SGLang** (EP=4) | 5,100 tok/s | Max batch throughput | MoE-aware scheduling groups requests by expert affinity |
| **vLLM 0.8** (disagg prefill) | 4,500 tok/s | Balanced deploy | Disagg prefill gives 2.3× gain for MoE (vs 1.3× for dense) |
| **TensorRT-LLM** (FP8) | 4,800 tok/s | Max absolute perf | Highest raw throughput, hardest to deploy |
| **vLLM 0.8** (baseline TP) | 3,800 tok/s | Simple setup | Good default, easiest operational model |

**Recommendation:** SGLang for throughput-first APIs. vLLM for general production with best ecosystem.

### Consumer GPUs (RTX 4090, RTX 3090, Apple Silicon)

| Engine | Config | RTX 4090 Speed | Notes |
|--------|--------|----------------|-------|
| **ExLlamaV3** | 3.5bpw EXL3 | 18 tok/s | Best speed, experimental MoE support |
| **llama.cpp** | Q3_K_M full GPU | 14 tok/s | Needs ~42GB, dual GPU or partial offload |
| **llama.cpp** | Q4_K_M + expert offload | 11 tok/s | Fits 24GB GPU + 64GB RAM |
| **llama.cpp** | Q4_K_M (M3 Ultra 192GB) | 15 tok/s | Apple Silicon unified memory advantage |

**Recommendation:** llama.cpp with expert offloading for stability. ExLlamaV3 for max speed if you can tolerate experimental status.

---

## Critical Optimizations for MoE

### 1. Expert Offloading (Consumer)
Keep hot experts on GPU, cold experts in CPU RAM. For Llama 4 Scout (16 experts/layer, 1 active), top 2-3 experts cover 60-80% of activations.
- **Impact:** 3× speedup (3.5 → 11 tok/s on RTX 4090)
- **Supported by:** llama.cpp (b4830+), ExLlamaV3 (v0.3+)

### 2. Disaggregated Prefill (Server)
Separate prefill and decode workers. Prefill causes uneven expert load; isolating it prevents decode stalls.
- **Impact:** 2.3× throughput for MoE (vs 1.3× for dense)
- **Supported by:** vLLM 0.8, SGLang 0.5

### 3. Expert Parallelism (Server)
Distribute experts across GPUs instead of tensor parallelism. Better throughput at high batch sizes.
- **Impact:** 30% better throughput than TP for Scout
- **Trade-off:** Higher single-request latency
- **Supported by:** SGLang 0.5, vLLM 0.8

### 4. FP8 Quantization (Server)
Halves memory with minimal quality loss. Scout FP8 fits on 2×H100 instead of 4.
- **Impact:** ~1.4× throughput gain from reduced bandwidth
- **Quality:** >99% of FP16 output quality
- **Supported by:** vLLM, SGLang, TensorRT-LLM

### 5. Per-Expert Calibration (Consumer)
ExLlamaV3's EXL3 format calibrates each expert independently.
- **Impact:** Perplexity 7.82 (EXL3 3.5bpw) vs 8.14 (GGUF Q3_K_M)
- **Supported by:** ExLlamaV3 v0.3+

---

## Quick Start: Llama 4 Scout on 4×H100

### vLLM with disaggregated prefill:
```bash
pip install vllm>=0.8.0
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-4-Scout-17B-109B \
  --tensor-parallel-size 4 \
  --enable-disagg-prefill \
  --max-model-len 8192
```

### SGLang with expert parallelism:
```bash
pip install sglang>=0.5.0
python -m sglang.launch_server \
  --model meta-llama/Llama-4-Scout-17B-109B \
  --expert-parallel-size 4 \
  --mem-fraction-static 0.85
```

### llama.cpp with expert offloading (RTX 4090):
```bash
./llama-server \
  -m Llama-4-Scout-109B-Q4_K_M.gguf \
  -ngl 99 \
  --expert-offload 13 \
  -c 4096
# --expert-offload N: keep top N experts on GPU per layer
```

---

## Decision Tree

```
Is this for production serving?
├─ YES → How many concurrent users?
│   ├─ High (>32) → SGLang with expert parallelism
│   ├─ Medium (4-32) → vLLM with disagg prefill
│   └─ Low (1-3) → vLLM with tensor parallelism (lower latency)
└─ NO → What GPU do you have?
    ├─ 48+ GB VRAM (or Apple 192GB) → llama.cpp Q4_K_M, no offloading needed
    ├─ 24GB + 64GB+ RAM → llama.cpp Q4_K_M + expert offloading (11 tok/s)
    ├─ 24GB, want max speed → ExLlamaV3 3.5bpw (18 tok/s, experimental)
    └─ <24GB → Scout Q2_K or wait for better quantization
```

---

## Maverick (400B) — Reality Check

Maverick requires enterprise hardware. Minimum practical configs:
- **FP8:** 8×H100 80GB (~2,400 tok/s aggregate)
- **Q4:** 4×H100 or heroic consumer setup (1.5 tok/s on 2×4090+256GB RAM)
- **128 experts** → expert offloading hit rates drop significantly
- Not recommended for consumer/prosumer deployment

---

*EVAL — The AI Tooling Intelligence Report*  
*Subscribe: https://buttondown.com/ultradune*
