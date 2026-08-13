# HomeIQ backlog drain — urgent fixes first, then empty the open Linear backlog

> Generated 2026-08-13 by the `orchestration-prompt` skill. **Successor to
> `prompts/homeiq-backlog-burndown.md`** (which it supersedes as the entry point —
> that file remains the reference for Wave 1–6 history and the full 2026-08-12
> backlog table). Waves 1–3, 5, 6 are DONE + verified; Wave 4 is human-blocked;
> Wave 7 is mid-flight with two stories verifier-passed but not closed in Linear.
> This prompt resumes at the exact frontier and drains everything that remains.
>
> **This is a multi-run loop.** One ~6-hour session finishes a wave or two.
> Re-enter it until the backlog is empty. Each sub-goal is a resumable checkpoint.

## Prerequisites / Wayfind gate

- **Route clear? Yes.** Wave order was locked by the predecessor prompt and the
  user's 2026-08-12 priority agreement; no open `wayfinder:map` tickets; all
  remaining chunks are execute / verify / fix. No decide work remains — if fog
  reappears (a genuinely new product decision surfaces mid-drain), stop that
  sub-goal and surface it; do not guess.
- **Wayfind resume (cold start):** `tapps_memory(action="search", query="burndown wave checkpoint")`
  — the CLI form is broken in this project (`MemoryStore requires a Postgres
  private_backend`); always use the MCP tool.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one wave per run) so it survives the terminal.

## Objective

Close out Wave 7 (setup wizard), then drain the remaining open HomeIQ backlog in
dependency order — MCP surface → genome/safety gate → HA front door → destructive
data-plane collapse — with every closure carrying independent-verifier evidence.

## Done-when (ground truth, not narration)

The backlog is empty when **every** clause holds. A single run satisfies the
clauses it reached; paste the artifacts for those and the current SCORE line for
the rest.

1. **Linear hygiene (immediate)** — TAP-5944 and TAP-5945 are closed in Linear
   with the prepared closure notes (see Sub-goal 1), pasted `get_issue` state
   `Done` for both.
2. **Wave 7 complete** — TAP-5946 and TAP-5947 closed with evidence; a full
   answers→converge→verify round-trip runs against a staged answer set (paste one
   driven flow); the 3-verifier wave panel passed (majority); epic TAP-5942 closed.
3. **Backlog re-read** — a fresh `linear-read` sweep of the whole project is
   pasted (count + ids), any issues filed since 2026-08-12 are triaged into the
   wave order (Urgent → front of queue), and every remaining open issue maps to a
   clause below or a recorded human-gate.
4. **Wave 8** — the `homeiq` MCP server answers `/health`; a pasted tool call
   returns real data for ≥1 query tool and ≥1 analytics tool; contract tests pin
   the schemas. (Epic TAP-5282: 5292–5297.)
5. **Wave 9** — every authored gene and chromosome passes offline kit validation,
   pasted; a pasted run shows the hard-deny list **refusing** a denied automation
   and a budget gate **holding** an over-cap plan (a correct refusal is a pass).
   (TAP-5285: 5311–5318, then TAP-5286: 5319–5325.)
6. **Wave 10** — the HA custom integration loads on the live instance and
   `/api/config/config_entries` shows the HomeIQ entry `loaded`. Installing it is
   an apply — route through the gateway path or hard-stop. (TAP-5284: 5305–5310.)
7. **Wave 11** — `docker ps --filter name=homeiq | grep -c healthy` is ≤15 and ≥8,
   **AND** for every retired service a pasted call proves its capability still
   reachable through an MCP tool or a gene. The second clause is mandatory.
   (TAP-5283: 5298–5304, 5910.)
8. **Wave 4 (standing)** — remains human-blocked on TAP-6018 unless the user
   clears it; each run re-checks `get_issue(TAP-6018)` once and records state.
9. **Always** — `.venv/bin/python -m pytest libs/homeiq-ha -q` → **0 failed**,
   pass count ≥ **194**; ha-setup-service tree → 0 failed, pass count ≥ **34**
   (run the two trees SEPARATELY — combining them breaks collection);
   `git status --short` clean at each story gate; every cited TAP id confirmed by
   `get_issue` (ids are workspace-sequential — verify the `project` field).

