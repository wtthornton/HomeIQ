# HomeIQ backlog burndown — all 6 open epics, dependency-ordered

> Generated 2026-08-01 after reading the **complete** open HomeIQ backlog: 6 epics and
> ~40 open stories. Supersedes `prompts/close-unblocked-post-5405-work.md`, which covered
> only 3 of them — keep that file for the narrow run, use this one for the backlog.
>
> **This is a multi-run loop.** One ~6-hour session finishes Wave 1 and starts Wave 2.
> Re-enter it as a Routine until the backlog is empty. Each wave is a resumable checkpoint.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-backlog-burndown.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Wave 0; work the lowest-numbered unfinished wave only; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one wave per run) so it survives the terminal.

## Objective

Burn down the HomeIQ backlog in dependency order — fix the build/CI harness first, then
the unblocked correctness defects, then the MCP tool surface, then the AgentForge genome
and safety gate, then the Home Assistant front door, and only then the data-plane collapse.

## The full backlog (read 2026-08-01T22:4x — every open issue, nothing omitted)

**Wave 1 · TAP-5281 Build decoupling and CI restoration** (Urgent) — 5287 · 5288 · 5289 · 5290 · 5291
**Wave 2 · Unblocked correctness** — TAP-5433 (Urgent) · TAP-5434 (High) · TAP-5424 (Urgent)
**Wave 3 · TAP-5282 HomeIQ MCP server as the single tool surface** (Urgent) — 5292 · 5293 · 5294 · 5295 · 5296 · 5297
**Wave 4 · TAP-5285 AgentForge species four** (High) — 5311 · 5312 · 5313 · 5314 · 5315 · 5316 · 5317 · 5318
**Wave 5 · TAP-5286 Automation safety gate and cost governance** (High) — 5319 · 5320 · 5321 · 5322 · 5323 · 5325
**Wave 6 · TAP-5284 Home Assistant integration with scoped LLM API** (High) — 5305 · 5306 · 5307 · 5308 · 5309 · 5310
**Wave 7 · TAP-5283 Data plane collapse, 58 containers to about 11** (High) — 5298 · 5299 · 5300 · 5301 · 5302 · 5303 · 5304

**Parked — human-gated, do NOT attempt:** TAP-5427 (backup encryption key, UI-only) ·
TAP-5429 (live HA apply, blocked on 5427) · TAP-5430 (needs the file-editor add-on) ·
TAP-5431 (needs HACS GitHub device auth). Touching these burns the run.

**Closed, do not reopen:** TAP-5405 + children 5406–5412 · TAP-5413 + children 5414–5418.

### Why this order (measured, not assumed)

- **Wave 1 is the foundation and is worse than the issue titles suggest.** All **54** service
  build contexts are `context: ../..` — the repo root — so a one-line change anywhere busts
  every service's Docker cache. `scripts/start-stack.sh:91` then runs
  `up -d --build --pull always --force-recreate`, rebuilding all 54 on every start. And the
  ten domain CI workflows (`ci-core`, `ci-devices`, `ci-ml`, `ci-automation`, `ci-collectors`,
  `ci-pattern-analysis`, `ci-blueprints`, `ci-energy-analytics`, `ci-frontends`,
  `ci-dashboard-contract`) trigger on **push to master/main only — none on `pull_request`**,
  so no PR gets domain CI. Every later wave pays this tax on every iteration; fix it first.
- **Wave 3 gates Waves 4–7.** The MCP tool catalogue is what the genes call, what the HA
  integration exposes, and what replaces the services Wave 7 deletes.
- **Wave 5 depends on Wave 4** — the safety gate wires a judging gene into a chromosome that
  Wave 4 authors.
- **Wave 7 is last because it is destructive.** Deleting 47 containers before their
  capabilities exist as MCP tools or genes turns a consolidation into an outage.

## Standing constraints

- **🔴 The live Home Assistant at `192.168.1.80` is a real home.** Read-only `audit` /
  `check` / `plan` only. **Any `apply` is an Autonomy hard-stop.** Never weaken
  `BackupGateNotSatisfied` to make something run.
