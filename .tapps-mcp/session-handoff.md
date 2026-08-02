# Session Handoff — HomeIQ go-live continuation

**Updated:** 2026-08-02T20:29:33Z
**Repo:** `/home/wtthornton/code/HomeIQ` · branch `master` (master IS main; `origin/HEAD -> origin/master`)
**HEAD at handoff:** `c3fa1e10` — pushed, `0` ahead / `0` behind, working tree clean

## Where things stand

Two epics closed this session: **TAP-5433** (17 dashboard paths reaching no backend route) and **TAP-5424** (12 REST-registry callers migrated to `homeiq_ha.client.HAWebSocketClient`).

Verified state:

1. Contract gate `bash scripts/verify-dashboard-contract.sh` — **79/79, 0 deviations, exit 0** (was 36/36)
2. REST registry call sites — **0**, down from 21
3. Source files importing `homeiq_ha.client` — **10**, up from 0
4. `libs/homeiq-ha` — 99 passed · `websocket-ingestion` — 522 passed
5. 58 containers healthy, none restarting

## START HERE — six containers are running stale code

**This is the first task and it blocks the truth of the TAP-5424 close-out.** The migration is committed and pushed but was never deployed. These six still run the pre-migration REST code:

```
homeiq-ai-training-service
homeiq-device-context-classifier
homeiq-device-health-monitor
homeiq-device-recommender
homeiq-device-setup-assistant
homeiq-ha-ai-agent-service
```

Only `admin-api`, `health-dashboard`, `data-api` and `websocket-ingestion` were rebuilt.

**Rebuild each with:**

```bash
docker compose -f domains/<domain>/compose.yml --env-file .env --profile production up -d --build <service>
```

**Expect trouble, and watch for it.** These six pull `homeiq-ha` for the first time on this build. `libs/homeiq-ha/client/ws.py:26` imports `websockets.asyncio`, which does not exist in `websockets` 12.0. `websocket-ingestion` crash-looped on exactly this with `ModuleNotFoundError: No module named 'websockets.asyncio'` until its pin was raised. If a rebuilt service crash-loops, that is the cause — raise its pin to `>=13.0,<17.0.0`.

Pins already raised: `requirements-base.txt`, `websocket-ingestion`, `device-intelligence-service`, `ha-ai-agent-service`. The others carry no explicit `websockets` pin, so they should resolve `>=13.0` from `homeiq-ha` — **verify rather than assume**.

**Verify by identity, not exit code.** Several compose services declare `build:` with no `image:`, so a successful `docker buildx bake` is not what compose runs. After each rebuild compare the running container's image id to the one just built, or assert a sentinel string from the new source inside the running container:

```bash
docker inspect --format '{{.Image}}' <container>
docker exec <container> grep -c 'homeiq_ha.client' /app/src/<file>.py
```

Then re-run the contract gate and confirm 58 healthy.

## Then, in order

### 1. File the unfiled defects

The energy 5xx cluster and two no-route families are described **inside TAP-5434's body but have no issues of their own** and will be lost there:

1. `/api/v1/energy/circuits|correlations|statistics|top-consumers|device-impact` — all 500 (5 routes)
2. `/api/v1/events/search` — called by the frontend, no route on either backend
3. `/api/v1/integrations/{service}/config` — same
4. `/api/v1/ha/game-context/{team}` and `/game-status/{team}` — 500
5. `/api/v1/hygiene/issues` — reaches data-api after this session's nginx fix, but 500s
6. `/api/v1/docker/containers/{name}/logs` — 500

Route Linear writes through the **`linear-issue` skill** (hook-gated on a `docs_validate_linear_issue` sentinel < 30 min old). Assignee `Claude Agent` = `9083b7a1-3fd3-479b-98f1-1f8a782ae10a`.

### 2. Clear the DB provisioning defects

**TAP-5437** — no `memory` schema in Postgres; every `/api/v1/memories/*` route 500s. **TAP-5438** — `patterns` table missing; three ai-automation routes 500. Both likely quick. TAP-5438 has two candidate root causes — missing table vs missing schema qualification — and the issue says do not guess between them.

### 3. Grow the contract gate

