# Adoption and Breakout (Phase 5)

How to add the auto-fix pipeline to a new project and how to move this folder into its own repository.

---

## 1. Adding the pipeline to a new project

You can **copy** the pipeline into your repo or **reference** it (e.g. submodule). Either way you need:

- **Runner or script:** Something that runs the pipeline (either the generic runner or the script with a config path).
- **Config:** A YAML config that describes your project, paths, runner settings, MCP, and optional prompt paths.
- **Optional: prompt templates** — Copy or point to `config/prompts/` if you want to edit prompts without changing code.
- **Optional: scan manifest** — A `scan-manifest.json` (see schema in parent `docs/`) if you use rotate mode.

### Option A: Copy into your repo

1. Copy the `auto-fix-pipeline/` directory into your repo (e.g. as `auto-fix-pipeline/` or `.auto-fix/`).
2. Copy or adapt `scripts/auto-bugfix.ps1` and `scripts/auto-bugfix-stream.ps1` from the template/source repo (e.g. HomeIQ). The script must support `-ConfigPath`.
3. Create a config file (e.g. `auto-fix-pipeline/config/example/my-project.yaml`) from the schema in `config/schema/README.md`. Set:
   - `project.name`, `project.languages`, `project.root`
   - `runner.model`, `runner.max_cost`, `runner.budget_allocation`
   - `paths.*` (dashboard, feedback, history, impl_dir)
   - `scan.manifest_path` if you use a scan manifest
   - `mcp.config_path`, `mcp.tapps_mcp_server` (e.g. `MCP_DOCKER`), and optionally `mcp.scan_tools` / `mcp.fix_tools` if you restrict tools
   - `prompts.find`, `prompts.retry`, etc. if you use template files (paths relative to project root)
4. Run from repo root:
   - **Via runner:** `.\auto-fix-pipeline\runner\run.ps1 -ConfigPath auto-fix-pipeline/config/example/my-project.yaml`
   - **Via script:** `.\scripts\auto-bugfix.ps1 -ConfigPath auto-fix-pipeline/config/example/my-project.yaml`
5. Ensure **Python** (with PyYAML) is available when using `-ConfigPath`; ensure **claude** CLI, **git**, **gh**, and (if used) **MCP** are set up.

### Option B: Reference (submodule or package)

1. Add this repo (or the future standalone pipeline repo) as a **submodule** or reference it as a **package**.
2. In your repo, create only a **config file** (and optionally a scan manifest and custom prompt overrides). Point config paths to the referenced pipeline (e.g. `auto-fix-pipeline/config/prompts/find.md` if the submodule is at `auto-fix-pipeline/`).
3. Run the **runner** or **script** from your repo root, passing the path to your config. The script/runner lives in the referenced tree; your repo only holds config and data (manifest, feedback dir, history file).

---

## 2. Using with MCP_DOCKER and TappsMCP

- **MCP_DOCKER** (Docker MCP Toolkit) provides TappsMCP (and optionally docs-mcp). Tools appear with the prefix `mcp__MCP_DOCKER__` (e.g. `mcp__MCP_DOCKER__tapps_quick_check`).
- **Config:** Set `mcp.tapps_mcp_server: "MCP_DOCKER"` and ensure `.mcp.json` at project root (or `mcp.config_path`) configures the MCP_DOCKER server. See parent repo `.cursor/MCP_SETUP_INSTRUCTIONS.md`.
- **Headless / CI:** Use `.mcp.json` at project root for headless runs (e.g. `claude --headless` or the auto-bugfix script). The pipeline passes the MCP config path to the CLI so tools are available during scan/fix/feedback.
- **Without TappsMCP:** Omit or disable MCP in config; the script still runs but quality/security tools won’t be in the allowed-tools list. You can point `prompts` at templates that don’t reference `{{tapps_prefix}}` or use built-in prompts and accept fewer tools.

---

## 3. Customization

- **Config:** Edit your YAML to change model, budget, paths, manifest, retry attempts, and prompt file paths.
- **Prompts:** Edit the Markdown files in `config/prompts/` (or your own paths set in `config.prompts`). Placeholders: `{{project_name}}`, `{{languages}}`, `{{scope_hint}}`, `{{bug_count}}`, `{{tapps_prefix}}`, `{{bugs_json}}`, `{{changed_files}}`, `{{feedback_file}}`, etc. See `config/prompts/README.md`.
- **Scan manifest:** Define units (path, name, priority_weight, scan_hint, etc.) for rotate mode; see parent `docs/scan-manifest.json` and scan-format docs.

---

## 4. Multi-repo mode (Phase 4)

From a **meta-repo** that contains multiple repositories (e.g. submodules or sibling directories):

1. Create a **repos.yaml** (see `config/repos-schema.md` and `config/example/repos-example.yaml`) with a `repos` array. Each entry has `path` (repo directory, relative to meta-repo root), optional `name`, and optional `config_path` (pipeline config; else `default_config`).
2. Ensure **scripts/auto-bugfix.ps1** exists in the meta-repo and supports **-ProjectRootOverride** and **-ConfigPath**.
3. Run: `.\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "auto-fix-pipeline/config/example/repos-example.yaml"` (or your `repos.yaml` path).

The runner invokes the script once per repo with `-ProjectRootOverride <repo path>` and `-ConfigPath <config path>`. Config paths in the YAML are relative to the meta-repo; at runtime, the script uses the repo path as project root for all path resolution.

---

## 5. Breakout: moving to its own repo

When you want **auto-fix-pipeline/** to become a **standalone repository**:

1. **Create a new repo** (e.g. `auto-fix-pipeline` or `agent-templates/auto-fix`).
2. **Copy into the new repo:**
   - `config/` (schema, example, prompts)
   - `runner/` (run.ps1, README)
   - `docs/` (NEXT_STEPS, adoption-and-breakout, architecture/workflows/reference as needed)
   - `stories/` (EPIC-00-INDEX, README) and any project-local stories
   - Root files: README.md, PROJECT.md, .gitignore
3. **Do not copy:** Scripts that live in the **host** repo (`scripts/auto-bugfix.ps1`, `scripts/auto-bugfix-stream.ps1`). The standalone repo is a **template**: it holds config schema, default prompts, and a **runner** that invokes the host’s script (or a script installed by the host from a known location).
4. **Document in the new repo:**
   - **README:** “This repo is a template. Clone or submodule it into your project. Your project must provide the pipeline script (e.g. from HomeIQ or a compatible fork) and a config file; the runner in this repo calls that script with `-ConfigPath`.”
   - **Install/usage:** How to copy or submodule this repo, where to put the script, and how to run the runner with a config path.
5. **Parent (e.g. HomeIQ):** Can replace `auto-fix-pipeline/` with a **submodule** pointing at the new repo, or keep a copy and periodically sync. The script stays in the parent repo; config and prompts can live in the submodule or in the parent.

After breakout, the new repo’s “Epic 0” is the structure that already exists; Epics 1–4 are reflected in the template (schema, example config, runner, script contract, prompts). Phase 4 (multi-repo runner with `repos.yaml`) can be added in the new repo if needed.
