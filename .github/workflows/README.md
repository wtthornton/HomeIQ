# GitHub Actions

**HomeIQ is a public repository, so GitHub Actions is free and unmetered.** Standard
GitHub-hosted runners (`ubuntu-latest`) cost nothing on public repos — there is no
minute cap and no per-minute charge. Every job in this directory runs on
`ubuntu-latest` except `af-agent-gate`, which takes a runner label as input and
defaults to a self-hosted runner (also free).

> **History:** these workflows were previously set to `workflow_dispatch` only, with a
> note claiming ~$70+/mo in Actions minutes. That was incorrect for a public repository
> and meant five PRs merged with no automated validation at all. Push/PR triggers were
> restored in July 2026.

## What runs automatically

| Workflow | Trigger |
|---|---|
| `ci-*` (9 domain groups) | push to `master`/`main` + PR, filtered to that domain, `libs/**`, and the workflow files |
| `libs-ci` | push to `master`/`main` + PR, filtered to `libs/**` and the workflow file |
| `quality-gate` | push to `master`/`main` + PR |
| `test` | push to `master`/`main` + PR |
| `integration-tests` | push to `master`/`main` + PR |
| `codeql-analysis` | PR |
| `docker-build`, `docker-test` | PR touching a Dockerfile or compose file |
| `compose-parse` | every PR (deliberately unfiltered — it detects compose files under names the path filters would miss) |
| `docker-security-scan` | PR touching a Dockerfile + weekly (Mon 06:00 UTC) |
| `dependabot-auto-merge` | Dependabot PRs |

### Path filters

Domain CI is path-filtered so a change to one domain runs one workflow rather than
ten. `libs/**` **is** included in every domain filter on purpose: the shared libraries
are consumed by every domain, so a lib edit genuinely can break any of them. The
filters exist for feedback latency and signal-to-noise, **not** for cost.

`concurrency` with `cancel-in-progress: true` is set per workflow, so pushing again
cancels the superseded run.

## Still manual (`workflow_dispatch`)

These are deliberate operator actions, not cost decisions — they deploy, publish, or
need an input only a human can supply:

- `deploy-production`, `docker-deploy`, `docker-release` — release and deploy
- `publish-shared-libs` — publishes packages
- `af-agent-gate` — requires a reachable AgentForge URL
- `update-documentation` — doc-generation bot
- `embedding-regression` — runs on demand
- `copilot-setup-steps`, `deployment-notify`, `reusable-group-ci` — helper/reusable
  workflows, not directly triggered

## What would actually cost money

Only two things, neither of which this repo uses:

- **Larger runners** (e.g. `ubuntu-latest-4-cores`, GPU, or larger macOS/Windows
  images) are billed even on public repositories. Keep jobs on `ubuntu-latest`.
- **Artifact and cache storage** is billed on private repos only; public repos are
  free. If HomeIQ is ever made private, this whole page needs revisiting — that is the
  condition that changes the math, not the number of workflows.

Sources: [GitHub Actions billing](https://docs.github.com/en/billing/managing-billing-for-your-products/managing-billing-for-github-actions/about-billing-for-github-actions),
[Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage).
