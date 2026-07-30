---
name: tapps-tool-reference
description: >-
  Look up when to use each TappsMCP tool. Full tool reference with per-tool
  guidance for session start, scoring, validation, checklist, docs, experts.
  Use when you need guidance on which TappsMCP tool to call for a given situation.
mcp_tools:
  - tapps_server_info
---

When the user asks about TappsMCP tools, provide the full tool reference.
Essential: tapps_session_start (first), tapps_quick_check (after edits),
tapps_validate_changed (before complete, always pass file_paths), tapps_checklist (before complete).

## Essential tools (always-on workflow)
| Tool | When to use it |
|------|----------------|
| **tapps_session_start** | **FIRST call in every session** — server info + call_graph cache status |
| **tapps_quick_check** | **After editing any Python file** — quick score + gate + basic security |
| **tapps_validate_changed** | **Before multi-file complete** — score + gate on changed files. Always pass explicit `file_paths`. `include_impact=true` (default) refreshes call-graph cache. |
| **tapps_checklist** | **Before declaring complete** — reports which tools were called |
| **tapps_quality_gate** | Before declaring work complete — ensures file passes preset |

## Validation & analysis
| Tool | When to use it |
|------|----------------|
| **tapps_security_scan** | Security-sensitive changes or before security review |
| **tapps_validate_config** | When adding/changing Dockerfile, docker-compose, infra |
| **tapps_impact_analysis** | Module-level import blast radius before API or layout changes |
| **tapps_call_graph** | Before editing a function — `query=callers|callees|chain|all`; stale cache auto-rebuilds on first use |
| **tapps_impact_analysis** | Module blast radius, or symbol-level with `symbol=` + `granularity=symbol|both` |
| **tapps_diff_impact** | After Python edits — ranked affected tests for changed files |
| **tapps_validate_changed** | `include_impact=true` (default) refreshes cache via diff_impact |
| **tapps_dead_code** | Find unused code during refactoring |
| **tapps_dependency_scan** | Check for CVEs before releases |
| **tapps_dependency_graph** | Understand module dependencies, circular imports |

## Planning, metrics & audit
| Tool | When to use it |
|------|----------------|
| **tapps_decompose** | Break a vague task into ordered, verifiable TAPPS tool-call steps before starting |
| **tapps_pipeline** | Show TAPPS pipeline stage progress and the next recommended tool call |
| **tapps_audit_campaign** | Plan, dispatch, or convert a file-scope audit campaign to a fix plan |
| **tapps_usage** | Session gap report: tools called vs pipeline expectations (edits without validation, libraries used without lookup_docs) |
| **tapps_dashboard** | Metrics dashboard: usage, gate pass rate, and trends |
| **tapps_stats** | Per-tool usage statistics: call counts, success rates, latency percentiles |

For function-level refactors use `/tapps-refactor`. Call `tapps_server_info` for the latest recommended workflow string.
