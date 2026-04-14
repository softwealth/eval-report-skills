# Changelog

All notable changes to the EVAL Skills repository will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-04-14

### Added
- `skills/agents/coding-agent-selection.md` — AI coding agent selection guide covering 10 agents across 4 architecture patterns (CodeAct, ACI, Plan-and-Execute, ReAct). Includes decision framework, model recommendations, MCP integration, and pitfalls. From EVAL #010.
- New `agents` category directory

## [0.1.0] - 2026-03-11

### Added
- Initial repository structure
- EVAL Skill Format Specification v1.0 (`SKILL_FORMAT.md`)
- Skill validation script (`scripts/validate_skill.py`)
- GitHub issue template for new skill requests
- 5 launch skills from EVAL Issue #1:
  - `skills/inference/vllm-serving.md` — vLLM v0.7.3 serving guide
  - `skills/data/qdrant-vector-db.md` — Qdrant v1.13.2 vector database guide
  - `skills/orchestration/langchain-lcel.md` — LangChain v0.3.x LCEL guide
  - `skills/tracking/wandb-tracking.md` — Weights & Biases experiment tracking guide
  - `skills/training/axolotl-finetuning.md` — Axolotl fine-tuning guide
- Category directory structure: inference, data, orchestration, tracking, training
- MIT License
- README with agent integration examples
