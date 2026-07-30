---
name: tapps-tool-reference
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Look up when to use each TappsMCP tool. Full tool reference with per-tool
  guidance for session start, scoring, validation, checklist, docs, experts, and more.
  Use when you need guidance on which TappsMCP tool to call for a given situation.
allowed-tools: mcp__nlt-setup__tapps_server_info
argument-hint: "[tool-name or 'all']"
---

When the user asks about TappsMCP tools (e.g. "when do I use tapps_score_file?",
"what tools does TappsMCP have?", "tapps_quick_check vs tapps_quality_gate"),
provide the full tool reference from this skill.

## Essential tools (always-on workflow)
| Tool | When to use it |
|------|----------------|
| **tapps_session_start** | **FIRST call in every session** - returns server info only |
| **tapps_quick_check** | **After editing any Python file** - quick score + gate + basic security |
| **tapps_validate_changed** | **Before multi-file complete** - score + gate on changed files. Always pass explicit `file_paths`. Default is quick; `quick=false` is a last resort. |
| **tapps_checklist** | **Before declaring complete** - reports which tools were called |
| **tapps_quality_gate** | Before declaring work complete - ensures file passes preset |

## Scoring & quality
| Tool | When to use it |
|------|----------------|
| **tapps_score_file** | When editing/reviewing - use quick=True during edit loops |
| **tapps_server_info** | At session start - discover version, tools, recommended workflow |

## Documentation & experts
| Tool | When to use it |
|------|----------------|
| **tapps_lookup_docs** | Before writing code using an external library |

## Project & memory
| Tool / path | When to use it |
|------|----------------|
| **`tapps-mcp memory` CLI** | Save/search/get architectural or pattern decisions (`memory save`, `search`, `get`) |
| **tapps_session_notes** | Session-local notes during the chat |
| **tapps-handoff-session / tapps-continue-session** | Cross-chat transfer via `.tapps-mcp/session-handoff.md` |
| **tapps_session_start** | `brain_bridge_health` before memory writes; hooks auto-recall |

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

## Pipeline & init
| Tool | When to use it |
|------|----------------|
| **tapps_init** | Pipeline bootstrap (once per project) - creates AGENTS.md, rules, hooks, MCP config (default). **CLI fallback:** `tapps-mcp upgrade --force --host auto` then `tapps-mcp doctor` |
| **tapps_upgrade** | After TappsMCP version update - refreshes generated files |
| **tapps_doctor** | Diagnose configuration issues |
| **tapps_set_engagement_level** | Change enforcement intensity (high/medium/low) |

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
