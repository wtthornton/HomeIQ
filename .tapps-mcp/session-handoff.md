# Session handoff

**Updated:** 2026-08-10T22:45:00Z
**Git:** 884f4a22
**Linear P0:** none verified (no `get_issue` calls — treat TAP ids as unconfirmed)

> Session 8: sync review → Wave 1 backlog burndown. Theme: four defects were
> **metrics measuring a proxy**, each reading green while the real fault went untouched.

## Done

- **Contract scanner (`2f250aa9`)** — counted backtick paths in a JSDoc block (`api.ts:782-798`) as call sites; red since Aug 1. Now strips TS comments. Also: `grep -rh` hides filenames, so the mocks/tests exclusion never excluded anything. 68→58 refs, all production sites kept. CI green.
- **CI restored 1 → 18 working workflows.** 18 of 19 documented-auto workflows sat `disabled_manually` at the **GitHub API level** while their `pull_request:` triggers were already correct. Enabled 17; verified by real runs. Repo is PUBLIC → Actions free.
- **`start-stack.sh` (`04f78dd3`)** — dropped forced `--pull always --force-recreate` (re-pulled every base image, recreated all 58 containers each start). `STACK_REFRESH=1` restores.
- **`automation-miner` → 58/58 healthy.** Latched degraded since the Aug 3 postgres swap on pre-fix code (`_try_recover`, `90613386`).
- **Wave 1 plan corrected (`f3857c15`)**; **MCP HTTP fleet committed (`884f4a22`, ADR-0024, another session's work, validated first)**.

## Open

- **`quality-gate` + `agentic-pr-review` RED, parked by user.** TappsMCP uninstallable at any ref: not on PyPI; repo root is a uv workspace; `packages/tapps-core` fails its wheel build on a hatchling `force-include` duplicate (`pyproject.toml:51-52`). **`013067f7` pins the root and is wrong** — changes the error, not the outcome. Fix is cross-project.
- **`dependabot-auto-merge` disabled** — squash-merges to master unattended.
- **`scripts/validate-github-workflows.sh` validates 1 of 33** — exits on first warning.
- **HomeIQ CLAUDE.md documents `pip install tapps-mcp`** — wrong as written.

## Next (P0) — Wave 2 (TAP-5433/5434/5424); plan stale 4 ways

1. **`git stash` head start GONE** — list empty; the 8 promised TAP-5433 fixes don't exist.
2. **Contract is 79/79, not 36.** Target ≥88 → 9 rows away.
3. **The 5 KNOWN_GAPS are unclosable as written** — all base-URL constants, not endpoints (`baseUrl = ... || '/ai-automation'`, `API_BASE = '/api/v1'`, `super('/rag-service')`, `super('/setup-service')`, `|| '/websocket-ingestion'`). Teach the scanner that a match with no path beyond the service prefix is a base URL.
4. **TAP-5424 clause misleads:** 12 importer files, 2 are tests → 10 app files. ~6 app files keep REST-registry fallbacks *while* importing the shared client: `data-api/src/devices_endpoints.py` (frontier), `device-health-monitor/src/ha_client.py`, `device-recommender/src/ha_client.py`, `ha-setup-service/src/integration_checker.py`, `device-setup-assistant/src/issue_detector.py`, `websocket-ingestion/src/discovery_service.py`.

## Blockers

- **Shared tree — `tapps-mcp-6c` writes here.** `git status --short` twice ~30s apart before editing; stage explicit paths, never `git add -A`.

## Verify

- `git status --porcelain` clean; master == origin/master
- `bash scripts/verify-dashboard-contract.sh` → 79/79, 0 deviations
- `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c '(healthy)'` → 58
- `.venv/bin/python -m pytest libs/homeiq-ha -q` → 99 passed (system python3 lacks pytest)
- `gh workflow list --all` → 18 active, dependabot-auto-merge disabled

## Quirks that cost time

- **One-service deploy needs `--env-file .env`** — else compose reads `.env` from the compose file's dir (absent) and `${POSTGRES_PASSWORD:-...}` falls back to a wrong default → runtime auth failure. `--project-directory .` is NOT the fix.
- **Masking a secret when diffing env verifies nothing** — hash and compare.
- **TCP connect proves reachability, not auth** — "DB unavailable" can mean `InvalidPasswordError`.
- **`.dockerignore:72` excludes `docs/`** — a cache probe there never enters the build context.
