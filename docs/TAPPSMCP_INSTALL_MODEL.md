# How TappsMCP is installed, and why it does not run in CI

**Status:** current as of 2026-08-20, verified against tapps-mcp 3.12.72.

## The distribution model

TappsMCP is **not published to any package index**. It is a local developer tool,
installed globally on the machine from a local source checkout.

```
/home/wtthornton/code/tapps-mcp          # source checkout (remote: wtthornton/TappsMCP.git)
  └─ packages/tapps-core                 # installed editable
  └─ packages/tapps-mcp
  └─ packages/docs-mcp

~/.tapps-mcp/releases/<version>-<sha>/   # one venv per release, e.g. 3.12.72-dd5c4e06
~/.tapps-mcp/current -> releases/<...>   # symlink selecting the active release
~/.local/bin/tapps-mcp -> ~/.tapps-mcp/current/bin/tapps-mcp
~/.local/bin/docsmcp   -> ~/.tapps-mcp/current/bin/docsmcp
```

The release directory is named `<version>-<sha>`, where the sha is the source
checkout's HEAD — so the installed build is always traceable to a commit.
`direct_url.json` in the installed dist-info records the local path it came from:

```json
{"url": "file:///home/wtthornton/code/tapps-mcp/packages/tapps-core",
 "dir_info": {"editable": true}}
```

Upgrades go through the `tapps-upgrade` skill, which reinstalls the global CLIs
from the local checkout and refreshes generated scaffolding. There is no
`pip install` step anywhere in that path.

## The agent surface: the `nlt-*` MCP servers

Agents do not invoke the CLI. They reach the same global install through six
local HTTP MCP servers — a "fleet" of `tapps-mcp` processes on loopback, each
serving a different tool bundle:

| Server | URL | Bundle |
|---|---|---|
| `nlt-build` | `http://127.0.0.1:8760/mcp` | scoring, gates, security, call graph, docs lookup |
| `nlt-memory` | `http://127.0.0.1:8761/mcp` | `tapps_memory`, handoff, session notes |
| `nlt-setup` | `http://127.0.0.1:8762/mcp` | doctor, init, upgrade, engagement level |
| `nlt-linear-issues` | `http://127.0.0.1:8763/mcp` | issue generate/validate, snapshot cache |
| `nlt-project-docs` | `http://127.0.0.1:8764/mcp` | doc generation and drift checks |
| `nlt-release-ship` | `http://127.0.0.1:8765/mcp` | changelog, release notes, release gate |

One fleet serves several projects. Per-project scope is a **request header**,
not a per-project server: `.mcp.json` sets `X-Tapps-Project-Root` to this repo's
path. PID and log files live in `~/.tapps-mcp/fleet/`.

All six bind to `127.0.0.1` only. Nothing about this arrangement is reachable
from a hosted CI runner, by design.

## Why the GitHub Actions quality gate was removed

A GitHub-hosted runner has neither the source checkout nor the global install, so
there is no command that can put `tapps-mcp` on its PATH:

| Attempt | Result |
|---|---|
| `pip install tapps-mcp` | HTTP 404 — not on PyPI, and not intended to be |
| `pip install "git+https://github.com/wtthornton/TappsMCP.git@<tag>"` | Build error: the repo root is a uv workspace with no `[project]` table, so setuptools hits flat-layout auto-discovery and refuses |
| ...`#subdirectory=packages/tapps-mcp` | Resolves past the build, then fails on `tapps-core`, which is also unpublished and resolves only via uv's workspace source |

The workflows that tried anyway never once succeeded: `agentic-pr-review` was
0-for-117 runs and the `quality-gate` job 0-for-176, both since 2026-03-06. They
were removed in `bfcf5379`.

**This is a distribution-model mismatch, not a packaging defect.** Publishing to
PyPI is not the fix, because a package index is not how this tool is meant to
travel.

> Note if publishing is ever reconsidered: the name `docs-mcp` on PyPI is already
> taken by an unrelated project (`herring101/docs-mcp`). A bare
> `pip install docs-mcp` installs a stranger's package.

## Where the gate is actually enforced

Locally, before code reaches CI — which is the intended design, not a fallback:

- `tapps_quick_check` after each Python edit
- `tapps_validate_changed` before declaring work complete
- `tapps_checklist` as the final verification step
- The Stop hook (`.claude/hooks/tapps-stop.sh`) writes to
  `.tapps-mcp/.completion-gate-violations.jsonl` when edits ship unvalidated
- `/tapps-finish-task` bundles validate + checklist

CI still enforces what does not need TappsMCP: `ruff check` and
`ruff format --check` run per service in `reusable-group-ci.yml`, and the
`regression-checks` job in `quality-gate.yml` guards the TAP-5291 / TAP-5993 /
TAP-6036 / TAP-5303 invariants.

## If the gate is wanted in CI again

The only path consistent with the distribution model is a **self-hosted runner**
that already carries the global install. Then the step is simply:

```bash
TAPPS_MCP_PROJECT_ROOT=/workspace tapps-mcp validate-changed --preset staging
```

Do not reintroduce it by making the job tolerate failure — no `|| true`, no
`continue-on-error`. A gate that cannot fail is worse than no gate, because it
reads as coverage.
