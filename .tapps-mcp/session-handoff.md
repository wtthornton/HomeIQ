# Session handoff
**Updated:** 2026-08-20T16:25:00Z
**Git:** aa8ef7cd on master
**Repo root:** /home/wtthornton/code/HomeIQ
**Linear:** filed TAP-6383 (Backlog/Medium). No P0 open.

## Done
- PR #122: stripped `|| true` from .github/workflows/integration-tests.yml (7 pytest, 4 pip installs) + fixed unreachable block after `exit "$FAILED"`. Masking hid NOTHING — all 9 jobs pass honestly, 0 new reds.
- PR #123: E2E was 0-for-40, structurally impossible (bare `up -d` = 45 services, 38 source builds, 180s wait; docker-build.yml `push: false` so no images to pull). Scoped to 7 services = transitive depends_on closure: influxdb postgres ha-simulator data-api websocket-ingestion admin-api health-dashboard. Now all 7 healthy, **18 passed / 8 failed / 1 flaky**.
- Four stacked blockers, each hidden by the prior: 7 `${VAR:?required}` names w/ 1 supplied (compose aborts at the first, so only GF_SECURITY_ADMIN_PASSWORD ever showed); homeiq_logs include-merge conflict; homeiq-network not created; data-api crash-on-boot (needs API_KEY).
- REAL DEFECT FIXED: infrastructure/postgres/init-monitoring.sql:71-72 used `tablename`/`indexname` from pg_stat_user_indexes (actual: `relname`/`indexrelname`). Script aborted there — of 8 views only 3 existed on the LIVE db, neither GRANT ran. Verified fixed on PG17 under ON_ERROR_STOP=1 in a rolled-back txn.
- Also fixed: health wait accepted `HEALTHY -gt 0`; pass-rate used `stats.expected` (the PASSED count) as its own denominator and read a path Playwright never wrote.

## Open
- **8 E2E failures + 1 flaky** — deferred by owner decision. Real UI assertions (heading /Anomaly Detection/i missing, alerts.spec.ts:48). UNVERIFIED hypothesis: data-dependent, CI has no HA data so dashboards render empty.
- `Integration Tests` (test.yml) — only confirmed red on master. 29 tests hit live HTTP with no services started; 2 need influxdb_client_3. Needs a service-container decision. UNTOUCHED. `Test Summary` aggregates it + E2E.
- Not in E2E scope (see workflows README): ai-automation-ui (:3001, needs domains/frontends/compose.yml) and full-suite run (needs published images). Do NOT widen back to bare `up -d`.
- Doctor WARN: alwaysApply rules 26491 vs 16384 ceiling; af-integration.mdc duplicated in .claude/rules/ and .cursor/rules/.
- CI backlog: docker-security-scan dupes 11 of docker-build's 21 Trivy legs; no top-level concurrency on 4 workflows.

## Next (P0)
- Triage the 8 E2E failures. Test the empty-state hypothesis first: `sh scripts/ensure-network.sh`, then `docker compose -p homeiq-e2e --env-file .env -f domains/core-platform/compose.yml up -d --build <the 7>`, open the dashboard. If sections are genuinely empty, the call is seed-data vs empty-tolerant specs — a test-design decision, ask the owner. The `playwright-report` artifact has e2e-results.json + traces.

## Blockers
- none

## Verify
- USER RULE: no full local suites; targeted files only.
- **Local Compose 5.1.1 is MORE LENIENT than the runner** — a passing local `docker compose config` does NOT predict CI. Cost two round-trips. See TAP-6383.
- `gh run view --log` empty here; use `gh api repos/wtthornton/HomeIQ/actions/jobs/<id>/logs`. `gh pr checks --json` unsupported.
- Diff PR reds vs master head before triaging.
- E2E takes ~9 min (builds 5 images) — a fast fail means a NEW bug, not the old one.
- 7 required compose vars: INFLUXDB_TOKEN, INFLUXDB_PASSWORD, POSTGRES_PASSWORD, JWT_SECRET_KEY, ADMIN_PASSWORD, HOMEIQ_MCP_READ_TOKENS, GF_SECURITY_ADMIN_PASSWORD. Reference = infrastructure/env.example (NOT .env.example, a stub missing all 7).
- Do NOT add `--project-directory` to the E2E compose call: `env_file: ../../.env` resolves relative to the compose FILE, so it would repoint outside the repo.
- A real .env exists at repo root (gitignored) — do not overwrite it locally.
- workflows README is load-bearing: check-workflow-enablement.sh derives its set from it (floor 15, now 20).

## Success criterion
- CI carries only checks that can actually pass; every remaining red is a real defect with an owner.
