# HomeIQ backlog burndown — all open epics, dependency-ordered

> Generated 2026-08-01; **updated 2026-08-12** after re-reading the complete open backlog
> (78 open issues) and the physical-layer day: ZHA live on the SLZB-06P7, 3 Inovelli Blue
> switches joined, Hue Bridge Pro paired (296 entities, 19 areas), HACS + Team Tracker
> installed, backups armed (6 exist, nightly 04:48), init gateway live on :8024 with a
> 03:15 nightly audit. Four new epics were filed from that work and are folded in below.
> Supersedes the 2026-08-01 wave table; the Wave-1 measurement history is preserved.
>
> **This is a multi-run loop.** One ~6-hour session finishes a wave or two. Re-enter it
> as a Routine until the backlog is empty. Each wave is a resumable checkpoint.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-backlog-burndown.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Wave 0; work the lowest-numbered unfinished wave only; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one wave per run) so it survives the terminal.

## Objective

Burn down the HomeIQ backlog in dependency order — first the urgent operational-honesty
defects, then the four 2026-08-12 epics in the user-agreed order (Hue absorption → office
presence physical → Zigbee health → switch comfort), then the wizard, then the strategic
platform epics (MCP surface → genome → safety gate → HA front door), and only then the
destructive data-plane collapse.

## The full backlog (read 2026-08-12 — 78 open issues via `linear-read`, nothing omitted)

