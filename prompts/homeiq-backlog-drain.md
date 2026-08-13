# HomeIQ backlog drain — urgent fixes first, then empty the open Linear backlog

> Generated 2026-08-13 by the `orchestration-prompt` skill; **rewritten same day
> against a live Linear read (59 open issues; 57 after TAP-5944/5945 closed with
> verifier evidence).** Successor to `prompts/homeiq-backlog-burndown.md` (kept as
> the Wave 1–6 history and measurement record). Wave 7 is two stories from done;
> Wave 1's epic is still open in Linear despite being functionally met; eight
> defect issues were filed after the burndown table was written. This prompt
> resumes at the exact frontier and drains everything that remains.
>
> **This is a multi-run loop.** One ~6-hour session finishes a sub-goal or two.
> Re-enter it until the backlog is empty. Each sub-goal is a resumable checkpoint.

## Prerequisites / Wayfind gate

- **Route clear? Yes.** Ordering locked by the predecessor prompt, the user's
  2026-08-12 priority agreement, and the 2026-08-13 live re-read; all remaining
  chunks are execute / verify / fix. If genuinely new decide work surfaces
  mid-drain, stop that sub-goal and surface it; do not guess.
- **Resume recall (cold start):** `tapps_memory(action="search", query="burndown wave checkpoint")`
  — the CLI form is broken in this project (`MemoryStore requires a Postgres
  private_backend`); always use the MCP tool.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one sub-goal per run) so it survives the terminal.

## Objective

Finish Wave 7, close out Wave 1's lingering epic, burn the post-burndown defect
batch, then drain the remaining backlog in dependency order — MCP surface →
genome/safety gate → HA front door → destructive data-plane collapse — every
closure carrying independent-verifier evidence.

## The live backlog (read 2026-08-13 via `linear-read` — 57 open after 5944/5945 closed)

| Sub-goal | Group | Open issues (priority) |
|---|---|---|
| 1 | Wave 7 finish — wizard epic TAP-5942 (High) | 5946 (H) · 5947 (H) · epic close |
| 2 | Wave 1 closeout — epic TAP-5281 (**Urgent**, functionally met 2026-08-10) | 5291 (H) · epic close (5287 canceled, 5288/5289/5290 Done) |
| 3 | Post-burndown defect batch (filed 2026-08-12) | **5993 (H — 32 hardcoded compose credentials)** · 5430 (H — recorder/http/automation-editor recipes) · 5431 (M) · 5994 (M) · 5997 (M) · 5999 (M) · 6007 (M) · 6027 (M) |
| 4 | Wave 8 — MCP server, epic TAP-5282 (**Urgent**) | 5292 (U) · 5293 (U) · 5294 (U) · 5295 (U) · 5296 (U) · 5297 (H) |
| 5 | Wave 9a — genome, epic TAP-5285 (H) | 5311 · 5312 · **5313 (U)** · 5314 · 5315 · 5316 · 5317 · **5318 (U)** |
| 6 | Wave 9b — safety gate, epic TAP-5286 (H) | **5319 (U)** · **5320 (U)** · 5321 (H) · **5322 (U)** · 5323 (M) · 5325 (M) |
| 7 | Wave 10 — HA integration, epic TAP-5284 (H) | 5305 · 5306 · 5307 · 5308 (H) · 5309 (M) · 5310 (H) |
| 8 | Wave 11 — data-plane collapse, epic TAP-5283 (**In Progress**) — destructive, last | **5298 (U)** · 5299 · 5300 (started) · 5301 · 5302 (started) · 5303 (M) · 5304 (M) · 5910 |
| standing | Wave 4 — office presence physical, epic TAP-5977 (H), HUMAN-BLOCKED | 5978 · 5979 · 5980 · 6018 (FP1E custom quirk) — re-check once per run, then skip |

13 open issues are **Urgent**. TAP-5992 (deploy-overwrite defect) closed Done
2026-08-13 — its interim always-pass-explicit-id rule is retired, but explicit
ids remain good practice.

## Done-when (ground truth, not narration)

The backlog is empty when **every** clause holds. A single run satisfies the
clauses it reached; paste the artifacts for those and the current SCORE line for
the rest.

1. **Wave 7** — TAP-5946 (readiness triggers for pairing, PIN flows, HACS) and
   TAP-5947 (discovery triage applies add/ignore/later decisions) closed with
   evidence; a full answers→converge→verify round-trip runs against a staged
   answer set (paste one driven flow); the 3-verifier wave panel passed
   (majority); epic TAP-5942 closed. TAP-5944/5945 are already Done
   (2026-08-13, verifier evidence on the tickets) — never reopen.