## Sub-goals (sequential; each a checkpoint)

0. **Establish preconditions (self-healing — the loop does this, not the user).**
   - `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks
     all other `tapps_*` tools until it runs. Re-run after any `/clear` or compact.
   - **🔴 Linear auth probe — before anything else.** ToolSearch
     `select:mcp__plugin_linear_linear__get_issue`. If the plugin tools do not
     load, the session is unauthenticated and **every closure this prompt exists
     for is blocked**: hard-stop once and tell the user to re-authorize Linear via
     `/mcp` in an interactive session. Do NOT fall back to raw Linear API calls
     (OAuth via the plugin is the only sanctioned path) and do NOT burn the run on
     code-only work while closures pile up — 2026-08-13 lost the closure step to
     exactly this.
   - Brain recall: `tapps_memory(action="search", query="burndown wave 7")` and
     `tapps_memory(action="search", query="homeiq backlog burndown")`. Wave 1–6
     outcomes live under `burndown-wave-*` keys — **never redo a verified wave.**
   - **🔴 Single-writer check:** `git status --short` twice ~30 s apart;
     `git log --oneline -3` for foreign commits. A dirty tree you did not create
     is a hard-stop. Never `git checkout` while another writer is active.
   - **Branch base:** `gh pr view 82 --json state | jq .state`. OPEN → branch off
     `feat/ha-init-agent-activation`'s tip and record the deviation; MERGED →
     work from master. Merging PR #82 is a human decision — hard-stop ask, once.
   - Test runner: `/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`;
     trees run SEPARATELY (both expose a `tests` package; libs shadows the
     service's `tests.path_setup`). Record start counts; enforce no-shrink.
   - Stack + smoke: healthy-container count; `curl :8024/health` → 200;
     `curl :8024/setup` → 200; `curl -s :8024/api/v1/init/queue | jq '.items|length'`
     (the key is `items` — `.queue` does not exist and silently returns 0; the
     count is live-derived from discovery flows and DRIFTS — never assert a
     frozen number). Off-contract POST to `/api/v1/init/answers` → **422**
     (schema hardened 2026-08-13, commit `6d8e5bab`).
   - **Deploy freshness:** several compose services declare `build:` with no
     `image:` — after any source change:
     `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`
     (`--env-file` is mandatory on single-service deploys or postgres creds break).
     Verify by identity, never by build exit code. Smoke before spend.
   - **Live-HA probe:** `GET :8024/api/v1/init/audit` (or latest
     `.tapps-mcp/init-audit-<date>.json` from the 03:15 cron). ZHA entry
     `01KZSE6SJ789RGEFCBRBA0VHDG` `loaded`; coordinator `192.168.1.121:6638`.
     Coordinator down → that is a Wave-5-class alert finding, not a reason to
     touch ZHA config.
   - **AgentForge reachability** (Waves 8–11): `mcp__agentforge__health`; if
     unavailable, wait-and-retry (containers recover in seconds). AF MCP caches
     `.env` at startup — `missing-bearer` after a key rotation means restart the
     server, not a bad key.
   - proof: session_start returned; Linear plugin loaded (or hard-stop recorded);
     brain recall pasted; single-writer clean; PR #82 state pasted; smoke set
     pasted (health/setup/queue/422); audit fetched.

1. **Close TAP-5944 + TAP-5945 (the leftover urgent fix).** Both are
   verifier-passed (2026-08-13, opus refute mode; full detail in brain key
   `burndown-wave-7-5944-5945-verified` and `.tapps-mcp/session-handoff.md`).
   Via the **`linear-issue` skill** (fetch → lint → comment/update → validate →
   save → invalidate snapshot), close each with its prepared note:
   - **TAP-5944:** GET /setup serves the wizard (200, headless-chrome-rendered,
     7/7 readiness badges). Acceptance count corrected: **11 items, not 12** —
     the 12th rendered card is the static sports-teams form; the proof key is
     `.items|length` (`.queue` doesn't exist); the count is live-derived and
     drifts, so the criterion is "matches the page's own status line", not a
     frozen number.
   - **TAP-5945:** POST /api/v1/init/answers ingests answers, converge is
     backup-gated and honest (`wrote_nothing`, `blocked_on_human` correct);
     compose `group_add` fix verified ([1000, 1001], manifest writable,
     bind-mount byte-identical); hardened 2026-08-13 with `extra="forbid"` +
     5 route-level tests (commit `6d8e5bab`) after the verifier found off-contract
     bodies returning 200.
   - proof: `get_issue` for both pastes state `Done`.

2. **TAP-5946 — pairing/permit readiness trigger.** `get_issue(TAP-5946)` first;
   root cause anchor `ws.py:200-206`; the fix speaks `zha/devices/permit` with an
   explicit `duration=N`. The 2026-08-12 manual pairing run is the reference
   protocol (readiness gates + physical button = human step — surface, never
   simulate). Required lookup before code: `tapps_lookup_docs` on the HA ZHA
   websocket API surface. Sequential in-session edit; `tapps_quick_check` per
   `src/` Python edit; fresh-context opus verifier refutes the proof.

3. **TAP-5947 — verify `config_entries/ignore_flow`.** `get_issue` first; this is
   a verify-shaped story — a correct "the flow is ignorable and stays ignored
   across restart" negative is a pass. Same edit/verify discipline.

4. **Wave-7 completion panel + close epic TAP-5942.** One full
   answers→converge→verify round-trip against a staged answer set (no-op answer
   set must yield `wrote_nothing: true`; a real one converges and read-back
   verifies). Then the 3-verifier panel (correctness · security/no-residue ·
   reproducibility — dispatch per Plane map), majority rules. Close 5946, 5947,
   then the epic via `linear-issue`.

5. **Live backlog re-read + urgent triage.** Via **`linear-read`** (cache-first;
   `state="open"` is a cache bucket — never pass it to the plugin), sweep the
   whole project. Paste the count and ids. Anything filed since 2026-08-12
   (TAP-6027 is known; expect others) gets triaged: Urgent/High operational
   defects jump the queue ahead of Wave 8; everything else slots into its epic's
   wave. Re-check TAP-6018 (Wave 4 gate) and record. Reconcile the TAP-5298 /
   TAP-5322 credential-move duplicate before Wave 9 — decide the owner, note it
   on the other, do it once.

6. **Waves 8 → 9 → 10 → 11 in order** (Done-when clauses 4–7). Re-read each
   epic's body before starting it (the dependency claims are issue-body-based,
   not build-verified). Wave 11 is destructive and last: never delete a service
   before a pasted call proves its capability reachable elsewhere; each deletion
   is an Autonomy hard-stop.

## Plane map (mechanism + literal dispatch parameters per chunk)

| Step | Plane | Mechanism | agentType | model | effort | Notes |
|---|---|---|---|---|---|---|
| Backlog re-reads | coordination | **`linear-read` skill** | n/a (in-session) | session | — | cache-first, hook-gated |
| Linear closures/comments | coordination | **`linear-issue` skill** | n/a (in-session) | session | — | handles the validate sentinel |
| Story implementation (5946, 5947, Waves 8–11) | execution | in-session, sequential, N=1 | n/a | session (frontier) | — | `tapps_quick_check` per `src/` edit |
| Research fan-outs (route discovery, entity sweeps) | coordination | 3–5 parallel `Agent()` calls | `Explore` | `haiku` (closed Qs) / `sonnet` (synthesis) | inherited | read-only enforced by agent type |
| Per-story verification | coordination | verifier subagent, fresh context, told to **refute** | `general-purpose` | `opus` | inherited | its verdict advances the loop, not the executor's claim |
| Wave-completion panel | coordination | 3 verifier subagents, perspective-diverse | `general-purpose` | `opus` | inherited | majority rules; never a cheap-model verdict on anything irreversible |
| Wave 8 MCP schema design | execution | in-session | n/a | session (frontier) | — | schema gates Waves 9–11 |
| Wave 3-style AF pipelines (if re-needed) | execution | AF author→judge workflow | AF-side | AF-side | — | deterministically re-check every judge finding against the artifact before amending |

`effort` is Workflow-only — Agent dispatches inherit the session's. If a future
wave grows a genuine N×stages fan-out, emit `.claude/workflows/<slug>.js` with
schema + `budget` + per-stage `model`/`effort` then; nothing here needs one today.

## Loop

- **State:** `git log --oneline -5`; `git status --short` (single-writer);
  backlog via `linear-read`; latest nightly audit; healthy-container count; brain
  recall of wave checkpoints and prior failures.
- **Decide:** the lowest-numbered unfinished sub-goal, then the lowest-numbered
  unfinished story within it. One story at a time. Human-gated items: record,
  surface in the final report, skip. Urgent triage results (Sub-goal 5) may
  insert ahead of Wave 8 — record the insertion.
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
  `SCORE: subgoal <s>/6 · wave <w>/11 · stories closed <n>/<open> · containers <n> healthy · pytest <fail> failures (<libs>+<svc>) · iteration <i>/45`
- **Repeat or stop:** until Done-when holds; caps **45 iterations** AND **1.5M
  output tokens per run**. Hitting a cap mid-wave is a normal stop — record the
  checkpoint; the next run resumes from it.

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
  every retired capability proven reachable**; dead-probe deletions keep the
  remaining probes' tests passing.
- **Caps must not fire on correct behavior:** a deny-list refusal is a pass · a
  budget gate holding is a pass · an honest `blocked_on_human` row is a pass · a
  verified zero-change second apply is the success signature of convergence · a
  422 on an off-contract body is the contract working · TAP-5947's "flow stays
  ignored" negative is a pass.
- **Independent verification:** creator ≠ verifier; ground-truth proof; no
  cheap-model verdict gates an irreversible step; re-derive load-bearing
  conclusions from returned evidence, not subagent narration (AF judges
  hallucinate findings — deterministic re-check before amending).
- **No fan-out of coupled coding** — migrations, gene authoring, retirement:
  sequential, in-session, N=1. Fan-out is read-only research and verification only.
  Check `git status` after any `general-purpose` fan-out.
- **Research grant:** web access, `tapps_research`, `tapps_lookup_docs`
  (Context7-backed, cache-first, free to repeat). **Required lookups before first
  code touching each surface:** ZHA websocket API (`zha/devices/permit`,
  Sub-goal 2) · `config_entries/ignore_flow` semantics (Sub-goal 3) · HA
  automation schema (2024.10+ plural `triggers:/conditions:/actions:`) · label/
  area registry semantics (labels store slug ids; match by name OR slug or
  re-applies mint `<slug>_2` dupes) · MCP server SDK (Wave 8) · AF workflow traps
  (`kind: task`; `$input` refs — literal `{{input}}` passes through; terminal
  state `complete`; `output_schema` on the workflow node; publish agents before
  workflows or 422).
- **Secrets:** `.env` gitignored and read-denied — work at key-name level
  (`.env.backup-pre-new-ha-20260801` holds the only copy of several credentials).
  `backup/config/info` returns the HA encryption key in plaintext — never log it,
  never paste it into Linear. Credential moves into the AF vault are moves, never
  copies.
- **Scope:** `/home/wtthornton/code/HomeIQ` only; Linear team `TappsCodingAgents`,
  project `HomeIQ`, assignee `Claude Agent`
  (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes forbidden.
- **Memory:** recall at start; record at every checkpoint including failures.
- **Harness compatibility (each adopted or overridden):** `tapps_session_start`
  first (adopted — PreToolUse gate) · Linear writes via `linear-issue` (adopted —
  save sentinel) · multi-issue reads via `linear-read` (adopted — snapshot gate;
  `state="open"` never reaches the plugin) · per-edit `tapps_quick_check` adopted
  for `src/` Python, **overridden to story-gate batching** for tests, TypeScript,
  YAML, shell, markdown · new Python modules small and re-exported from hubs (MI
  is length-dominated past ~800 lines; name-matched `test_<module>.py` is what
  test-coverage detects) · Stop-hook completion gate: run `tapps_validate_changed`
  + `tapps_checklist` before ending any session with code edits.
- **Discipline:** root-cause not workarounds; no green-by-suppression;
  right-sized; durable over expedient; match repo conventions; no silent scope
  creep. If the correct fix is out of scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR,
  staged diff) and keep going. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** Linear plugin
  unauthenticated (Sub-goal 0 — closures are the point of this prompt) · any HA
  write outside the gateway converge path · ZHA formation / device removal /
  integration uninstall · deleting any service in Wave 11 · merging PR #82 (or
  any merge to `master`) · force-push · deleting un-recreatable data · a write
  outside this repo's team/project · physical-world steps (sensor placement,
  switch wiring, pairing buttons — surface as readiness gates, never simulate) ·
  a genuinely ambiguous decision where a wrong guess is expensive.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior
failures → specific hypothesis → change something → retry. ≤3 distinct strategies
per story, then one escalation, then stop with a concise diagnosis naming what
was tried and why each failed. Expected-fail is the design — verification rarely
passes first try (2026-08-13's verifier found 2 real gaps in "done" work); scope
a narrow fix sub-goal from the verifier's gaps.

## Unverified assumptions

Confirm each before depending on it.

- **Waves 8–11 dependency claims** are issue-body-based, not build-verified —
  re-read each epic before starting it.
- **The open-issue count.** 78 on 2026-08-12; Waves 1–3/5/6 closures and any new
  filings have moved it — Sub-goal 5's live re-read is the source of truth.
- **TAP-5946/5947 scope** is known only from handoff notes — `get_issue` before
  the first edit.
- **TAP-6018 (Wave 4 gate)** may have been cleared by the human — re-check once
  per run.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` ·
  assignee `Claude Agent` · brain project `homeiq`.
