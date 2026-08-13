# Close TAP-5405 (HA Init/Setup Agent)

> Rewritten 2026-08-01 after the phase-1 live-audit session. **TAP-5413 (dashboard) is Done** —
> all five children closed, contract at 36/36, CI gate merged. Only its residual is carried here.
> Run from an orchestrator session in `/home/wtthornton/code/HomeIQ`.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/close-ha-and-dashboard-epics.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save the same line as a Routine (one sub-goal per run) so it survives the terminal.

## Where this stands (verified 2026-08-01T21:5x, not narrated)

| Fact | Evidence |
|---|---|
| TAP-5413 + children 5414–5418 | **Done** — `3bc9af04`, `64b90c58` |
| TAP-5406 (shared client), 5407 (engine), 5412 (stub wizards) | **Done** — `45fe71a1`, `4ba8c1f8`, `3b9ce0f7` |
| TAP-5408/5409/5410/5411 | **In Review** — code shipped, live proof incomplete |
| TAP-5424 (12 REST-registry callers) | **Backlog** — client imported by nothing outside `libs/homeiq-ha` |
| TAP-5405 epic | **In Review** |
| Phase 1 (backups) | live-audited, five defects fixed, full apply→verify→restore cycle proven |
| Phase-1 fix set | **UNCOMMITTED** — 8 modified + 2 new files in the working tree |
| Phases 2–6 | never exercised live (handoff names 2, 4, 5; confirm 3 and 6 from audit output, don't assume) |
| `TAP-5428` | **Was unallocated, now belongs to another project.** The prior handoff named it as the HomeIQ P0. At 22:05 on 2026-08-01 `get_issue` returned "Could not find referenced Issue"; by 22:16 the same day an unrelated session had allocated TAP-5428 to `Web-Store-DNA` ("AF policy mode is permissive", parent TAP-5180). TAP ids are workspace-wide sequential across projects, so a missing id is usually *not yet allocated* — and it will later be filled by whatever work claims it next. An unverified inherited id is therefore worse than merely wrong: it can silently resolve to a real issue in a project you are forbidden to write to (`agent-scope.md`). Confirm both existence **and** `project` with `get_issue` before acting. |

## Objective

Take TAP-5405 from In Review to closed: commit the proven phase-1 work, exercise the
remaining phases against the live instance under the snapshot guard (or record an
explicit, reasoned deferral for each), resolve the client-adoption gap, and leave every
child issue Done or Cancelled-with-a-reason.

## Done-when (ground truth, not narration)

**All five artifacts pasted in one final iteration:**

1. `git status --short` showing the phase-1 fix set committed and the tree clean of
   `libs/homeiq-ha` changes, plus the `git log --oneline -3` that contains it.
2. `.venv/bin/python -m pytest libs/homeiq-ha -q` showing **≥99 passed, 0 failed, 0 errors**,
   and `bash scripts/verify-dashboard-contract.sh` exiting 0 at **36/36, 0 deviations**
   (guards against regressing the closed epic).
3. For every phase 2–6: **either** a live `snapshot → apply → verify → diff → restore` transcript
   ending in **post-restore diff = 0 differences** with an independent re-read confirming the
   exact baseline, **or** a one-line recorded reason it is deferred/blocked, with the Linear id
   that now tracks it. No phase may be silently skipped.
4. `python -m homeiq_ha.agent audit` against live HA: a status for every registered recipe
   (13 at authoring; the set grows — 20 as of 2026-08-13; count `default_recipes()`, don't
   pin to a number) plus the assertion line proving **zero write calls** were issued.
5. Linear query result showing **TAP-5405 and every child Done or Cancelled**, one-line reason
   per Cancelled, and every follow-up story created. **Every id in the output verified by
   `get_issue` before it is cited.**

> **A stale-image or stale-branch run does not count.** Artifacts must be produced against the
> current working tree.

## Sub-goals (sequential; each a checkpoint)

**0. Establish preconditions (self-healing — the loop does this, not the user).**
   - `mcp__nlt-build__tapps_session_start()` **first** — a PreToolUse gate blocks all other
     `tapps_*` MCP tools until this runs. Re-run after any `/clear` or compact.
   - Brain recall: `uv run tapps-mcp memory search --query "ha-init-agent backup phase1 snapshot restore"`
     — fold in prior attempts and failures before acting.
   - Test runner: **`/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`**. System `python3`
     has **no pytest** — using it produces a false "no module" failure.
   - **Verify inherited issue ids.** Before acting on any TAP-#### from a handoff, prompt, or
     memory entry, confirm it with `get_issue(id=...)`. TAP-5428 was carried as the session P0
     and does not exist.
   - Stack health: `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c healthy`
     should be 58. If not, `bash scripts/domain.sh start <domain>` for the gap.
   - **Host-port overrides are in effect** (this box runs other stacks): dashboard **13000**,
     admin-api **18004**, websocket **18001**, postgres **15432**, retention **18080**,
     carbon **18010**, OTLP **14317/14318**, jaeger UI **16687**, ai-automation-ui **13001**.
     Never assume the documented defaults.
   - **Deploy freshness (merged ≠ live).** Several compose services declare `build:` with no
     `image:`, so `docker buildx bake` output is **not** what compose runs. After any source change:
     `docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d --build <service>`.
     `docker buildx bake` requires **`-f docker-bake.hcl`**.
   - **Harness compatibility** (bake these in, do not fight them):
     - `save_issue` is PreToolUse-gated on a `docs_validate_linear_issue` sentinel **< 30 min old**.
       Route Linear writes through the **`linear-issue` skill**; re-validate if the loop has run
       > 30 min since the last validation.
     - `list_issues` is PreToolUse-gated on a prior `tapps_linear_snapshot_get`. Route multi-issue
       reads through **`linear-read`**; single issues use `get_issue(id=...)` directly.
       Note: `state="open"` is a tapps-mcp cache bucket — pass it to `snapshot_get`/`snapshot_put`,
       **never** to the plugin's `list_issues`.
     - `PostToolUse` on Edit/Write nudges a per-edit quality check — **adopted for `src/` Python
       edits** (`tapps_quick_check`, ~200 ms), **overridden to story-gate batching** for test files
       and markdown. State this once; do not re-litigate per edit.
   - proof: session_start returned; 58 healthy pasted; pytest runs; TAP-5428's non-existence
     re-confirmed or the correct id identified.

**1. Commit the phase-1 fix set.** 8 modified + 2 new files; validation was green last session
   but is **not** carried forward as proof — re-run it. Conventional-commit message naming the
   five defects (missing `agent_ids`; verify-before-job-lands; capture-mid-job; schedule never set
   destination; capture didn't track `create_backup.agent_ids`).
   - `.venv/bin/python -m pytest libs/homeiq-ha -q` → 0 failed
   - `tapps_validate_changed(file_paths="<explicit comma list>")` → green
   - `git status --short` before staging; nothing outside the 10 known files
   — proof: the commit hash, the pytest summary, and a clean `git status --short`.

**2. Exercise phases 2–6 live, under the snapshot guard.**
   The engine gained `snapshot`/`diff`/`restore` (`4f1a0fca`) precisely so a live phase is
   re-testable without leaving residue. Per phase, in order:
   `capture snapshot → apply --phase N → verify (independent re-read) → diff → restore → diff again`.
   The cycle is only a pass when the **post-restore diff is 0** and an independent read confirms
   the exact baseline. A phase that cannot run (missing prerequisite, human gate) is **recorded
   as blocked with a reason and a Linear id** — not skipped.
   - **Authorization line (edit this before the run):** phase 1 was explicitly cleared and executed.
     **Phases 2–6 are NOT cleared.** The loop must batch a single authorization ask covering the
     phases it intends to apply, with the diff it would make, and **may proceed on the read-only
     `check`/`plan` for all of them without asking**. Replace this paragraph with an explicit
     "phases N–M are authorized" line to skip the ask.
   — proof: per phase, the transcript above, or the blocked reason + issue id.

**3. Backup encryption key — the real human gate.** `BackupScheduleRecipe` stays
   `BLOCKED_ON_HUMAN`: the key cannot be set via any API. Batch this into the sub-goal 2
   authorization ask with the exact UI path the human must take. **A backup without the key is
   unrecoverable** — do not mark phase 1 complete while this is open; mark it *blocked, correctly*.
   Note `backup/config/info` returns the key in plaintext — never log it.
   — proof: the recipe's status line reading `BLOCKED_ON_HUMAN` with the actionable instruction.

**4. TAP-5424 — the client is wired into nothing.** `HAWebSocketClient` shipped and is proven live
   (164 entities, 19 devices), but all 12 REST-registry call sites still hit
   `GET /api/config/*_registry`, which does not exist and 404s. `devices_endpoints.py` masks it
   behind a DB fallback, so a registry outage renders as stale data.
   Decide, and record the decision: migrate now inside this loop, or explicitly defer with a
   priority. Do **not** close TAP-5405 while silently pretending the platform bug is fixed.
   — proof: either `grep -rn 'api/config/entity_registry\|api/config/device_registry\|api/config/area_registry' domains/`
     returning no application call sites plus per-service tests, or TAP-5424 re-prioritized with a
     written rationale linked from the epic.

**5. TAP-5409 / TAP-5411 residuals.** Genuinely unimplemented, not blocked: `recorder:` / `http:`
   YAML tuning (needs a file-access add-on first), Powercalc, Local Calendar, automation-editor
   enablement, power-sensor template aliases. For each: implement, or **Cancel with a one-line
   reason**, or split into a new story. TeamTrackerRecipe must **assert** the resulting entity_id
   contains `team_tracker` rather than trusting the integration's documented default.
   — proof: pytest 0 failures across the recipe suite; each residual mapped to done/cancelled/new-story.

**6. Dashboard residual.** TAP-5413 is closed at 36/36, but **11 path families remain
   under-covered** by the contract script. That is a real coverage gap in a gate that now runs in
   CI. Enumerate them, then either extend `scripts/verify-dashboard-contract.sh` or file one story
   with the list. Re-run the script either way — the closed epic must not regress.
   — proof: contract script exits 0 at 36/36 (or higher), plus the story id or the extended row set.

**7. Close out.** Run the full Done-when set. Via the **`linear-issue` skill**: close what is done,
   **cancel with a one-line reason** what proved unnecessary, **create** stories for everything
   discovered. Update the TAP-5405 body's "Implementation status" block to match reality.
   Record learnings to the brain, including the TAP-5428 phantom-id failure.
   — proof: the five Done-when artifacts, pasted together in one message.

## Plane map (mechanism + model tier per chunk)

| Step | Plane | Mechanism | Model tier | Notes |
|---|---|---|---|---|
| Re-confirm inherited facts (issue ids, phase status) | coordination | 1 subagent | cheap / low effort | read-only; the handoff has already been wrong once |
| Live phase cycles (sub-goal 2) | execution | **in-session, sequential** | frontier | mutates a real home; never fan out, never parallel |
| Registry-caller migration (TAP-5424, 12 sites) | execution | **in-session, sequential** | cheap for mechanical sites; frontier for `devices_endpoints.py` fallback removal | coupled to each service's tests |
| Per-story verification | coordination | **verifier subagent, fresh context** | **frontier / high effort** | re-runs the check; refutes the claim |
| Final epic verification | coordination | **3 verifier subagents, perspective-diverse** | **frontier / high effort** | correctness · security (no key logged, no HA residue) · reproducibility |
| Linear writes | coordination | **`linear-issue` skill** | cheap | hook-gated; skill handles the sentinel |
| Linear multi-reads | coordination | **`linear-read` skill** | cheap | hook-gated; cache-first |

## Loop

- **State:** read the two epics via `linear-read`; `git log --oneline -5`; `git status --short`;
  contract script score; brain recall of prior failures.
- **Decide:** lowest-numbered sub-goal not yet verified-done. One at a time.
- **Execute:** on the committed mechanism above. Code edits sequential, in-session. After each
  `src/` Python edit run `tapps_quick_check`; at each story gate run `tapps_validate_changed`
  with explicit `file_paths`.
- **Verify (independent):** spawn a **fresh-context verifier subagent (frontier)** told to
  **refute** the sub-goal's proof — it re-runs the deterministic check itself and defaults to
  "not done" on any doubt. **Its verdict advances the loop, not the executor's claim.**
- **On fail:** diagnose — read the actual error, inspect state, recall prior failures — then
  hypothesis → fix → retry *with something changed*. ≤3 distinct strategies per sub-goal, then
  escalate once, then stop with a concise diagnosis. **Never re-run the same action on the same error.**
- **Record:** `uv run tapps-mcp memory save --key <slug> --tier pattern --value "<outcome incl. what failed and why>"`.
- **Context hygiene:** prune stale reads each iteration; prefer targeted `grep` over a full
  re-`Read`; carry a compact state summary forward, not raw transcripts. Delegate noisy
  multi-file reading to a subagent and keep only its summary.
- **Print every iteration:**
  `SCORE: pytest <fail> failures · contract <pass>/36 · phases live-proven <n>/6 · children closed <n>/9 · iteration <i>/30`
- **Repeat or stop:** until Done-when holds; caps **30 iterations** AND **1.0M output tokens**.

## Guardrails

- **Termination:** the Done-when artifact set; caps 30 iterations AND 1.0M output tokens.
- **Independent verification** — a verifier that did not do the work, against ground truth.
- **🔴 LIVE HOME ASSISTANT — snapshot-guarded, phase-scoped.** `192.168.1.80` is a real home.
  Read-only `audit` / `check` / `plan` is always permitted. **`apply` is permitted only for a phase
  explicitly authorized in sub-goal 2, and only inside the snapshot→apply→verify→diff→restore
  cycle.** An unauthorized phase apply, or an apply without a captured snapshot, is an **Autonomy
  hard-stop**. Never leave the instance mutated at the end of an iteration unless the user asked
  for a persistent change.
- **A recipe reporting `NEEDS_APPLY` is a correct result,** not a failure — the home is genuinely
  unconfigured. `BLOCKED_ON_HUMAN` on the encryption key is likewise correct. Do not let a caps
  check or a verifier score these red.
- **Never cite an unverified issue id.** Every TAP-#### that reaches a commit message, a Linear
  body, or a Done-when artifact must have been confirmed by `get_issue`. This is the TAP-5428 lesson.
- **No fan-out of coupled work** — live phase cycles and the registry migration are sequential
  in-session. Fan-out is for research and verification only.
- **Scope:** `/home/wtthornton/code/HomeIQ` only. Linear team `TappsCodingAgents`, project `HomeIQ`,
  agent assignee `Claude Agent` (`9083b7a1-3fd3-479b-98f1-1f8a782ae10a`). Cross-project writes are
  forbidden (`agent-scope.md`).
- **Memory:** recall at start, record at every checkpoint including failures.
- **Discipline:** root-cause not workarounds; **no green-by-suppression** — never skip, disable, or
  weaken a test or checker to go green; right-sized; durable over expedient; match repo conventions;
  no silent scope creep. If the correct fix is out of scope, stop and say so.
- **Secrets:** `.env` is gitignored and stays that way. Never commit a key. `backup/config/info`
  returns the HA backup encryption key in plaintext — never log it, never paste it into Linear.

## Autonomy

- Act on every reversible, in-scope step. No "should I proceed?" checkpoints.
- Irreversible/outward → produce the reversible precursor (branch + draft PR, staged diff) and keep
  going; the human reviews async. **A draft PR is not a stop.**
- **Hard-stop once (batched, with a recommendation) only for:** an `apply` to a live-HA phase not
  yet authorized · the encryption-key gate · merge to `master` · force-push · deleting
  un-recreatable data · a genuinely ambiguous decision where a wrong guess is expensive.
  Batch sub-goal 2's authorization and sub-goal 3's key gate into **one** ask.

## Failure handling

Diagnose, don't repeat. Read the real error → inspect state → recall prior failures → form a
specific hypothesis → change something → retry. ≤3 distinct strategies per sub-goal, then one
escalation, then stop with a concise diagnosis naming what you tried and why each failed.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` · Linear `TappsCodingAgents` / `HomeIQ` · assignee `Claude Agent`
- Epic: **TAP-5405** — children 5406 ✅, 5407 ✅, 5408 ⏳, 5409 ⏳, 5410 ⏳, 5411 ⏳, 5412 ✅, 5424 📋
- Closed: **TAP-5413** and 5414–5418 — carry only the 11-path-family coverage residual
- Design + evidence: `docs/ha-init-agent-design.md` · `docs/operations/dashboard-triage-2026-08-01.md`
- Engine: `libs/homeiq-ha/src/homeiq_ha/agent/` — `recipes.py`, `snapshot.py`, `backup.py`, `readonly.py`
- Live HA: `http://192.168.1.80:8123`, HA 2026.7.4, Supervised on Pi, HAOS 18.2
- Test fixture models the real async contract — `backup/generate` returns a job handle, lands over
  2+ polls via `_advance_backup()`. A test that passes here works on real HA.
- Prior learnings: `uv run tapps-mcp memory search --query "homeiq ha setup agent backup snapshot"`

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in a new session.
- **Fan-out sub-step:** `.claude/workflows/phantom-endpoint-map.js` is **retired** — TAP-5417 closed.
  Everything remaining is coupled and sequential; N=1.
