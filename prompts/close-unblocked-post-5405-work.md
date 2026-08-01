# Close the three unblocked issues left after TAP-5405

> Generated 2026-08-01 immediately after the TAP-5405 close-out. Scoped to a **~6-hour
> autonomous run**. Run from an orchestrator session in `/home/wtthornton/code/HomeIQ`.
>
> **Everything here is unblocked.** No human gate, no live-Home-Assistant write, no
> cross-project write. If you find yourself waiting on a person, you have wandered
> out of scope — re-read Sub-goal 0.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/close-unblocked-post-5405-work.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one sub-goal per run) so it survives the terminal.

## Objective

Fix the 17 dashboard paths that reach no backend route, grow the contract gate to cover
what the frontend actually calls, and migrate the REST-registry callers onto the shared
WebSocket client — leaving TAP-5433, TAP-5434 and TAP-5424 Done or honestly partial.

## Where this stands (verified 2026-08-01T22:3x, not narrated)

| Fact | Evidence |
|---|---|
| TAP-5405 + all 9 children | **Done** — `ccb487c5`, `86b43836`, `32466d75` |
| `libs/homeiq-ha` suite | 99 passed, 0 failed |
| Contract gate | 36/36, 0 deviations, exit 0 |
| TAP-5433 (17 broken paths) | **Backlog, Urgent** — 7 prefix mismatches + 10 no-route |
| TAP-5434 (coverage 36 of 84) | **Backlog, High** |
| TAP-5424 (registry migration) | **Backlog, Urgent** — 21 sites / 12 files / 7 domains / 7069 lines |
| `homeiq_ha.client` importers in `domains/` | **zero** — `grep` returns nothing |
| Live HA | untouched, `diff` = 0 differences; **keep it that way** |

**Explicitly out of scope — human-gated, do not attempt:** TAP-5427 (backup encryption
key, UI-only), TAP-5429 (live apply of phases 3–6, blocked on 5427), TAP-5430
(recorder/http/automation-editor, needs the file-editor add-on), TAP-5431 (Local
Calendar/Powercalc, needs HACS GitHub device auth). Touching these burns the run.

## Standing constraints

- **🔴 The live Home Assistant at `192.168.1.80` is a real home.** Read-only `audit` /
  `check` / `plan` is permitted. **Any `apply` is an Autonomy hard-stop** — no phase is
  authorized in this run, and the backup gate would refuse anyway. Never weaken
  `BackupGateNotSatisfied` to make something run.
- **Never commit a secret.** `.env` is gitignored and stays that way. `backup/config/info`
  returns the HA encryption key in plaintext — never log it, never paste it into Linear.
