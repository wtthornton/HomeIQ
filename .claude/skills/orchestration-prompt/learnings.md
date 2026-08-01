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
