# Config

Pipeline config **schema** and **example** for the auto-fix pipeline (Epic 1 complete).

- **Schema:** `config/schema/` — README (documented YAML shape) and `config-schema.json` (JSON Schema). Reference: `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` §4.1.
- **Example:** `config/example/homeiq-default.yaml` — matches HomeIQ behavior and points to prompt templates.
- **Prompts:** `config/prompts/` — find, retry, fix, refactor, test, feedback templates with `{{placeholders}}` (Epic 4). Used when config sets `prompts.find` etc.
- **Multi-repo:** `config/repos-schema.md` — schema for `repos.yaml`. Example: `config/example/repos-example.yaml` (Phase 4).

No production config or secrets. HomeIQ continues to use repo-root config and `scripts/` as today.
