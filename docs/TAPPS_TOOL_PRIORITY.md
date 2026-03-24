# TappsMCP Tool Priority for HomeIQ

**Last Updated:** March 23, 2026  
**Purpose:** Recommended tool order and rationale for using TappsMCP in the HomeIQ project

**MCP setup:** In this project TappsMCP is provided by **tapps-mcp** via direct stdio (not the legacy Docker MCP Toolkit gateway). Use `.cursor/mcp.json` (IDE) and `.mcp.json` (headless/auto-bugfix) with the `tapps-mcp` entry. Tools are exposed as `mcp__tapps-mcp__tapps_*`. See [.cursor/MCP_SETUP_INSTRUCTIONS.md](../.cursor/MCP_SETUP_INSTRUCTIONS.md).

---

## Quick reference: tool order

Use this order when running TappsMCP tools in HomeIQ:

| # | When | Tool | Notes |
|---|------|------|--------|
| 1 | **Every session start** | `tapps_session_start` | First call; provides server + project context. |
| 2 | First session or when unsure | `tapps_project_profile` | Detects tech stack and multi-domain structure. |
| 3 | If config seems wrong | `tapps_doctor` | Validates MCP config, binaries, hooks. |
| 4 | **Before using a library** | `tapps_lookup_docs(library='...')` | Prevents wrong API usage (FastAPI, InfluxDB, aiohttp, etc.). |
| 5 | Before changing/removing a public API | `tapps_impact_analysis(file_path='...')` | Use for shared libs and Tier 1 services. |
| 6 | Domain decisions (security, testing, API, DB) | `tapps_consult_expert(question='...')` | RAG-backed guidance. |
| 7 | **After each Python file edit** | `tapps_quick_check(file_path='...')` | Fast score + gate + basic security. |
| 8 | **Before declaring done (multi-file)** | `tapps_validate_changed()` | Score + gate + security on all changed files. |
| 9 | Before done (per-file gate) | `tapps_quality_gate(file_path='...')` | Enforce preset; critical services need ≥80. |
| 10 | Auth/API/secrets/input handling | `tapps_security_scan(file_path='...')` | Bandit + secret detection. |
| 11 | After editing Docker/compose/infra | `tapps_validate_config(file_path='...')` | WebSocket/MQTT/InfluxDB best practices. **Note:** Root `docker-compose.yml` uses Compose **`include:`** only (no top-level `services:`) — validators may report a false “missing services” finding; validate **`domains/<group>/compose.yml`** files instead. |
| 12 | **Final step before "done"** | `tapps_checklist(task_type='...')` | Verifies no required step was skipped. |

**Optional / situational:** `tapps_dependency_scan` (releases, new deps), `tapps_dependency_graph` (refactors, import issues), `tapps_dead_code` (refactors), `tapps_report` (summaries), `tapps_memory` (cross-session decisions), `tapps_session_notes` (session-only notes).

---

## Overview

This document defines the **priority order** for TappsMCP tools when working on HomeIQ, and explains **why** this order is recommended. Use it as a reference for AI assistants and developers integrating TappsMCP into their workflow.

---

## Project Context

HomeIQ has characteristics that shape which tools matter most:

| Factor | Implication |
|--------|-------------|
| **~58 containers / 62 Compose services** | Batch validation (`tapps_validate_changed`) matters more than single-file checks |
| **1700+ Python files** | Quick feedback loops (`tapps_quick_check`) keep sessions efficient |
| **Docker-heavy** | Config validation (`tapps_validate_config`) is essential for compose/Dockerfile changes |
| **Tier 1 critical services** | websocket-ingestion, data-api, admin-api, health-dashboard need stricter gates (score ≥80) |
| **Security-sensitive** | APIs, auth, external integrations justify explicit `tapps_security_scan` |
| **Quality targets** | Score ≥70 (≥80 for critical), security ≥7.0, coverage ≥80% |

### Evaluation summary

