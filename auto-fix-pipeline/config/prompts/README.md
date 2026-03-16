# Prompt templates (Epic 4)

Pipeline prompts are stored here as Markdown templates with placeholders. When the script is run with `-ConfigPath` and the config file sets `prompts.find`, `prompts.retry`, etc., the script loads these files and substitutes placeholders. Otherwise it uses built-in inline prompts (unchanged behavior).

## Placeholders

| Placeholder | Used in | Description |
|-------------|---------|-------------|
| `{{project_name}}` | find, retry, feedback | From config `project.name` or "HomeIQ" |
| `{{languages}}` | find, retry, fix, refactor, test | From config `project.languages` or "Python" |
| `{{scope_hint}}` | find, retry | Runtime scope (target dir / scan unit hint) |
| `{{bug_count}}` | find, retry, feedback | Number of bugs to find or fixed |
| `{{tapps_prefix}}` | all | MCP tool prefix (e.g. `mcp__tapps-mcp__`) |
| `{{prompt_overrides}}` | find, retry | Content of FIND_PROMPT_OVERRIDES.md if present |
| `{{bugs_json}}` | fix, test | JSON array of bugs to fix or that were fixed |
| `{{changed_files}}` | refactor, feedback | Comma-separated list of changed files |
| `{{feedback_file}}` | feedback | Path to feedback markdown file |
| `{{feedback_dir}}` | feedback | Directory for feedback files (e.g. docs/tapps-feedback) |
| `{{run_timestamp}}` | feedback | Run date/time |
| `{{branch}}` | feedback | Git branch name |

## Files

- **find.md** — Scan phase (TappsMCP + code review)
- **retry.md** — Scan retry (no MCP)
- **fix.md** — Fix phase
- **refactor.md** — Chain: refactor phase
- **test.md** — Chain: test phase
- **feedback.md** — Feedback phase

## Config

In your pipeline config YAML, point to these templates (paths relative to project root):

```yaml
prompts:
  find: "auto-fix-pipeline/config/prompts/find.md"
  retry: "auto-fix-pipeline/config/prompts/retry.md"
  fix: "auto-fix-pipeline/config/prompts/fix.md"
  refactor: "auto-fix-pipeline/config/prompts/refactor.md"
  test: "auto-fix-pipeline/config/prompts/test.md"
  feedback: "auto-fix-pipeline/config/prompts/feedback.md"
```

Omitting `prompts` or a key keeps the script’s built-in prompt for that phase.
