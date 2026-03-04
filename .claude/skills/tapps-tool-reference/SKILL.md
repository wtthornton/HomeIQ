---
name: tapps-tool-reference
description: >-
  Look up when to use each TappsMCP tool. Full tool reference with per-tool
  guidance for session start, scoring, validation, checklist, docs, experts, and more.
allowed-tools: mcp__tapps-mcp__tapps_server_info
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
| **tapps_validate_changed** | **Before multi-file complete** - score + gate on changed files |
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
| **tapps_consult_expert** | Domain-specific decisions (security, testing, APIs, etc.) |
| **tapps_research** | Combined expert + docs in one call |
| **tapps_list_experts** | See which expert domains exist |

## Project & memory
| Tool | When to use it |
|------|----------------|
| **tapps_project_profile** | When you need project context (tech stack, type) |
| **tapps_memory** | Session start: search past decisions. Session end: save learnings |
| **tapps_session_notes** | Key decisions during session - promote to memory for persistence |

## Validation & analysis
| Tool | When to use it |
|------|----------------|
| **tapps_security_scan** | Security-sensitive changes or before security review |
| **tapps_validate_config** | When adding/changing Dockerfile, docker-compose, infra |
| **tapps_impact_analysis** | Before modifying a file's public API |
| **tapps_dead_code** | Find unused code during refactoring |
| **tapps_dependency_scan** | Check for CVEs before releases |
| **tapps_dependency_graph** | Understand module dependencies, circular imports |

## Pipeline & init
| Tool | When to use it |
|------|----------------|
| **tapps_init** | Pipeline bootstrap (once per project) - creates AGENTS.md, rules, hooks |
| **tapps_upgrade** | After TappsMCP version update - refreshes generated files |
| **tapps_doctor** | Diagnose configuration issues |
| **tapps_set_engagement_level** | Change enforcement intensity (high/medium/low) |

Use `tapps_server_info` for the latest recommended workflow string.
