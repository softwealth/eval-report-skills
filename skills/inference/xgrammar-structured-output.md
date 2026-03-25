# XGrammar Structured Output — Near-Zero Overhead JSON Generation

**EVAL #008** | March 25, 2026 | Skill Pack: Inference
**Tags:** structured-output, json, xgrammar, vllm, sglang, constrained-decoding

---

## Overview

XGrammar is the structured generation engine that makes grammar-constrained decoding essentially free. It's now the default backend in both vLLM (v0.7+) and SGLang (v0.4+), replacing the older `outlines` library. Combined with SGLang's jump-forward decoding, structured output overhead drops to <3% of unconstrained throughput.

## When to Use This

- You need guaranteed valid JSON from LLM inference
- You're building agent systems that output tool calls or API payloads
- You're generating structured data (configs, schemas, forms) from natural language
- You want grammar constraints without paying a throughput tax

## Key Concepts

### Adaptive Token Mask Caching

XGrammar partitions the vocabulary into two categories:

1. **Context-Independent (CI) tokens (~95% of vocab)**: Validity depends only on the last few characters, not the full parse state. Masks are **precomputed at grammar compile time**.
2. **Context-Dependent (CD) tokens (~5% of vocab)**: Must be checked dynamically at each decode step.

This reduces per-step computation from O(V) to O(CD), where CD << V.

### Jump-Forward Decoding (SGLang)

Orthogonal to XGrammar's mask efficiency. When the grammar FSM reaches a state with only one valid transition (deterministic tokens like field names, `{`, `}`, `:`), the system **skips the LLM forward pass entirely** and appends the tokens directly. Eliminates 40-60% of LLM calls for known JSON schemas.

## Performance Numbers

| Metric | XGrammar | Outlines (previous) |
|--------|----------|-------------------|
| Grammar compilation | <10ms | >5 seconds |
| Per-token mask gen (CI) | <1μs | >500μs |
| End-to-end overhead | <3% throughput loss | 30-50% throughput loss |
| Compilation speedup vs llama.cpp | 220x | — |

## Setup

### vLLM (Default since v0.7)

XGrammar is the default structured output backend. No extra installation needed.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")

# JSON schema constraint
response = client.chat.completions.create(
    model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
    messages=[{"role": "user", "content": "Extract: John is 30 and lives in NYC"}],
    response_format={
        "type": "json_schema",
        "json_schema": {
            "name": "person",
            "schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "age": {"type": "integer"},
                    "city": {"type": "string"}
                },
                "required": ["name", "age", "city"]
            }
        }
    }
)
# Output: {"name": "John", "age": 30, "city": "NYC"}
```

### SGLang (with Jump-Forward)

```python
import sglang as sgl

@sgl.function
def extract_person(s, text):
    s += sgl.user(f"Extract person info from: {text}")
    s += sgl.assistant(sgl.gen(
        "result",
        regex=r'\{"name": "[^"]+", "age": \d+, "city": "[^"]+"\}'
    ))

# Jump-forward automatically detects and skips deterministic tokens
state = extract_person.run(text="John is 30 and lives in NYC")
print(state["result"])
```

### Regex Constraints

```python
# vLLM with regex
response = client.chat.completions.create(
    model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
    messages=[{"role": "user", "content": "Generate an email address for John Smith"}],
    extra_body={
        "guided_regex": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    }
)
```

### BNF Grammar Constraints

```python
# Custom grammar for specific output formats
response = client.chat.completions.create(
    model="meta-llama/Llama-4-Scout-17B-16E-Instruct",
    messages=[{"role": "user", "content": "Generate a SQL SELECT statement"}],
    extra_body={
        "guided_grammar": """
        root ::= "SELECT " columns " FROM " table where_clause
        columns ::= column ("," column)*
        column ::= [a-zA-Z_]+
        table ::= [a-zA-Z_]+
        where_clause ::= "" | " WHERE " condition
        condition ::= column " = " value
        value ::= "'" [a-zA-Z0-9_]+ "'"
        """
    }
)
```

## Architecture: How XGrammar Works

```
JSON Schema  →  EBNF Grammar  →  Character-level Automaton  →  Token-level Bitmasks
                                                                      ↓
                                                            Adaptive Caching Layer
                                                           ┌─────────┬────────────┐
                                                           │ CI Mask  │  CD Check   │
                                                           │ (cached) │ (per-step)  │
                                                           │  ~95%    │   ~5%       │
                                                           └─────────┴────────────┘
```

1. **Grammar compilation** (<10ms): JSON Schema → EBNF → pushdown automaton
2. **Token classification**: Split vocabulary into CI and CD sets
3. **Precomputation**: Build bitmasks for all CI tokens across all grammar states
4. **Runtime**: At each decode step, retrieve precomputed CI mask + compute CD tokens
5. **Jump-forward** (SGLang only): Check if FSM state is deterministic, skip LLM if so

## Practical Tips

1. **Complex schemas are fine**: XGrammar handles nested objects, arrays, enums, optional fields. Compilation stays under 10ms for typical schemas.

2. **Batch-friendly**: Structured output doesn't break continuous batching. Different requests can have different schemas within the same batch.

3. **Don't over-constrain**: Let the model decide values while constraining structure. Too-tight regex patterns kill output quality.

4. **Prefer JSON Schema over regex**: JSON Schema gives XGrammar more optimization opportunities (deterministic field names → more jump-forward skipping).

5. **Monitor accuracy, not just speed**: Structured output guarantees valid JSON, not correct content. Always validate semantic correctness separately.

## Version Compatibility

| Engine | Min Version | XGrammar | Jump-Forward |
|--------|-------------|----------|--------------|
| vLLM | v0.6.4+ | ✅ Default | ❌ |
| vLLM | v0.7.0+ | ✅ Default | ❌ |
| vLLM | v0.8.3 | ✅ Default | ❌ |
| SGLang | v0.4.0+ | ✅ Default | ✅ |
| SGLang | v0.5.2 | ✅ Default | ✅ (enhanced) |

## References

- XGrammar paper: arxiv.org/abs/2411.15100
- XGrammar GitHub: github.com/mlc-ai/xgrammar
- SGLang compressed FSM: lmsys.org/blog/2024-02-05-compressed-fsm/
- vLLM structured output docs: docs.vllm.ai/en/latest/features/structured_outputs.html
- EVAL #008 deep-dive: buttondown.com/ultradune

---

*EVAL Skill Pack — Machine-readable by AI agents, useful for humans.*
*github.com/softwealth/eval-report-skills*