- **Scope is this repo only.** Linear team `TappsCodingAgents`, project `HomeIQ`, assignee
  `Claude Agent` (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes are
  forbidden (`agent-scope.md`) — and note TAP ids are workspace-wide sequential, so an
  unverified id can resolve into another project.
- **No green-by-suppression.** Never skip, disable, `# noqa`, `# type: ignore`, or weaken
  a test or checker to go green. If the correct fix is out of scope, stop and say so.
- **Verify every inherited TAP id with `get_issue` before citing it** — confirm both
  existence *and* the `project` field.

## Done-when (ground truth, not narration)

**All six artifacts pasted in one final iteration:**

1. `git status --short` clean, plus `git log --oneline` showing this run's commits.
2. `.venv/bin/python -m pytest libs/homeiq-ha -q` showing **≥99 passed, 0 failed, 0 errors**
   — the count must **not shrink** below today's 99.
3. `bash scripts/verify-dashboard-contract.sh` exits 0 with **0 deviations at ≥88 rows**
   (today's total is 36; the enumerated frontend set is 84 families). A run that still
   reports 36/36 has not done sub-goal 2. **The row count must go up.**
4. For each of the 17 TAP-5433 families: **either** a pasted non-404 status against the
   running stack, **or** a one-line recorded reason the client call was removed instead,
   with the commit that removed it. No family silently dropped.
5. `grep -rn 'api/config/entity_registry\|api/config/device_registry\|api/config/area_registry' domains/ --include=*.py`
   returning **no application call sites**, **AND** `grep -rln 'homeiq_ha.client' domains/`
   returning **≥ the number of services migrated** (today: 0). Both clauses required —
   the first alone is satisfiable by deleting the callers.
6. Linear result showing TAP-5433, TAP-5434, TAP-5424 each **Done, or still open with a
   pasted written statement of exactly what remains and why**. Every id confirmed by
   `get_issue` before it is cited.

> **A stale-image run does not count.** Artifacts 3 and 4 must be produced against a
> stack rebuilt from the current working tree — see Sub-goal 0.

## Sub-goals (sequential; each a checkpoint)

**0. Establish preconditions (self-healing — the loop does this, not the user).**
   - `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks all other
     `tapps_*` MCP tools until this runs. Re-run after any `/clear` or compact.
   - Brain recall: `tapps_memory(action="search", query="homeiq registry migration dashboard contract")`.
     The CLI (`uv run tapps-mcp memory search`) is **broken** — it raises
     `ValueError: MemoryStore requires a Postgres private_backend`. Use the MCP tool.
   - Test runner: **`/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`**. System
     `python3` has **no pytest** and produces a false "no module" failure.
   - Stack health: `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c healthy`
     should be **58**. If not, `bash scripts/domain.sh start <domain>` for the gap.
   - **Host-port overrides are in effect** (this box runs other stacks): dashboard **13000**,
     admin-api **18004**, websocket **18001**, postgres **15432**, retention **18080**,
     carbon **18010**, OTLP **14317/14318**, jaeger UI **16687**, ai-automation-ui **13001**.
     Never assume the documented defaults.
   - **Artifact identity — merged ≠ live, and built ≠ loaded.** Several compose services
     declare `build:` with **no `image:`**, so `docker buildx bake` output is *not* what
     compose runs. After any source change:
     `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`.
     Then verify by **identity**, not by exit code: compare the running container's image
     id to the one just built, or assert a sentinel string from the new source inside the
     running container. `docker buildx bake` requires **`-f docker-bake.hcl`**.
   - **Smoke before spend:** after any rebuild, curl the rebuilt service's `/health` and one
     cheap end-to-end call before running the contract sweep.
   - **Harness compatibility** (bake these in, do not fight them):
     - `save_issue` is PreToolUse-gated on a `docs_validate_linear_issue` sentinel **< 30 min
       old**. Route Linear writes through the **`linear-issue` skill**; re-validate if the
       loop has run > 30 min since the last validation.
     - `list_issues` is PreToolUse-gated on a prior `tapps_linear_snapshot_get`. Route
       multi-issue reads through **`linear-read`**; single issues use `get_issue(id=...)`.
       `state="open"` is a tapps-mcp cache bucket — pass it to `snapshot_get`/`snapshot_put`,
       **never** to the plugin's `list_issues`.
     - `PostToolUse` on Edit/Write nudges a per-edit quality check — **adopted for `src/`
       Python edits** (`tapps_quick_check`, ~200 ms), **overridden to story-gate batching**
       for test files, TypeScript, shell and markdown. State this once; do not re-litigate.
   - proof: session_start returned; 58 healthy pasted; pytest runs; a rebuilt container's
     image id matches the freshly built one.

**1. TAP-5433 — the 17 paths that reach no backend route.** Highest value: these are live
   defects, not coverage gaps. Two distinct classes, handled differently:
   - **7 prefix mismatches** (mechanical). nginx rewrites `/ai-automation/(.*)` → `/$1`
     (`nginx.conf:515-520`) but the routers mount at `/api/...`
     (`analysis_router.py:19`), so the client must include the `/api` segment. Fix in
     `health-dashboard/src/services/api.ts` at :831, :835, :841, :850, :864, :891, :896.
   - **10 with no route at all** — each needs a *decision*: implement server-side, or
     remove the client call. Both are valid outcomes; record which and why per family.
     Includes `/api/v1/health/services/:name`, `/api/v1/memories/stats` (shadowed by
     `/{memory_id}` at `memory_endpoints.py:326`), `/api/v1/memories/consolidation/status`,
     and six `/ai-automation/*` paths.
   - Also: the `anomaly` router (`ai-pattern-service/src/anomaly/routes.py:17`) is defined
     but never `include_router`'d in `main.py:201-250` — register it or remove
     `AnomalyAlertsPanel`. And `TeamScheduleView.tsx:56` calls `dataApi.getTeamSchedule`,
     which does not exist on `DataApiClient`.
   — proof: per family, a pasted non-404 against the running stack **or** the removal commit.

**2. TAP-5434 — grow the contract gate from 36 to ≥88 rows.** Do this *after* sub-goal 1,
   or you will encode today's breakage as the expected contract.
   - The script is table-driven: tab-separated rows at `verify-dashboard-contract.sh:47-82`,
     read loop at `:118-140`. Adding coverage = adding rows.
   - **It only issues GETs.** Either add a way to express POST/PUT families, or record
     explicitly in the header comment that non-GET coverage is out of scope and why.
   - Replace the 4 rows that probe paths the frontend never calls (`:56`, `:58`, `:69`,
     `:70`) with the parameterised paths it does call.
   - **Rate limit is real:** admin-api limits at 60 req/min burst 20 and the script paces at
     `CONTRACT_PACE` (default 1.1s). At ~88 rows the sweep takes ~1.6 min. Do **not** lower
     the pace to speed it up — an unpaced sweep produces false 429s that look like failures.
   — proof: script exits 0, 0 deviations, at ≥88 rows.

**3. TAP-5424 — migrate the REST-registry callers.** The biggest chunk; expect it to consume
   the remainder of the run and possibly not finish. **Partial is fine if honest** — see
   Done-when 6.
   - 21 call sites, 12 files, 7 domains. Migrate onto `homeiq_ha.client.HAWebSocketClient`.
   - **Order matters — cheapest and least coupled first**, so a truncated run still lands
     whole services: `device-recommender` → `device-setup-assistant` (×2 files) →
     `device-context-classifier` → `device-health-monitor` → `ha-ai-agent-service` →
     `ha-setup-service` (×2) → `ai-training-service` → `device-intelligence-service` →
     `websocket-ingestion` → `data-api/devices_endpoints.py` **last**.
   - `devices_endpoints.py:2263-2268` is the hard one: its DB fallback masks the 404 as
     stale data. Removing it changes failure semantics — that is the one site that needs
     real judgement, not a mechanical swap.
   - **Three services have no `tests/` directory** and TAP-5424's acceptance requires a test
     per migrated service: `device-recommender`, `device-setup-assistant`,
     `device-context-classifier`. Creating those suites is part of the work, not a surprise.
   - **New finding to fold in:** `api-automation-edge/src/clients/ha_websocket_client.py:23`
     defines its *own* `HAWebSocketClient` on raw `websockets`. Converging it is in scope.
   — proof: the two-clause grep from Done-when 5, plus each touched service's suite passing.

**4. Close out.** Run the full Done-when set. Via the **`linear-issue` skill**: close what is
   done; for anything partial, update the body with exactly what remains and why. Record
   learnings to the brain, including any mechanism that fought you.

## Plane map (mechanism + model tier per chunk)

| Step | Plane | Mechanism | Model tier | Notes |
|---|---|---|---|---|
| Re-confirm issue ids + current stack state | coordination | 1 subagent | cheap / low effort | read-only; ids have been wrong before |
| TAP-5433 route research (10 no-route families) | coordination | **4 parallel `Explore` subagents** | cheap / low effort | read-only; independent per family |
| TAP-5433 prefix fixes (7 sites) | execution | **in-session, sequential** | cheap / low effort | mechanical string edits |
| TAP-5433 no-route decisions | execution | **in-session, sequential** | **frontier / high effort** | implement-vs-remove is a judgement call |
| TAP-5434 row authoring | execution | **in-session, sequential** | cheap / low effort | table rows; verify by running the script |
| TAP-5424 per-service migration | execution | **in-session, sequential, one service at a time** | cheap for the 10 mechanical sites; **frontier** for `devices_endpoints.py` | **N=1.** Do not fan out — each service is coupled to its own tests and container |
| Per-sub-goal verification | coordination | **verifier subagent, fresh context** | **frontier / high effort** | re-runs the check; refutes the claim |
| Final verification | coordination | **3 verifier subagents, perspective-diverse** | **frontier / high effort** | correctness · no-secret-no-HA-residue · reproducibility |
| Linear writes / multi-reads | coordination | **`linear-issue` / `linear-read` skills** | cheap | hook-gated; the skills handle the sentinels |

## Loop

- **State:** `git log --oneline -5`; `git status --short`; contract script score; the three
  issues via `linear-read`; brain recall of prior failures.
- **Decide:** lowest-numbered sub-goal not yet verified-done. One at a time.
- **Execute:** on the committed mechanism above. Code edits sequential, in-session. After
  each `src/` Python edit run `tapps_quick_check`; at each sub-goal gate run
  `tapps_validate_changed` with explicit `file_paths`.
- **Verify (independent):** spawn a **fresh-context verifier subagent (frontier)** told to
  **refute** the sub-goal's proof. Hand it the **exact command, the expected artifact, the
  `file:line` anchors, and the environment quirks** — port 13000 not 3000, `.venv/bin/python`
  not `python3`, `set -a && . ./.env` for HA credentials, `CONTRACT_PACE` must not be
  lowered. Never hand it your narration. Its report must quote the output it observed, and
  **its verdict advances the loop, not the executor's claim.**
- **On fail:** diagnose — read the actual error, inspect state, recall prior failures — then
  hypothesis → fix → retry *with something changed*. ≤3 distinct strategies per sub-goal,
  then escalate once, then stop with a concise diagnosis. **Never re-run the same action on
  the same error.**
- **Record:** `tapps_memory(action="save", key=<slug>, tier="pattern", value="<outcome incl. what failed and why>")`.
- **Context hygiene:** prune stale reads each iteration; prefer targeted `grep` over a full
  re-`Read`; carry a compact state summary forward, not raw transcripts. Delegate noisy
  multi-file reading to a subagent and keep only its summary.
- **Print every iteration:**
  `SCORE: contract <pass>/<total> · broken-paths fixed <n>/17 · services migrated <n>/12 · pytest <fail> failures · sub-goal <k>/4 · iteration <i>/45`
- **Repeat or stop:** until Done-when holds; caps **45 iterations** AND **1.5M output tokens**.

## Guardrails

- **Termination:** the Done-when artifact set; caps 45 iterations AND 1.5M output tokens.
- **No green-by-deletion:** Done-when 3 requires the contract row count to **grow** past 36,
  and Done-when 5 pairs "zero REST registry callers" with "≥N services importing
  `homeiq_ha.client`". Neither is satisfiable by removing the thing being measured.
- **Caps must not fire on correct behaviour:** removing a client call that has no backend
  route is a **correct** outcome for a TAP-5433 family, not a failure — Done-when 4 accepts
  it. A contract row asserting a deliberate `404 (decided)` is likewise correct. Do not let
  a verifier score either red.
- **🔴 No live-HA writes.** Read-only only. Any `apply` is an Autonomy hard-stop.
- **Independent verification** — a verifier that did not do the work, handed the proof
  command rather than the claim, judged against ground truth.
- **No fan-out of coupled coding** — the 12 service migrations are sequential, in-session,
  N=1. Fan-out is for research and verification only.
- **Context hygiene** — targeted `grep` over full re-`Read`; compact state summary forward.
- **Scope:** `/home/wtthornton/code/HomeIQ` only. Linear team `TappsCodingAgents`, project
  `HomeIQ`, assignee `Claude Agent`. Cross-project writes forbidden; verify every TAP id's
  `project` field before citing it.
- **Secrets:** `.env` stays gitignored; never commit a key; never log the HA encryption key.
- **Memory:** recall at start, record at every checkpoint including failures.
- **Harness compatibility:** `tapps_session_start` before any `tapps_*` call · `linear-issue`
  skill for every write (30-min sentinel) · `linear-read` for every multi-issue read ·
  per-edit quality nudge **adopted** for `src/` Python, **overridden to sub-goal-gate
  batching** for tests, TypeScript, shell and markdown.
- **Discipline:** root-cause not workarounds; **no green-by-suppression**; right-sized;
  durable over expedient; match repo conventions; no silent scope creep. If the correct fix
  is out of scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR, staged diff)
  and keep going; the human reviews async. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** any `apply` against the live
  Home Assistant · a write outside this repo's team/project · merge to `master` ·
  force-push · deleting un-recreatable data · removing a backend route that another service
  still consumes · a genuinely ambiguous decision where a wrong guess is expensive.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior failures → form a
specific hypothesis → change something → retry. ≤3 distinct strategies per sub-goal, then one
escalation, then stop with a concise diagnosis naming what you tried and why each failed.

## Unverified assumptions

Confirm each before depending on it — all three come from a research subagent's static
analysis, not an observed runtime.

- **The 84-family enumeration and the 36-row baseline.** Basis: one research subagent; I
  spot-verified 5 of its highest-consequence claims against source (row count, the
  `/api/analysis` prefix, the unregistered anomaly router, the missing `/stats` route, the
  missing `/health/services/{name}`) and all held. The remaining ~79 families are unverified
  individually. **Confirm by:** re-deriving the frontend call set with a fresh grep before
  authoring rows, rather than trusting the list wholesale.
- **`/api/integrations/:platform/analytics` and `/performance` may be unreachable** because
  `nginx.conf:131` uses `proxy_pass http://data_api/api/integrations;` with no
  `$request_uri`, which can drop the sub-path. Basis: static read of nginx config only.
  **Confirm by:** `curl -s -o /dev/null -w '%{http_code}' http://localhost:13000/api/integrations/hue/analytics`.
- **The 7 `/ai-automation/*` prefix fixes will return non-404 once `/api` is added.** Basis:
  reading the router prefix and the nginx rewrite, not a request. **Confirm by:** curling one
  fixed path against the running stack before editing the other six.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` · assignee `Claude Agent`
- Issues: **TAP-5433** (Urgent) · **TAP-5434** (High) · **TAP-5424** (Urgent)
- Evidence: `docs/operations/dashboard-triage-2026-08-01.md` · `docs/ha-init-agent-design.md`
- Shared client: `libs/homeiq-ha/src/homeiq_ha/client/` — `HAWebSocketClient`, proven live
  (164 entities, 19 devices), imported by zero services today
- Prior learnings: `tapps_memory(action="search", query="homeiq registry migration dashboard contract")`

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in a new session.
- **Fan-out sub-step:** none committed. The only parallel work is read-only research
  (TAP-5433 route discovery) and verification — both plain subagents, no Workflow script.
  The 12 service migrations are coupled to their own tests and are sequential, N=1.
