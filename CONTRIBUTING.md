# Contributing to HomeIQ

Contributions are welcome! This guide covers the development workflow and quality expectations.

## Getting Started

```bash
# Fork the repo, then:
git clone https://github.com/YOUR_USERNAME/HomeIQ.git
cd HomeIQ

# Create a feature branch
git checkout -b feature/your-feature-name
```

## Development Guidelines

- **Python 3.12** — all services target Python 3.12
- **Formatting** — follow [ruff](https://docs.astral.sh/ruff/) formatting, type hints preferred
- **Commits** — use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `chore:`)
- **Tests** — add tests for new features, run `pytest` before submitting
- **Docker** — test your changes build with `docker compose build <service-name>`

### Local full stack (optional)

- Copy `infrastructure/env.example` to **`.env` in the repo root** (Compose and `start-stack` expect this path).
- Start everything: `./scripts/start-stack.sh` or `.\scripts\start-stack.ps1` (ordered domains + `--profile production`).
- Do not use bare `docker compose up` from the repo root for routine work — see [docs/deployment/DEPLOYMENT_QUICK_REFERENCE.md](docs/deployment/DEPLOYMENT_QUICK_REFERENCE.md).

### Docker Security Requirements

All Docker images must follow these security practices:

- **Non-root user** — containers must run as a non-root user (use `USER appuser` after setting up permissions)
- **npm ci** — use `npm ci` instead of `npm install` for reproducible builds
- **No secrets** — never hardcode API keys, passwords, or tokens in Dockerfiles or source code
- **Minimal base images** — prefer Alpine-based images where possible

## Quality Gate (TAPPS)

Every pull request that changes Python files is automatically checked by the **TAPPS quality pipeline** via [`.github/workflows/tapps-quality.yml`](.github/workflows/tapps-quality.yml). The quality gate runs in CI and posts results directly on your PR as a comment.

**PRs with failing quality gates cannot be merged.**

### What the quality gate checks

| Category | What it checks |
|---|---|
| **Linting** | ruff — style, formatting, import order |
| **Complexity** | radon — cyclomatic complexity, maintainability index |
| **Security** | bandit — common vulnerability patterns, hardcoded secrets |
| **Dead code** | vulture — unused functions, imports, variables |
| **Type safety** | mypy — type annotation correctness |

### Quality presets

The CI pipeline uses the **standard** preset by default:

| Preset | Minimum Score | When used |
|---|---|---|
| `standard` | 70+ | Default for all PRs |
| `strict` | 80+ | Used for shared libraries (`libs/`) |
| `framework` | 75+ | Used for framework-level code |

### What to expect on your PR

1. When you open or update a PR that changes `.py` files, the **Quality Gate** workflow runs automatically.
2. After the workflow completes, a comment appears on the PR with:
   - Pass/fail status
   - Per-file quality scores
   - Details of any issues found
3. If the gate **passes**, you're good to go.
4. If the gate **fails**, review the output and fix the reported issues before requesting review.

### Running the quality gate locally

You can run the same checks locally before pushing:

```bash
# Install tapps-mcp and quality checkers
pip install tapps-mcp ruff mypy bandit radon vulture

# Validate your changed files (compares against HEAD)
tapps-mcp validate-changed --preset standard

# Validate a specific file
tapps-mcp validate-changed --file-paths path/to/your/file.py --preset standard
```

### Common quality issues and fixes

| Issue | Fix |
|---|---|
| ruff lint errors | Run `ruff check --fix .` to auto-fix |
| High complexity | Break large functions into smaller ones |
| Bandit security warning | Review the flagged pattern; use `# nosec` only if it's a false positive with a comment explaining why |
| Unused imports | Remove them, or if needed for re-export, use `__all__` |

## Pull Request Process

1. Create a feature branch from `master`
2. Make your changes following the guidelines above
3. Run tests locally: `pytest`
4. Run the quality gate locally: `tapps-mcp validate-changed --preset standard`
5. Push and open a Pull Request
6. Wait for CI checks (quality gate, domain CI, integration tests) to pass
7. Address any review feedback
8. A maintainer will merge once all checks pass

## Shared Libraries

Changes to shared libraries under `libs/` have a wider blast radius. The quality gate uses the **strict** preset for these files. Run impact analysis before modifying shared libraries:

```bash
tapps-mcp impact-analysis --file-path libs/homeiq-data/src/homeiq_data/database_pool.py
```

## Project Structure

See the [README](README.md) for the full project structure and architecture overview.
