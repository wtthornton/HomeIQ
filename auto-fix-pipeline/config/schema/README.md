# Pipeline config schema

This directory defines the **pipeline config shape** for the auto-fix pipeline. The runner (or script with `-ConfigPath`) reads a single YAML file; all keys are optional with sensible defaults.

**Reference:** `implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md` §4.1.

---

## Top-level keys

| Key | Type | Description |
|-----|------|--------------|
| `version` | integer | Config version; use `1`. |
| `project` | object | Project identity and root. |
| `runner` | object | CLI, model, cost, budget allocation. |
| `scan` | object | Manifest, selector, output format, retries. |
| `fix` | object | Chain phases and validation. |
| `mcp` | object | MCP config path, server name, tools, experts, docs. |
| `paths` | object | Dashboard, feedback, history, impl dir, scan-failure prefix. |
| `prompts` | object | Optional paths to prompt template files. |

---

## project

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `name` | string | — | Project name (e.g. `"HomeIQ"`). |
| `languages` | array of string | `["python"]` | Languages for prompts and tool hints. |
| `root` | string | `"."` | Project root; or use env `WORKSPACE_ROOT`. |

---

## runner

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cli` | string | `"claude"` | CLI or path to wrapper. |
| `model` | string | `"claude-sonnet-4-6"` | Model identifier. |
| `max_cost` | number | `5.0` | Total cost budget (e.g. USD). |
| `budget_allocation` | object | see below | Ratios for scan / fix / chain / feedback. |

**budget_allocation** (ratios must sum to 1.0):

- `scan` (number): e.g. `0.30`
- `fix` (number): e.g. `0.40`
- `chain` (number): e.g. `0.15` (refactor + test)
- `feedback` (number): e.g. `0.15`

---

## scan

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `manifest_path` | string | `"docs/scan-manifest.json"` | Path to scan manifest (relative to project root). |
| `selector` | string | `"builtin"` | `"builtin"`, path to script, or `"none"` for full-repo. |
| `output_format` | object | see below | Markers and bug object schema. |
| `retry_attempts` | integer | `2` | Max scan attempts (first + retries). |
| `retry_fallback_tools` | array of string | `["Read","Grep","Glob"]` | Tools allowed on retry (no MCP). |

**output_format:**

- `markers`: array of two strings, e.g. `["<<<BUGS>>>", "<<<END_BUGS>>>"]`
- `schema`: bug object shape; keys `file` (string), `line` (int), `description` (string), `severity` (string)

---

## fix

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `chain_phases` | array of string | `["fix","refactor","test"]` | Phases after fix (optional). |
| `validation_required` | boolean | `true` | Require quality/validation before completion. |

---

## mcp

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `config_path` | string | `".mcp.json"` | MCP config path (project root). |
| `tapps_mcp_server` | string | `"tapps-mcp"` | Server name; tool prefix becomes `mcp__{server}__`. |
| `scan_tools` | string | (see example) | Comma-separated tools for scan phase. |
| `fix_tools` | string | (see example) | Comma-separated tools for fix phase. |
| `expert_domains` | array of string | (see example) | Domains for `tapps_consult_expert`. |
| `docs_lookup` | boolean | `true` | Use Context7 / `tapps_lookup_docs` when available. |

Tool names must use the configured prefix, e.g. `mcp__tapps-mcp__tapps_quick_check`.

---

## paths

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `dashboard_state` | string | `"scripts/.dashboard-state.json"` | Dashboard state file. |
| `dashboard_html` | string | `"scripts/dashboard.html"` | Dashboard HTML path. |
| `feedback_dir` | string | `"docs/tapps-feedback"` | Directory for feedback markdown files. |
| `history_file` | string | `"docs/BUG_HISTORY.json"` | Bug history JSON. |
| `impl_dir` | string | `"implementation"` | Implementation notes / scan failure saves. |
| `scan_failure_prefix` | string | `"auto-bugfix-scan-failure"` | Filename prefix for failed scan output. |

---

## prompts (optional overrides)

If present, paths to template files (relative to project root). Placeholders: `{{project_name}}`, `{{languages}}`, `{{scope_hint}}`, `{{allowed_tools}}`, `{{bug_count}}`.

| Key | Description |
|-----|-------------|
| `find` | Scan/find prompt. |
| `retry` | Retry scan prompt. |
| `fix` | Fix phase prompt. |
| `refactor` | Refactor phase prompt. |
| `test` | Test phase prompt. |
| `feedback` | Feedback phase prompt. |

---

## Validation

- **JSON Schema:** `config-schema.json` in this directory can be used to validate a config (after converting YAML to JSON or using a YAML-aware validator).
- **Example:** `config/example/homeiq-default.yaml` matches current HomeIQ behavior and conforms to this schema.