2. **Wave 1 closeout** — TAP-5291 closed-with-evidence or re-scoped (comment
   naming the 2026-08-10 measurement), epic TAP-5281 closed. The measured state
   still holds: `start-stack.sh` free of `--pull always --force-recreate`,
   `gh workflow list --all` showing ≥18/19 documented workflows `active`.
3. **Defect batch** — each of 5993/5430/5431/5994/5997/5999/6007/6027 pastes a
   verified fix **or** a recorded re-scope/removal reason (a correct removal is
   a pass). 5993 first: zero hardcoded credential defaults remaining in domain
   compose files (paste the sweep), with services still starting via `--env-file`.
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
   pass count ≥ **194**; ha-setup-service tree → 0 failed, pass count ≥ **34**
   (run the two trees SEPARATELY — combining them breaks collection);
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
   - Brain recall: `tapps_memory(action="search", query="burndown wave 7")` and
     `"homeiq backlog burndown"`. Verified outcomes live under `burndown-wave-*`
     keys — **never redo a verified wave.**
   - **🔴 Single-writer check:** `git status --short` twice ~30 s apart;
     `git log --oneline -3` for foreign commits. A dirty tree you did not create
     is a hard-stop. Never `git checkout` while another writer is active.
   - **Branch base:** `gh pr view 82 --json state | jq .state`. OPEN → branch off
     `feat/ha-init-agent-activation`'s tip and record the deviation; MERGED →
     work from master. Merging PR #82 is a human decision — hard-stop ask, once.
   - Test runner: `/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`;
     trees run SEPARATELY (both expose a `tests` package). Record start counts;
     enforce no-shrink against those.
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
     brain recall pasted; single-writer clean; PR #82 state pasted; smoke set
     pasted (health/setup/queue/422); audit fetched.

1. **Finish Wave 7 (epic TAP-5942).**
   - **TAP-5946 — readiness triggers for pairing, PIN flows, and HACS**
     (`get_issue` first for full acceptance). Context from the 2026-08-12 manual
     run: the pairing-permit protocol (`zha/devices/permit` with explicit
     `duration=N`; root-cause anchor `ws.py:200-206`) is the reference; physical
     button presses are readiness gates — surface and wait, never simulate.
     Required lookup before code: `tapps_lookup_docs` on the HA ZHA websocket
     API surface.
   - **TAP-5947 — discovery triage applies add/ignore/later decisions**
     (`get_issue` first). Verify `config_entries/ignore_flow` semantics — "the
     flow stays ignored across restart" is a correct negative and a pass.
   - **Epic gate:** one full answers→converge→verify round-trip against a staged
     answer set (a no-op set must yield `wrote_nothing: true`; a real one
     converges and read-back verifies), then the 3-verifier panel (correctness ·
     security/no-residue · reproducibility), majority rules. Close 5946, 5947,
     epic 5942 via `linear-issue`.

2. **Wave 1 closeout (epic TAP-5281, Urgent).** TAP-5291 (regression checks:
   start-stack refresh opt-in + CI workflow enablement) — build it small or
   re-scope with a comment naming the 2026-08-10 measurement; re-verify the
   measured state still holds (`start-stack.sh` flags, `gh workflow list`
   states). Then close the epic. Do not re-litigate the refuted claims
   (build-context sweep was measured correct; 5287 is canceled).

3. **Post-burndown defect batch (urgent fixes).** In order:
   - **TAP-5993 (High, security):** 32 hardcoded credential defaults across
     domain compose files. Root-cause fix: required env vars without baked
     defaults (`${VAR:?}` or documented `--env-file` requirement), never
     committed values. Paired clause: every touched service still starts via
     the documented path (paste one `up -d` + health).
   - **TAP-5430 (High):** recorder/http/automation-editor recipes needing file
     access — re-read the ticket against PR #82's landed engine before building.
   - **Mediums, cheapest-first:** 6027 (BackupScheduleRecipe summary contradicts
     its own detail — likely a one-liner), 5431 (Local Calendar / Powercalc /
     power-sensor aliases), 5994 (`data_sources_active` query method never
     existed), 5997 (event search federates to services lacking the endpoint —
     a correct fix may be removal), 5999 (admin-api docker socket unreadable →
     mock mode), 6007 (sensitive-key predicate misses embedded credentials).
     Each: fix-with-evidence or re-scope-with-reason via `linear-issue`.