- **Never commit a secret.** `.env` stays gitignored. `backup/config/info` returns the HA
  encryption key in plaintext — never log it, never paste it into Linear. Waves 5 and 7 both
  move a model-provider credential into the AgentForge vault; that is a *move*, never a copy
  into the repo.
- **Scope is this repo only.** Linear team `TappsCodingAgents`, project `HomeIQ`, assignee
  `Claude Agent` (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes forbidden
  (`agent-scope.md`). TAP ids are workspace-wide sequential — verify every id's `project`
  field with `get_issue` before citing it.
- **No green-by-suppression.** Never skip, disable, `# noqa`, `# type: ignore`, or weaken a
  test or checker to go green. If the correct fix is out of scope, stop and say so.
- **Never delete a capability to hit a count.** Waves 1 and 7 both measure things going down.
  See the paired clauses in Done-when.

## Done-when (ground truth, not narration)

The backlog is empty when **every** wave's clause holds. A single run satisfies the waves it
reached; paste the artifacts for those and the current SCORE line for the rest.

1. **Wave 1** — `grep -rh -A1 'build:' domains/*/compose.yml | grep -c 'context: \.\./\.\.'`
   returns **0**, **AND** `docker compose config --services` across the domain files still
   lists **≥54 services** (so contexts were scoped, not services deleted). `start-stack.sh`
   no longer forces `--build --pull always --force-recreate`. **≥10 domain workflows carry a
   `pull_request:` trigger** — a count that must rise from today's 0.
2. **Wave 2** — `bash scripts/verify-dashboard-contract.sh` exits 0 with **0 deviations at
   ≥88 rows** (today 36 — must rise). Each of the 17 TAP-5433 families shows a pasted
   non-404 **or** a recorded removal reason. `grep -rn 'api/config/entity_registry\|api/config/device_registry\|api/config/area_registry' domains/ --include=*.py`
   returns no application call sites **AND** `grep -rln 'homeiq_ha.client' domains/` returns
   **≥12** (today 0) — both clauses required, the first alone is satisfiable by deletion.
3. **Wave 3** — the `homeiq` MCP server answers `/health`, and a pasted tool call returns real
   data for **≥1 query tool and ≥1 analytics tool**. Contract tests pin the schemas.
4. **Wave 4** — every authored gene and chromosome passes offline kit validation, pasted.
5. **Wave 5** — a pasted run showing the hard-deny list **refusing** a denied automation, and a
   budget gate **holding** a plan that exceeds its cap. A correct refusal is a pass, not a failure.
6. **Wave 6** — the HA custom integration loads on the live instance **read-only**, and
   `/api/config/config_entries` shows the HomeIQ entry `loaded`. Installing it is a write —
   Autonomy hard-stop before that step.
7. **Wave 7** — `docker ps --filter name=homeiq | grep -c healthy` is **≤15 and ≥8**, **AND**
   for every retired service a pasted call proves its capability still reachable through an
   MCP tool or a gene. The second clause is mandatory: without it the target is met by
   deleting functionality.
8. **Always** — `.venv/bin/python -m pytest libs/homeiq-ha -q` shows **≥99 passed, 0 failed**
   (must not shrink), `git status --short` is clean, and every cited TAP id was confirmed by
   `get_issue`.

## Wave 0 — Establish preconditions (self-healing — the loop does this, not the user)

- `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks all other
  `tapps_*` MCP tools until this runs. Re-run after any `/clear` or compact.
- Brain recall: `tapps_memory(action="search", query="homeiq build contexts CI MCP server genes data plane")`.
  The CLI (`uv run tapps-mcp memory search`) is **broken** — raises
  `ValueError: MemoryStore requires a Postgres private_backend`. Use the MCP tool.
- Test runner: **`/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`**. System `python3`
  has **no pytest** and yields a false "no module" failure.
- Stack health: `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c healthy`
  should be **58** *until Wave 7 deliberately reduces it*. If low before Wave 7,
  `bash scripts/domain.sh start <domain>`.
- **Host-port overrides are in effect** (this box runs other stacks): dashboard **13000**,
  admin-api **18004**, websocket **18001**, postgres **15432**, retention **18080**, carbon
  **18010**, OTLP **14317/14318**, jaeger UI **16687**, ai-automation-ui **13001**.
- **Artifact identity — merged ≠ live, and built ≠ loaded.** Several compose services declare
  `build:` with **no `image:`**, so `docker buildx bake` output is *not* what compose runs.
  After any source change:
  `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`.
  Verify by **identity** — compare the running container's image id to the one just built, or
  assert a sentinel string from the new source inside the running container — never by the
  build's exit code. `docker buildx bake` requires **`-f docker-bake.hcl`**.
  *(Wave 1 is largely the permanent fix for this trap.)*
- **Smoke before spend:** after any rebuild, curl the service's `/health` plus one cheap
  end-to-end call before running a sweep.
- **AgentForge reachability** (Waves 3–5): confirm the `mcp__agentforge__health` tool responds
  before authoring genes or registering the MCP server. If it is unreachable, Waves 4–5 are
  blocked — record that and move to a wave that is not.
- **Harness compatibility** (bake in, do not fight):
  - `save_issue` is PreToolUse-gated on a `docs_validate_linear_issue` sentinel **< 30 min old**.
    Route Linear writes through the **`linear-issue` skill**; re-validate if > 30 min have passed.
  - `list_issues` is PreToolUse-gated on a prior `tapps_linear_snapshot_get`. Route multi-issue
    reads through **`linear-read`**; single issues use `get_issue(id=...)`. `state="open"` is a
    tapps-mcp cache bucket — pass it to `snapshot_get`/`snapshot_put`, **never** to `list_issues`.
  - `PostToolUse` on Edit/Write nudges a per-edit quality check — **adopted for `src/` Python
    edits** (`tapps_quick_check`, ~200 ms), **overridden to wave-gate batching** for tests,
    TypeScript, YAML, shell and markdown. State once; do not re-litigate.
- **Reconcile the duplicate before Wave 5.** TAP-5298 ("Delete openai-service and move the
  provider credential into the AgentForge vault", child of 5283) and TAP-5322 ("Move the model
  provider credential into the AgentForge vault", child of 5286) overlap on the same credential
  move. Decide which owns it, note it on the other, and do it once.
- proof: session_start returned; healthy count pasted; pytest runs; a rebuilt container's image
  id matches the freshly built one; AgentForge health pasted or recorded unreachable.

## Plane map (mechanism + model tier per chunk)

| Step | Plane | Mechanism | Model tier | Notes |
|---|---|---|---|---|
| Re-read backlog state each wave | coordination | **`linear-read` skill** | cheap | hook-gated, cache-first |
| Wave 1 compose-context scoping (54 services) | execution | **in-session, sequential per domain file** | cheap / low effort | mechanical; verify by cache behaviour, not by diff |
| Wave 1 CI trigger restoration (10 workflows) | execution | **in-session, sequential** | cheap / low effort | add `pull_request:` beside `push:`; keep the paths filters |
| Wave 2 route research (10 no-route families) | coordination | **4 parallel `Explore` subagents** | cheap / low effort | read-only, independent per family |
| Wave 2 registry migration (12 services) | execution | **in-session, sequential, one service at a time** | cheap for the 10 mechanical sites; **frontier** for `data-api/devices_endpoints.py` | **N=1** — each service is coupled to its own tests and container |
| Wave 3 MCP tool catalogue + schemas | execution | **in-session, sequential** | **frontier / high effort** | schema design is load-bearing for Waves 4–7 |
| Wave 3 tool implementations | execution | **in-session, sequential** | cheap / low effort once the schema is fixed | |
| Waves 4–5 gene / chromosome / skill authoring | execution | **in-session, sequential** | **frontier / high effort** | safety semantics; a wrong deny-list is expensive |
| Wave 6 HA integration scaffold | execution | **in-session, sequential** | **frontier / high effort** | installing on the live instance is a hard-stop |
| Wave 7 service retirement | execution | **in-session, sequential, one service at a time** | **frontier / high effort** | destructive; each deletion needs its replacement proven first |
| Per-wave verification | coordination | **verifier subagent, fresh context** | **frontier / high effort** | re-runs the check; refutes the claim |
| Final verification per wave-completion | coordination | **3 verifier subagents, perspective-diverse** | **frontier / high effort** | correctness · security/no-residue · reproducibility |
| Linear writes | coordination | **`linear-issue` skill** | cheap | hook-gated; the skill handles the sentinel |

## Loop

- **State:** `git log --oneline -5`; `git status --short`; the backlog via **`linear-read`**;
  contract score; healthy-container count; brain recall of prior failures.
- **Decide:** the **lowest-numbered wave not yet verified-done**, then the lowest-numbered
  unfinished story within it. One story at a time. Do not start a later wave because an
  earlier one is hard — record the blocker and say so.
- **Execute:** on the committed mechanism above. Code edits sequential, in-session. After each
  `src/` Python edit run `tapps_quick_check`; at each story gate run `tapps_validate_changed`
  with explicit `file_paths`.
- **Verify (independent):** spawn a **fresh-context verifier subagent (frontier)** told to
  **refute** the story's proof. Hand it the **exact command, the expected artifact, the
  `file:line` anchors, and the environment quirks** — port 13000 not 3000, `.venv/bin/python`
  not `python3`, `set -a && . ./.env` for HA credentials, `CONTRACT_PACE` must not be lowered
  (admin-api rate-limits at 60 req/min and an unpaced sweep yields false 429s). Never hand it
  your narration. Its report must quote the output it observed, and **its verdict advances the
  loop, not the executor's claim.**
- **On fail:** diagnose — read the actual error, inspect state, recall prior failures — then
  hypothesis → fix → retry *with something changed*. ≤3 distinct strategies per story, then
  escalate once, then stop with a concise diagnosis. **Never re-run the same action on the
  same error.**
- **Record:** `tapps_memory(action="save", key=<slug>, tier="pattern", value="<outcome incl. what failed and why>")`.
- **Context hygiene:** prune stale reads each iteration; prefer targeted `grep` over a full
  re-`Read`; carry a compact state summary forward, not raw transcripts. Delegate noisy
  multi-file reading to a subagent and keep only its summary.
- **Print every iteration:**
  `SCORE: wave <w>/7 · stories done <n>/40 · repo-root contexts <n>/54 · PR-gated workflows <n>/10 · contract <pass>/<total> · services migrated <n>/12 · containers <n> · pytest <fail> failures · iteration <i>/45`
- **Repeat or stop:** until Done-when holds; caps **45 iterations** AND **1.5M output tokens
  per run**. Hitting a cap mid-wave is a normal stop — record the checkpoint and let the next
  run resume from it.

## Guardrails

- **Termination:** the Done-when set; caps 45 iterations AND 1.5M output tokens per run.
- **No green-by-deletion — every downward count is paired:** repo-root contexts → 0 **but
  ≥54 services still build**; containers 58 → ≤15 **but every retired capability proven
  reachable**; REST-registry callers → 0 **but ≥12 services importing the shared client**;
  contract rows must **rise** past 36; PR-gated workflows must **rise** past 0.
- **Caps must not fire on correct behaviour:** a Wave 5 deny-list **refusing** an automation is
  a pass. A budget gate **holding** a plan is a pass. Removing a frontend call that has no
  backend route is a **correct** Wave 2 outcome. A contract row asserting a deliberate
  `404 (decided)` is correct. Do not let a verifier score any of these red.
- **🔴 No live-HA writes.** Read-only only; any `apply` — including installing the Wave 6
  integration — is an Autonomy hard-stop.
- **Wave 7 is destructive and ordered last on purpose.** Never delete a service before a
  pasted call proves its capability reachable elsewhere. Deleting first and restoring later is
  not an option — the data is live.
- **Independent verification** — a verifier that did not do the work, handed the proof command
  rather than the claim, judged against ground truth.
- **No fan-out of coupled coding** — service migrations, gene authoring and service retirement
  are sequential, in-session, N=1. Fan-out is for research and verification only.
- **Context hygiene** — targeted `grep` over full re-`Read`; compact state summary forward.
- **Scope:** `/home/wtthornton/code/HomeIQ` only; team `TappsCodingAgents`, project `HomeIQ`.
  Verify every TAP id's `project` field before citing it.
- **Secrets:** `.env` stays gitignored; never commit a key; never log the HA encryption key;
  credential moves into the AgentForge vault are moves, not copies.
- **Memory:** recall at start, record at every checkpoint including failures.
- **Harness compatibility:** `tapps_session_start` before any `tapps_*` call · `linear-issue`
  for every write (30-min sentinel) · `linear-read` for every multi-issue read · per-edit
  quality nudge **adopted** for `src/` Python, **overridden to wave-gate batching** elsewhere.
- **Discipline:** root-cause not workarounds; **no green-by-suppression**; right-sized; durable
  over expedient; match repo conventions; no silent scope creep. If the correct fix is out of
  scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR, staged diff) and
  keep going; the human reviews async. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** any `apply` against the live
  Home Assistant, including installing the Wave 6 integration · **deleting any service in
  Wave 7** · a write outside this repo's team/project · merge to `master` · force-push ·
  deleting un-recreatable data · removing a backend route another service still consumes · a
  genuinely ambiguous decision where a wrong guess is expensive.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior failures → form a
specific hypothesis → change something → retry. ≤3 distinct strategies per story, then one
escalation, then stop with a concise diagnosis naming what you tried and why each failed.

## Unverified assumptions

Confirm each before depending on it.

- **The wave ordering's dependency claims.** Basis: reading issue bodies, not a build.
  Waves 3→4→5→6→7 are inferred from what each epic says it consumes. **Confirm by:** before
  starting each wave, re-read its epic body and the one it claims to depend on, and check the
  dependency still holds.
- **Waves 4–5 assume AgentForge is reachable and accepts published genes.** Basis: the
  `mcp__agentforge__*` tools appear in this session's tool list; not exercised. **Confirm by:**
  `mcp__agentforge__health` in Wave 0.
- **The 84-family dashboard enumeration behind Wave 2.** Basis: one research subagent; 5 of its
  highest-consequence claims were spot-verified against source and held; the remaining ~79 are
  unverified individually. **Confirm by:** re-deriving the frontend call set with a fresh grep
  before authoring contract rows.
- **`/api/integrations/:platform/analytics` may be unreachable** because `nginx.conf:131` uses
  `proxy_pass http://data_api/api/integrations;` with no `$request_uri`. Basis: static read.
  **Confirm by:** `curl -s -o /dev/null -w '%{http_code}' http://localhost:13000/api/integrations/hue/analytics`.
- **Wave 7's "about 11" target.** Basis: the epic title. The Done-when uses ≤15 and ≥8 to avoid
  chasing an exact number that the architecture may not land on. **Confirm by:** recount after
  Waves 3–6 and restate the target with a reason if it has moved.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` · assignee `Claude Agent`
- Measured facts driving Wave 1: **54/54** build contexts are `../..`;
  `scripts/start-stack.sh:91` forces `--build --pull always --force-recreate`; **0** of the ten
  domain CI workflows trigger on `pull_request`.
- Shared client: `libs/homeiq-ha/src/homeiq_ha/client/` — `HAWebSocketClient`, proven live
  (164 entities, 19 devices), imported by **zero** services today.
- Evidence: `docs/ha-init-agent-design.md` · `docs/operations/dashboard-triage-2026-08-01.md`
- Narrow alternative: `prompts/close-unblocked-post-5405-work.md` (Wave 2 only)
- **Head start for Wave 2, in `git stash`:** a subagent applied 8 of the TAP-5433
  `/ai-automation/*` prefix fixes during the 2026-08-01 session. They were stashed rather
  than committed because they were **never built, tested, or curled against the stack**.
  `git stash list` → the entry naming TAP-5433. Review with `git stash show -p stash@{n}`,
  and only `git stash pop` after you have a running stack to verify against. Treat it as an
  unverified suggestion, not as done work — the remaining 9 families are untouched.
- Prior learnings: `tapps_memory(action="search", query="homeiq build contexts CI MCP server genes data plane")`

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in a new session.
- **Durable:** a Routine running one wave per invocation, push=draft-PR.
- **Fan-out sub-step:** none committed. The only parallel work is read-only research (Wave 2
  route discovery) and verification — plain subagents, no Workflow script. Every code-editing
  chunk is coupled to its own tests and container and runs N=1.