- **Scale:** ~1,760 Python files across 9 domain groups and **~58** production containers (**62** Compose definitions) make batch validation (`tapps_validate_changed`) and quick per-file feedback (`tapps_quick_check`) essential; single-file-only workflows do not scale.
- **Tech stack:** Python with FastAPI, aiohttp, Flask, pytest. Always run `tapps_lookup_docs` before using these (and InfluxDB, Pydantic, etc.) to avoid wrong APIs.
- **Critical path:** Tier 1 services (websocket-ingestion, data-api, admin-api, health-dashboard) are the event and query backbone; use `tapps_impact_analysis` before changing shared code and enforce score ≥80 for these.
- **Infrastructure:** Docker and many compose files mean `tapps_validate_config` is required when changing Dockerfile or compose; config validation catches deployment and connectivity issues early.
- **Security surface:** APIs, auth, and external integrations justify explicit `tapps_security_scan` on security-sensitive changes.
- **Conclusion:** The priority order below is tuned for this mix: session/discovery first, research before coding, quick checks during edits, batch validation and gates before done, checklist last.

---

## Priority Tiers

### Tier 1: Session Start (Every Session)

| Order | Tool | Why This Order |
|-------|------|----------------|
| 1 | **tapps_session_start** | Must run first. Combines server info + project profile. All subsequent tools rely on this context. Skipping it leaves tools with generic, non-HomeIQ-specific advice. |

---

### Tier 2: Discovery (First Session or When Uncertain)

| Order | Tool | Why This Order |
|-------|------|----------------|
| 2 | **tapps_project_profile** | Immediately after session start. Detects project type, tech stack, and structure. HomeIQ's multi-domain layout (9 groups) benefits from explicit structure detection so tools apply the right patterns. |
| 3 | **tapps_doctor** | Run once if config is suspect. Validates MCP config, binaries (ruff, mypy, bandit), hooks, and generated files. Answers "Is TappsMCP set up correctly?" before debugging tool failures. |

---

### Tier 3: Before Writing or Modifying Code

| Order | Tool | Why This Order |
|-------|------|----------------|
| 4 | **tapps_lookup_docs** | Before using any external library. Prevents hallucinated APIs—especially important for FastAPI, InfluxDB, aiohttp, Pydantic, etc. Run *before* writing code that imports or calls external APIs. |
| 5 | **tapps_impact_analysis** | Before changing a file's public API or removing exports. Maps what depends on it. Critical for shared libs (`homeiq-resilience`, `homeiq-data`, `homeiq-patterns`) and Tier 1 services where changes cascade. |
| 6 | **tapps_consult_expert** | When making domain-specific decisions (security, testing, API design, database, architecture). RAG-backed guidance avoids reinventing the wheel. Use when unsure about patterns or tradeoffs. |

---

### Tier 4: During Edits (Per File)

| Order | Tool | Why This Order |
|-------|------|----------------|
| 7 | **tapps_quick_check** | After each Python file change. Fast score + gate + basic security in one call. Keeps edit-lint-fix loops tight. Use `quick=True` during development; full scoring before declaring done. |

---

### Tier 5: Before Declaring Work Complete

| Order | Tool | Why This Order |
|-------|------|----------------|
| 8 | **tapps_validate_changed** | Runs score + gate + security on *all* changed files (git diff). Essential for multi-file work. HomeIQ often has cross-service changes; this catches regressions before PR. |
| 9 | **tapps_quality_gate** | Ensures each file passes the configured preset (standard/strict/framework). Enforces HomeIQ thresholds: score ≥70 (≥80 for critical services), no critical security issues. |
| 10 | **tapps_security_scan** | Explicit security pass. Use for auth, API routes, input validation, secrets handling, or any security-sensitive code. Bandit + secret detection with redacted context. |
| 11 | **tapps_validate_config** | When touching Dockerfile, docker-compose, or infra config. Validates against WebSocket/MQTT/InfluxDB best practices. HomeIQ has many compose files; this prevents misconfigurations. |

---

### Tier 6: Final Verification

| Order | Tool | Why This Order |
|-------|------|----------------|
| 12 | **tapps_checklist** | Last step before "done". Reports which tools were called and which are missing. Pass `task_type` (e.g. `feature`, `bugfix`, `security`, `refactor`) for task-appropriate requirements. Ensures no required step was skipped. |

