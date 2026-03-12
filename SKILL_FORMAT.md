# EVAL Skill Format Specification

**Version: 1.0**

This document defines the format for EVAL Skill Pack files. All skill files in this repository MUST conform to this specification.

## Overview

An EVAL Skill file is a Markdown document with YAML frontmatter. It is designed to be:

1. **Human-readable** — engineers can read it as documentation
2. **Machine-parseable** — agents can extract structured data from it
3. **Self-contained** — everything needed to use the tool is in one file
4. **Opinionated** — it tells you when to use AND when NOT to use the tool

## File Structure

```
---
<YAML frontmatter>
---

# <Tool Name> v<Version>

## When to Use
## When NOT to Use
## Quick Start
## Common Patterns
## Configuration Reference
## Pitfalls & Gotchas
## Compared To
```

## YAML Frontmatter

The frontmatter is a YAML block delimited by `---` on its own line. All fields listed as REQUIRED must be present.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Tool name, lowercase, no spaces. Used as the canonical identifier. Example: `vllm`, `qdrant`, `langchain` |
| `version` | string | Version of the tool this skill covers. Use exact version (e.g., `0.7.3`) or range (e.g., `0.3.x`). |
| `category` | enum | One of: `inference`, `data`, `orchestration`, `tracking`, `training` |
| `trigger` | string | Natural-language description of when an agent should activate this skill. This is the primary field used for skill selection/routing. Should be a complete sentence starting with "when". |
| `updated` | date | ISO 8601 date when this skill was last verified. Format: `YYYY-MM-DD` |
| `confidence` | enum | One of: `tested` (verified by running code), `reviewed` (reviewed docs/source), `community` (community-contributed, not independently verified) |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `eval_issue` | integer | The EVAL newsletter issue number where this tool was covered |
| `tags` | list[string] | Additional tags for search/filtering. Example: `[gpu, serving, openai-compatible]` |
| `requires` | list[string] | System requirements. Example: `[cuda>=11.8, python>=3.10]` |
| `deprecated_by` | string | If this tool has been superseded, the name of the replacement |
| `min_skill_format` | string | Minimum skill format version required. Default: `1.0` |

### Example Frontmatter

```yaml
---
name: vllm
version: 0.7.3
category: inference
trigger: 'when the user needs to serve an LLM locally, deploy an OpenAI-compatible API, run batch inference at high throughput, or serve quantized/LoRA models'
updated: 2026-03-11
confidence: tested
eval_issue: 1
tags: [gpu, serving, openai-compatible, llm]
requires: [cuda>=11.8, python>=3.9]
---
```

## Markdown Body

### Title (REQUIRED)

```markdown
# <Tool Name> v<Version>
```

The H1 heading must match the tool name and version from frontmatter. Use the display name (can include capitalization), not the `name` field.

### When to Use (REQUIRED)

```markdown
## When to Use

- <scenario 1>
- <scenario 2>
...
```

A bullet list of specific scenarios where this tool is the right choice. Each bullet should describe a concrete use case, not a generic capability. Aim for 4-8 bullets.

**Good**: "You need to serve an LLM with an OpenAI-compatible HTTP API"
**Bad**: "You want to do inference"

### When NOT to Use (REQUIRED)

```markdown
## When NOT to Use

- <scenario> -> use <alternative> instead
- <scenario> -> use <alternative> instead
...
```

A bullet list of scenarios where a different tool is a better fit. Each bullet MUST include a specific alternative recommendation using the `->` arrow format. This is critical for agent routing — it prevents agents from selecting the wrong tool.

**Good**: "You just need a simple chat UI -> use Ollama or llama.cpp instead"
**Bad**: "This tool doesn't do everything"

### Quick Start (REQUIRED)

```markdown
## Quick Start

```bash
# Install
<install command>

# Basic usage
<minimal usage command>
```
```

The fastest path from zero to a working result. Must include:
1. Installation command (pip, docker, etc.)
2. Minimal usage command
3. Expected output or verification step

All commands must be copy-paste ready. No placeholder values that require user research — use sensible defaults or well-known model names.

### Common Patterns (REQUIRED)

```markdown
## Common Patterns

### <Pattern Name>

```<language>
<complete code example>
```
```

Real-world usage patterns that go beyond the quick start. Each pattern should be a named subsection (H3) with a complete, runnable code example. Include 3-6 patterns covering the most common use cases.

### Configuration Reference (REQUIRED)

```markdown
## Configuration Reference

| Flag/Option | Default | Description |
|-------------|---------|-------------|
| <flag> | <default> | <description> |
```

A table of the most important configuration options. Cover:
- The 10-15 most commonly used flags/options
- Include default values (or "required" if no default)
- Keep descriptions concise but precise

### Pitfalls & Gotchas (REQUIRED)

```markdown
## Pitfalls & Gotchas

- **<Short title>**: <Explanation and workaround>
```

Things that will waste an engineer's (or agent's) time if they don't know about them. Each gotcha must include:
1. A bold title (the symptom or mistake)
2. Why it happens
3. How to fix or avoid it

Aim for 5-10 gotchas. Focus on non-obvious issues that aren't in the README.

### Compared To (REQUIRED)

```markdown
## Compared To

| Feature | <This Tool> | <Alt 1> | <Alt 2> | <Alt 3> |
|---------|-------------|---------|---------|---------|
| <feature> | <value> | <value> | <value> | <value> |
```

A feature comparison table against 2-4 alternatives. Compare on dimensions that matter for the decision (not marketing features). Be honest — if an alternative is better at something, say so.

## File Naming

Skill files must be named: `<tool-name>-<focus>.md`

- Use lowercase with hyphens
- `<tool-name>` matches the `name` field in frontmatter
- `<focus>` briefly describes what aspect of the tool is covered

Examples:
- `vllm-serving.md`
- `qdrant-vector-db.md`
- `langchain-lcel.md`
- `wandb-tracking.md`
- `axolotl-finetuning.md`

## File Placement

Skills must be placed in the correct category subdirectory:

```
skills/
├── inference/       # category: inference
├── data/            # category: data
├── orchestration/   # category: orchestration
├── tracking/        # category: tracking
└── training/        # category: training
```

The subdirectory must match the `category` field in the frontmatter.

## Validation

All skill files can be validated using:

```bash
python scripts/validate_skill.py <path-to-skill-file>
```

The validator checks:
- Valid YAML frontmatter with all required fields
- Correct field types and enum values
- Presence of all required sections
- File naming convention
- Category/directory consistency
- Date format
- Non-empty content sections

## Versioning

This format specification follows semantic versioning:
- **Major** (breaking): Required fields added, section structure changed
- **Minor** (compatible): Optional fields added, clarifications
- **Patch**: Typo fixes, examples updated

Current version: **1.0**
