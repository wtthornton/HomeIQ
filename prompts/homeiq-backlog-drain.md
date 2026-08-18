# HomeIQ backlog drain — resume at TAP-5431, then empty the open Linear backlog

> Generated 2026-08-13 by the `orchestration-prompt` skill; **rewrite #2, same
> day, against a live Linear read (50 open issues, 12 Urgent).** Successor to
> `prompts/homeiq-backlog-burndown.md` (Wave 1–6 history and measurement record).
> Rewrite #1's Sub-goals 1–3 are COMPLETE: Wave 7 (epic TAP-5942) closed, Wave 1
> (epic TAP-5281) closed, six defects (5993/5994/5997/5999/6007/6027) closed with
> verifier evidence — never redo them (brain keys `burndown-*`). **PR #82 is
> MERGED (`b934a7ec`)** — all new work branches off `master`. Four follow-up
> defects (6034–6037) were filed during the defect batch and join the queue.
>
> **This is a multi-run loop.** One ~6-hour session finishes a sub-goal or two.
> Re-enter it until the backlog is empty. Each sub-goal is a resumable checkpoint.

## Prerequisites / Wayfind gate

- **Route clear? Yes.** Ordering locked by the predecessor prompts, the user's
  2026-08-12 priority agreement, and the 2026-08-13 live re-reads; all remaining
  chunks are execute / verify / fix. Two known decide-shaped traps are called out
  inline (TAP-5430 write mechanism, TAP-6018 quirk split) — surface them, don't
  guess. If genuinely new decide work surfaces mid-drain, stop that sub-goal and
  surface it.
- **Resume recall (cold start):** `tapps_memory(action="search", query="burndown wave checkpoint")`
  — the CLI form is broken in this project (`MemoryStore requires a Postgres
  private_backend`); always use the MCP tool.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one sub-goal per run) so it survives the terminal.
- Linear must be authenticated (`/mcp` first if in doubt).

## Objective

Land the two surviving ha-init-agent recipes (TAP-5431, TAP-5430), burn the
2026-08-13 follow-up defect batch, then drain the remaining backlog in dependency
order — MCP surface → genome/safety gate → HA front door → destructive
data-plane collapse — every closure carrying independent-verifier evidence.

## The live backlog (re-read 2026-08-17 via `linear-read` — 46 open after Phase 0 triage; plan: `docs/planning/backlog-implementation-plan-2026-08-17.md`)

