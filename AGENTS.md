# TappsMCP — instructions for AI assistants

When the **TappsMCP** MCP server is configured in your host (Cursor, Claude Desktop, etc.), you have access to tools that provide **deterministic code quality checks, doc lookup, and domain expert advice**. Use them to avoid hallucinated APIs, missed quality steps, and inconsistent output.

---

## What TappsMCP is

TappsMCP is an MCP server that exposes tools for:

- **Scoring** Python files (0-100 across 7 categories)
- **Security scanning** (Bandit + secret detection)
- **Quality gates** (pass/fail vs presets)
- **Documentation lookup** (up-to-date library docs via Context7)
- **Config validation** (Dockerfile, docker-compose, WebSocket/MQTT/InfluxDB)
- **Domain experts** (16 built-in experts with RAG-backed answers, optional vector search)
- **Project context** (project type detection, tech stack, impact analysis)
- **Session notes** (persist decisions and constraints across long sessions)
- **Quality reports** (JSON, Markdown, or HTML summaries)
- **Session checklist** (track which tools were used so you don't skip required steps)

You only see these tools when the host has started the TappsMCP server and attached it to your session.

**File paths:** For tools that take `file_path`, use **paths relative to the project root** (e.g. `src/main.py`, `tests/test_foo.py`) so they work with both stdio and Docker. If the server is configured with `TAPPS_MCP_HOST_PROJECT_ROOT` (e.g. when using Docker), you can also pass **absolute host paths** (e.g. `C:\projects\myapp\src\main.py`); the server will map them to the project root.

---

## When to use each tool

| Tool | When to use it |
|------|----------------|
| **tapps_server_info** | At **session start** — discover version, available tools, and installed checkers. Response includes a short `recommended_workflow` string. |
| **tapps_score_file** | When **editing or reviewing** a Python file. Use `quick=True` during edit–lint–fix loops; use full (default) **before declaring work complete**. |
| **tapps_security_scan** | When the change is **security-sensitive** or before a security-focused review. |
| **tapps_quality_gate** | **Before declaring work complete** — ensures the file passes the configured quality preset. Do not consider work done until it passes (or the user accepts the risk). |
| **tapps_lookup_docs** | **Before writing code** that uses an external library — use the returned docs to avoid hallucinated APIs. |
| **tapps_validate_config** | When **adding or changing** Dockerfile, docker-compose, or infra config. |
| **tapps_consult_expert** | When making **domain-specific decisions** (security, testing, APIs, database, etc.) and you want authoritative, RAG-backed guidance. Pass `domain` when context makes it obvious (e.g. editing a test file → `domain="testing-strategies"`). |
| **tapps_list_experts** | When you need to see **which expert domains exist** before calling `tapps_consult_expert`. |
| **tapps_project_profile** | At **session start** or when you need project context — detects project type, tech stack, and structure so you can apply the right patterns. |
| **tapps_session_notes** | When you make a **key decision or discover a constraint** — save it so you can recall it later in a long session. |
| **tapps_impact_analysis** | Before **modifying a file's public API** — shows what depends on it and what could break. |
| **tapps_report** | After scoring/gating, when the user wants a **formatted quality summary** (Markdown, JSON, or HTML). |
| **tapps_checklist** | **Before declaring work complete** — reports which tools were called and which are missing (with reasons). Fix missing required steps before saying done. |
| **tapps_dashboard** | When the user wants to **review how TappsMCP is performing** — scoring accuracy, gate pass rates, expert effectiveness, cache performance, quality trends, and alerts. Supports json, markdown, and html output. |
| **tapps_stats** | When the user wants **usage statistics** — call counts, success rates, average durations, cache hit rates, and gate pass rates. Filterable by tool and time period. |
| **tapps_feedback** | After receiving a tool result — report whether the output was **helpful or not**. This feedback improves adaptive scoring and expert weights over time. |
| **tapps_init** | At the **start of a pipeline run** — profiles the project, sets context, and plans the workflow stages (discover, research, develop, validate, verify). |

---

## Domain hints for tapps_consult_expert

Pass the `domain` parameter when the context clearly implies a domain. This improves routing accuracy and avoids auto-detection mistakes.

| Context | domain value |
|---------|--------------|
| Editing test files, conftest.py, pytest config | `testing-strategies` |
| Security-sensitive code, auth, validation | `security` |
| API routes, FastAPI/Flask endpoints | `api-design-integration` |
| Database models, migrations, queries | `database-data-management` |
| Dockerfile, docker-compose, k8s manifests | `cloud-infrastructure` |
| CI/CD, workflows, build config | `development-workflow` |
| Code quality, linting, type hints | `code-quality-analysis` |
| Architecture decisions, patterns | `software-architecture` |

When in doubt, omit `domain` to let auto-detection from the question text choose.

---

## Recommended workflow

1. **Session start:** Call `tapps_server_info` and `tapps_project_profile` (and optionally `tapps_list_experts` if you may need experts).
2. **Record key decisions:** Use `tapps_session_notes(action="save", ...)` to persist constraints and decisions so they survive long sessions.
3. **Before using a library:** Call `tapps_lookup_docs(library=...)` and use the returned content when implementing.
4. **Before modifying a file's API:** Call `tapps_impact_analysis(file_path=...)` to see what depends on it.
5. **During edits:** Call `tapps_score_file(file_path=..., quick=True)` (and `fix=True` if you want ruff to apply fixes).
6. **Before declaring work complete:**
   - Call `tapps_score_file(file_path=..., quick=False)` on changed files.
   - Call `tapps_quality_gate(file_path=...)` — work is not done until it passes.
   - Call `tapps_checklist(task_type=...)` and, if `complete` is false, call the missing required tools (use `missing_required_hints` for reasons).
   - Optionally call `tapps_report(format="markdown")` to generate a quality summary.
7. **When in doubt:** Use `tapps_consult_expert` for domain-specific questions; use `tapps_validate_config` for Docker/infra files.

---

## Checklist task types

Use the `task_type` that best matches the current work:

- **feature** — New code
- **bugfix** — Fixing a bug
- **refactor** — Refactoring
- **security** — Security-focused change
- **review** — General code review (default)

The checklist uses this to decide which tools are required vs recommended vs optional for that task.
