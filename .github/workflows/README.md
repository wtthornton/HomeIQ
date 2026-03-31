# GitHub Actions — cost-controlled mode

**Push and pull_request triggers are disabled** on heavy workflows to reduce Actions minutes (~$70+/mo was typical when every `libs/**` change fanned out domain CI + Docker + E2E).

## Run CI when you need it

1. Open **Actions** → pick the workflow (e.g. `CI — Core Platform`, `E2E & Integration Tests`).
2. **Run workflow** → choose branch (usually `main` / `master`).

## Kept automatic (lightweight)

- **dependabot-auto-merge** — only runs for Dependabot PRs.

## Also manual-only now

Docker build/test/deploy, production deploy, CodeQL, embedding regression, shared-lib publish, doc update bot, and **agentic PR review** (was every PR sync).

## Re-enable push/PR CI later

Restore `push:` / `pull_request:` blocks from git history when billing allows, or narrow path filters and **remove `libs/**`** from filters so one lib edit does not start 10+ workflows.