- **Host-port overrides:** dashboard **13000**, admin-api **18004**, websocket
  **18001**, postgres **15432**, retention **18080**, carbon **18010**, OTLP
  **14317/14318**, jaeger **16687**, ai-automation-ui **13001**, init gateway
  **8024**.
- **Wave-7 state (2026-08-13):** TAP-5943 Done. TAP-5944/5945 verifier-passed
  after same-session gap fixes (commit `6d8e5bab`: `extra="forbid"` + 5 route
  tests; redeployed + live-re-verified) — closure notes prepared, blocked only on
  Linear auth. Floors: homeiq-ha **194**, ha-setup-service **34**.
- **Live HA (2026-08-12 verified):** ZHA on SLZB-06P7 at `192.168.1.121:6638`,
  entry `01KZSE6SJ789RGEFCBRBA0VHDG`; 3 Inovelli Blue switches + Aqara
  multi-sensor placed and manifested; 1 stalled-interview device (ieee …c0:f4);
  Hue Bridge Pro `192.168.1.170` (296 entities / 50 devices / 19 areas); HACS +
  Team Tracker live; backups nightly 04:48; init-gateway audit cron 03:15 →
  `.tapps-mcp/init-audit-<date>.json`. TAP-5992's interim rule stands: every
  automation deploy passes an explicit id.
