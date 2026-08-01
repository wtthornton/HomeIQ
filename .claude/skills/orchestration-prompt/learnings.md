# orchestration-prompt learnings (project-scoped)

Append one-line lessons as you generate prompts. Keep them project-scoped; never
bleed across repos. This file is created once by the scaffolder and never
overwritten on upgrade — it's yours.

<!-- Example: -->
<!-- - Validation goals need a verified-correct-negative Done-when, or the loop chases an unreachable target. (2026-06-18) -->
- HomeIQ harness gates the loop must pre-satisfy: `save_issue` needs a `docs_validate_linear_issue` sentinel <30min (use the `linear-issue` skill), `list_issues` needs a prior `snapshot_get` (use `linear-read`), and all `tapps_*` MCP tools need `tapps_session_start` first. (2026-08-01)
- Merged != live here in a second way: several HomeIQ compose services declare `build:` with no `image:`, so `docker buildx bake` output is NOT what compose runs — rebuild via `docker compose up -d --build <service>` or the loop verifies a stale container. (2026-08-01)
- When the user has said "do not set anything up", split the Done-when between *agent implemented and tested* (fixtures/simulator) and *agent applied to the live system* (Autonomy hard-stop) — otherwise the loop mutates production to score itself green. (2026-08-01)
- Validation-goal caveat for audit tooling: an `audit` that reports every recipe NEEDS_APPLY is a correct pass, not a failure — state this explicitly or the loop chases an unreachable all-green. (2026-08-01)
- The skill's own files are tapps-managed (BEGIN/END markers) — customizing them without adding an `upgrade_skip_files` entry in `.tapps-mcp.yaml` means the next `tapps_upgrade` silently reverts the work. (2026-08-01)
- The `uv run tapps-mcp memory search` CLI is broken in this project (raises `ValueError: MemoryStore requires a Postgres private_backend`) — emit the `tapps_memory` MCP tool call for brain recall, never the CLI form. (2026-08-01)
- Pair every must-reach-zero clause with a must-grow one drawn from the SAME work: "0 REST-registry callers" alone is satisfiable by deleting the callers, so it must carry "AND >= N services import the shared client". Same for "0 deviations" → "at >= N rows". (2026-08-01)
- When a sub-goal's correct outcome is sometimes *removal* (a frontend call with no backend route), say so in Guardrails under "caps must not fire on correct behaviour" — otherwise the verifier scores a correct deletion red and the loop re-adds dead code. (2026-08-01)
- Order a long migration cheapest-and-least-coupled first, and say why: a 6-hour run that truncates should leave whole services done rather than every service half-done. (2026-08-01)
- Rate limits are a correctness trap in sweep scripts: admin-api caps at 60 req/min and `verify-dashboard-contract.sh` paces at 1.1s, so the prompt must forbid lowering `CONTRACT_PACE` to "speed it up" — the resulting 429s look exactly like failures. (2026-08-01)
- Carry an explicit "out of scope — human-gated, do not attempt" list naming the blocked issue ids; a loop told only what to do will wander into the blocked work and burn the run rediscovering the gate. (2026-08-01)
- ALWAYS read the full open backlog (`linear-read` over the whole project) before scoping a prompt — scoping to "the issues this session produced" missed 5 of 6 open HomeIQ epics and ~37 stories, and got the ordering wrong: the foundational build/CI epic was invisible. (2026-08-01)
- Verify the foundation epic's claims with a grep before assigning wave order: "all 54 build contexts are `../..`" and "0 of 10 domain CI workflows trigger on pull_request" are what justify putting build decoupling first, and both took one command each. (2026-08-01)
- When a Done-when clause measures a count going DOWN (containers 58→11, repo-root contexts 54→0), pair it with a capability-preservation clause ("every retired service's capability proven reachable", ">=54 services still build") — otherwise the target is met by deleting the system. This is the mirror of the must-grow rule. (2026-08-01)
- Order destructive waves last and make each deletion an Autonomy hard-stop; a consolidation epic that runs before its replacement surface exists is an outage, not a refactor. (2026-08-01)
