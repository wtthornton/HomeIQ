# OpenAI Model Research: GPT-5.2 vs Mini, 5.2 vs 5.2-Codex

**Date:** February 2026  
**Purpose:** Whether to use gpt-5.2 for some/all mini use cases, and whether to use gpt-5.2-codex vs gpt-5.2 for better quality.

---

## 1. Model roles (OpenAI docs)

| Model | Best for | Price (Standard, per 1M tokens) |
|-------|----------|---------------------------------|
| **gpt-5.2** | Complex reasoning, broad world knowledge, code-heavy or multi-step agentic tasks | Input $1.75, Output $14 |
| **gpt-5.2-pro** | Tough problems that need harder thinking | Input $21, Output $168 |
| **gpt-5.2-codex** | Interactive coding products; full spectrum of coding tasks; long-horizon agentic coding | Input $1.75, Output $14 |
| **gpt-5-mini** | Cost-optimized reasoning and chat; well-defined tasks; balances speed, cost, capability | Input $0.25, Output $2 |
| **gpt-5-nano** | High-throughput, simple instruction-following or classification | Input $0.05, Output $0.40 |
| **gpt-4o-mini** | (Current default for many services) | Input $0.15, Output $0.60 |

Sources: [GPT-5.2](https://developers.openai.com/api/docs/models/gpt-5.2), [GPT-5.2-Codex](https://developers.openai.com/api/docs/models/gpt-5.2-codex), [GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini), [Latest model guide](https://developers.openai.com/api/docs/guides/latest-model), [Pricing](https://developers.openai.com/api/docs/pricing).

---

## 2. gpt-5.2 vs gpt-5.2-codex (quality)

- **Same price:** $1.75 / $14 per 1M tokens.
- **gpt-5.2:** "Best model for coding and agentic tasks across industries"; general-purpose flagship.
- **gpt-5.2-codex:** "Upgraded version of GPT-5.2 optimized for agentic coding in Codex or similar environments"; "most intelligent coding model optimized for long-horizon, agentic coding tasks."

**Recommendation:** Use **gpt-5.2-codex** for the **ha-ai-agent-service** (main chat + YAML generation + tool use). Our flow is agentic, code/YAML-heavy, and multi-step — which matches Codex’s target. Keep **gpt-5.2** as a valid alternative if you prefer the general-purpose flagship; Codex is the coding-specialized variant for better quality on code/agent tasks.

---

## 3. Where to use 5.2 (or 5.2-codex) vs mini

**Use gpt-5.2 or gpt-5.2-codex only for:**

- **ha-ai-agent-service** — main chat, YAML generation, enhancements, tool use. Already on gpt-5.2; consider switching to **gpt-5.2-codex** for best quality on automation/YAML and agentic behavior.

**Do not move all workloads to 5.2** — cost would scale poorly (5.2 is ~7× more expensive than gpt-5-mini on input, ~7× on output).

**Use a “mini” tier for:**

- Intent planning (ai-automation-service-new)
- Entity extraction / query (ai-query-service)
- Proactive prompt generation (proactive-agent-service)
- Device name suggestions (device-intelligence-service)
- Evaluation LLM judge (shared evaluation)

---

## 4. gpt-4o-mini vs gpt-5-mini for “mini” workloads

- **gpt-4o-mini:** $0.15 in / $0.60 out. Current default for automation, query, proactive, device-intelligence, evaluation.
- **gpt-5-mini:** $0.25 in / $2 out. "Faster, cost-efficient version of GPT-5 for well-defined tasks"; supports reasoning; better instruction following and accuracy than 4o-mini.

**Recommendation:**  
- **Upgrade from gpt-4o-mini to gpt-5-mini** for services where quality matters and volume is moderate: **ai-automation-service-new** (intent/template selection), **ai-query-service** (entity extraction), **proactive-agent-service** (prompt generation). Expect better plan/entity/prompt quality for a modest cost increase.  
- **Keep gpt-4o-mini** (or use gpt-5-mini) for: **device-intelligence-service** (name suggestions — high volume, simple task) and **evaluation LLM judge** (rubric scoring — well-defined, many runs). Choose gpt-5-mini if you want better judge consistency and can absorb the higher output cost.

---

## 5. Summary table (recommended)

| Service | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| ha-ai-agent-service | gpt-5.2 | **gpt-5.2-codex** | Best quality for agentic, code/YAML-heavy flows; same price as 5.2. |
| ai-automation-service-new | gpt-4o-mini | **gpt-5-mini** | Better intent/template quality; well-defined task, moderate cost. |
| ai-query-service | gpt-4o-mini | **gpt-5-mini** | Better entity extraction; well-defined task. |
| proactive-agent-service | gpt-4o-mini | **gpt-5-mini** | Better prompt generation. |
| device-intelligence-service | gpt-4o-mini | **gpt-4o-mini** or gpt-5-mini | Keep 4o-mini for cost; use 5-mini if name quality is priority. |
| Evaluation (LLM judge) | gpt-4o-mini | **gpt-4o-mini** or gpt-5-mini | 4o-mini for cost; 5-mini for better judge consistency. |

---

## 6. Implementation notes

- **ha-ai-agent:** Set `OPENAI_MODEL=gpt-5.2-codex` (or keep `gpt-5.2`). Confirm reasoning params (e.g. `reasoning_effort`) are supported for codex if used.
- **Other services:** Set `openai_model=gpt-5-mini` (or env equivalent) where recommended; leave as `gpt-4o-mini` where cost is the priority.
- **Pricing:** 5.2 and 5.2-codex are same price; gpt-5-mini is ~1.7× 4o-mini input and ~3.3× 4o-mini output — monitor usage after switching.

---

## 7. Changes applied (February 2026)

- **ha-ai-agent-service** `config.py`: default `openai_model` set to `gpt-5.2-codex`; docs (README, ENVIRONMENT_VARIABLES, DEPLOYMENT, API_DOCUMENTATION, PERFORMANCE, MONITORING, ERROR_HANDLING) updated.
- **ai-automation-service-new** `config.py`: default `openai_model` set to `gpt-5-mini`.
- **ai-query-service** `config.py`: default `openai_model` set to `gpt-5-mini`.
- **proactive-agent-service** `config.py`: default `openai_model` set to `gpt-5-mini`.
- **device-intelligence-service** and **evaluation LLM judge**: left at gpt-4o-mini per recommendation (cost vs quality).
