<p align="center">
  <strong>EVAL Skills</strong><br>
  <em>Machine-readable tool intelligence for AI agents and ML engineers</em>
</p>

<p align="center">
  <a href="https://github.com/eval-report/skills/actions"><img src="https://img.shields.io/github/actions/workflow/status/eval-report/skills/validate.yml?label=skill%20validation&style=flat-square" alt="Validation"></a>
  <a href="https://github.com/eval-report/skills/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="License"></a>
  <a href="https://github.com/eval-report/skills/tree/main/skills"><img src="https://img.shields.io/badge/skills-5+-green?style=flat-square" alt="Skills"></a>
  <a href="https://evalreport.com"><img src="https://img.shields.io/badge/newsletter-EVAL-orange?style=flat-square" alt="Newsletter"></a>
</p>

---

# EVAL Skill Packs

**We eval the tools so you can ship the models.**

EVAL Skill Packs are structured, machine-readable files that teach AI agents how to use ML/AI tools correctly. Each skill file contains everything an agent (or engineer) needs: when to use a tool, when NOT to use it, quick start commands, common patterns, configuration reference, pitfalls, and comparisons to alternatives.

Think of them as man pages for the AI age — but opinionated, practical, and designed to be consumed by both humans reading docs AND agents executing tasks.

## Why This Exists

AI coding agents are great at writing code. They're terrible at making tooling decisions. Ask an agent to "set up LLM serving" and you'll get a hallucinated config from 2023. These skill files fix that by giving agents:

- **Current, tested knowledge** — every skill is validated against the actual tool
- **Decision logic** — explicit "when to use" and "when NOT to use" triggers
- **Copy-paste patterns** — working code snippets, not pseudocode
- **Gotcha awareness** — the pitfalls that waste hours when you hit them

## Quick Start

### For Humans

Browse the [`skills/`](./skills) directory. Each `.md` file is a self-contained guide to one tool:

```
skills/
├── inference/          # LLM serving & inference engines
│   └── vllm-serving.md
├── data/               # Vector DBs, data pipelines, storage
│   └── qdrant-vector-db.md
├── orchestration/      # LLM frameworks, chaining, agents
│   └── langchain-lcel.md
├── tracking/           # Experiment tracking, observability
│   └── wandb-tracking.md
└── training/           # Fine-tuning, training frameworks
    └── axolotl-finetuning.md
```

### For AI Agents

Skill files are designed for agent ingestion. Each file has YAML frontmatter with structured metadata followed by markdown content:

```yaml
---
name: vllm
version: 0.7.3
category: inference
trigger: 'when the user needs to serve an LLM locally...'
updated: 2026-03-11
confidence: tested
eval_issue: 1
---
```

**Agent integration pattern:**

```python
import yaml
import pathlib

def load_skills(skills_dir: str = "skills") -> list[dict]:
    """Load all EVAL skill files into a list of structured dicts."""
    skills = []
    for path in pathlib.Path(skills_dir).rglob("*.md"):
        text = path.read_text()
        if text.startswith("---"):
            _, frontmatter, body = text.split("---", 2)
            meta = yaml.safe_load(frontmatter)
            meta["content"] = body.strip()
            meta["path"] = str(path)
            skills.append(meta)
    return skills

def find_skill(skills: list[dict], query: str) -> dict | None:
    """Find the most relevant skill for a user query.
    
    In production, use embedding similarity against the 'trigger' field.
    Simple keyword matching shown here for clarity.
    """
    query_lower = query.lower()
    for skill in skills:
        trigger = skill.get("trigger", "").lower()
        if any(word in trigger for word in query_lower.split()):
            return skill
    return None

# Usage
skills = load_skills("skills")
skill = find_skill(skills, "I need to serve a Llama model")
if skill:
    print(f"Use {skill['name']} v{skill['version']}")
    print(skill["content"])
```

**Using the trigger field for tool selection:**

The `trigger` field is a natural-language description of when this tool is the right choice. Agents should match user intent against trigger fields to select the right skill. This works with:

- **Embedding similarity** — embed the trigger and the user's request, pick highest cosine similarity
- **LLM routing** — pass all triggers to a cheap model, ask it to pick the best match
- **Keyword matching** — simple but effective for explicit tool mentions

### Fetching Skills at Runtime

