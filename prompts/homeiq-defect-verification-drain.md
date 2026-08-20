# HomeIQ defect + verification drain — close what master already fixed, then burn the anchored defect stories

> Generated 2026-08-19 by the `orchestration-prompt` skill, against a live Linear
> read (61 open issues; snapshot cached under
> `TappsCodingAgents__HomeIQ__open`). **Complement, not successor, to
> `prompts/homeiq-backlog-drain.md`** — that prompt remains the SoT for the epic
> waves (TAP-5283 data-plane collapse, TAP-5284 HA front door, TAP-5286 safety
> gate, DNA epics). This prompt drains the *anchored defect stories and
> verification closures* that landed in Linear after the drain prompt's
> 2026-08-17 sync and are invisible to it.
>
> Commits `c9c225ec` and `8182ecbd` (2026-08-19, master) already implemented
> several open issues' fixes. Sub-goal 1 verifies and closes those first —
> cheapest wins, and it stops the next session from re-implementing landed work.
>
> **This is a multi-run loop.** One session finishes a sub-goal or two. Re-enter
> until Done-when holds. Every sub-goal is a resumable checkpoint recorded to
> brain under `defect-drain:*`.

## Prerequisites / Wayfind gate

- **Route clear? Yes, for everything in scope.** Every in-scope issue carries a
  `file.py:LINE` anchor and a stated defect — execute/verify/fix chunks only.
  Anchors are **hints**: modules get split, so re-locate symbols by grep before
  trusting line ranges.
- **Out of scope — do NOT attempt (a loop told only what to do wanders into
  gated work):**
  - Epic waves owned by `prompts/homeiq-backlog-drain.md`: TAP-5283 + children
    (5299, 5301, 5304, 6102), TAP-5284 + children (5305–5310), TAP-5286 +
    children (5321, 5322, 5323), TAP-6103.
  - Architecture/decide-shaped DNA epics: TAP-6251, TAP-6252, TAP-6253,
    TAP-6255 (SG1 may *update* 6255 with evidence of what 2026-08-19 delivered,
    but closing it is a human call — its scope is an epic, not a story).
  - Physical-hardware issues (Autonomy hard-stop class — pairing buttons,
    sensor placement): TAP-5977, TAP-5978, TAP-5979, TAP-5980, TAP-6018.
- **Resume recall (cold start):**
  `tapps_memory(action="search", query="defect-drain checkpoint")` — the
  `uv run tapps-mcp memory search` CLI is **broken** in this project
  (`MemoryStore requires a Postgres private_backend`); always use the MCP tool.

## How to run (cold start — paste into a NEW session)

- **Goal loop (recommended):**
  `Read prompts/homeiq-defect-verification-drain.md in full, run its Prerequisites (incl. brain resume recall), then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.`
- **Durable:** save that same line as a Routine (one sub-goal per run).
- Linear must be authenticated — Sub-goal 0 probes it and hard-stops once if
  absent (OAuth is user-only, not self-healing).

## Objective

Every anchored defect story filed against HomeIQ in the 2026-08 triage waves is
either closed with independent-verifier evidence or explicitly re-dispositioned
— starting with the issues master already fixed, then the In Review batch, the
TAP-6169 test-debt children, the TAP-6230 naming children, and the two
AgentForge-integration defects.

## Done-when (ground truth, not narration)

`tapps_linear_snapshot_get(team="TappsCodingAgents", project="HomeIQ", state="open")`
(refreshed after the final write) pastes a result in which **zero** issues from
the in-scope list below remain open, **AND** each closure comment in Linear
carries the verifier's deterministic evidence (test-count line, grep/SQL output,
or HTTP transcript), **AND** the final session pastes a
`tapps_validate_changed` summary over its changed files plus a `pytest` summary
line with 0 failures for every touched service.

In-scope list (34 issues):
- **SG1 verify-and-close:** TAP-6233, TAP-6249, TAP-6228, TAP-6232 (+ evidence
  update, not close, on TAP-6255)