4. **Wave 8 — MCP server (epic TAP-5282, Urgent; 5292→5297 in id order).**
   Required lookup before code: MCP server SDK docs. The tool catalogue + JSON
   schemas (5292) gate everything downstream — design them in-session at
   frontier quality. Reconcile the TAP-5298 / TAP-5322 credential-move duplicate
   **before** Wave 9: decide the owner, note it on the other, do it once.

5. **Wave 9a — genome (epic TAP-5285; 5311–5318).** AF workflow traps apply
   (see Guardrails research grant). Offline kit validation is the evidence.

6. **Wave 9b — safety gate (epic TAP-5286; 5319–5323, 5325).** A deny-list
   refusal and a budget-gate hold are passes — paste them.

7. **Wave 10 — HA integration (epic TAP-5284; 5305–5310).** Installing on live
   HA is an apply — gateway path or hard-stop.

8. **Wave 11 — data-plane collapse (epic TAP-5283; 5298–5304, 5910) —
   destructive, last.** 5300/5302 are already In Progress — read their current
   state before continuing them. Never delete a service before a pasted call
   proves its capability reachable elsewhere; each deletion is an Autonomy
   hard-stop. Container target ≤15 and ≥8 with every retirement
   capability-proven.

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
- **Record:** `tapps_memory(action="save", key="burndown-wave-<n>-<story>",
  tier="pattern", value="<outcome incl. what failed and why>")`. On fail, the
  structured handoff: completed · undone · commands+exit codes · issues found.
- **Context hygiene:** prune stale reads each iteration; targeted grep over full
  re-Read; compact state summary forward, never raw transcripts; delegate noisy
  multi-file reads to `Explore` and keep only the summary.
- **Print every iteration:**
  `SCORE: subgoal <s>/8 · open issues <n>/57 · containers <n> healthy · pytest <fail> failures (<libs>+<svc>) · iteration <i>/45`
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
  the gateway: hard-stop.
- **No green-by-deletion — every downward count is paired:** containers ≤15 **but
  every retired capability proven reachable**; credential defaults → 0 **but
  every touched service still starts via the documented path**.
- **Caps must not fire on correct behavior:** a deny-list refusal is a pass · a
  budget gate holding is a pass · an honest `blocked_on_human` row is a pass · a
  verified zero-change second apply is the success signature of convergence · a
  422 on an off-contract body is the contract working · an ignored flow staying
  ignored (5947) is a pass · removing a federation call to a nonexistent
  endpoint (5997) can be the correct fix.
- **Independent verification:** creator ≠ verifier; ground-truth proof; no
  cheap-model verdict gates an irreversible step; re-derive load-bearing
  conclusions from returned evidence, not subagent narration (AF judges
  hallucinate findings — deterministic re-check before amending).
- **No fan-out of coupled coding** — migrations, gene authoring, retirement:
  sequential, in-session, N=1. Fan-out is read-only research and verification
  only. Check `git status` after any `general-purpose` fan-out.
- **Research grant:** web access, `tapps_research`, `tapps_lookup_docs`
  (Context7-backed, cache-first, free to repeat). **Required lookups before
  first code touching each surface:** ZHA websocket API (`zha/devices/permit`,
  Sub-goal 1) · `config_entries/ignore_flow` semantics (Sub-goal 1) · HA
  automation schema (2024.10+ plural `triggers:/conditions:/actions:`) ·
  label/area registry semantics (labels store slug ids; match by name OR slug or
  re-applies mint `<slug>_2` dupes) · MCP server SDK (Sub-goal 4) · AF workflow
  traps (`kind: task`; `$input` refs — literal `{{input}}` passes through;
  terminal state `complete`; `output_schema` on the workflow node; publish
  agents before workflows or 422).
- **Secrets:** `.env` gitignored and read-denied — work at key-name level
  (`.env.backup-pre-new-ha-20260801` holds the only copy of several
  credentials). `backup/config/info` returns the HA encryption key in plaintext
  — never log it, never paste it into Linear. Credential moves into the AF vault
  are moves, never copies. TAP-5993's fix removes defaults; it must never print
  the real values it replaces.
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
  TypeScript, YAML, shell, markdown · new Python modules small and re-exported
  from hubs (MI is length-dominated past ~800 lines; name-matched
  `test_<module>.py` is what test-coverage detects) · Stop-hook completion gate:
  run `tapps_validate_changed` + `tapps_checklist` before ending any session
  with code edits.
