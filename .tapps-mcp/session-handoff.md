# Session handoff

**Updated:** 2026-08-11T00:40:00Z
**Git:** d1764362 (master == origin/master, clean)
**Linear P0:** TAP-5434 open, but only on its blocked criterion

> Session 9: closed the actionable half of session 8's Open list via PR #74.
> Theme continued: gates that report a result while measuring something else.

## Done — PR #74, merged as `d1764362` (5 commits)

- **`4eb9e118` TAP-5434 absolute-URL criterion.** Six `VITE_*_URL || localhost:PORT`
  fetches. Five unreachable — `9c170ff2` (Feb 26, app consolidation) dropped the
  Synergies tab; `SynergiesTab` + `AnalyticsDashboard` deleted, 1105 lines. The
  sixth pointed at the **wrong service**: port 8019 is device-health-monitor,
  device-intelligence is 8028. Now behind `/device-intelligence/` nginx location
  injecting `X-API-Key` (that service wants X-API-Key, not Bearer).
- **`ad36e4e9` validator checked 1 of 31.** `set -e` + `((WARNINGS++))` — post-
  increment returns 1 when the counter is 0. Two more once it ran: the missing-
  script check had **never fired** (sed needed quotes real lines lack), and the
  `curl -f` warning fired only on correct code.
- **`25e82af5`** CLAUDE.md documented an impossible install (all 3 paths verified
  failing in a clean venv). **`0d2666a3`** dependabot rationale +
  `upgrade_skip_files`. **`c015fa32`** dangling docs.

## Open

- **TAP-5434's 88-row target** — blocked on ~20 families at 500/no-route.
- **TAP-5876** (TappsMCP Platform): `docs-mcp>=0.1.0` resolved by uv-only
  `[tool.uv.sources]`; an unrelated package owns that name on PyPI. Latent only
  because resolution dies earlier on unpublished `tapps-core`.
- **CI is red and always has been.** 12 of 24 checks fail on master. `ci` matrix =
  12 ruff errors in `health-dashboard/scripts/generate-icons*.py`. Quality Gate /
  E2E / Cross-Group failed on **every** master commit since Aug 2025.
- **Session 8's "18 workflows verified by real runs" meant they RUN, not PASS.**

## Corrections to the previous handoff

1. **TAP-5433 and TAP-5424 were already Done** (Aug 2) — 2 of 3 P0 ids were stale.
2. **The TappsMCP blocker is not tapps-core's hatchling force-include.** At
   v3.12.65 it is setuptools rejecting the root's flat layout (uv workspace, no
   `[project]`). "Cross-project" still holds; the cause was wrong.
3. Validator count is **31** workflow files, not 33.

## Next (P0) — pick one

1. **Fix the `ci` ruff failures** — 12 errors in two icon scripts. Turns 7 of 12
   failing checks green.
2. **Provision the two DB gaps** TAP-5434 names (absent `memory` schema, absent
   `patterns` table); each probably wants its own issue.
3. **`/api/v1/real-time-metrics` answers at ~10.0s** — real perf defect.

## Blockers

- **Shared tree — `tapps-mcp-6c` writes here.** `git status --short` twice ~30s
  apart before editing; stage explicit paths, never `git add -A`.

## Verify

- `git status --porcelain` clean; master == origin/master @ `d1764362`
- `bash scripts/verify-dashboard-contract.sh` → 80/80, 0 deviations
- `bash scripts/check-dashboard-contract-coverage.sh` → no new uncovered, 5 gaps
- `bash scripts/validate-github-workflows.sh` → 31/31, 0 errors 0 warnings
- `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c '(healthy)'` → 58

## Quirks that cost time

- **`gh pr checks` piped into anything loses the exit code** — `$?` is the pipe's
  tail. Redirect to a file, check separately.
- **`tapps_validate_config` calls nginx.conf a "websocket" config** and returns
  Python asyncio advice. Use `docker exec homeiq-dashboard nginx -t`.
- **One-service deploy needs `--env-file .env`**; also recreates its dependency
  containers, not just the target.
- **`.dockerignore:72` excludes `docs/`.**