| Wave | Epic / group | Issues |
|---|---|---|
| 1 | Build/CI reconciliation (TAP-5281, Urgent) — **functionally met 2026-08-10, stories still open** | 5287 · 5288 · 5289 · 5290 · 5291 |
| 2 | Urgent operational honesty (standalones + bug batch) | 5902 (In Progress) · 5903 · **5992 (deploy-overwrite defect, High — regression tests specified; interim rule: always pass explicit automation id on deploy)** · 5437 · 5438 · 5445 · 5446 · 5447 · 5448 · 5449 · 5450 · 5434 · 5439 · 5440 |
| 3 | **Epic A** — Hue absorption (TAP-5973, High) | 5974 · 5975 · 5976 |
| 4 | **Epic B** — Office presence goes physical (TAP-5977, High) | 5978 · 5979 · 5980 |
| 5 | **Epic C** — Zigbee operational health (TAP-5981, Medium) | 5982 · 5983 (coordinator watchdog) · 5984 (log passthrough) |
| 6 | **Epic D** — Switch comfort (TAP-5985, Medium) + init-agent closeout | 5987 (gesture catalogue) · 5988 (smart-bulb eval) · 5989 (switch #4 wiring, human-gated) — **5986 (fan automation) closed Done 2026-08-12** · 5921 · 5991 (re-scope 5429/5430/5431 against PR #82) · 5990 (goal-loop ADR) |
| 7 | Setup wizard (TAP-5942, High — gated on proving the manual loop, which 2026-08-12 did) | 5943 · 5944 · 5945 · 5946 · 5947 — **do 5289 (Wave 1) first**, the wizard serves from ha-setup-service |
| 8 | HomeIQ MCP server (TAP-5282, Urgent) | 5292 · 5293 · 5294 · 5295 · 5296 · 5297 |
| 9 | AgentForge species four (TAP-5285) then safety gate (TAP-5286) | 5311–5318 then 5319–5325 |
| 10 | HA integration with scoped LLM API (TAP-5284) | 5305–5310 |
| 11 | Data plane collapse (TAP-5283, In Progress: 5300/5302 started) — **destructive, last** | 5298 · 5299 · 5300 · 5301 · 5302 · 5303 · 5304 · 5910 |

**Human-gated, do NOT attempt (record and skip):** physical sensor/switch placement
(Wave 4's sensor must be physically in the office — ask, don't assume) · the 4th Inovelli
switch (dark LED after reset — suspected wiring, needs hands) · merging PR #82 · anything
the audit lists as `blocked_on_human` or `needs_user_input`.

**Closed, do not reopen:** TAP-5405+5406–5412 · TAP-5413+5414–5418 · TAP-5424 · TAP-5427
(backup key was set headless 2026-08-12 — the "UI-only" claim in its body was disproven) ·
TAP-5433 · TAP-5410 · TAP-5411.

### Why this order (measured where possible)

- **Wave 1 is reconciliation, not construction.** The 2026-08-10 measurement (preserved
  below) showed the epic's real defects were already fixed; its five stories are still
  open in Linear. Close each with evidence or re-scope to what measurement left standing
  (5289's compose fragment is real and gates Wave 7; 5291's regression check may still
  be worth building). Do not re-litigate the refuted claims.
- **Wave 2 makes the data plane honest before anything builds on it.** TAP-5902 (55
  dropped env keys silently killing feeds) and TAP-5903 (health = uptime lies) corrupt
  every downstream diagnosis; the postgres schema 500s (5437/5438) and the 500-batch
  block dashboard trust.
- **Waves 3–6 are the user-agreed 2026-08-12 priority (A→B→C→D).** A unblocks the
  manifest engine's claim to the whole ~90-device house; B is small and high-value;
  C prevents a repeat of the 2026-08-12 silent coordinator outage; D is comfort.
- **Wave 7 after 3–6:** the wizard productizes exactly the flows run by hand on
  2026-08-12 — pairing windows, readiness gates, tap/blink identification, discovery
  triage. TAP-5946 should inherit that protocol (already noted on the ticket).
- **Wave 8 gates 9–11** (unchanged from 2026-08-01): the MCP tool catalogue is what the
  genes call, what the HA integration exposes, and what replaces the services Wave 11
  deletes. **Wave 11 is last because it is destructive.**

## Standing constraints

- **🔴 The live Home Assistant at `192.168.1.80` is a real home — but the 2026-08-01
  blanket read-only rule is superseded.** Applies are now allowed **only** through the
  init gateway's established converge path (`POST :8024/api/v1/init/converge`), which is
  backup-gated, per-phase scoped (`{"phase": N}` — a full-stack converge halts at the
  first `BLOCKED_ON_HUMAN`), and read-back verified. Never weaken `BackupGateNotSatisfied`.
  Outside that path, HA writes remain hard-stops. **Absolute never-do:** re-running ZHA
  network formation on the loaded entry (orphans every paired device), removing paired
  devices, deleting areas with assigned devices, uninstalling loaded integrations.
- **Never commit a secret.** `.env` stays gitignored (and is read-denied — work at
  key-name level; `.env.backup-pre-new-ha-20260801` holds the only copy of several
  credentials). `backup/config/info` returns the HA encryption key in plaintext — never
  log it, never paste it into Linear. Credential moves into the AgentForge vault are
  moves, never copies.
- **Scope is this repo only.** Linear team `TappsCodingAgents`, project `HomeIQ`,
  assignee `Claude Agent` (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes
  forbidden (`agent-scope.md`). TAP ids are workspace-wide sequential — verify every id's
  `project` field with `get_issue` before citing it.
- **No green-by-suppression.** Never skip, disable, `# noqa`, `# type: ignore`, or weaken
  a test or checker to go green. If the correct fix is out of scope, stop and say so.
- **Never delete a capability to hit a count.** Waves 1 and 11 measure things going down;
  see the paired clauses in Done-when.
- **PR #82 is the manifest engine's home** (`feat/ha-init-agent-activation`, 20+ commits,
  draft). Until it merges, Waves 3–7 branch off its tip (record the deviation), not off
  master. Merging it is a human decision — a hard-stop ask, once.

## Done-when (ground truth, not narration)

The backlog is empty when **every** wave's clause holds. A single run satisfies the waves
it reached; paste the artifacts for those and the current SCORE line for the rest.

1. **Wave 1** — every one of 5287/5288/5290/5291 is closed-with-evidence or re-scoped
   (comment naming the 2026-08-10 measurement), and 5289's compose fragment is repaired
   or deleted with `docker compose -f domains/<d>/compose.yml config` exiting 0.
   The 2026-08-10 measured state must still hold: `start-stack.sh` free of
   `--pull always --force-recreate`, `gh workflow list --all` showing ≥18/19 documented
   workflows `active`.
2. **Wave 2** — TAP-5902: the key-restoration is committed and every named feed's data
   route (not `/health`) pastes fresh data. TAP-5903: at least the fleet's tier-1
   services' health endpoints probe a real dependency (paste one before/after).
   Postgres: `/api/v1/memories/*` and the three patterns routes return non-500, pasted.
   Bug batch: each of 5445–5450 pastes a non-500/non-404 response **or** a recorded
   removal reason (a correct removal is a pass). Contract rows ≥88 with 0 deviations
   (`bash scripts/verify-dashboard-contract.sh`, paced — never lower `CONTRACT_PACE`).
3. **Wave 3 (A)** — nightly audit shows the Hue surface managed: 50 Hue devices in the
   manifest, area-slug collisions reconciled (no `master_bedroom`-vs-`bedroom` dupes in
   the area registry, pasted), a committed scene stance covering all 190, and second
   apply = zero changes.
4. **Wave 4 (B)** — `binary_sensor.office_presence_group` contains a physical presence
   sensor (registry read-back pasted), the VAL-017-style behavioral smoke passes against
   the real sensor, proxies demoted to test-harness-only, and the stalled-interview
   device (ieee …c0:f4) resolved to a named, placed device or documented as removed.
5. **Wave 5 (C)** — the nightly audit gains per-device LQI/availability rows (pasted from
   a real artifact), a coordinator-unreachable alert fires in a staged test (paste the
   alert), and `/core/logs` returns parseable text.
6. **Wave 6 (D)** — Epic D's stories closed: gesture catalogue committed as
   manifest-declared **options** (deploying any binding stays user-gated), fan
   presence-comfort automation live and behaviorally verified **if its temp/presence
   prerequisites verified available**, 5921's dead probes deleted with the MI debt paid
   (gate passes without suppression), 5429/5430/5431 each closed or re-scoped with a
   comment naming what PR #82 already delivered.
7. **Wave 7** — the wizard serves on the LAN, `GET /api/v1/init/queue` returns the live
   audit-derived queue, a full answers→converge→verify round-trip runs against a staged
   answer set, and readiness triggers cover pairing/PIN/HACS (paste one driven flow).
8. **Wave 8** — the `homeiq` MCP server answers `/health`, a pasted tool call returns
   real data for ≥1 query tool and ≥1 analytics tool, contract tests pin the schemas.
9. **Wave 9** — every authored gene and chromosome passes offline kit validation,
   pasted; a pasted run shows the hard-deny list **refusing** a denied automation and a
   budget gate **holding** an over-cap plan (a correct refusal is a pass).
10. **Wave 10** — the HA custom integration loads on the live instance and
    `/api/config/config_entries` shows the HomeIQ entry `loaded`. Installing it is an
    apply — route through the gateway path or hard-stop.
11. **Wave 11** — `docker ps --filter name=homeiq | grep -c healthy` is ≤15 and ≥8,
    **AND** for every retired service a pasted call proves its capability still reachable
    through an MCP tool or a gene. The second clause is mandatory.
12. **Always** — `.venv/bin/python -m pytest libs/homeiq-ha -q` shows **0 failed** and a
    pass count ≥ the count at run start (must not shrink; it was ≥99 on 2026-08-01 and
    grew on 2026-08-12), `git status --short` is clean at each story gate, and every
    cited TAP id was confirmed by `get_issue`.

## Wave 0 — Establish preconditions (self-healing — the loop does this, not the user)

- `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks all other
  `tapps_*` MCP tools until this runs. Re-run after any `/clear` or compact.
- Brain recall: `tapps_memory(action="search", query="homeiq backlog burndown wave checkpoint")`
  and `tapps_memory(action="search", query="ha-init-agent-activation-progress")`. The CLI
  (`uv run tapps-mcp memory search`) is **broken** (`MemoryStore requires a Postgres
  private_backend`) — use the MCP tool.
- **🔴 Single-writer check — before ANY edit.** This repo has had two+ Claude sessions on
  one working tree (observed 2026-08-01 and again 2026-08-12 with the init-agent loop).
  `git status --short` twice ~30 s apart; `git log --oneline -3` for foreign commits. A
  dirty tree you did not create, or files changing between reads, is a hard-stop, not
  something to stash around. **Never `git checkout` while another writer is active.**
- **Branch base:** check PR #82 (`gh pr view 82`). Merged → work from master. Unmerged →
  branch off `feat/ha-init-agent-activation`'s tip for Waves 3–7 and record the deviation.
- Test runner: **`/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`**. System
  `python3` has no pytest.
- Stack health: `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c healthy`.
  If low before Wave 11, `bash scripts/domain.sh start <domain>`. **"(healthy)" counts
  measure uptime, not function** — probe the real data route before trusting any service.
- **Host-port overrides:** dashboard **13000**, admin-api **18004**, websocket **18001**,
  postgres **15432**, retention **18080**, carbon **18010**, OTLP **14317/14318**, jaeger
  **16687**, ai-automation-ui **13001**, init gateway **8024**.
- **Merged ≠ live, built ≠ loaded.** Several compose services declare `build:` with no
  `image:`. After any source change:
  `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`
  (single-service deploys **need `--env-file`** or they get the wrong postgres password).
  Verify by identity (image id or in-container sentinel), never by build exit code.
- **Smoke before spend:** after any rebuild, curl `/health` plus one cheap end-to-end call.
- **Live-HA state probe:** `GET :8024/api/v1/init/audit` (or read the latest
  `.tapps-mcp/init-audit-<date>.json` from the 03:15 cron). Confirm ZHA entry
  `01KZSE6SJ789RGEFCBRBA0VHDG` is `loaded`, backups ≥1 and schedule present, coordinator
  reachable at `192.168.1.121:6638`. Coordinator down → that's Wave 5's problem statement,
  not a reason to touch ZHA config.
- **AgentForge reachability** (Waves 3, 6, 8–10): `mcp__agentforge__health` before
  authoring or invoking. If AF is unavailable, **wait and retry** (containers cycle,
  recover in seconds — user rule). The `agentforge` MCP server caches `.env` at startup:
  after a key rotation its tools return `missing-bearer` until restart while curl works —
  do not diagnose that as a bad key. AF experts can return degenerate output
  (`{"advice":"test"}`) at full cost — retry once with an anti-placeholder instruction.
  AF judges hallucinate findings against their own input — deterministically re-check
  every finding against the artifact before amending; reject-with-evidence is a
  first-class disposition.
- **Harness compatibility** (bake in, do not fight):
  - `save_issue` is gated on a `docs_validate_linear_issue` sentinel < 30 min — route all
    Linear writes through the **`linear-issue` skill**.
  - `list_issues` is gated on a prior `tapps_linear_snapshot_get` — route multi-issue
    reads through **`linear-read`**; single issues via `get_issue(id=...)`. `state="open"`
    is a cache bucket — never pass it to the plugin.
  - Per-edit quality nudge **adopted** for `src/` Python (`tapps_quick_check`),
    **overridden to wave-gate batching** for tests, TypeScript, YAML, shell, markdown.
  - New Python modules: plan small cohesive modules re-exported from the hub file — the
    gate's maintainability score is module-length-dominated (MI ~0 past ~800 lines) and
    name-matched `test_<module>.py` files are what test-coverage detects.
- **Research grant:** the loop has web access, `tapps_research`, and `tapps_lookup_docs`
  (Context7-backed, local-cache-first — free to repeat). **Required lookups before first
  code touching each surface:** HA automation schema (2024.10+ plural
  `triggers:/conditions:/actions:` — legacy singular lints clean and fails at runtime),
  HA label/area registry semantics (labels store slug ids; HomeIQ stores `prefix:name` —
  match by name OR slug or every re-apply mints `<slug>_2` dupes), MCP server SDK (Wave
  8), HACS/Team Tracker entity naming (Wave 6 fan work). AF workflow authoring traps:
  `kind: task` not `kind: agent`; `$input` refs (a literal `{{input}}` passes through);
  terminal state `complete`; `output_schema` on the workflow node; publish agents before
  workflows or 422.
- **Reconcile the credential-move duplicate before Wave 9:** TAP-5298 (child of 5283) and
  TAP-5322 (child of 5286) both move the provider credential to the AF vault. Decide the
  owner, note it on the other, do it once.
- proof: session_start returned; brain recall pasted; single-writer check clean; PR #82
  state pasted; healthy count + one data-route probe pasted; audit fetched; AF health
  pasted or wait-and-retry recorded.

## Plane map (mechanism + model tier per chunk)

| Step | Plane | Mechanism | Model tier | Notes |
|---|---|---|---|---|
| Re-read backlog each wave | coordination | **`linear-read` skill** | cheap | cache-first, hook-gated |
| Wave 1 story reconciliation | coordination | in-session | cheap | evidence already exists; write comments via `linear-issue` |
| Wave 2 env-key + health fixes | execution | in-session, sequential per service | `sonnet` / low | mechanical once the key-map is settled |
| Wave 2 postgres schema + 500 batch | execution | in-session, sequential | **frontier / high** for schema design; cheap for route fixes | |
| Wave 3 Hue sweep (50 devices) | execution | **AF author→judge pipeline** (existing manifest workflow) | AF-side | deterministic re-check of every judge finding before amending |
| Wave 3 scene governance | execution | in-session | **frontier / high** | policy design, load-bearing |
| Waves 4–6 HA-side stories | execution | in-session, sequential; converge via gateway per-phase | `sonnet`, frontier for automation semantics | human-gated placements recorded, not attempted |
| Wave 7 wizard stories | execution | in-session, sequential | **frontier / high** for API design; cheap for page serving | |
| Wave 8 MCP catalogue + schemas | execution | in-session, sequential | **frontier / high** | schema gates Waves 9–11 |
| Waves 9–10 gene/skill/integration authoring | execution | in-session, sequential | **frontier / high** | safety semantics |
| Wave 11 service retirement | execution | in-session, one service at a time | **frontier / high** | destructive; replacement proven first |
| Research fan-outs (route discovery, entity sweeps) | coordination | 3–5 parallel subagents — `Agent(subagent_type: "Explore", model: "haiku")` for closed questions, `"sonnet"` for synthesis | cheap | read-only enforced by agent type; check `git status` after any `general-purpose` fan-out |
| Per-story verification | coordination | verifier subagent, fresh context — `Agent(subagent_type: "general-purpose", model: "opus")` told to **refute** | **frontier** | its verdict advances the loop, not the executor's claim |
| Wave-completion verification | coordination | 3 verifier subagents, perspective-diverse (correctness · security/no-residue · reproducibility), `model: "opus"` | **frontier** | majority rules; never a cheap-model verdict gating anything irreversible |
| Linear writes | coordination | **`linear-issue` skill** | cheap | handles the sentinel |

## Loop

- **State:** `git log --oneline -5`; `git status --short` (single-writer check);
  backlog via **`linear-read`**; latest nightly audit; healthy-container count; brain
  recall of prior wave checkpoints and failures.
- **Decide:** the **lowest-numbered wave not yet verified-done**, then the
  lowest-numbered unfinished story within it. One story at a time. Do not start a later
  wave because an earlier one is hard — record the blocker and say so. Human-gated items:
  record, surface in the final report, skip.
- **Execute:** on the committed mechanism above. Code edits sequential, in-session.
  `tapps_quick_check` after each `src/` Python edit; `tapps_validate_changed` with
  explicit `file_paths` at each story gate.
- **Verify (independent):** spawn a fresh-context **opus** verifier told to **refute**
  the story's proof. Hand it the exact command, expected artifact, `file:line` anchors,
  and environment quirks (port 13000 not 3000; `.venv/bin/python`; `--env-file` on
  single-service deploys; `CONTRACT_PACE` must not be lowered — admin-api rate-limits at
  60 req/min and unpaced sweeps yield false 429s; HA reads via the gateway). Never hand
  it narration. Its verdict advances the loop.
- **On fail:** diagnose — read the actual error, inspect state, recall prior failures —
  hypothesis → fix → retry *with something changed*. ≤3 distinct strategies per story,
  then escalate once, then stop with a concise diagnosis. Never re-run the same action on
  the same error.
- **Record:** `tapps_memory(action="save", key="burndown-wave-<n>-<story>", tier="pattern",
  value="<outcome incl. what failed and why>")`. On a failed story, record the structured
  handoff: what completed, what is undone, commands + exit codes, issues found.
- **Context hygiene:** prune stale reads each iteration; targeted `grep` over full
  re-`Read`; compact state summary forward, not raw transcripts; delegate noisy
  multi-file reading to an `Explore` subagent and keep only its summary.
- **Print every iteration:**
  `SCORE: wave <w>/11 · stories closed <n>/61 open · contract <pass>/<total> · audit <sat>/<blocked>/<needs> · containers <n> healthy · pytest <fail> failures · iteration <i>/45`
- **Repeat or stop:** until Done-when holds; caps **45 iterations** AND **1.5M output
  tokens per run**. Hitting a cap mid-wave is a normal stop — record the checkpoint and
  let the next run resume from it.

## Guardrails

- **Termination:** the Done-when set; caps 45 iterations AND 1.5M output tokens per run.
- **No green-by-deletion — every downward count is paired:** containers ≤15 **but every
  retired capability proven reachable**; contract deviations → 0 **at ≥88 rows** (must
  rise past 36); dead-probe deletion (5921) **but the health service's remaining probes
  still pass their tests**.
- **Caps must not fire on correct behavior:** a deny-list refusing an automation is a
  pass · a budget gate holding a plan is a pass · removing a frontend call with no
  backend route is a correct Wave 2 outcome · an audit that honestly reports
  `blocked_on_human` rows is a pass, not a defect · a verified zero-change second apply
  is the *success* signature of convergence, not "nothing happened".
- **🔴 HA writes only through the gateway converge path** — backup-gated, per-phase,
  read-back verified. ZHA formation on the loaded entry / device removal / integration
  uninstall: never. Anything else outside the gateway: hard-stop.
- **Wave 11 is destructive and ordered last on purpose.** Never delete a service before
  a pasted call proves its capability reachable elsewhere.
- **Independent verification** — a verifier that did not do the work, handed the proof
  command rather than the claim, judged against ground truth. Never let a cheap model's
  verdict gate an irreversible step; re-derive load-bearing conclusions from returned
  evidence, not subagent narration.
- **No fan-out of coupled coding** — migrations, gene authoring, retirement: sequential,
  in-session, N=1. Fan-out is for read-only research and verification only.
- **Scope:** `/home/wtthornton/code/HomeIQ` only; team `TappsCodingAgents`, project
  `HomeIQ`. Verify every TAP id's project before citing.
- **Secrets:** as Standing constraints — and `.env` is read-denied; work at key-name
  level from `.env.backup-pre-new-ha-20260801`'s key list.
- **Memory:** recall at start, record at every checkpoint including failures.
- **Harness compatibility:** `tapps_session_start` first · `linear-issue` for writes ·
  `linear-read` for multi-issue reads · per-edit quality nudge adopted for `src/` Python,
  wave-gate batching elsewhere · small modules re-exported from hubs.
- **Discipline:** root-cause not workarounds; no green-by-suppression; right-sized;
  durable over expedient; match repo conventions; no silent scope creep. If the correct
  fix is out of scope, stop and say so.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR, staged
  diff) and keep going. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** any HA write outside the
  gateway converge path · ZHA formation / device removal / integration uninstall ·
  deleting any service in Wave 11 · merging PR #82 (or any merge to `master`) ·
  force-push · deleting un-recreatable data · a write outside this repo's team/project ·
  physical-world steps (sensor placement, switch wiring, pairing buttons) — surface
  these, never simulate them · a genuinely ambiguous decision where a wrong guess is
  expensive.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior failures →
form a specific hypothesis → change something → retry. ≤3 distinct strategies per story,
then one escalation, then stop with a concise diagnosis naming what you tried and why
each failed. Expected-fail is the design: verification rarely passes first try — scope a
narrow fix sub-goal from the verifier's gaps, ≤3 validation rounds per story, never
weaken the contract to go green.

## Unverified assumptions

Confirm each before depending on it.

- **The wave ordering's dependency claims for Waves 8–11.** Basis: issue bodies, not a
  build. **Confirm by:** re-read each epic and its claimed dependency before starting it.
- **TAP-5902's remaining scope.** It is In Progress — the 2026-08-12 session may have
  restored some keys. **Confirm by:** `get_issue(TAP-5902)` + read its branch/PR state
  before re-doing work.
- **Wave 2's 500-batch reproduction.** Basis: 2026-08-02 probes; the stack has changed
  since (Hue, HACS, new integrations). **Confirm by:** re-curl each route before fixing —
  some may already be green, some newly broken.
- **The stashed TAP-5433 prefix fixes** (2026-08-01, `git stash list`) may now conflict
  or be moot — TAP-5433 closed. **Confirm by:** review `git stash show -p`; drop if moot.
- **pytest floor.** ≥99 on 2026-08-01, grew since. **Confirm by:** run at Wave 0, record
  the start count, enforce no-shrink against *that*.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` ·
  assignee `Claude Agent`
- **2026-08-12 physical-layer state (all live-verified that day):** ZHA on SLZB-06P7 at
  `192.168.1.121:6638`, entry `01KZSE6SJ789RGEFCBRBA0VHDG` — 3 Inovelli Blue switches
  (Office Fan VZM35, Office Light Dimmer, Bar Light Dimmer, all placed + manifested),
  1 Aqara multi-sensor (meshed and roomed; the fan presence-comfort automation runs
  against it — 0.34s response, proven, TAP-5986 closed), 1 stalled-interview device
  (ieee …c0:f4). TAP-5992 records a deploy-overwrite defect found during the fan work
  (deploy without an explicit id overwrote a neighboring automation, since restored) —
  until fixed, every automation deploy passes an explicit id. Hue Bridge Pro at `192.168.1.170` — 296 entities, 50 devices, 19 areas
  (the old aiohue pairing bug no longer reproduces; do not cite it). HACS installed +
  GitHub-authed; Team Tracker live (Golden Knights NHL, Raiders NFL). Backups: 6 exist,
  nightly 04:48, daily/7. Init gateway :8024; nightly audit cron 03:15 →
  `.tapps-mcp/init-audit-<date>.json`. Audit at update time: 13 sat / 3 blocked / 0
  needs-apply (pre-Hue-absorption; 2026-08-13: 19 sat / 1 blocked of 20 — the recipe
  set grows, verify counts against the live audit rather than these snapshots).
- **Coordinator outage 2026-08-12 (Wave 5's origin):** SLZB dropped off the network
  after a reboot; nothing alerted — ZHA sat in `setup_retry` silently. Recovery was a
  30s power-cycle. LQI/watchdog/alerting is the fix, not ZHA config changes.
- Wave-1 measurement history (2026-08-10, preserved): build contexts 54/54 repo-root are
  **correct, not debt** (targeted COPY + BuildKit digests: 16/16 layers cached, 50.84 kB
  transfer); the real defects were `start-stack.sh:91` forcing
  `--pull always --force-recreate` (fixed `04f78dd3`) and **18 of 19 documented
  workflows `disabled_manually`** at the GitHub API level (17 re-enabled;
  `dependabot-auto-merge` deliberately off). Count `gh workflow list` **state**, not
  triggers.
- **Known CI blocker, not fixable from this repo:** TappsMCP has no installable dist
  (see CLAUDE.md "CI Integration") — the fix is upstream.
- Shared client: `libs/homeiq-ha/src/homeiq_ha/client/` — proven live; Wave-2-era
  migration completed (TAP-5424 closed).
- PR #82: https://github.com/wtthornton/HomeIQ/pull/82 — the manifest engine, init
  gateway, ZHA recipe, backup gating. Merge is the human's call.
- Evidence: `docs/ha-init-agent-design.md` ·
  `docs/operations/dashboard-triage-2026-08-01.md` · `prompts/ha-init-agent-activation.md`
  (the completed 20/20 goal loop this prompt inherits from)
- Prior learnings: `tapps_memory(action="search", query="homeiq backlog burndown")`

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in a new
  session.
- **Durable:** a Routine running one wave per invocation, push=draft-PR.
- **Fan-out sub-steps:** read-only research and verification only — plain subagents with
  the agentType/model spelled out in the Plane map. Every code-editing chunk is N=1
  sequential. No Workflow script is committed for this loop: the only multi-stage
  parallel chunk (wave-completion 3-verifier panel) is small enough for direct Agent
  dispatches; if a future wave grows a genuine N×stages fan-out, emit
  `.claude/workflows/<slug>.js` with schema + budget + per-stage model/effort then.
