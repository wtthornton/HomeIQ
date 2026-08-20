# Make TappsMCP installable by a plain `pip install` in CI

## Context

Consuming repos cannot install TappsMCP in CI. HomeIQ has now **deleted** its
TappsMCP-dependent workflows because they had never once passed:

- `agentic-pr-review.yml` — 0 successes in 117 runs since 2026-03-06
- the `quality-gate` job in `quality-gate.yml` — 0 successes in 176 runs since 2026-03-06

Those workflows are gone from HomeIQ as of commit `bfcf5379`. They will be
restored when this issue is fixed. Until then HomeIQ has **no automated quality
gate** — every consuming project in the same position is equally uncovered.

This is not a HomeIQ configuration problem. Verified against
`wtthornton/TappsMCP` at v3.12.65 / v3.12.72 on 2026-08-20.

## The three failure modes, in the order a consumer hits them

**1. `pip install tapps-mcp` → 404.** Not on PyPI. Verified:
`https://pypi.org/pypi/tapps-mcp/json` returns HTTP 404. Same for `tapps-core`.

**2. `pip install "git+https://github.com/wtthornton/TappsMCP.git@v3.12.65"` → build failure.**
The repo root `pyproject.toml` contains only `[tool.uv.workspace]`,
`[tool.uv.sources]`, and `[tool.uv]` — there is **no `[project]` table**. With no
project metadata and no explicit package discovery config, setuptools falls back
to flat-layout auto-discovery, finds seven top-level directories, and refuses:

```
error: Multiple top-level packages discovered in a flat-layout:
  ['npm', 'deploy', 'docker', 'plugin', 'stories', 'prompts', 'packages'].
```

**3. Adding `#subdirectory=packages/tapps-mcp` → dependency resolution failure.**
Gets past the build, then fails on `tapps-core>=1.0.0`, which is also unpublished.
It resolves in-workspace only via `[tool.uv.sources] tapps-core = { workspace = true }`,
and that key is **uv-only** — plain pip ignores it entirely.

So there is no pip path at all. Every consumer that follows the documented CI
integration gets a red job on its first run and every run after.

## What to decide

Pick one. I have a mild preference for (A) because it is the only option that
makes `pip install tapps-mcp` work for consumers who are not already on uv, but
(B) is a legitimate answer if uv-only is a deliberate product stance — in which
case the docs must say so plainly.

**(A) Publish `tapps-core` and `tapps-mcp` to PyPI.** Real fix. Requires an
account/token, a release workflow, and a decision on whether `docs-mcp` ships too.

> **Naming hazard — check this before publishing.** `docs-mcp` on PyPI is
> **already taken by an unrelated project** (`herring101/docs-mcp`, v0.1.2,
> "An MCP server that enables efficient searching and referencing of
> user-configured documents"). That name is not available, and worse, any CI
> that runs `pip install docs-mcp` today silently installs a stranger's package.
> Publish under a namespaced name (`tapps-docs-mcp`) and audit consuming repos
> for a bare `pip install docs-mcp`.

**(B) Make CI use uv instead of pip, and document that as the only supported path.**
Cheaper. `uv pip install "git+...#subdirectory=packages/tapps-mcp"` resolves
`tapps-core` via `[tool.uv.sources]`. Consumers must then install uv first, and
every doc/README/generated workflow that currently says `pip install tapps-mcp`
has to change — including the workflow templates `tapps_init` scaffolds into
consumer repos, which is how the broken command got into HomeIQ in the first place.

**(C) Add a `[project]` table to the repo root** so the root is itself an
installable distribution. Verify this does not break the uv workspace before
committing to it — a root `[project]` alongside `[tool.uv.workspace]` changes
resolution semantics, and I have not tested it.

## Acceptance criteria

- [ ] A documented, copy-pasteable command installs a working `tapps-mcp` CLI on
      a clean Ubuntu runner with only Python 3.12 preinstalled. State the exact
      command in the README.
- [ ] `tapps-mcp validate-changed --preset standard` runs to completion on a
      checkout of a consuming repo and exits non-zero only on real gate failures.
- [ ] A CI job in the TappsMCP repo itself proves the above on every push — a
      clean-runner install smoke test. This class of bug survived because nothing
      ever tested the consumer's install path.
- [ ] The workflow templates emitted by `tapps_init` / `tapps_upgrade` use the
      working command. Regenerating in a consumer repo must not reintroduce a
      broken install.
- [ ] If `docs-mcp` is published, it is under a name TappsMCP actually controls.
- [ ] Consuming repos are told how to restore their gate. For HomeIQ that means
      reverting `bfcf5379`, which deleted `agentic-pr-review.yml`,
      `tapps-quality.yml`, `tapps-quality-reusable.yml`, and the `quality-gate`
      job — and deliberately kept the `regression-checks` job in that same file.

## Verifying the fix

Reproduce the current failure first, so you know the test is real:

```bash
docker run --rm -it python:3.12-slim bash -c '
  pip install "git+https://github.com/wtthornton/TappsMCP.git@v3.12.72" 2>&1 | tail -5'
# expect: Multiple top-level packages discovered in a flat-layout

docker run --rm -it python:3.12-slim bash -c '
  pip install "git+https://github.com/wtthornton/TappsMCP.git@v3.12.72#subdirectory=packages/tapps-mcp" 2>&1 | tail -5'
# expect: failure resolving tapps-core
```

Then the same container, with the fixed command, must end at:

```bash
tapps-mcp --version && tapps-mcp doctor --quick
```

## Note on scope

Do not fix this by making the consumer's CI tolerate the failure — no
`|| true`, no `continue-on-error`, no pinning to a stub. A gate that cannot fail
is the thing being removed here, not the thing being built. If the answer is
"uv only, pip is unsupported," say that in the docs and change the templates;
that is a real answer. Silently degrading the gate is not.
