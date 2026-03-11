# repos.yaml schema (multi-repo mode, Phase 4)

When the runner is invoked in **multi-repo mode** (e.g. `run-multirepo.ps1 -ReposPath repos.yaml`), it reads a `repos.yaml` file that lists repositories to run the pipeline on. Paths in the file are relative to the **meta-repo root** (the directory containing `repos.yaml` unless overridden).

## Top-level keys

| Key | Type | Description |
|-----|------|-------------|
| `repos` | array | List of repo entries (required). |
| `default_config` | string | Optional. Default pipeline config path (relative to meta-repo root) used when a repo has no `config_path`. |

## Repo entry

| Key | Type | Description |
|-----|------|-------------|
| `path` | string | **Required.** Path to the repo directory (relative to meta-repo root or absolute). Must contain or be the repo root (runner will look for `scripts/auto-bugfix.ps1` here or use a shared script with `-ProjectRootOverride`). |
| `name` | string | Optional. Display name for logs. |
| `config_path` | string | Optional. Pipeline config YAML path (relative to meta-repo root). If omitted, `default_config` is used. |
| `languages` | array | Optional. Override for prompts (e.g. `["python","typescript"]`). |
| `purpose` | string | Optional. Short description (for docs only). |

## Example

```yaml
default_config: "auto-fix-pipeline/config/example/homeiq-default.yaml"

repos:
  - path: "services/api"
    name: "API service"
    config_path: "auto-fix-pipeline/config/example/homeiq-default.yaml"
  - path: "services/web"
    name: "Web app"
    # uses default_config
  - path: "C:/other/my-repo"
    name: "External repo"
    config_path: "auto-fix-pipeline/config/example/homeiq-default.yaml"
```

## How the runner uses it

1. Resolve meta-repo root (directory of `repos.yaml` or `-MetaRoot`).
2. For each entry in `repos`: resolve `path` to absolute (relative to meta-repo root).
3. Resolve `config_path` or `default_config` to absolute (relative to meta-repo root).
4. Invoke the pipeline script with `-ProjectRootOverride <repo path>` and `-ConfigPath <config path>`. The script may live in meta-repo (e.g. `scripts/auto-bugfix.ps1`) and is called once per repo.
