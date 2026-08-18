# AgentForge integration — decision record

**Date:** 2026-07-30
**Status:** Accepted
**Scope:** How HomeIQ consumes AgentForge as an external agent runtime.

HomeIQ is an **AgentForge consumer**. AgentForge is an enterprise agent OS
(one Docker image, config-driven `AF_MODE`) — it is not a place to put HomeIQ
business logic. Canonical platform guide:
[CONNECTING_PROJECTS.md](https://github.com/wtthornton/AgentForge/blob/main/docs/CONNECTING_PROJECTS.md);
kit architecture: ADR-020.

---

## Decisions

| Axis | Decision |
|------|----------|
| **Wiring** | **Pattern A** — HTTP publish (`PUT /projects/homeiq/...`). Patterns B/C/D are not used. |
| **Product archetype** | **Pipeline + gateway** — AF runs multi-stage dev-loop cognition; HomeIQ owns build/deploy/DB side effects. |
| **Project slug** | `homeiq` |
| **Layout** | `scout` — `agentforge/projects/homeiq/{agents,workflows}/` |
| **API port** | **8010** (`agentforge-api`), pinned. Never `:8001` (`agentforge-main`, the dashboard). |
| **Auth** | Project bearer `afp_*` in gitignored `.env`, loaded via `AGENTFORGE_LOAD_DOTENV=1`. |
| **MCP profile** | `runtime` (5 tools). Publish runs through the CLI, not MCP. |

### Why `scout` layout and not `nlt`

`--layout nlt` puts agents and workflows at repo top level. HomeIQ already has a
top-level [`workflows/`](../workflows/) directory holding five legacy YAML files in a
**non-AgentForge schema** — `workflow: {id, steps: [{agent, action, context_tier,
creates, next}]}`, referencing agents `analyst` / `planner` / `reviewer` that do
not exist in this project. AgentForge's schema is `name` / `inputs` / `nodes` /
`output_schema`. The `nlt` layout would collide with that directory.

Those legacy files are **out of scope and left untouched**. They are not
AgentForge specs and are not migratable as-is.

---

## Publish

Agents are flat `.md` files under `agentforge/projects/homeiq/agents/`; workflows
are `.yaml` under `agentforge/projects/homeiq/workflows/`.

```bash
export AGENTFORGE_REPO=/home/wtthornton/code/AgentForge
export AGENTFORGE_URL=http://localhost:8010

python "$AGENTFORGE_REPO/clients/agentforge-integration-kit/scripts/af_publish.py" \
  --slug homeiq --layout scout --repo-root .
```

**Publish order is load-bearing:** agents before workflows. Workflows validate
`agent:` references at load time and return **422** if a referenced agent is not
yet published. The CLI enforces this and exits non-zero on violation.

**Activate semantics:** first publish returns HTTP **201** and auto-activates.
Republish with an unchanged content hash returns **200** and does *not* activate —
pass `--activate` to force.

Pre-publish content gate (no LLM cost):

```bash
# CI — refuse when safe residuals remain
python .../af_publish.py --slug homeiq --layout scout --check-only

# Local — write safe fixes into Git, review, commit, then publish
python .../af_publish.py --slug homeiq --layout scout --autofix-safe
```

## Setup (per developer machine)

The kit's `af-*` skills and `af-integration.mdc` are **absolute symlinks** into a
local AgentForge clone, so they are gitignored rather than committed — a
committed symlink would dangle in every other clone. Each developer runs:

```bash
export AGENTFORGE_REPO=/path/to/AgentForge
bash "$AGENTFORGE_REPO/clients/agentforge-integration-kit/scripts/install_kit.sh" \
  --repo-root . --merge-mcp --af-mcp-only --slug homeiq
bash "$AGENTFORGE_REPO/clients/agentforge-integration-kit/scripts/af_kit_install_verify.sh" \
  --repo-root .
```

`--merge-mcp --af-mcp-only` is required: it merges only the `agentforge` block and
leaves the `nlt-*` tapps servers untouched. Never use `--force-mcp` here.

Then put the project bearer in a gitignored `.env`:

```
AGENTFORGE_URL=http://localhost:8010
AGENTFORGE_PROJECT_SLUG=homeiq
AGENTFORGE_API_KEY=afp_…
```

## What is published

| Artifact | Path | Role |
|---|---|---|
| `homeiq-service-auditor` | `agentforge/projects/homeiq/agents/homeiq-service-auditor.md` | `judge` — reads supplied source, emits findings |
| `homeiq-audit-aggregator` | `agentforge/projects/homeiq/agents/homeiq-audit-aggregator.md` | `aggregator` — findings → ship/block decision |
| `homeiq-service-audit` | `agentforge/projects/homeiq/workflows/homeiq-service-audit.yaml` | 2-node DAG `audit → decide` |
| Collector | `scripts/af_audit_service.py` | Consumer half — collects source, runs the workflow, sets exit code |
| Kit wrapper | `scripts/af.sh` | Pins this repo's key/URL/slug for every kit CLI |

```bash
python scripts/af_audit_service.py domains/core-platform/data-api
python scripts/af_audit_service.py --changed-only origin/master --max-spend 2.00
# exit 0 = all ship, 1 = any block, 2 = an audit could not run
```

Runs cost real money (~$0.03–0.21 per service observed) and there are 53 service
directories under `domains/`. `--max-services` (default 10) and `--max-spend`
(default $5) are therefore on by default, and a capped run prints what it skipped
rather than silently truncating.

### Always use `scripts/af.sh` for kit CLIs

```bash
scripts/af.sh publish --gate-safe
scripts/af.sh validate --tier quick
scripts/af.sh doctor
```

A machine-global `AGENTFORGE_API_KEY` is exported into the systemd user session by
unrelated NLT services (`~/.config/nlt-{builder,worker,intake-dispatcher}.env`),
and its value is a **truncated 7-character string** (`afp_new`). It shadows this
repo's working key and makes every bare kit CLI fail with
`401 key-invalid-or-revoked`. `scripts/af.sh` reads the key from this repo's
`.env` and pins it, so HomeIQ is unaffected. Those NLT files are other projects'
credentials — fixing them is out of scope here, but note that **any AgentForge
call those services make is currently failing auth**.

### Project keys cannot be recovered

AgentForge stores `sha256(salt + raw_key)` (`backend/auth/pg_project_keys.py`);
`ProjectKey` never exposes the hash or salt. A raw `afp_*` key is shown **once**
at issue time. If HomeIQ's key is lost, mint a replacement rather than hunting
for the old one:

```bash
curl -sX POST http://localhost:8010/projects/homeiq/keys \
  -H "Authorization: Bearer $EXISTING" -H 'Content-Type: application/json' \
  -d '{"label": "rotation-2026-qN"}' | jq -r '.raw_key'
```

`GET /projects/homeiq/keys` lists id/label/created/last-used/revoked metadata only.

### AgentForge cannot see this repo

AF runs in its own container with no view of the HomeIQ working tree. An agent
handed a bare directory path will correctly report `blocked`. **Source must be
collected here and passed in as a workflow input** — that is the consumer half of
the pipeline+gateway split, and why `scripts/af_audit_service.py` exists.

Note also that `invoke_task`'s `context` parameter is for Goal overrides only
(TAP-3608). It is **not** a general payload channel: `context.files` never reaches
the agent. Content goes in the prompt or in declared workflow inputs.

### Workflow authoring gotchas (verified against `backend/workflows/models.py`)

| Thing | Correct value | Wrong value that fails silently |
|---|---|---|
| Node kind for an agent | `kind: task` | `kind: agent` (rejected — `extra="forbid"`) |
| Input reference | `$service_path`, `$audit` | `{{service_path}}` — **passes through literally**, agent sees the raw braces |
| Terminal run state | `complete` | `success` (never emitted) |
| Run poll shape | `GET /workflows/runs/{id}` → `run.state` | top-level `state` (only on `/outputs`) |

`spec_version: 2` enables strict refs, but strictness only catches refs that
*start with* `$`. A `{{…}}` placeholder is treated as a literal string and is
never flagged — this cost a full debug cycle. Always confirm a real run resolved
its inputs, not just that the run completed.

### Schema enforcement lives on the workflow node, not the agent

An agent's frontmatter `output_schema` is declared but **not enforced** on a plain
`invoke_task` — the model improvises keys. Enforcement comes from the workflow
node's `output_schema` plus `output_repair_retries` (0–3), which re-invokes with
the validation error fed back. Both nodes here use `output_repair_retries: 2` and
produce exactly-conformant output.

## Verify

```bash
python .../af_kit_validate.py --slug homeiq --base-url http://localhost:8010 --tier quick --json
python .../af_doctor.py --base-url http://localhost:8010 --slug homeiq --repo-root .
```

Auth proof is `health().auth.scoped_probe == "ok"` — **not** `claude mcp list`
Connected and **not** a bare 200 from `/health`.

## Dual source of truth

HomeIQ **Git** is the authoring source of truth for agent definitions. AgentForge's
version store is the **runtime** definition store — what the matcher loads after
publish/activate. Edits applied only inside AgentForge (including AutoFix Apply)
create drift until exported back:

```bash
python .../af_export.py --slug homeiq --name <agent> --layout scout --repo-root .
```

AgentForge never pushes to this repo's Git remote.

## Per-gene budget caps (TAP-5321)

Every one of the 23 genes under `agentforge/projects/homeiq/agents/` declares
`max_budget_usd`. An undeclared cap is not "the platform default" for this fleet —
`resolve_fallback_max_budget_usd` in AgentForge treats `<= 0` as *unlimited*, so a
missing or zero cap is unbounded spend on a runaway loop.

### What the cap actually enforces

`max_budget_usd` is a **per-invocation** ceiling on combined Path A (OAuth) + Path B
(Platform API) spend for one agent node — not a monthly or cumulative allowance.
Enforcement differs by lane (`AgentForge/docs/AGENT_AUTHORING.md`, TAP-5346):

| Lane | Enforcement |
|---|---|
| Host CLI (`AF_AGENT_RUNTIME=legacy`) | Hard ceiling — CLI stops the run, `error_max_budget_usd` |
| SdkRunner (default `AF_AGENT_RUNTIME=sdk`) | Hard ceiling — native SDK budget option, overrun fails the run |
| `invoke_internal` (template dispatch post-check) | **Advisory only** — logs a warning after the fact |

### Sizing rule

`cap = the smallest value on the ladder {0.10, 0.25, 0.50, 0.75, 1.00, 1.50, 2.00, 3.50}`
`that is >= 3x the highest observed single-invocation cost`.

3x, not 1.5x, because the observed sample is small and a cap that merely clears today's
p90 turns any prompt-size growth into a hard refusal. A gene with no invocations yet
inherits the band of the nearest observed peer with the same model and role — that is an
**estimate**, flagged as such in the table below, and should be re-derived once the gene
has real traffic.

### Evidence basis

Snapshot taken 2026-08-18 from the live AF instance, 87 project invocations:

```bash
curl -H "Authorization: Bearer $AGENTFORGE_API_KEY" \
  "$AGENTFORGE_URL/projects/homeiq/stats"
curl -H "Authorization: Bearer $AGENTFORGE_API_KEY" \
  "$AGENTFORGE_URL/projects/homeiq/invocations?limit=200"
```

`GET /projects/homeiq/stats/costs` does **not** exist on AF 4.59.1 (404); per-invocation
cost comes from `/invocations`, project rollup from `/stats` and `/spend`.

`by_agent` in `/stats` reports the **namespaced** name AF stamps on a published gene
(`homeiq-hiq-summarize`), and pre-namespace rows for the same gene appear bare
(`hiq-summarize`). Both map to one gene file; the observed maxima below are across both.

### Caps

`obs max` = highest single-invocation `cost_usd`; `n` = invocations in the snapshot.
"peer estimate" rows have no traffic and were sized from model + role against the named peer.

| Gene | Model / role | obs max (n) | Cap | Basis |
|---|---|---|---|---|
| `hiq-anomaly-triage` | haiku / router | $0.0545 (2) | 0.25 | 3x = $0.16; was 0.50 (over-provisioned) |
| `hiq-assistant` | haiku / producer | $0.0901 (3) | 0.30 | 3x = $0.27; sized from live spend on 2026-08-18 (ids 19583/19584/19586), not a peer estimate |
| `hiq-classify` | haiku / router | — (0) | 0.25 | peer estimate — `hiq-anomaly-triage`; was 0.10 |
| `hiq-correlate` | sonnet / aggregator | — (0) | 0.50 | peer estimate — `homeiq-audit-aggregator`; unchanged |
| `hiq-device-health-triage` | haiku / router | — (0) | 0.25 | peer estimate — `hiq-anomaly-triage`; was 0.50 |
| `hiq-draft-automation` | sonnet / producer | — (0) | 1.50 | peer estimate — `homeiq-ha-automation-author` ($0.3676); **was 0.30, below peer cost** |
| `hiq-energy-digest` | haiku / producer | — (0) | 0.25 | peer estimate — `hiq-summarize`; was 0.50 |
| `hiq-explain-anomaly` | sonnet / judge | $0.1654 (2) | 0.50 | 3x = $0.50; unchanged |
| `hiq-extract` | sonnet / producer | — (0) | 0.50 | peer estimate — structured extraction, `hiq-correlate` band; unchanged |
| `hiq-judge-automation` | sonnet / judge | $0.2042 (1) | 0.75 | 3x = $0.61; **was 0.30, only 1.5x its own observed cost** |
| `hiq-kb-librarian` | haiku / producer | — (0) | 0.25 | peer estimate — `hiq-summarize`; was 0.10 |
| `hiq-memory-curator` | haiku / producer | — (0) | 0.25 | peer estimate — `hiq-summarize`; was 0.10 |
| `hiq-notify` | haiku / gateway | $0.0000 (2, both errored) | 0.10 | **no valid observation** — the 2 runs failed on incomplete config before spending. Deliberately tight: a `high` risk_level effector that only formats and sends. Unchanged |
| `hiq-pattern-summary` | sonnet / producer | — (0) | 0.50 | peer estimate — `hiq-correlate` band; unchanged |
| `hiq-rank` | haiku / producer | — (0) | 0.25 | peer estimate — `hiq-summarize`; was 0.10 |
| `hiq-scan-injectionpayload` | sonnet / judge | — (0) | 0.75 | peer estimate — sonnet-judge band (`hiq-judge-automation`); was 0.50 |
| `hiq-summarize` | haiku / producer | $0.0520 (2) | 0.25 | 3x = $0.16; **was 0.10, under 2x** |
| `homeiq-audit-aggregator` | sonnet / aggregator | $0.1551 (21) | 0.50 | 3x = $0.47; was 0.30 |
| `homeiq-automation-judge` | sonnet / judge | $0.2509 (3) | 1.00 | 3x = $0.75; **was 0.30, only 1.2x its own observed cost** |
| `homeiq-ha-automation-author` | sonnet / producer | $0.3676 (4) | 1.50 | 3x = $1.10; **was 0.50, only 1.4x** |
| `homeiq-ha-organization-author` | sonnet / producer | $1.1019 (4) | 3.50 | 3x = $3.31; unchanged (matches the provenance note in `config/ha-organization-manifest.yaml`) |
| `homeiq-ha-organization-judge` | sonnet / judge | $0.9749 (3) | 3.50 | 3x = $2.92; unchanged |
| `homeiq-mcp-probe` | sonnet / producer | $0.2222 (4, all errored) | 0.75 | 3x = $0.67. The 4 runs errored but **still incurred cost** — a cap must cover failed runs too. Was 0.30 |
| `homeiq-service-auditor` | sonnet / judge | $0.6432 (24) | 2.00 | 3x = $1.93; was 1.00 |

The pattern the numbers exposed: caps were assigned in uniform buckets
(0.10 / 0.30 / 0.50), so the heaviest genes sat closest to their own ceiling. Four genes
were within 1.5x of their observed cost and one (`hiq-draft-automation`) was capped
*below* what its direct peer already spends — all latent false refusals.

### Refusal evidence

The cap refuses; it does not silently degrade to a cheaper answer. Verified end-to-end on
`homeiq-service-auditor` (24 invocations, observed max $0.6432) by publishing it at
`max_budget_usd: 0.01`, invoking it, then restoring `2.00`.

Under the $0.01 cap — `POST /projects/homeiq/tasks/invoke`, terminal event from
`GET /projects/homeiq/invocations/{id}/events`:

```json
{"type":"result","usage":{...},"result":"","subtype":"error_max_budget_usd",
 "is_error":true,"num_turns":1,
 "session_id":"0377a6ee-8c09-4ee1-8224-dc11bde8d8d9",
 "duration_ms":6080,"total_cost_usd":0.20689100000000002}
```

`GET /projects/homeiq/invocations/31283659-58ca-4bc5-9403-ad45ce9656c0/result`:

```json
{"invocation_id":"31283659-58ca-4bc5-9403-ad45ce9656c0","id":19482,"status":"error",
 "result":"","goal_status":null,"goal_turns":null,"goal_verifier_reason":null,
 "is_error":true,"agent_used":"homeiq-homeiq-service-auditor","result_length":0,
 "transport_ok":false,"result_is_json":false}
```

Note `result_length: 0` and `transport_ok: false`. The turn stream shows the model had
already emitted a `StructuredOutput` tool-use block, and the budget kill discarded it —
the caller receives an error envelope, never a partial or degraded answer. The run still
cost $0.2069 because the cap is checked against accumulated spend and the first turn's
cache-creation tokens land in one shot: **a cap bounds the blast radius, it does not make
an over-cap invocation free.**

After restoring `max_budget_usd: 2.0` and republishing with `--activate` (v6), the same
route succeeded — `GET /.../4ab9af47-7911-4800-b31d-308e81a0fb93/result`:

```json
{"invocation_id":"4ab9af47-7911-4800-b31d-308e81a0fb93","id":19535,"status":"complete",
 "result":"{\"assessment_status\":\"complete\",\"confidence\":0.85,...}",
 "is_error":false,"agent_used":"homeiq-homeiq-service-auditor",
 "result_length":1242,"transport_ok":true,"result_is_json":true}
```

Cost $0.0765718, `is_error: false`. Reproduce with:

```bash
python .../af_publish.py --slug homeiq --layout scout --repo-root . \
  --only agent:homeiq-service-auditor --activate --skip-workflow-check
```

### Project-level cap is owner-gated — not settable from this repo

There is **no project-level budget write endpoint** on AF 4.59.1:
`GET /projects/{slug}/spend` is read-only, and the OpenAPI document exposes no
`PUT`/`POST` counterpart. The soft/hard monthly ceiling is `AF_MONTHLY_BUDGET_USD`, an
**instance-wide environment variable on the AgentForge deployment**, which lives outside
this repo and is AgentForge-operator territory (see *Credential custody* above).

Consequence: the per-gene caps in the table are the only spend ceiling HomeIQ controls.
They bound a single runaway invocation, not a month of them. Aggregate control needs the
AF operator to set `AF_MONTHLY_BUDGET_USD`; until then, monitor
`GET /projects/homeiq/spend` on the AgentForge Ops dashboard page.

### Publish state

All 23 genes are published and active with the caps in this checkout, verified by reading
each gene's active version back from AF (`GET /projects/homeiq/agents/{name}`) and matching
`max_budget_usd` against the repo file.

Getting there needed the content gate cleared first: `af_publish.py --check-only` was red
for 10 genes on **pre-existing** conformance findings (`body_conformance/section/*`,
`interface/envelope_base_fields_present`) unrelated to budgets. `--autofix-safe` wrote the
fixes into the 10 gene files locally (`still_safe_residual=0`, no hand-editing needed), and
`--check-only` then went green across all 23. Reach for that lane before hand-editing a
gene body — the remaining `[warn/propose]` and `[warn/none]` findings do not gate publish.

**A republish returns HTTP 200 and does not activate.** Always pass `--activate`.

### Operator surface

`domains/frontends/observability-dashboard` renders these caps on the **AgentForge Ops**
page: `agent_budget_loader.load_agent_budgets` parses the frontmatter, `agentforge_client`
joins it to live `/invocations` spend, and `agentforge_ops_view` builds the table plus the
over-cap warning. Do not duplicate that parsing elsewhere.

The page grades the cap against the figure it actually governs: `budget_status` compares
`AgentStats.max_invocation_cost_usd` — the costliest single run — against the per-run cap,
and reports cumulative spend as its own column. `homeiq-service-auditor` therefore reads
`OK` (peak run $0.6432, 32% of its $2.00 cap) where the earlier cumulative comparison read
`OVER BUDGET` at $7.67 with nothing ever refused. The authoritative refusal signal remains
`subtype: error_max_budget_usd` in the invocation event stream.

Two caveats on that page:

1. Caps are read from **this checkout**, not from the AF version store. A gene edited
   locally but not yet published shows its local cap while AF still enforces the activated
   version.
2. A cap the loader cannot read (I/O or permission failure) renders as `unknown` /
   `UNKNOWN CAP`, never as "no cap" — AF treats an absent cap as unlimited, so the two
   must not collapse.

---

## Out of scope (platform purity)

- **No HomeIQ-named agents in `AgentForge/backend/agents/`.** Consumer agents live
  here and reach AF over HTTP.
- **No HomeIQ code in AgentForge platform code** — Home Assistant clients,
  PostgreSQL access, domain models, and vertical runners stay in this repo.
- **No bind-mounting HomeIQ paths into AF containers** and no edits to AgentForge's
  tracked `docker-compose.yml`.
- **No in-process `agentforge.plugins`** for HomeIQ integrations. Per the three-door
  model, prefer AGENTS.md (door 1) or MCP (door 2); plugin code (door 3) requires an
  image rebuild and is platform-operator territory.
- **No bespoke publish script.** `af_publish.py` covers the need.
- **Side effects stay here.** Build, deploy, database writes, and Home Assistant
  state changes run in HomeIQ services — AF agents produce analysis and plans.

## Credential custody

This repo's `.env` carries **only** `AGENTFORGE_URL`, `AGENTFORGE_PROJECT_SLUG`, and
`AGENTFORGE_API_KEY` (`afp_*`).

Never place in this repo: `ANTHROPIC_API_KEY`, `AF_MASTER_KEY`,
`AF_PLUGIN_ADMIN_KEY`, `TAPPS_BRAIN_AUTH_TOKEN`, or MCP search keys
(`AF_EXA_KEY`, `AF_TAVILY_KEY`, …). Those are AgentForge-operator-owned. Agents
declare `mcp_servers: [exa]` by registry key; AF spawns them with its own env.

HomeIQ-owned third-party secrets go in the AF vault at `scope: project:homeiq` via
the project bearer, and are referenced by **name** in agent `credentials:`.

## tapps-mcp relationship

tapps-mcp and the AgentForge kit are complementary and must not be conflated:
**tapps = quality / memory / docs; kit = AF wiring.** The kit was installed with
`--merge-mcp --af-mcp-only`, which left all `nlt-*` servers untouched.

## Upgrades

After an AgentForge image upgrade, run the `af-upgrade` skill (or
`af_kit_upgrade.py --upgrade`) to reconcile the kit's `compatible_af_version`
against `GET /health`.
