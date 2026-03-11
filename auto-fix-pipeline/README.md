# Auto-Fix Pipeline (Isolated Project)

**Purpose:** Isolated area for the config-driven auto-fix pipeline and MCP design. This directory is intended for future breakout into a separate repository.

**Preferred entry point (Epic 52):** `.\auto-fix-pipeline\runner\run.ps1 -Bugs 3` — config-driven. Direct script `.\scripts\auto-bugfix.ps1` also uses config by default (`homeiq-default.yaml` or `$env:AUTO_FIX_CONFIG`). Multi-repo: `runner/run-multirepo.ps1 -ReposPath repos.yaml`. See [docs/adoption-and-breakout.md](docs/adoption-and-breakout.md).

**References:**

- **Config:** [config/README.md](config/README.md) — schema in `config/schema/`, example in `config/example/homeiq-default.yaml`
- **Runner:** [runner/README.md](runner/README.md) — single-repo `runner/run.ps1`; multi-repo `runner/run-multirepo.ps1` (Phase 4)
- **Recommended next steps:** [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md)
- Epic 0 (structure setup): [stories/epic-50-auto-fix-isolated-project-structure.md](../stories/epic-50-auto-fix-isolated-project-structure.md)
- Architecture: [docs/architecture/auto-fix-mcp-architecture.md](../docs/architecture/auto-fix-mcp-architecture.md)
- Generalization plan: [implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md](../implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md)
