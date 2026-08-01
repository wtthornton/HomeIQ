---
name: continuous-learning-v2
description: >-
  Instinct-based learning system that observes sessions via hooks, creates
  atomic instincts with confidence scoring, and evolves them into
  skills/commands/agents. v2.1 adds project-scoped instincts. Use when setting
  up continuous learning, tuning instincts, evolving learned behaviors, or
  managing project vs global instinct scope.
origin: ECC
version: 2.1.0
---

# Continuous Learning v2.1 - Instinct-Based Architecture

Turns Claude Code sessions into reusable knowledge via atomic **instincts** —
small learned behaviors with confidence scoring.

**v2.1** adds **project-scoped instincts** so framework conventions stay in the
project that taught them, while universal patterns can still be global.

## When to Activate

- Setting up automatic learning from Claude Code sessions
- Configuring instinct-based extraction via hooks
- Tuning confidence thresholds or reviewing instinct libraries
- Evolving instincts into skills, commands, or agents
- Managing project vs global scope / promoting instincts

## Instincts (summary)

An instinct is one trigger -> one action, with confidence (0.3-0.9), domain tags,
evidence, and scope (`project` default or `global`).

Full YAML example and pipeline diagram:
[references/architecture.md](references/architecture.md).

## Commands

| Command | Description |
|---------|-------------|
| `/instinct-status` | Show instincts (project + global) with confidence |
| `/evolve` | Cluster instincts into skills/commands; suggest promotions |
| `/instinct-export` | Export instincts (filterable by scope/domain) |
| `/instinct-import <file>` | Import instincts with scope control |
| `/promote [id]` | Promote project instincts to global scope |
| `/projects` | List known projects and instinct counts |

## Quick Start

1. **Hooks** — wire `observe.sh` on PreToolUse/PostToolUse (plugin or
   `~/.claude/skills/...` path). Full JSON:
   [references/operations.md](references/operations.md#quick-start-hooks).
2. **Dirs** — created on first use under `~/.claude/homunculus/` (global +
   per-project hashes).
3. **Operate** — `/instinct-status`, `/evolve`, `/promote` as needed.

## Companions

| Topic | File |
|-------|------|
| Architecture, instinct model, project detection, what's new | [references/architecture.md](references/architecture.md) |
| Hooks setup, config, scope, promotion, confidence, privacy | [references/operations.md](references/operations.md) |

Load companions only when configuring or debugging the learning system.