| Sub-goal | Group | Open issues (priority) |
|---|---|---|
| 1 | P0 resume — TAP-5431 (M) | **DONE 2026-08-13** (PR #83 merged 2026-08-18) |
| 2 | TAP-5430 (H) | recorder + http hardening recipes ONLY — owner Decision A (agent SSH credential in `core_ssh`); shares its blocker with 6018 |
| 3 | Follow-up defect batch (filed 2026-08-13) | **all DONE** (6034 · 6035 · 6036 · 6037) |
| 4 | Wave 8 — MCP server, epic TAP-5282 (**Urgent**) | 5292 **DONE** · **6071 (H, first — unblocks `detect_anomalies`)** · 5293 (U) · 5294 (U) · 5295 (U, tools 14/15 deferred — Decision E) · 5296 (U) · 5297 (H) |
| 5 | Wave 9a — genome, epic TAP-5285 (H) | 5311 · **5318 (U, pull forward — every gene lands through the pipeline)** · 5312 · **5313 (U)** · 5319/5316 · 5314 · 5315 · 5317 |
| 6 | Wave 9b — safety gate, epic TAP-5286 (H) | **5320 (U)** · 5321 (H) · 5323 (M) · 5325 (M) · **6102 (H, cutover) → 5322 (U)** |
| 6.5 | Wave 11a — evidence-backed deletions, epic TAP-5283 (Decision D: **before** Wave 10) | 5910 (absorbs 5300 + 5298 deletion half) · 5303 (M) · then 6103 (CI debt) |
| 7 | Wave 10 — HA integration, epic TAP-5284 (H) | 5305 · 5306 · 5307 · 5308 (H) · 5309 (M) · 5310 (H) · 5304 (M, last) |
| 8 | Wave 11b — consolidations, epic TAP-5283 — destructive, last | 5299 · 5301 |
| standing | Wave 4 — office presence, epic TAP-5977 (H) | 6018 (**agent-workable quirk**, file drop needs Decision A) → 5979 (human) → 5978 (human) → 5980 · re-check 6018 once per run |
| anytime | small | 6066 (M, libs undeclared imports) |

Canceled as duplicates of 5910 on 2026-08-17: 5298, 5300, 5302 (see comments).
Closed work is closed: epics 5281/5942/5405/5413/5973/5981/5985 and every
defect above are Done with evidence on the tickets — never reopen.

## Done-when (ground truth, not narration)

The backlog is empty when **every** clause holds. A single run satisfies the
clauses it reached; paste the artifacts for those and the current SCORE line for
the rest.

1. **TAP-5431** — a Local Calendar config entry exists with its `calendar.*`
   entity id **asserted by the recipe from a live flow, never assumed**;
   `CALENDAR_ENTITIES` names it and `calendar-service` stops logging the
   not-found warning (paste the log check); Powercalc is installed via HACS and
   ≥1 light reports power (paste the state); template aliases exist for the
   power/energy ids `home_assistant.py:106-133` probes; a second `apply` reports
   zero changes (paste it).
2. **TAP-5430** — `http.login_attempts_threshold: 5` and a shortened
   `recorder.purge_keep_days` with update-domain/signal-strength exclusions are
   applied **through recipes**, SQLite retained; `check` reports SATISFIED
   without writes on an already-matching instance; second `apply` reports zero
   changes. The automation-editor clause is already delivered — do not redo it.
3. **Defect batch** — each of 6034/6035/6036/6037 pastes a verified fix **or** a
   recorded re-scope/removal reason (a correct removal is a pass). 6036 first:
   zero committed credential **values** in tracked env files (paste the sweep at
   key-name level — never print the values being removed), **AND** every touched
   service still starts via the documented path (paste one `up -d` + health).
4. **Wave 8** — the `homeiq` MCP server answers `/health`; a pasted tool call
   returns real data for ≥1 query tool and ≥1 analytics tool; contract tests pin
   the schemas; `homeiq` registered in the AgentForge overlay MCP registry.
5. **Wave 9** — every authored gene and chromosome passes offline kit
   validation, pasted; a pasted run shows the hard-deny list **refusing** a
   denied automation and a budget gate **holding** an over-cap plan (a correct
   refusal is a pass).
6. **Wave 10** — the HA custom integration loads on the live instance and
   `/api/config/config_entries` shows the HomeIQ entry `loaded`. Installing it
   is an apply — route through the gateway path or hard-stop.
7. **Wave 11** — `docker ps --filter name=homeiq | grep -c healthy` is ≤15 and
   ≥8, **AND** for every retired service a pasted call proves its capability
   still reachable through an MCP tool or a gene. The second clause is mandatory.
8. **Wave 4 (standing)** — remains human-blocked unless the user clears it;
   each run re-checks `get_issue(TAP-6018)` once and records state.
9. **Always** — `.venv/bin/python -m pytest libs/homeiq-ha -q` → **0 failed**,
   pass count ≥ **222**; ha-setup-service tree → 0 failed, pass count ≥ **56**
   (run the two trees SEPARATELY — combining them breaks collection); admin-api
   tree ≥ **393**; data-api search suite ≥ **6** when touched;
   `git status --short` clean at each story gate; every cited TAP id confirmed
   by `get_issue` (ids are workspace-sequential — verify the `project` field).

## Sub-goals (sequential; each a checkpoint)

0. **Establish preconditions (self-healing — the loop does this, not the user).**
   - `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks
     all other `tapps_*` tools until it runs. Re-run after any `/clear` or compact.
   - **Linear auth probe.** ToolSearch `select:mcp__plugin_linear_linear__get_issue`.
     If the plugin tools do not load, the session is unauthenticated — hard-stop
     once and tell the user to re-authorize via `/mcp`. Do NOT fall back to raw
     Linear API calls and do NOT burn the run on code-only work while closures
     pile up (2026-08-13 lost a closure step to exactly this).
   - Brain recall: `tapps_memory(action="search", query="burndown wave checkpoint")`
     and `"homeiq backlog drain"`. Verified outcomes live under `burndown-*`
     keys — **never redo a verified wave or closed defect.**
   - **🔴 Single-writer check:** `git status --short` twice ~30 s apart;
     `git log --oneline -3` for foreign commits. A dirty tree you did not create
     is a hard-stop — EXCEPT a lone modified `.tapps-mcp/session-handoff.md`,
     which session tooling rewrites routinely and is not a foreign-writer signal.
     Never `git checkout` while another writer is active.
   - **Branch base: `master`.** PR #82 MERGED as `b934a7ec`
     (`git merge-base --is-ancestor` confirms the old feature tip is contained).
     `git fetch origin master` and branch each story/wave off `origin/master`;
     the old `feat/ha-init-agent-activation` branch is dead — never commit to it.
     Old pre-rewrite hashes 9ff4f658 / d6eac06a are DEAD (history rewritten
     2026-08-13, triage-store scrub).
   - Test runner: `/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`;
     trees run SEPARATELY (both expose a `tests` package). Record start counts;
     enforce no-shrink against floors 222 (homeiq-ha) / 56 (ha-setup-service).
   - Stack + smoke: healthy-container count; `curl :8024/health` → 200;
     `curl :8024/setup` → 200; `curl -s :8024/api/v1/init/queue | jq '.items|length'`
     (key is `items` — `.queue` silently returns 0; count is live-derived and
     DRIFTS — never assert a frozen number). Off-contract POST to
     `/api/v1/init/answers` → **422** (contract hardened, commit `6d8e5bab`).
   - **Deploy freshness:** several compose services declare `build:` with no
     `image:` — after any source change:
     `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`
     (`--env-file` is mandatory on single-service deploys or postgres creds
     break). Verify by identity, never by build exit code. Smoke before spend.
   - **Live-HA probe:** `GET :8024/api/v1/init/audit` (or latest
     `.tapps-mcp/init-audit-<date>.json` from the 03:15 cron). ZHA entry
     `01KZSE6SJ789RGEFCBRBA0VHDG` `loaded`; coordinator `192.168.1.121:6638`.
     Coordinator down → that is an alert finding, not a reason to touch ZHA config.
   - **AgentForge reachability** (Sub-goals 4–8): `mcp__agentforge__health`; if
     unavailable, wait-and-retry (containers recover in seconds). AF MCP caches
     `.env` at startup — `missing-bearer` after a key rotation means restart the
     server, not a bad key.
   - proof: session_start returned; Linear plugin loaded (or hard-stop recorded);
     brain recall pasted; single-writer clean; branch-off-master confirmed; smoke
     set pasted (health/setup/queue/422); audit fetched.

1. **TAP-5431 — Local Calendar, Powercalc, power-sensor template aliases (P0).**
   `get_issue(TAP-5431)` first for full acceptance. LARGE, live-HA-apply.
   - **Order: reversible code first.** Author the three `IntegrationRecipe`
     subclasses (base at `recipes.py:619-668`; copy the `TeamTrackerRecipe`
     pattern at `recipes.py:672-735` — it asserts the resulting `entity_id`
     instead of trusting the documented default) with offline tests, THEN apply
     live through the gateway.
   - **Local Calendar:** read the config-flow schema **from a LIVE flow** —
     never guess the field name; that trap is why TeamTrackerRecipe exists.
     `run_config_flow` raises `HAHumanGateRequired` on ANY `progress` step, but
     not every progress step is a human gate — distinguish poll-able progress
     from genuine human gates.
   - **Powercalc:** install via HACS (unblocked 2026-08-12 — `hacs.bootstrap:
     satisfied`, Team Tracker already installed through it). The install may
     force an HA restart — that is an apply; route it through the gateway
     converge path, never a raw restart call.
   - **Template aliases follow Powercalc** (they only make sense once a power
     source exists): satisfy the literal entity-id matching at
     `domains/data-collectors/smart-meter-service/src/adapters/home_assistant.py:106-133`;
     the calendar entity feeds `domains/data-collectors/calendar-service/src/main.py:119-120`.
   - Design-doc row 3.8 stays accurate: `calendar-service` does NOT hard-fail
     without a calendar entity — the symptom is an inert collector.
   - Close via `linear-issue` with verifier evidence.

2. **TAP-5430 — recorder + http hardening recipes (remaining scope ONLY).**
   `get_issue(TAP-5430)` first. The automation-editor clause was delivered
   before the re-scope (live deploys work since 2026-08-12) — do not redo it.
   - Both file-access add-ons are installed and running (`addons.core_ssh` +
     `addons.core_configurator` satisfied in the nightly audit) — the phase-4
     blocker is gone.
   - **CHECK `docs/ha-init-agent-design.md` rows 3.5/3.6 for the
     remote-YAML-write mechanism before building.** If the mechanism is
     undecided there, surface it as decide-work and stop this sub-goal — do not
     guess a write path into `/config`.
   - `http.login_attempts_threshold` → 5 (default `-1` disables IP banning
     entirely even though `ip_ban_enabled` defaults true). `recorder` →
     shortened `purge_keep_days` + exclusions for update-domain and
     signal-strength noise; SQLite retained, no MariaDB. Reconcile with the
     existing recorder scoring at
     `domains/device-management/ha-setup-service/src/optimization_engine.py:167`.
   - New recipes join `default_recipes` at `recipes.py:760-770`. Idempotency and
     SATISFIED-without-writes are acceptance clauses — paste both.

3. **Follow-up defect batch (filed 2026-08-13).** In order:
   - **TAP-6036 (High, security):** committed credential values in tracked
     `env.test`/`env.prod`-style files. Root-cause fix: required env vars
     without baked values, documented `--env-file` path. Work at key-name
     level — the fix must never print the real values it removes. Paired
     clause: every touched service still starts (paste one `up -d` + health).
     Note on the ticket that rotation of previously-committed values is
     owner-gated (recorded on TAP-5993's trail) — record, don't execute.
   - **TAP-6034 (High):** wire `setup_wizard.html` to the readiness-trigger and
     triage-decision backends that TAP-5946/5947 delivered. Frontend work —
     `tapps_quick_check` does not gate HTML/JS; validate behaviorally (drive the
     wizard against the live gateway and paste the round-trip).
   - **TAP-6035 (Medium):** DNS-rebinding guard for the same-origin check in
     `routes_init.py` — validate the Host header against an allowlist, not
     origin-vs-request equality alone. Lookup first: current (2026) guidance on
     DNS-rebinding defenses for LAN services.
   - **TAP-6037 (Medium):** shared-lib test suites (`libs/*`) never run on
     push/PR. Wire them into CI with `uv`/venv — NOT `pip install tapps-mcp`
     (no installable dist exists; see CLAUDE.md "CI Integration" — that red is
     upstream and out of scope).
   - Each: fix-with-evidence or re-scope-with-reason via `linear-issue`.

4. **Wave 8 — MCP server (epic TAP-5282, Urgent; 6071 → 5293 → 5294 → 5295 →
   5296 → 5297).** Required lookup before code: MCP server SDK docs. The
   catalogue + schema (5292, v1.1.1 NORMATIVE at `docs/mcp/`) gate everything
   downstream; bump to v1.2.0 marking tools 14/15 `deferred` (Decision E).
   Credential-move duplicate is reconciled: 5322 owns it, gated on 6102.

5. **Wave 9a — genome (epic TAP-5285; 5311–5318).** AF workflow traps apply
   (see Guardrails research grant). Offline kit validation is the evidence.

6. **Wave 9b — safety gate (epic TAP-5286; 5319–5323, 5325).** A deny-list
   refusal and a budget-gate hold are passes — paste them.

7. **Wave 10 — HA integration (epic TAP-5284; 5305–5310).** Installing on live
   HA is an apply — gateway path or hard-stop.

6.5. **Wave 11a — evidence-backed deletions (TAP-5910 → 5303 → 6103) —
   runs after Wave 8 and BEFORE Wave 10 (Decision D).** 5298/5300/5302 are
   canceled into 5910. Never delete a service before a pasted call proves its
   capability reachable elsewhere (or an explicit "no capability" finding);
   each deletion is an Autonomy hard-stop. 5910's evidence table needs a
   per-service "re-homed in / dropped" column (ai-core-service orphans four ML
   services → 5301).

8. **Wave 11b — consolidations (epic TAP-5283; 5299, 5301) — destructive,
   last.** Container target ≤15 and ≥8 with every retirement capability-proven.

## Plane map (mechanism + literal dispatch parameters per chunk)

| Step | Plane | Mechanism | agentType | model | effort | Notes |
|---|---|---|---|---|---|---|
| Backlog re-reads | coordination | **`linear-read` skill** | n/a (in-session) | session | — | cache-first, hook-gated |
| Linear closures/comments | coordination | **`linear-issue` skill** | n/a (in-session) | session | — | handles the validate sentinel |
| Story implementation | execution | in-session, sequential, N=1 | n/a | session (frontier) | — | `tapps_quick_check` per `src/` edit |
| Research fan-outs (route discovery, entity sweeps) | coordination | 3–5 parallel `Agent()` calls | `Explore` | `haiku` (closed Qs) / `sonnet` (synthesis) | inherited | read-only enforced by agent type |
| Per-story verification | coordination | verifier subagent, fresh context, told to **refute** | `general-purpose` | `opus` | inherited | its verdict advances the loop, not the executor's claim |
| Wave-completion panel | coordination | 3 verifier subagents, perspective-diverse | `general-purpose` | `opus` | inherited | majority rules; never a cheap-model verdict on anything irreversible |
| Wave 8 MCP schema design | execution | in-session | n/a | session (frontier) | — | schema gates Waves 9–11 |
| AF author→judge pipelines (if needed) | execution | AF workflow | AF-side | AF-side | — | deterministically re-check every judge finding against the artifact before amending |

`effort` is Workflow-only — Agent dispatches inherit the session's. If a future
sub-goal grows a genuine N×stages fan-out, emit `.claude/workflows/<slug>.js`
with schema + `budget` + per-stage `model`/`effort` then; nothing here needs one
today.

## Loop

- **State:** `git log --oneline -5`; `git status --short` (single-writer);
  backlog via `linear-read`; latest nightly audit; healthy-container count;
  brain recall of checkpoints and prior failures.
- **Decide:** the lowest-numbered unfinished sub-goal, then the lowest-numbered
  unfinished story within it. One story at a time. Human-gated items: record,
  surface in the final report, skip. Newly-filed Urgent/High defects may insert
  ahead of Sub-goal 4 — record the insertion.
- **Execute:** on the committed mechanism above. Code edits sequential,
  in-session. `tapps_quick_check` after each `src/` Python edit;
  `tapps_validate_changed` with explicit `file_paths` at each story gate.
- **Verify (independent):** fresh-context **opus** verifier told to **refute**
  the story's proof. Hand it the exact command, expected artifact, `file:line`
  anchors, and environment quirks (ports below; `.venv/bin/python`; `--env-file`
  on single-service deploys; `CONTRACT_PACE` never lowered — admin-api
  rate-limits at 60 req/min and unpaced sweeps yield false 429s; HA reads via
  the gateway; queue key is `.items` and the count drifts). Never hand it
  narration. Its verdict advances the loop.
- **On fail (expected-fail fix loop):** structured handoff → diagnose (read the
  real error, inspect state, recall prior failures) → hypothesis → fix → retry
  *with something changed*. ≤3 validation rounds per story, then escalate once,
  then stop with a concise diagnosis. Never weaken a contract to go green.
- **Record:** `tapps_memory(action="save", key="burndown-<subgoal>-<story>",
  tier="pattern", value="<outcome incl. what failed and why>")`. On fail, the
  structured handoff: completed · undone · commands+exit codes · issues found.
- **Context hygiene:** prune stale reads each iteration; targeted grep over full
  re-Read; compact state summary forward, never raw transcripts; delegate noisy
  multi-file reads to `Explore` and keep only the summary.
- **Print every iteration:**
  `SCORE: subgoal <s>/8 · open issues <n>/50 · containers <n> healthy · pytest <fail> failures (<libs>+<svc>) · iteration <i>/45`
- **Repeat or stop:** until Done-when holds; caps **45 iterations** AND **1.5M
  output tokens per run**. Hitting a cap mid-sub-goal is a normal stop — record
  the checkpoint; the next run resumes from it.

## Guardrails

- **Termination:** the Done-when set; caps 45 iterations AND 1.5M output tokens/run.
- **🔴 HA writes only through the gateway converge path** (`POST :8024/api/v1/init/converge`,
  backup-gated, per-phase `{"phase": N}`, read-back verified — a full-stack
  converge halts at the first `BLOCKED_ON_HUMAN`; that halt is a finding, not a
  lost run). Never weaken `BackupGateNotSatisfied`. **Absolute never-do:** ZHA
  network formation on the loaded entry, removing paired devices, deleting areas
  with assigned devices, uninstalling loaded integrations. Anything else outside
  the gateway: hard-stop. A Powercalc-forced HA restart counts as an apply —
  gateway path only.
- **No green-by-deletion — every downward count is paired:** containers ≤15 **but
  every retired capability proven reachable**; committed credential values → 0
  **but every touched service still starts via the documented path**.
- **Caps must not fire on correct behavior:** a deny-list refusal is a pass · a
  budget gate holding is a pass · an honest `blocked_on_human` row is a pass · a
  verified zero-change second apply is the success signature of convergence · a
  422 on an off-contract body is the contract working · a SATISFIED-without-
  writes `check` on a matching instance (5430) is a pass · removing a dead call
  path can be the correct fix.
- **Independent verification:** creator ≠ verifier; ground-truth proof; no
  cheap-model verdict gates an irreversible step; re-derive load-bearing
  conclusions from returned evidence, not subagent narration (AF judges
  hallucinate findings — deterministic re-check before amending).
- **No fan-out of coupled coding** — migrations, gene authoring, retirement:
  sequential, in-session, N=1. Fan-out is read-only research and verification
  only. Check `git status` after any `general-purpose` fan-out.
- **Research grant:** web access, `tapps_research`, `tapps_lookup_docs`
  (Context7-backed, cache-first, free to repeat). **Required lookups before
  first code touching each surface:** HA config-flow WS API + Local Calendar
  flow shape (Sub-goal 1 — then read the schema from a LIVE flow) · HACS
  install flow for Powercalc (Sub-goal 1) · HA template-sensor schema
  (2024.10+ plural `triggers:/conditions:/actions:` where applicable) · HA
  `http:`/`recorder:` option semantics (Sub-goal 2) · DNS-rebinding defenses
  for LAN services (6035) · MCP server SDK (Sub-goal 4) · AF workflow traps
  (`kind: task`; `$input` refs — literal `{{input}}` passes through; terminal
  state `complete`; `output_schema` on the workflow node; publish agents before
  workflows or 422) · label/area registry semantics (labels store slug ids;
  match by name OR slug or re-applies mint `<slug>_2` dupes).
- **Secrets:** `.env` gitignored and read-denied — work at key-name level
  (`.env.backup-pre-new-ha-20260801` holds the only copy of several
  credentials). `backup/config/info` returns the HA encryption key in plaintext
  — never log it, never paste it into Linear. Credential moves into the AF vault
  are moves, never copies. 6036's fix removes values; it must never print the
  real values it replaces. Rotation of previously-committed creds is owner-gated
  — record, never execute.
- **Scope:** `/home/wtthornton/code/HomeIQ` only; Linear team
  `TappsCodingAgents`, project `HomeIQ`, assignee `Claude Agent`
  (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes forbidden.
- **Memory:** recall at start; record at every checkpoint including failures.
- **Harness compatibility (each adopted or overridden):** `tapps_session_start`
  first (adopted — PreToolUse gate) · Linear writes via `linear-issue` (adopted —
  save sentinel) · multi-issue reads via `linear-read` (adopted — snapshot gate;
  `state="open"` never reaches the plugin; the PostToolUse hook auto-populates
  the snapshot cache after `list_issues`) · per-edit `tapps_quick_check` adopted
  for `src/` Python, **overridden to story-gate batching** for tests,
  TypeScript, YAML, shell, markdown, HTML (6034 validates behaviorally) · new
  Python modules small and re-exported from hubs (MI is length-dominated past
  ~800 lines; name-matched `test_<module>.py` is what test-coverage detects) ·
  Stop-hook completion gate: run `tapps_validate_changed` + `tapps_checklist`
  before ending any session with code edits.
- **Discipline:** root-cause not workarounds; no green-by-suppression;
  right-sized; durable over expedient; match repo conventions; no silent scope
  creep. If the correct fix is out of scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR,
  staged diff) and keep going. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** Linear plugin
  unauthenticated (Sub-goal 0) · any HA write outside the gateway converge path
  (incl. a Powercalc-forced restart) · ZHA formation / device removal /
  integration uninstall · deleting any service in Sub-goal 8 · any merge to
  `master` · force-push · deleting un-recreatable data · credential rotation ·
  a write outside this repo's team/project · physical-world steps (sensor
  placement, switch wiring, pairing buttons — surface as readiness gates, never
  simulate) · a genuinely ambiguous decision where a wrong guess is expensive
  (the TAP-5430 write-mechanism question if design rows 3.5/3.6 don't settle it).

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior
failures → specific hypothesis → change something → retry. ≤3 distinct
strategies per story, then one escalation, then stop with a concise diagnosis
naming what was tried and why each failed. Expected-fail is the design —
verification rarely passes first try (the 2026-08-13 verifier panels found real
gaps twice in "done" work); scope a narrow fix sub-goal from the verifier's gaps.

## Unverified assumptions

Confirm each before depending on it.

- **Waves 8–11 dependency claims** are issue-body-based, not build-verified —
  re-read each epic before starting it.
- **TAP-5300/5302 In-Progress state** — started 2026-08-11; read their branches
  and comments before continuing (another session's partial work may exist, and
  it predates the history rewrite).
- **TAP-6018 (Wave 4 gate)** — a custom ZHA quirk is code; if the ticket's
  blocker turns out to be authoring the quirk rather than physical placement,
  re-scope it into agent-workable + human-gated halves. Re-check once per run.
- **TAP-6034 scope** — filed from the wizard epic's verifier round; `get_issue`
  for the concrete wiring list before estimating.
- **Post-merge deploy state** — master now carries the 31-commit branch; the
  running containers may predate the merge. Sub-goal 0's deploy-freshness gate
  is the check, not an assumption of freshness.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` ·
  assignee `Claude Agent` · brain project `homeiq`.
- **Git state at rewrite (2026-08-13 evening):** PR #82 MERGED as `b934a7ec`;
  `feat/ha-init-agent-activation` tip `c2c35577` fully contained in
  `origin/master`; new work branches off `master`. History rewrite note: old
  hashes 9ff4f658 / d6eac06a are DEAD (triage-store scrub, TAP-5942).
- **Host-port overrides:** dashboard **13000**, admin-api **18004**, websocket
  **18001**, postgres **15432**, retention **18080**, carbon **18010**, OTLP
  **14317/14318**, jaeger **16687**, ai-automation-ui **13001**, init gateway
  **8024**.
- **Test floors (2026-08-13):** homeiq-ha **222**, ha-setup-service **56**
  (trees SEPARATE), admin-api **393**, data-api search **6**.
- **Live HA (2026-08-12 verified):** ZHA on SLZB-06P7 at `192.168.1.121:6638`,
  entry `01KZSE6SJ789RGEFCBRBA0VHDG`; 3 Inovelli Blue switches + Aqara
  multi-sensor placed and manifested; 1 stalled-interview device (ieee …c0:f4);
  Hue Bridge Pro `192.168.1.170` (296 entities / 50 devices / 19 areas); HACS +
  Team Tracker live (Powercalc installable now); file-access add-ons
  `core_ssh` + `core_configurator` installed and running; backups nightly 04:48;
  init-gateway audit cron 03:15 → `.tapps-mcp/init-audit-<date>.json`.
- **InfluxDB reality (documented 2026-08-13):** all event data lives in
  `home_assistant_events` (365d); the declared per-type buckets are empty —
  see `docs/operations/influxdb-retention.md` and brain memory
  `influxdb-buckets-declared-vs-actual`. The sports_data 90d retention change
  is a NO-OP; `REVOKE CONNECT ... FROM PUBLIC` on postgres is owner-gated.
- **Prompt lineage (reviewed 2026-08-13):** this file's rewrite #1 drained
  Sub-goals 1–3 (Wave 7, Wave 1 closeout, 6-defect batch) — history and
  evidence on the tickets and under brain keys `burndown-*`. Supersedes
  `homeiq-backlog-burndown.md` (Wave 1–6 history + measurements live there).
  `tapps-mcp-defects-from-homeiq-2026-08-02.md` is a handoff owned by the
  TappsMCP repo — out of scope here.
  `tapps-brain-defects-from-homeiq-2026-08-02.md` is self-marked SUPERSEDED —
  never execute it.
- **Known CI blocker, not fixable here:** TappsMCP has no installable dist (see
  CLAUDE.md "CI Integration") — upstream fix. TAP-6037 must work around it with
  `uv`/venv, not wait on it.
- Evidence: `docs/ha-init-agent-design.md` · `.tapps-mcp/session-handoff.md` ·
  brain keys `burndown-*`.

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in
  a NEW session **with Linear authenticated** (`/mcp` first if in doubt).
- **Durable:** a Routine running one sub-goal per invocation, push=draft-PR.
- **Fan-out sub-steps:** read-only research and verification only, per the Plane
  map. Every code-editing chunk is N=1 sequential. No Workflow script is needed
  today; emit `.claude/workflows/<slug>.js` only if a sub-goal grows a genuine
  N×stages fan-out.
