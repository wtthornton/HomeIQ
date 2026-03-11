---
epic: auto-fix-isolated-project-structure
priority: high
status: complete
estimated_duration: 1 day
risk_level: low
source: Generalization plan — isolate auto-fix/MCP work for future repo breakout
type: structure
---

# Epic 50 (Epic 0): Auto-Fix Pipeline — Isolated Project Structure

**Status:** Complete (Executed)  
**Priority:** P1 High  
**Duration:** 1 day  
**Risk Level:** Low — additive only; no changes to existing HomeIQ paths or behavior  
**Note:** This is **Epic 0** for the isolated auto-fix project. When the project is later split into its own repo, this epic becomes that repo’s Epic 0 (structure setup).

## Context

The auto-fix pipeline and MCP architecture (TappsMCP, docs-mcp via MCP_DOCKER) are documented and used from within HomeIQ. To prepare for eventual breakout into a separate repository, we isolate all new “project” work under a single top-level directory. This epic creates **only** the folder and file structure for that project. No HomeIQ code is moved, no existing scripts or configs are modified, and no references from the rest of HomeIQ to this directory are required for normal operation.

## Scope

- Create `auto-fix-pipeline/` at repository root.
- Populate it with minimal placeholder structure: docs, config, runner placeholder, stories index, and project metadata.
- Do **not** move `scripts/auto-bugfix.ps1`, `scripts/auto-bugfix-stream.ps1`, or any existing HomeIQ file into this tree.
- Do **not** change `domains/`, `scripts/`, `docs/`, `implementation/`, or any other existing path.

## Stories

### Story 50.1: Create root directory and README

**Priority:** P1 | **Estimate:** 30 min | **Risk:** Low

**Acceptance Criteria:**

- [x] Directory `auto-fix-pipeline/` exists at repository root (sibling to `domains/`, `scripts/`, `docs/`).
- [x] File `auto-fix-pipeline/README.md` exists and states:
  - Purpose: isolated area for the config-driven auto-fix pipeline and MCP design; intended for future repo breakout.
  - No HomeIQ scripts or configs are moved here in this epic; HomeIQ continues to use `scripts/auto-bugfix.ps1` and existing paths.
  - Link to this epic (`stories/epic-50-auto-fix-isolated-project-structure.md`) and to `docs/architecture/auto-fix-mcp-architecture.md`.
- [x] No other files or subdirectories are created in this story.

---

### Story 50.2: Create docs/ structure

**Priority:** P1 | **Estimate:** 30 min | **Risk:** Low

**Acceptance Criteria:**

- [x] Directory `auto-fix-pipeline/docs/` exists.
- [x] File `auto-fix-pipeline/docs/README.md` exists and is an index for this project’s documentation (architecture, workflows, reference); states that detailed architecture lives in the parent repo at `docs/architecture/auto-fix-mcp-architecture.md` until breakout.
- [x] Directories exist: `auto-fix-pipeline/docs/architecture/`, `auto-fix-pipeline/docs/workflows/`, `auto-fix-pipeline/docs/reference/`.
- [x] Each subdirectory contains a `.gitkeep` or a one-line `README.md` so the directory is tracked and purpose is clear.
- [x] No content is copied or moved from HomeIQ `docs/`; placeholders only.

---

### Story 50.3: Create config/ structure

**Priority:** P1 | **Estimate:** 30 min | **Risk:** Low

**Acceptance Criteria:**

- [x] Directory `auto-fix-pipeline/config/` exists.
- [x] File `auto-fix-pipeline/config/README.md` exists and describes: future location for pipeline config schema and example (e.g. `.auto-fix/config.yaml` as in the generalization plan).
- [x] Directories exist: `auto-fix-pipeline/config/schema/`, `auto-fix-pipeline/config/example/`.
- [x] Each contains `.gitkeep` or a minimal README; no production config or secrets.
- [x] No existing HomeIQ config files are moved or duplicated here.

---

### Story 50.4: Create runner/ placeholder

**Priority:** P1 | **Estimate:** 20 min | **Risk:** Low

**Acceptance Criteria:**

- [x] Directory `auto-fix-pipeline/runner/` exists.
- [x] File `auto-fix-pipeline/runner/README.md` exists and states: future location for the generic runner (e.g. portable entrypoint that reads config); HomeIQ continues to use `scripts/auto-bugfix.ps1` at repo root.
- [x] No scripts, code, or symlinks are added; no references from HomeIQ into this directory.

---

### Story 50.5: Create stories/ and Epic 0 index

**Priority:** P1 | **Estimate:** 30 min | **Risk:** Low

**Acceptance Criteria:**

- [x] Directory `auto-fix-pipeline/stories/` exists.
- [x] File `auto-fix-pipeline/stories/README.md` exists and states: Epic 0 (structure setup) is defined in the parent repo as Epic 50 in `stories/epic-50-auto-fix-isolated-project-structure.md`; this folder will hold project-local epics/stories after breakout.
- [x] Optional: `auto-fix-pipeline/stories/EPIC-00-INDEX.md` exists as a one-page index that lists Epic 0 and its stories (50.1–50.7) with pointers to the parent epic file. No duplication of full epic content.

---

### Story 50.6: Add .gitignore and project metadata

**Priority:** P2 | **Estimate:** 15 min | **Risk:** Low

**Acceptance Criteria:**

- [x] File `auto-fix-pipeline/.gitignore` exists with minimal entries (e.g. `*.log`, `__pycache__/`, `.env`, `node_modules/`) so future work in this tree does not commit noise.
- [x] No root-level `.gitignore` or other HomeIQ git config is modified.
- [x] Optional: `auto-fix-pipeline/PROJECT.md` or similar one-pager with project name (“Auto-Fix Pipeline”), scope (config-driven runner, MCP integration), and “lives under HomeIQ until repo breakout.”

---

### Story 50.7: Document in main docs index (non-breaking)

**Priority:** P2 | **Estimate:** 15 min | **Risk:** Low

**Acceptance Criteria:**

- [x] In `docs/README.md`, one line or short subsection is added under an appropriate section (e.g. Architecture or a new “Isolated projects” subsection) that states: `auto-fix-pipeline/` at repo root is the isolated project for the auto-fix pipeline and MCP design; see `auto-fix-pipeline/README.md` and `docs/architecture/auto-fix-mcp-architecture.md`.
- [x] No existing links or sections are removed or broken.
- [x] HomeIQ build, deploy, and test paths are unchanged.

---

## Definition of Done (Epic)

- [x] All stories 50.1–50.7 are complete.
- [x] `auto-fix-pipeline/` exists with the structure above; all referenced files and directories are present.
- [x] No file under `domains/`, `scripts/`, `docs/` (except the one additive docs/README change), `implementation/`, or root is modified in a way that changes behavior.
- [x] CI and normal development workflows for HomeIQ remain valid.

**Executed:** Structure created and indexed. Next: **Epic 1** (auto-fix project).

## References

- [AUTO_BUGFIX_GENERALIZATION_PLAN.md](../implementation/AUTO_BUGFIX_GENERALIZATION_PLAN.md)
- [docs/architecture/auto-fix-mcp-architecture.md](../docs/architecture/auto-fix-mcp-architecture.md)
- [.cursor/MCP_SETUP_INSTRUCTIONS.md](../.cursor/MCP_SETUP_INSTRUCTIONS.md)
