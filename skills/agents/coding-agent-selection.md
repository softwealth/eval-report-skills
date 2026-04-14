---
name: coding-agent-selection
version: 1.0.0
category: agents
trigger: 'when the user needs to choose an AI coding agent, set up an autonomous coding workflow, compare coding assistants, or integrate an AI agent into their development environment'
updated: 2026-04-14
confidence: tested
eval_issue: 10
---

# AI Coding Agent Selection Guide

## When to Use

- You need to choose between AI coding agents for your team or personal workflow
- You want to set up an autonomous coding assistant in your IDE or terminal
- You need to compare agents for a specific use case (refactoring, bug fixing, greenfield, migration)
- You want to understand the architectural tradeoffs between different agent approaches

## The Four Architecture Patterns

### 1. Code-as-Action (CodeAct)
**Agent:** OpenHands (formerly OpenDevin)
**Interface:** Web/Cloud | **License:** Open Source
**Best for:** Research, building custom agent platforms, flexible automation

The agent writes and executes code as its primary action mechanism rather than calling predefined tools. Maximum flexibility but wider failure surface.

```bash
# Install OpenHands
pip install openhands
# Or run via Docker (recommended)
docker pull ghcr.io/all-hands-ai/openhands:latest
docker run -p 3000:3000 ghcr.io/all-hands-ai/openhands:latest
```

### 2. Agent-Computer Interface (ACI)
**Agent:** SWE-agent (Princeton NLP)
**Interface:** Terminal/CLI | **License:** Open Source
**Best for:** Automated bug fixing, research on agent-tool interaction design

Purpose-built interfaces optimized for LLM agents. Key insight: the interface matters as much as the model.

```bash
# Install SWE-agent
pip install sweagent
# Run on a GitHub issue
sweagent run --model claude-3.5-sonnet --issue https://github.com/org/repo/issues/123
```

### 3. Plan-and-Execute
**Agents:** Plandex, Devin
**Best for:** Complex multi-file refactors, auditable changes, team environments

Creates detailed plans before executing. All changes sandboxed and reviewable.

```bash
# Install Plandex
curl -sL https://plandex.ai/install.sh | bash
# Start a task
plandex new "Refactor the auth module to use JWT tokens"
plandex tell "Use RS256 signing, add refresh token support"
# Review planned changes before applying
plandex diff
plandex apply
```

### 4. React-and-Iterate (Standard Tool-Use Loop)
**Agents:** Cline, Aider, Roo Code, Goose, GitHub Copilot, Cursor, Amazon Q
**Best for:** Most developers, most tasks — the mainstream architecture

Observe → reason → act → observe loop. Differentiated by interface, safety model, and extensibility.

#### Cline (IDE — VS Code)
```
# Install from VS Code marketplace: search "Cline"
# Configure: Cmd+Shift+P → "Cline: Open Settings"
# Set your API key (Claude recommended)
# Every action requires approval by default — safe for production codebases
```

#### Aider (Terminal)
```bash
# Install
pip install aider-chat
# Basic usage
cd your-project && aider
# Architect mode (two-model: planner + implementer)
aider --architect --model claude-3.5-sonnet --editor-model claude-3-haiku
# Autonomous mode (reduced human intervention)
aider --auto-commits --yes
```

#### Goose (Terminal — Block/Square)
```bash
# Install
pip install goose-ai
# Or via Homebrew
brew install block/tap/goose
# Run with custom toolkits
goose session --toolkit developer --toolkit github
```

## Decision Framework

| Your Situation | Recommended Agent | Why |
|---------------|-------------------|-----|
| Solo dev, terminal workflow | **Aider** | Git integration, architect mode, transparent LLM leaderboard |
| IDE user, wants safety controls | **Cline 4.0** | Approval-gated actions, MCP extensibility, multi-LLM support |
| Enterprise / AWS shop | **Amazon Q Developer** | Code transformation agents, deep AWS integration |
| Need async task delegation | **Devin 2.0** | Assign via Slack, cloud sandbox, works independently |
| Maximum customization (IDE) | **Roo Code** | Custom modes for different task types |
| Maximum customization (terminal) | **Goose** | Pluggable toolkit architecture |
| Research / building agent products | **OpenHands** | CodeAct architecture, most flexible and extensible |
| Complex multi-file with audit trail | **Plandex** | Plan-first, version-controlled sandbox |

## Model Recommendations by Agent

| Agent | Best Model | Budget Model | Notes |
|-------|-----------|--------------|-------|
| Aider (architect) | Claude Sonnet (architect) + Haiku (editor) | DeepSeek V3 | Two-model saves cost |
| Cline | Claude Sonnet | Llama 4 Scout (via Ollama) | MCP works with any model |
| OpenHands | Claude Sonnet | GPT-4o | CodeAct needs strong reasoning |
| SWE-agent | Claude Sonnet | GPT-4o | ACI design compensates for weaker models |
| Goose | Claude Sonnet | Any supported | Toolkit approach is model-agnostic |

## MCP Integration (2026 Standard)

Most agents now support Model Context Protocol for extensible tool access:

```json
// Example MCP server config (Cline, Roo Code, Aider)
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/project"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_TOKEN": "your-token" }
    }
  }
}
```

**MCP-compatible agents (as of April 2026):** Cline, Aider, Roo Code, Goose, Ollama, LM Studio, Cursor, Claude Desktop, ChatGPT, Gemini.

## Pitfalls

1. **Don't chase SWE-bench scores.** The benchmark measures isolated bug fixes in Python repos. Your workflow likely involves different tasks. Trial agents on your actual codebase.
2. **Start supervised, then relax.** Use Cline's approval mode or Aider's non-autonomous mode until you trust the agent with your codebase. Then gradually increase autonomy.
3. **Git is your safety net.** Always work in a branch. Both Aider and Plandex create automatic commits. Use them.
4. **MCP servers are the new npm packages.** Same supply chain risk. Only connect to trusted, audited MCP servers in production.
5. **Model costs add up.** A complex coding task can use 50-100K tokens. Aider's architect mode with a cheap editor model is the best cost optimization pattern.
6. **Context window matters more than speed.** Agents that can see more of your codebase make better decisions. Prefer models with 128K+ context for agent use.

## Verification

After setup, verify your agent works:

```bash
# For Aider
aider --message "Add a docstring to every function in main.py" --yes --dry-run

# For Cline: open VS Code, Cmd+Shift+P → "Cline: New Task"
# Ask: "List all TODO comments in this project"

# For SWE-agent
sweagent run --model claude-3.5-sonnet --repo /path/to/repo --issue "Add type hints to utils.py"
```

---

*From EVAL #010 — The AI Coding Agent Wars. Updated April 14, 2026.*
*EVAL is the weekly AI tooling intelligence report: [buttondown.com/ultradune](https://buttondown.com/ultradune)*