- **SG2 In Review batch:** TAP-6151, TAP-6152, TAP-6153, TAP-6154, TAP-6155, TAP-6156
- **SG3 test-debt children of TAP-6169:** TAP-6170, TAP-6171, TAP-6174,
  TAP-6175, TAP-6177, TAP-6178, TAP-6180, TAP-6181, TAP-6183, TAP-6184,
  TAP-6185 (then TAP-6169 itself)
- **SG4 naming children of TAP-6230:** TAP-6227, TAP-6231, TAP-6234, TAP-6235
  (then TAP-6230 itself, if all children including SG1's are closed)
- **SG5 AgentForge pair:** TAP-6167 (with TAP-6152 if not already closed in SG2)
- **SG6 singles:** TAP-6107, TAP-6236, TAP-6242, TAP-6066, TAP-6202, TAP-6168,
  TAP-6229

A **correct negative counts**: an issue whose premise a verifier refutes with
evidence (the defect no longer reproduces, or the ticket's claim was wrong) is
*closed as verified-invalid with the refutation pasted* — that is success, not
a miss. Do not implement a fix for a defect you could not first reproduce.

## Validation contract (before execution)

Closure classes — every issue must satisfy its class before `save_issue` moves
it to Done:

| ID | Behavioral assertion | Fulfilled by | Evidence tool |
|----|----------------------|--------------|---------------|
| VAL-REPRO | Before any fix: the defect is reproduced (failing test, failing curl, or SQL/grep showing the bad state) — or refuted, closing the issue as invalid with evidence | every SG | pytest / curl / psql (`docker exec -i`!) / grep |
| VAL-FIX | After the fix: the same reproduction now passes, pasted verbatim | every SG | same tool as VAL-REPRO |
| VAL-SUITE | The touched service's test suite passes: pytest summary line with 0 failures | every SG | pytest (run from the service dir — root pytest collects nothing from `scripts/tests/`) |
| VAL-GATE | `tapps_quick_check` on each edited file; `tapps_validate_changed(file_paths=...)` before the sub-goal closes. Legacy files scoring <70 pre-diff are not regressions (see brain memory `quality-gate-legacy-files-below-70`) — paste the before/after score instead of refactoring the whole file | every SG | nlt-build tools |
| VAL-CLOSE | The Linear closure comment contains VAL-REPRO + VAL-FIX evidence and names the commit SHA | every SG | linear-issue skill |
| VAL-NAME | No fix introduces a friendly-name-as-identity path: "would a rename break this?" answered NO for every new comparison (`.claude/rules/friendly-names.md` is a standing rule) | SG1, SG4 | verifier review + grep `area.*in .*name`, `infer.*area` |

Per-ticket behavioral assertions are written **at the top of each ticket's
execution**, from the ticket's `## Acceptance` checkboxes, before any code is
read — the Missions ordering at ticket granularity.

## Sub-goals (sequential; each a checkpoint)

0. **Establish preconditions (self-healing).**
   - `tapps_session_start()` first — all `tapps_*`/nlt* tools run degraded
     without it.
   - **Linear auth probe:** ToolSearch for `mcp__plugin_linear_linear__get_issue`
     and call it on TAP-6229 (cheapest issue). If the plugin is absent or
     unauthenticated → hard-stop once and ask the user to run `/mcp`; OAuth
     cannot be self-healed.
   - **Git state:** on `master`, clean tree,
     `git merge-base --is-ancestor HEAD origin/master || git pull --ff-only`.
     New work branches off master; one branch per sub-goal.
   - **Brain resume:** `tapps_memory(action="search", query="defect-drain checkpoint")`
     — skip any issue a checkpoint already records as closed-with-evidence.
   - **AgentForge health (needed by SG5, cheap to do now):**
     `mcp__agentforge__health()` then `mcp__agentforge__list_agents(project_slug="homeiq")`.
     If `missing-bearer`: the agentforge MCP server caches `.env` at startup —
     restart the MCP server before diagnosing the key; `scripts/af.sh` working
     while the MCP tool 401s is the signature of the cached-env trap. If AF is
     genuinely down, run the `af-troubleshoot` skill; SG5 blocks, SG1–SG4/6 do not.
   - **Harness gates this loop will hit** (bake the unlock, don't fight it):
     Linear *reads* go through the `linear-read` skill (snapshot_get before
     list_issues — per-key sentinel, no exemptions); Linear *writes* go through
     the `linear-issue` skill (docs_validate sentinel <30 min before
     save_issue); single-issue lookups are `get_issue(id)` directly. After any
     write: `tapps_linear_snapshot_invalidate(team, project)`.
   - proof: session_start payload, get_issue(TAP-6229) title, `git status`
     clean, AF health JSON — pasted.

1. **Verify-and-close what master already fixed** — fulfills VAL-REPRO(refute
   path)..VAL-CLOSE per issue.
   - TAP-6233 (`sync_name_to_ha` reported success without writing): commit
     `c9c225ec` reordered accept-name to HA-first with 502 refusal
     (`name_enhancement_router.py`). Verify: grep the current ordering, then
     behavioral — POST an accept against the live service with HA unreachable
     must 502 and change nothing (or pytest-level equivalent).
   - TAP-6249 (`device_entities` keyed on mutable entity_id): `c9c225ec` added
     `ux_device_entities_registry_key (domain, platform, unique_id)` + upsert
     on that tuple + `ON UPDATE CASCADE` FKs. Verify against the **live**
     Postgres (port **15432** — 5432 is another project):
     `docker exec -i <pg> psql ... "\d device_entities"` and a
     `GROUP BY domain` distribution check (a NOT NULL column can still be 100%
     `'unknown'` — check the distribution, not the constraint).
   - TAP-6228 (name-match area fix can overwrite a human assignment):
     `c9c225ec` capped name-derived confidence at 49 < the 80 action threshold,
     `basis="name_only"`, `actionable=False`, and validation now reports
     `name_area_mismatch` instead of asserting. Verify the cap-vs-threshold
     test exists and passes
     (`test_no_name_match_can_ever_reach_a_system_action_threshold`); confirm
     no remaining write path consumes name-derived confidence ≥80.
   - TAP-6232 (route all name/area writes through one gateway): brain memory
     `homeiq-ha-registry-write-gateway` + commits through `90c95b5d`. Verify by
     grep: every `config/entity_registry/update` / area-write call site routes
     via HARegistryWriter; list any stragglers — if found, this becomes a fix
     ticket, not a close.
   - TAP-6255 (p1 genome epic): do NOT close. Post an evidence comment listing
     what `c9c225ec` delivered (packs layer rendered from measured intake,
     drift gate fails loudly on empty templates, measured home atlas) against
     its acceptance boxes, and leave the rest to the human/epic owner.
   - proof: per-issue evidence pasted into Linear via `linear-issue` skill;
     snapshot invalidated.

2. **Disposition the In Review batch** (TAP-6151, 6152, 6153, 6154, 6155,
   6156). For each: `get_issue` → find the PR/branch it references → is the fix
   merged? If merged: verify per VAL-FIX/VAL-SUITE and close. If the PR is
   stale/unmerged: rebase-or-rewrite as a fresh branch off master, land it
   (draft PR = reversible precursor; merging to master is allowed here as
   routine in-scope work), verify, close. Re-verify PR/branch state **live** —
   handoffs about PR state rot within hours.

3. **Burn the TAP-6169 test-debt children** (11 stories, mechanical, each
   anchored): 6170 (naive DateTime vs asyncpg), 6171 (FK-ordered teardown),
   6174 (INFLUXDB_TOKEN in CI), 6175 (Database import name), 6177
   (version vs engine_version key), 6178 (503 vs 200 health assertion), 6180
   (settings singleton env patch), 6181 (isinstance vs MagicMock), 6183
   (weather-api health payload), 6184 (devices 404 vs 200), 6185 (air-quality
   config guards). Rules: fix the **root cause** on whichever side is wrong
   (the ticket names which — verify its premise first; three load-bearing
   premises were false in the last generated prompt); no skips, no xfail-to-
   green, no assertion deletion to pass. One service at a time, serial. Close
   TAP-6169 when all children are done and its own Done-when (the format-gate
   suite list) is pasted green.

4. **Burn the remaining TAP-6230 naming children:** TAP-6231 (five duplicate
   naming-rule implementations → consolidate to the one server-side rubric —
   brain memory `naming-rubric-single-source`: regenerate golden vectors after
   any rubric change or CI goes red), TAP-6234 (generated names penalized by
   the rubric that scores them), TAP-6235 (AUTO_GENERATE_NAME_SUGGESTIONS
   defaults off — decide-trap: turning a generation pipeline ON for a live home
   is an outward change; implement + test behind the flag, flip the default
   only with the evidence that generated suggestions pass the rubric, else
   surface as a one-line recommendation), TAP-6227 (unassignable devices
   counted as gaps). VAL-NAME applies to every diff. Then close TAP-6230 iff
   every child (incl. SG1's) is closed.

5. **AgentForge integration pair** — TAP-6167 (+ TAP-6152 if SG2 left it open):
   `hiq-assistant.md` has no `timeout_seconds`, so every invoke steers async
   and turns take 13–33 s. **Premise check first** (brain memory
   `agentforge-latency-is-the-agent-run`): the 14–27 s is the *gene run
   itself*, not the async steering — the POST returns in 45 ms. So the fix is
   (a) set `timeout_seconds` and completion criteria correctly per the
   `af-goal` skill, (b) author the agent frontmatter per `af-author-agent`
   (note: `homeiq-ha-automation-tester` previously failed the kit validator on
   two missing frontmatter fields — validate before publish), (c) publish per
   `af-publish` (agents before workflows or 422), (d) prove the end-to-end
   with `af-smoke-test` + `mcp__agentforge__invoke_task` and paste the
   latency + sync/async mode from `mcp__agentforge__get_workflow_run`. AF
   workflow traps if any YAML is touched: `kind: task` not `kind: agent`;
   `$input` refs (a literal `{{input}}` passes through untouched); terminal
   state is `complete` not `success`; `output_schema` on the workflow node.
   Consult the platform `expert-*` agents (free to invoke) for review; a
   degenerate `{"advice":"test"}` response gets one retry with an explicit
   anti-placeholder instruction, then fall back to codebase conventions. Judge
   findings are re-checked deterministically against the artifact before any
   amendment — reject-with-evidence is a first-class disposition.

6. **Singles sweep** (dependency-free, cheapest first): TAP-6229 (docs, p4),
   TAP-6236 (config gate passes on automation-disabling config — write the
   failing config fixture first), TAP-6242 (models lost on redeploy — volume
   mount or persist path; verify with a `--force-recreate` restart, and note
   `docker compose up -d` without a config delta does NOT recreate), TAP-6107
   (context_parent_id never written — verify against InfluxDB
   `home_assistant_events` bucket; the per-type buckets are declared but
   empty), TAP-6066 (undeclared imports audit — emit the diff of pyproject
   changes), TAP-6202 + TAP-6168 (CI workflow additions — budget a local
   dry-run first; "new CI green on the first try" is a smell, and the fix for
   what it finds belongs in the same branch).

## Plane map (literal dispatch per chunk)

| Step | Plane | Mechanism | agentType | model | effort | Notes |
|------|-------|-----------|-----------|-------|--------|-------|
| SG0 probes | coordination | inline (this session) | — | session | — | cheap, sequential |
| Per-ticket premise check / repro hunt | coordination | subagent | `Explore` | `sonnet` | — | read-only enforced by agent type; returns file:line + repro command |
| Bulk cross-service greps (gateway stragglers, name-rule impls, undeclared imports) | coordination | 3–5 parallel subagents | `Explore` | `haiku` | — | closed questions only ("does file X contain pattern Y") — return the match table, orchestrator draws conclusions |
| Code fixes (SG2–SG6) | execution | serial edits, one service branch at a time, this session | `general-purpose` (inline) | session | — | **never fan out coupled edits** |
| Verify each closure | coordination | **fresh-context verifier subagent** | `general-purpose` | `opus` | — (Agent tool has no effort param) | prompt it to **refute** the closure — re-run the repro, re-run the suite; name the specific weakness to attack (e.g. "prove the 502 path changes nothing locally") |
| AF expert consult (SG5) | coordination | `mcp__agentforge__invoke_task` on `expert-*` | — | — | — | free to author; advice recorded, rejections noted |
| Post-fix Linear close | execution | `linear-issue` skill | — | session | — | validator sentinel then save_issue; assignee = agent user, never the OAuth human |

Cheap-model rule: `haiku` answers closed, evidence-checkable questions only. No
cheap-model verdict gates a close — the orchestrator re-derives every verdict
from the evidence table the subagent returns.

## Loop

- **State:** brain recall (`defect-drain checkpoint`), refresh the Linear open
  snapshot via `linear-read` flow, `git status`, read the current sub-goal's
  next open issue with `get_issue(id)`.
- **Decide:** next open in-scope issue in sub-goal order; within a sub-goal,
  cheapest/least-coupled first. If an issue turns out decide-shaped (a real
  product tradeoff, e.g. the TAP-6235 default flip) → implement up to the
  decision line, record the recommendation, move on — batch the ask.
- **Execute:** per-ticket: write the VAL assertions from `## Acceptance` →
  reproduce (VAL-REPRO) → fix root cause → VAL-FIX/VAL-SUITE/VAL-GATE.
  Required lookups before touching an external surface (Context7-backed,
  cache-first, free to repeat): `tapps_lookup_docs` for pytest/sqlalchemy/
  asyncpg/fastapi as touched; HA automation YAML uses plural
  `triggers:/conditions:/actions:` (2024.10+); AF YAML per SG5 traps.
- **Verify (independent):** fresh `opus` verifier refutes the proof (see plane
  map). Its verdict — not the executor's claim — closes the ticket.
- **On fail:** structured handoff → narrow fix sub-goal → re-execute →
  re-verify. ≤**3** validation rounds per ticket, then escalate once (different
  approach), then leave the ticket open with a pasted diagnosis and move on.
- **Record:** `tapps_memory(action="save", key="defect-drain:<TAP-id>", ...)`
  with: closed?, commit SHA, evidence type, failure-and-why if any. At session
  end: `tapps_handoff_save` + commit; `tapps_checklist(task_type="feature")`.
- **Context hygiene:** prune stale reads; targeted grep over re-Read; carry a
  compact per-ticket state line, not transcripts. Print each iteration:
  `SCORE: closed=<n>/34 open=<ids…> round=<k>`.
- **Repeat or stop:** until Done-when; caps: **40 loop iterations** AND
  **1.5M tokens per session** (checkpoint to brain and end the session cleanly
  near either cap — a >600k-token goal loop becomes disproportionately
  vulnerable to overload kills; fresh sessions resume cheaply from brain).

## Guardrails

- Termination: Done-when above; caps 40 iterations / 1.5M tokens per session,
  multi-session by design.
- Caps must not fire on correct behavior: a verified refutation (defect does
  not reproduce, premise false) **closes** the ticket as invalid-with-evidence
  — it is not a failed round. Correct removals (dead code, wrong assertion on
  the *test* side when the ticket says so) score green.
- Independent verification on every close; creator ≠ verifier; verifier told
  *what specifically to attack*, and invited to attack the FIX's coverage, not
  just the fixed instances.
- Every subagent dispatch names agentType + model (as the plane map does);
  read-only work runs `Explore` so the tool boundary enforces it; check
  `git status` after any `general-purpose` fan-out.
- Serial writes: one service branch at a time; parallel reads OK.
- Research grant: web, `tapps_research`, `tapps_lookup_docs` (never "conserve"
  lookups — they are cache-first and free to repeat).
- Harness compatibility (adopted): `tapps_session_start` first;
  `tapps_quick_check` per edited Python file; `tapps_validate_changed` with
  explicit `file_paths` per sub-goal (quick mode); `linear-read` /
  `linear-issue` skills for all Linear traffic; snapshot invalidate after
  writes. Override adopted from brain: legacy files below the 70 gate are
  reported, not whole-file-refactored.
- **Friendly names are never identity** (`.claude/rules/friendly-names.md`):
  every diff answers "would a rename break this?" — the dangerous violation is
  the name match one hop removed wearing a better label. Verify devices by
  ieee/registry tuple/LED probe, never by name.
- Postgres is on **15432**; `docker exec` piping SQL needs `-i` and end-state
  verification, not exit-code trust; data-api tests never touch Postgres (fully
  mocked), so schema-state bugs need the live DB.
- Discipline: root cause, no green-by-suppression (no skip/xfail/noqa/
  eslint-disable to pass), right-sized, match conventions, no scope creep.

## Autonomy

- Act on every reversible in-scope step; no "should I proceed?" checkpoints.
  The original request is standing authorization for the
  generator→validator→save_issue chain; assignee defaults to the agent user.
- Hard-stop once, batched with a recommendation, only for: the TAP-6235
  default-flip (outward behavior change on a live home), any destructive op,
  physical-hardware steps (out of scope anyway), Linear OAuth absent, contract
  itself wrong, or projected next-step cost above the budget cap.
- Irreversible/outward → produce the reversible precursor (branch + draft PR,
  flag-off implementation) and continue.

## Failure handling

- Diagnose, don't repeat: read the actual error, inspect state, recall
  `defect-drain:*` failures, hypothesize, change something, retry. ≤3 distinct
  strategies per ticket → escalate once → leave open with diagnosis.
- Expected-fail is the design: first verifier refusal on a non-trivial fix is
  normal — scope the narrow fix, never weaken a VAL to go green.

## Context

- Repo: `/home/wtthornton/code/HomeIQ` (single repo; services under
  `domains/`, shared libs under `libs/`, scripts under `scripts/`).
- Linear: team `TappsCodingAgents`, project `HomeIQ`. Cache key
  `TappsCodingAgents__HomeIQ__open`.
- MCP servers in play: `nlt-build` (session_start, lookup_docs, quick_check,
  validate_changed, checklist, impact_analysis/call_graph for refactors),
  `nlt-memory` (tapps_memory, tapps_handoff_save), `nlt-linear-issues`
  (snapshot_get/put/invalidate, docs_generate/validate via skills),
  `nlt-setup` (tapps_doctor if the environment misbehaves), `agentforge`
  (health, list_agents, invoke_task, get_workflow_run, run_workflow).
- Skills in play: `linear-read`, `linear-issue`, `tapps-finish-task`,
  `af-goal`, `af-author-agent`, `af-publish`, `af-smoke-test`,
  `af-troubleshoot` (and `af-workflow` if workflow YAML is touched).
- Prior learnings: brain queries `defect-drain`, `burndown wave checkpoint`,
  memory files `quality-gate-legacy-files-below-70`,
  `homeiq-ha-registry-write-gateway`, `naming-rubric-single-source`,
  `agentforge-latency-is-the-agent-run`, `inovelli-non-neutral-and-hue-circuits`.

## Run-as

- **Cold-start loop (recommended):** the paste line from "How to run" above, in
  a fresh session.
- `/goal "Zero of the 34 in-scope issues in prompts/homeiq-defect-verification-drain.md remain open in the refreshed Linear snapshot, every closure carrying pasted verifier evidence"`
  — only if this file is already in context.
- Routine: nightly, one sub-goal per run, push = draft PR.