**TAP-5434** reaches 88+ rows naturally as the above defects die. Rows are only added for endpoints observed behaving correctly — do not assert a broken family at 200 (makes the gate red for causes it cannot fix) or at its current 5xx (freezes breakage into the contract). The policy is recorded in the script header.

### 4. Close the confidence gaps

- **data-api's DB-backed suite does not run** — PostgreSQL auth fails locally (`asyncpg.exceptions.InvalidPasswordError` for user `homeiq`), so a Tier-1 service is unverified. Its unit tests use the `*_unit.py` naming its conftest honours to skip DB setup.
- **No stale-image guard.** The six stale containers were found by hand. Add a CI check comparing image build time against last source commit for that service directory — this is the systemic fix for the class of bug that left `websocket-ingestion` broken unnoticed.

## Blocked on the human — the actual HA go-live path

Nothing this session touched live Home Assistant; every `apply` is an Autonomy hard-stop.

1. **TAP-5427 (Urgent)** — set the backup encryption key and take the first backup. UI-only.
2. **TAP-5429** — apply phases 3 to 6 live; blocked on TAP-5427's backup gate.
3. **TAP-5430** — recorder/http/automation-editor recipes; needs the file-editor add-on.
4. **TAP-5431** — Local Calendar and Powercalc; needs HACS GitHub device auth.

## Not go-live, do not let these blur the finish line

TAP-5283 (58 → ~11 containers), TAP-5284 (HA integration with scoped LLM API), TAP-5285 (AgentForge genes), TAP-5286 (safety and cost governance).

## Environment quirks that will bite

1. **Host-port overrides:** dashboard **13000**, admin-api **18004**, websocket **18001**, postgres **15432**, ai-automation-ui **13001**. Not the documented defaults.
2. **Test runner is `.venv/bin/python -m pytest`.** System `python3` has no pytest and produces a false "no module" failure. `.venv` has no `pip`; use `uv pip`.
3. **`ruff` is at `/home/wtthornton/.local/bin/ruff`**, not in `.venv`.
4. **Do not lower `CONTRACT_PACE`** in the contract script — admin-api rate limits at 60 req/min burst 20 and an unpaced sweep produces false 429s. `CONTRACT_TIMEOUT` is 15 because `/api/v1/real-time-metrics` answers at ~10.0s (TAP-5439).
5. **Never use `git stash` for a quality-gate baseline.** Use `git worktree add` or `git show HEAD:path`. A second agent session shared this working tree on 2026-08-01 and its stash/checkout/cherry-pick destroyed ~9 uncommitted edits. Check `git log`/`reflog` for a second writer before a long run, and commit early.
6. **Quality-gate baselines are location-sensitive.** Scoring a copy at repo root inflates `devex` to 10 because `AGENTS.md` sits there; the same file five levels down scores 0. Compare at equal directory depth, or use an untouched sibling as the control. Related: `tapps_quick_check`'s cache is keyed on content alone and will return another file's path and score for identical content at a different path.
7. **Always end with `tapps_validate_changed` over the whole changed set.** ruff F821 caught a `NameError` introduced this session that a unit test missed because it only covered the extracted helper.

## Tooling defects filed upstream

**TAP-5442** — `tapps_memory` `architectural` and `pattern` tier writes return success and do not persist; only `context` does. `health` reports `entry_count: 0` while entries are retrievable, and `search` returns nothing for entries `get` can fetch. Both tapps-mcp and tapps-brain are being fixed.

Paste-ready reports: `prompts/tapps-mcp-defects-from-homeiq-2026-08-02.md` and `prompts/tapps-brain-defects-from-homeiq-2026-08-02.md`.

**Consequence for this handoff:** session learnings live in `homeiq-session-learnings-2026-08-02` under the `context` tier, which has a 14-day half-life and expires around **2026-08-16**. This file is the durable record; do not rely on brain recall.

## Open issues at handoff

TAP-5434, TAP-5437, TAP-5438, TAP-5439, TAP-5440, TAP-5442 · human-gated TAP-5427, TAP-5429, TAP-5430, TAP-5431 · epics TAP-5283, TAP-5284, TAP-5285, TAP-5286