- **Discipline:** root-cause not workarounds; no green-by-suppression;
  right-sized; durable over expedient; match repo conventions; no silent scope
  creep. If the correct fix is out of scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR,
  staged diff) and keep going. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** Linear plugin
  unauthenticated (Sub-goal 0) · any HA write outside the gateway converge path ·
  ZHA formation / device removal / integration uninstall · deleting any service
  in Sub-goal 8 · merging PR #82 (or any merge to `master`) · force-push ·
  deleting un-recreatable data · a write outside this repo's team/project ·
  physical-world steps (sensor placement, switch wiring, pairing buttons —
  surface as readiness gates, never simulate) · a genuinely ambiguous decision
  where a wrong guess is expensive.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior
failures → specific hypothesis → change something → retry. ≤3 distinct
strategies per story, then one escalation, then stop with a concise diagnosis
naming what was tried and why each failed. Expected-fail is the design —
verification rarely passes first try (the 2026-08-13 verifier found 2 real gaps
in "done" work); scope a narrow fix sub-goal from the verifier's gaps.

## Unverified assumptions

Confirm each before depending on it.

- **Waves 8–11 dependency claims** are issue-body-based, not build-verified —
  re-read each epic before starting it.
- **TAP-5430/5431 residual scope** — both were re-scoped by TAP-5991 against
  PR #82; read the re-scope comments before building.
- **TAP-5300/5302 In-Progress state** — started 2026-08-11; read their branches
  and comments before continuing (another session's partial work may exist).
- **TAP-6018 (Wave 4 gate)** — a custom ZHA quirk is code; if the ticket's
  blocker turns out to be authoring the quirk rather than physical placement,
  re-scope it into agent-workable + human-gated halves. Re-check once per run.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` ·
  assignee `Claude Agent` · brain project `homeiq`.
- **Host-port overrides:** dashboard **13000**, admin-api **18004**, websocket
  **18001**, postgres **15432**, retention **18080**, carbon **18010**, OTLP
  **14317/14318**, jaeger **16687**, ai-automation-ui **13001**, init gateway
  **8024**.
- **Wave-7 state (2026-08-13):** TAP-5943/5944/5945 Done (5944/5945 closed with
  adversarial-verifier evidence on the tickets; contract hardened `6d8e5bab`).
  Floors: homeiq-ha **194**, ha-setup-service **34**.
- **Live HA (2026-08-12 verified):** ZHA on SLZB-06P7 at `192.168.1.121:6638`,
  entry `01KZSE6SJ789RGEFCBRBA0VHDG`; 3 Inovelli Blue switches + Aqara
  multi-sensor placed and manifested; 1 stalled-interview device (ieee …c0:f4);
  Hue Bridge Pro `192.168.1.170` (296 entities / 50 devices / 19 areas); HACS +
  Team Tracker live; backups nightly 04:48 (24 exist as of 2026-08-13);
  init-gateway audit cron 03:15 → `.tapps-mcp/init-audit-<date>.json`; audit at
  rewrite time: 20 recipes, 1 blocked_on_human (`organization.device_areas`).
- **Prompt lineage (reviewed 2026-08-13):** supersedes
  `homeiq-backlog-burndown.md` (Wave 1–6 history + measurements live there);
  which superseded `ha-init-agent-activation.md` (completed 20/20) and
  `ha-office-presence-lighting.md` (completed 24/24).
  `ci-pipeline-full-repair.md` complete (merged `f3cacfbe`);
  `close-ha-and-dashboard-epics.md` / `close-unblocked-post-5405-work.md`
  superseded. `tapps-mcp-defects-from-homeiq-2026-08-02.md` is a handoff owned
  by the TappsMCP repo — out of scope here.
  `tapps-brain-defects-from-homeiq-2026-08-02.md` is self-marked SUPERSEDED —
  never execute it.
- **Known CI blocker, not fixable here:** TappsMCP has no installable dist (see
  CLAUDE.md "CI Integration") — upstream fix.
- Evidence: `docs/ha-init-agent-design.md` · `.tapps-mcp/session-handoff.md` ·
  brain keys `burndown-wave-*` (incl. `burndown-wave-7-5944-5945-verified`).
- PR #82: https://github.com/wtthornton/HomeIQ/pull/82 — manifest engine, init
  gateway, ZHA recipe, backup gating. Merge is the human's call.

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in
  a NEW session **with Linear authenticated** (`/mcp` first if in doubt).
- **Durable:** a Routine running one sub-goal per invocation, push=draft-PR.
- **Fan-out sub-steps:** read-only research and verification only, per the Plane
  map. Every code-editing chunk is N=1 sequential. No Workflow script is needed
  today; emit `.claude/workflows/<slug>.js` only if a sub-goal grows a genuine
  N×stages fan-out.
