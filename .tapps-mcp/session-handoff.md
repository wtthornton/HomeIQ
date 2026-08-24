# Session handoff
**Updated:** 2026-08-24T01:13:55Z
**Git:** 7474dacc
**Linear P0:** TAP-6483

## Done
- Four appliance decisions recorded in `docs/architecture/adr-appliance-packaging.md`: HomeIQ owns a headless pre-provisioned HA (HACS build-time only, no Supervisor); one shared HA credential generated per install, rotation deferred; installer + pinned compose bundle, not a fused image; Zeek ships opt-in.
- **Epic TAP-6460 closed** — TAP-6461/6462/6463 plus TAP-6492. Every criterion re-verified on `master`; `grep -r HOMEIQ_INTEGRATION` returns zero repo-wide.
- **ner-service 16.3 GB → 3.39 GB** (missing CPU wheel index). The rebuild also proved it could not build at all — only Dockerfile of 39 with an incomplete lib closure.
- Observability tier gated behind an `observability` profile: **48 → 42 production services**. Tracing export now opt-in.
- TAP-6492: ha-setup-service had no migration chain at all. Migration 001 creates all five tables and runs at startup; verified against a fresh DB and the live one, converging on identical schemas.
- 5 PRs merged (#125–#129), none open. 414 homeiq-ha + 69 ha-setup-service tests.
- **Filed 3 TappsMCP defects** in the TappsMCP Platform project: TAP-6493 (handoff lints clean when no section parses), TAP-6494 (validate_config rejects the absolute path its own remediation demands), TAP-6495 (`_split_csv` shreds `non_goals` on internal commas). Confirmed TAP-6387 with root cause and TAP-6389; flagged TAP-5664 as its duplicate and TAP-6444 as apparently already fixed.

## Open
- Live stack unchanged: compose was edited, containers were not restarted. The six observability containers still run.
- Memory footprint not re-measured (7,406 MiB is from 2026-08-18) — blocked on the restart above.
- TAP-6490's four stories are described but deliberately not filed; the installer design is still open.
- Zeek retention undecided: opt-in says whether traffic is captured, not what is kept or for how long. Blocks the wizard step only.
- Does tapps-brain ship? AgentForge degrades fine when it is unreachable, but its compose has a required-value token and an external network it owns, so it ships unless someone does the escape-hatch work.

## Next (P0)
- Build the pre-provisioned Home Assistant image: pin the HA version, vendor Powercalc, Team Tracker and the Aqara FP1E quirk into `/config/custom_components/`, ship no HACS at runtime, and add a checked-in component version manifest CI verifies. Testable today against the existing `home-assistant-test` fixture; unblocks the next three stories.

## Blockers
- none

## Changed files
- `docs/architecture/adr-appliance-packaging.md` (new)
- `libs/homeiq-ha/src/homeiq_ha/agent/{flow_credentials,blockers,unclaimed}.py`
- `domains/device-management/ha-setup-service/{src/migrations.py,alembic/versions/001_ha_setup_tables.py}`
- `domains/ml-engine/ner-service/{Dockerfile,requirements-prod.txt}`
- `infrastructure/container-budget.json`, `hacs.json` (deleted)

## Verify
- `git log --oneline -1` — expect `7474dacc`
- `grep -rn HOMEIQ_INTEGRATION . --exclude-dir=.git` — expect zero
- `python3 scripts/check-container-budget.py` — expect `OK: 42 production services`
- `python -m pytest libs/homeiq-ha/tests/ -q` — expect 414 passed
- CI reds carry no signal here: `E2E & Integration Tests` and `CI — ML Engine` are red on master head, `Docker Build and Test` / `Docker Test` are 12/12 red on every branch. Always diff a PR's reds against master head.
- Linear auto-closes an issue when its PR merges regardless of whether acceptance holds — TAP-6461 and TAP-6463 both did. Re-run criteria against `master` before trusting a closed story.
- After any handoff save, check `handoff_sections` is populated — TAP-6493: non-matching headings parse to empty and still lint clean.

## Success criterion
- TAP-6483 merged: a pinned HA image carrying the three vendored components, no HACS at runtime, and a version manifest CI checks.
