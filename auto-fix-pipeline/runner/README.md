# Runner

**Epic 2:** Config-driven entrypoint that loads a pipeline config (YAML) and invokes the existing `scripts/auto-bugfix.ps1` with parameters derived from config.

## Relation to scripts/auto-bugfix.ps1

- **Preferred entry point:** `.\auto-fix-pipeline\runner\run.ps1 -Bugs 3` (config-driven; passes -ConfigPath to the script).
- **Alternative:** `.\scripts\auto-bugfix.ps1 -Bugs 3` — uses config by default (`homeiq-default.yaml` or `$env:AUTO_FIX_CONFIG`). Both runner and script require config (Epic 52).

## Usage

From the **repository root**:

```powershell
.\auto-fix-pipeline\runner\run.ps1
.\auto-fix-pipeline\runner\run.ps1 -ConfigPath "auto-fix-pipeline/config/example/homeiq-default.yaml"
.\auto-fix-pipeline\runner\run.ps1 -Bugs 3 -Chain
```

Config path:

- **Default:** `$env:AUTO_FIX_CONFIG` if set; otherwise `auto-fix-pipeline/config/example/homeiq-default.yaml` (relative to repo root).
- **-ConfigPath:** Explicit path (relative to repo root or absolute).

The runner passes **-ConfigPath** to the script; the script loads the YAML and uses it for model, budget, MCP, paths, and manifest (Epic 3). Other script parameters (**Bugs**, **Chain**, **NoDashboard**, **NoRotate**, **TargetUnit**, **Worktree**, **Branch**, **TargetDir**, **Base**) are passed through.

## Requirements

- **scripts/auto-bugfix.ps1** and its dependencies (claude CLI, git, gh, MCP). When the script is given **-ConfigPath**, it parses YAML via Python + PyYAML; ensure Python with `pyyaml` is available if you use config.

## Multi-repo mode (Phase 4)

To run the pipeline on **multiple repositories** from a meta-repo:

```powershell
.\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "auto-fix-pipeline/config/example/repos-example.yaml"
.\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "repos.yaml" -Bugs 3
```

- **-ReposPath** (required): Path to `repos.yaml` (list of repos with `path`, optional `name`, `config_path`). Paths in the file are relative to meta-repo root. See `config/repos-schema.md` and `config/example/repos-example.yaml`.
- The runner invokes `scripts/auto-bugfix.ps1` once per repo with **-ProjectRootOverride** (repo path) and **-ConfigPath** (shared or per-repo). The script must support `-ProjectRootOverride` (Phase 4).

Meta-repo root defaults to the repo containing `auto-fix-pipeline/`; override with **-MetaRoot**. Script path defaults to `scripts/auto-bugfix.ps1` in meta-repo; override with **-ScriptPath**.

## Config shape

See `auto-fix-pipeline/config/schema/README.md` and `config/example/homeiq-default.yaml`. For multi-repo, see `config/repos-schema.md`.