---

### Tier 7: Optional / Situational

| Tool | When to Use |
|------|-------------|
| **tapps_dependency_scan** | Before releases or when adding new pip dependencies. Scans for known CVEs via pip-audit. |
| **tapps_dependency_graph** | Before refactoring or when debugging import/coupling issues. Detects circular imports and coupling metrics. |
| **tapps_dead_code** | During refactoring. Vulture-based detection of unused functions, classes, imports, variables. |
| **tapps_report** | When generating a quality summary (Markdown, JSON, or HTML) for reviews or documentation. |
| **tapps_memory** | For cross-session decisions. Persist key constraints or architecture choices so they survive long sessions. |
| **tapps_session_notes** | For session-local notes. Save decisions or discoveries within the current session. |

---

## Visual Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│ SESSION START                                                    │
│ 1. tapps_session_start                                           │
│ 2. tapps_project_profile (first session or when unsure)          │
│ 3. tapps_doctor (if config suspect)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ BEFORE CODING                                                    │
│ 4. tapps_lookup_docs(library='...')     ← before using library   │
│ 5. tapps_impact_analysis(file_path=...) ← before changing API    │
│ 6. tapps_consult_expert(question='...') ← domain decisions       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ DURING EDITS                                                     │
│ 7. tapps_quick_check(file_path=...)     ← after each change      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ BEFORE DONE                                                      │
│ 8. tapps_validate_changed()              ← all changed files     │
│ 9. tapps_quality_gate(file_path=...)     ← per-file pass         │
│10. tapps_security_scan(file_path=...)    ← auth/API/secrets      │
│11. tapps_validate_config(file_path=...)  ← Docker/compose        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ FINAL                                                            │
│12. tapps_checklist(task_type='...')      ← verify completeness   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Rationale for This Order

### Why session start first?
- TappsMCP tools assume project context (tech stack, structure, presets).
- Without `tapps_session_start`, recommendations are generic.
- One call; negligible cost; unlocks all downstream tools.

### Why discovery before coding?
- `tapps_project_profile` detects HomeIQ's multi-domain layout and applies correct patterns.
- `tapps_doctor` avoids debugging tool failures caused by config issues.

### Why lookup/impact/consult before coding?
- `tapps_lookup_docs` prevents wrong API usage that would fail later.
- `tapps_impact_analysis` prevents breaking dependents when changing shared code.
- `tapps_consult_expert` provides domain guidance *before* implementing, not as an afterthought.

### Why quick_check during edits?
- Fast feedback keeps edit cycles short.
- Catching issues early is cheaper than fixing after `tapps_validate_changed` fails.

### Why validate_changed before quality_gate/security_scan?
- `tapps_validate_changed` runs score + gate + security on *all* changed files in one pass.
- Use `tapps_quality_gate` and `tapps_security_scan` when you need deeper, file-specific analysis or when validate_changed wasn't sufficient.

### Why validate_config when touching Docker?
- HomeIQ has many compose files and Dockerfiles.
- Config validation catches WebSocket, MQTT, InfluxDB, and deployment anti-patterns.

### Why checklist last?
- It reports which required tools were *not* called.
- Running it first would be meaningless; it must come after all other validation steps.

---

## Checklist Task Types

Use the appropriate `task_type` with `tapps_checklist`:

| task_type | Use Case |
|-----------|----------|
| `feature` | New code, new endpoints |
| `bugfix` | Fixing bugs |
| `refactor` | Restructuring without changing behavior |
| `security` | Security-sensitive changes |
| `review` | General code review (default) |

---

## Related Documentation

- [TAPPS Quality Baseline](../reports/quality/TAPPS_BASELINE.md) — Per-service scores, gate results, and security baseline
- [AGENTS.md](../AGENTS.md) — TappsMCP instructions for AI assistants
- [docs/README.md](README.md) — Documentation index
- [.cursor/rules/](../.cursor/rules/) — Cursor rules including TAPPS pipeline
