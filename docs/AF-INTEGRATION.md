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
