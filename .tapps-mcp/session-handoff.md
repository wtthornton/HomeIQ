# Session handoff
**Updated:** 2026-08-20T17:56:00Z
**Git:** 936704b2 on master
**Repo root:** /home/wtthornton/code/HomeIQ
**Linear:** TAP-6383 open (Backlog/Medium). No P0 open.

## Done
- PR #124 merged (rebase, 3 commits). E2E **8 failures -> 5**; 21 passed / 5 failed / 1 flaky. No new reds: PR's failing set is identical to master head's (E2E, Integration Tests, Test Summary).
- **The handoff's old empty-data hypothesis is DISPROVEN.** The 8 E2E failures were never one cause. 3 were test-side defects that fail regardless of data or stack size; 5 are downstream of #123's deliberate 7-service scoping.
  - `overview.spec.ts:49` + `smoke.spec.ts:33` matched `/operational|degraded|critical|down/`, but `calculateOverallStatus()` (OverviewTab.tsx:231) returns exactly `'operational'|'degraded'|'error'`, rendered by SystemStatusHero as ALL SYSTEMS OPERATIONAL / DEGRADED PERFORMANCE / SYSTEM ERROR. The pattern matched two strings the UI never emits and omitted the one it does. Fixed all 3 occurrences in overview.spec.ts.
  - `devices.spec.ts:42` failed on **strict mode** (2 elements), so the page HAD rendered. The "No Devices Found" empty state (DevicesTab.tsx:259) renders its own Refresh. Added `data-testid="devices-refresh"` to the toolbar button; chose that over `.first()`, which depends silently on DOM order.
  - Checked and rejected the obvious cause: `useRAGStatus.ts` computes RAG locally from the health aggregate, it does NOT call the (unscoped) rag-service. CI's `error` state comes from the aggregate being legitimately unhealthy at 7 of 48 services.
- REAL DEFECT FIXED: ha-device-control listens on **8046**, but its own Settings default and all consumers said 8040. Port 8040 belongs to rule-recommendation-ml (TECH_STACK.md:250) — that collision is why it moved; Story 61.1 fixed docs+compose and missed the source. Every cross-service call failed. Rebuilt + redeployed proactive-agent-service and ha-ai-agent-service; verified in-container that `get_house_status()` now returns a dict where it previously raised.
- Docker: 59 -> 48 containers, -31.6GB images (106.5GB -> 74.91GB, 0% reclaimable), 0 dangling HomeIQ volumes, 48/48 healthy. The 11 removed were retired in b0f54955 (2026-08-18) but never stopped. Full `docker inspect` snapshot saved to scratchpad before deletion.
- `scripts/domain.sh verify` now detects retired-service orphans (declared-vs-running diff via `compose config --services`, all 3 profiles). Tested clean-exit-0 AND planted-orphan-exit-1.

## Open
- **5 E2E failures** — `alerts.spec.ts:48`, `data-sources.spec.ts:46`, `validation.spec.ts:49`, `smoke.spec.ts:55`, `smoke.spec.ts:179`. These specs assert against a FULLY HEALTHY system while #123 scoped the stack to 7 of 48 services. Suite and stack now encode contradictory assumptions. This is a **test-design decision for the owner**: widen the stack, seed data, or make the specs scope-tolerant. Do not just widen back to bare `up -d`.
- Flaky `smoke.spec.ts:78` "all sidebar groups are navigable without errors" — untouched.
- `Integration Tests` (test.yml) red on master. 29 tests hit live HTTP with no services started; 2 need influxdb_client_3. Needs a service-container decision. UNTOUCHED. `Test Summary` aggregates it + E2E.
- `device_control_client.py` scores 69.51 vs the 70 gate. Proven pre-existing (pristine HEAD copy scores identically); NOT suppressed, not refactored.
- **automation-miner deploy drift**: the running container uses image `a32be81f`, but tagged `:latest` is `cca010b5` — a newer build never deployed. Image deliberately NOT deleted. Needs a redeploy or an explanation.
- Doctor WARN: alwaysApply rules 26491 vs 16384 ceiling; af-integration.mdc duplicated in .claude/rules/ and .cursor/rules/.
- CI backlog: docker-security-scan dupes 11 of docker-build's 21 Trivy legs; no top-level concurrency on 4 workflows.

## Next (P0)
- Decide the Category B question above, then implement it. Cheapest first probe: the specs assert a healthy aggregate, so confirm whether the 7-service scope can ever produce `operational` — if it structurally cannot, the specs must become scope-tolerant rather than the stack growing.

## Blockers
- none

## Verify
- USER RULE: no full local suites; targeted files only.
- **health-dashboard `type-check` is NOT a gate** — ~120 pre-existing tsc errors across 50 files (26 in ragCalculations.ts). Filter tsc output to the files you touched; gate on `vite build` + targeted vitest instead.
- **Local Compose 5.1.1 is MORE LENIENT than the runner** — a passing local `docker compose config` does NOT predict CI. See TAP-6383.
- **The local stack is healthy, so degraded-state E2E failures CANNOT be reproduced locally.** The old status regex passes here. CI is the only proof for those.
- Do NOT add `--remove-orphans` to domain.sh's start path: it runs `--profile production` and Compose's orphan/profile interaction is version-sensitive, so it can delete the test-profile containers (ha-simulator, home-assistant-test, websocket-ingestion-test) the E2E job needs.
- `gh run view --log` empty here; use `gh api repos/wtthornton/HomeIQ/actions/jobs/<id>/logs`. `gh pr checks --json` unsupported (plain `gh pr checks <n>` is tab-separated and works).
- Read E2E results from the `playwright-report` artifact: `gh run download <id> -n playwright-report`, then jq on `e2e-results.json`. Spec titles live at `.specs[]`, NOT `.tests[]` (those are null).
- **Always diff PR reds against master head before triaging** — master is red on 3 checks by default.
- E2E takes ~8-9 min (builds 5 images). PR open -> merge was ~13 min.
- 7 required compose vars: INFLUXDB_TOKEN, INFLUXDB_PASSWORD, POSTGRES_PASSWORD, JWT_SECRET_KEY, ADMIN_PASSWORD, HOMEIQ_MCP_READ_TOKENS, GF_SECURITY_ADMIN_PASSWORD. Reference = infrastructure/env.example (NOT .env.example, a stub missing all 7).
- Do NOT add `--project-directory` to the E2E compose call: `env_file: ../../.env` resolves relative to the compose FILE.
- A real .env exists at repo root (gitignored) — do not overwrite it.
- workflows README is load-bearing: check-workflow-enablement.sh derives its set from it (floor 15, now 20).
- Other projects share this Docker daemon (agentforge, tapps-brain, nltmarketing, newcompanyideas). Their volumes/networks are out of scope per agent-scope.md. NEVER prune `zigbee2mqtt_data` (Zigbee pairing keys) or `ha_config`.

## Success criterion
- CI carries only checks that can actually pass; every remaining red is a real defect with an owner.