```python
import urllib.request
import yaml

RAW_BASE = "https://raw.githubusercontent.com/eval-report/skills/main/skills"

def fetch_skill(category: str, filename: str) -> dict:
    """Fetch a single skill file from GitHub."""
    url = f"{RAW_BASE}/{category}/{filename}"
    text = urllib.request.urlopen(url).read().decode()
    _, frontmatter, body = text.split("---", 2)
    meta = yaml.safe_load(frontmatter)
    meta["content"] = body.strip()
    return meta

# Fetch the vLLM skill on-demand
skill = fetch_skill("inference", "vllm-serving.md")
```

## Skill File Format

Every skill file follows the [EVAL Skill Format Specification](./SKILL_FORMAT.md). The key components:

| Section | Purpose |
|---------|---------|
| **YAML Frontmatter** | Machine-readable metadata: name, version, category, trigger, confidence |
| **When to Use** | Bullet list of scenarios where this tool is the right choice |
| **When NOT to Use** | Bullet list of scenarios with better alternatives (with recommendations) |
| **Quick Start** | Minimal steps to get from zero to working — copy-paste ready |
| **Common Patterns** | Real-world usage patterns with complete code examples |
| **Configuration Reference** | Table of flags/options/parameters with defaults |
| **Pitfalls & Gotchas** | Things that will waste your time if you don't know about them |
| **Compared To** | Feature matrix against alternatives |

See [SKILL_FORMAT.md](./SKILL_FORMAT.md) for the complete specification.

## Validating Skills

Use the validation script to check skill files against the format spec:

```bash
# Validate a single skill
python scripts/validate_skill.py skills/inference/vllm-serving.md

# Validate all skills
python scripts/validate_skill.py skills/

# Strict mode (warnings become errors)
python scripts/validate_skill.py --strict skills/
```

Requirements: Python 3.10+, `pyyaml`

```bash
pip install pyyaml
```

## Categories

| Category | Directory | What's in it |
|----------|-----------|-------------|
| **Inference** | `skills/inference/` | LLM serving engines, inference optimization, model deployment |
| **Data** | `skills/data/` | Vector databases, data pipelines, embeddings, storage |
| **Orchestration** | `skills/orchestration/` | LLM frameworks, prompt chaining, agent frameworks |
| **Tracking** | `skills/tracking/` | Experiment tracking, LLM observability, monitoring |
| **Training** | `skills/training/` | Fine-tuning frameworks, training pipelines, RLHF |

## Contributing

We welcome skill contributions! Here's how:

### Writing a New Skill

1. **Fork this repo**
2. **Pick a tool** that ML engineers actually use in production
3. **Copy the template**: `cp SKILL_FORMAT.md skills/<category>/your-tool.md`
4. **Follow the format spec** — every section matters
5. **Test your examples** — all code snippets must work
6. **Submit a PR**

### Quality Bar

Every skill must meet these criteria:

- [ ] Valid YAML frontmatter with all required fields
- [ ] `trigger` field accurately describes when to use the tool
- [ ] "When NOT to Use" section includes specific alternatives
- [ ] Quick Start goes from `pip install` to working output in <5 commands
- [ ] Code examples are complete and runnable (no `...` placeholders)
- [ ] Configuration table covers the 10 most-used options
- [ ] Pitfalls section includes at least 3 non-obvious gotchas
- [ ] Comparison table includes at least 2 alternatives
- [ ] Passes `python scripts/validate_skill.py --strict`

### Requesting a Skill

Don't see the tool you need? [Open a skill request](https://github.com/eval-report/skills/issues/new?template=new-skill-request.md).

## About EVAL

EVAL is **The AI Tooling Intelligence Report** — a weekly newsletter for ML engineers making tooling decisions. We systematically track, test, and evaluate the tools that AI builders use in production. No hype. No sponsored reviews. Just honest, opinionated analysis.

- **Newsletter**: [evalreport.com](https://evalreport.com)
- **Twitter/X**: [@evalreport](https://twitter.com/evalreport)
- **GitHub**: [eval-report](https://github.com/eval-report)

Each skill in this repo corresponds to a tool covered in the newsletter. The `eval_issue` field in the frontmatter links back to the newsletter issue where that tool was evaluated.

## License

MIT — see [LICENSE](./LICENSE). Use these skills in your agents, products, and workflows. Attribution appreciated but not required.

---

<p align="center">
  <em>Built by EVAL — we eval the tools so you can ship the models.</em>
</p>
