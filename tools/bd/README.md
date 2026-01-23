# Beads (bd) – task tracking for TappsCodingAgents

This directory contains the **bd** (Beads) binary used by TappsCodingAgents for dependency-aware task tracking.

## Usage

- **In terminal** (from project root):
  ```powershell
  .\tools\bd\bd.exe ready
  .\tools\bd\bd.exe create "Task title" -p 0
  .\tools\bd\bd.exe list
  ```
  Or run `.\scripts\set_bd_path.ps1` (session) or `.\scripts\set_bd_path.ps1 -Persist` (User PATH). `bd` is also in `tools\bd`.

- **Via TappsCodingAgents:**
  - `@simple-mode *todo ready` → runs `bd ready`
  - `@simple-mode *todo create "Title"` → runs `bd create`
  - `*build`, `*fix`, `*review`, workflows: when `beads.hooks_*` are enabled, tapps-agents creates/closes Beads issues automatically.

## Config

`.tapps-agents/config.yaml` → `beads`:

- `enabled: true`
- `hooks_simple_mode`, `hooks_workflow`: create/close issues for *build, *fix, workflows
- `sync_epic: true`: Epic execution syncs stories to Beads

## Beads-specific checks

```powershell
bd doctor
bd doctor --fix
```

Optional, for multi-clone or team use: `bd migrate sync beads-sync` to set up a sync-branch workflow.

## Project state

- **Prefix:** `HomeIQ` (e.g. `HomeIQ-a3f2dd`)
- **DB:** `.beads/beads.db`
- **Init:** `bd init` already run in this repo.

## Troubleshooting

If `bd create` fails with `issue_prefix config is missing`, see **[implementation/BEADS_BD_ISSUES_AND_RECOMMENDATIONS.md](../implementation/BEADS_BD_ISSUES_AND_RECOMMENDATIONS.md)** for diagnosis and workarounds.

## Links

- [Beads (steveyegge/beads)](https://github.com/steveyegge/beads)
- TappsCodingAgents: `docs/BEADS_INTEGRATION.md` (in tapps-agents package)