- **Prompt lineage (reviewed 2026-08-13):** this file supersedes
  `homeiq-backlog-burndown.md` (Waves 1–6 history + measurement records live
  there); which superseded `ha-init-agent-activation.md` (completed 20/20; its
  residual wizard work IS Wave 7 here) and `ha-office-presence-lighting.md`
  (completed 24/24). `ci-pipeline-full-repair.md` is complete (merged
  `f3cacfbe`); `close-ha-and-dashboard-epics.md` and
  `close-unblocked-post-5405-work.md` are superseded (their epics are on the
  "Closed, do not reopen" list). `tapps-mcp-defects-from-homeiq-2026-08-02.md`
  is a handoff owned by the TappsMCP repo — out of scope here (write-scope
  rule). `tapps-brain-defects-from-homeiq-2026-08-02.md` is self-marked
  SUPERSEDED (flawed-reasoning record) — never execute it.
- **Known CI blocker, not fixable here:** TappsMCP has no installable dist (see
  CLAUDE.md "CI Integration") — upstream fix.
- Evidence: `docs/ha-init-agent-design.md` · `.tapps-mcp/session-handoff.md` ·
  brain keys `burndown-wave-*`.

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in a
  NEW session **with Linear authenticated** (`/mcp` first if in doubt).
- **Durable:** a Routine running one wave per invocation, push=draft-PR.
- **Fan-out sub-steps:** read-only research and verification only, per the Plane
  map. Every code-editing chunk is N=1 sequential. No Workflow script is needed
  today; emit `.claude/workflows/<slug>.js` only if a wave grows a genuine
  N×stages fan-out.
