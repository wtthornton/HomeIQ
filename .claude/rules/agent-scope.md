---
alwaysApply: true
---
# Deployed Agent Scope (TappsMCP)

Agents deployed by `tapps_init` / `tapps_upgrade` (and Claude Code itself
working in this project) must stay scoped to THIS repo and THIS project for
any **write** operation.

## Allowed (read)

- Documentation lookups across any project (`tapps_lookup_docs`, web search,
  reading sibling repos).
- Searching memory across federated projects to inform decisions.
- Cloning or browsing other repositories for reference only.

## Forbidden (write outside the deploying project)

- Creating, updating, commenting on, or moving Linear (or other tracker)
  issues that belong to a different project than this repo.
- Modifying files, branches, or pull requests in any other repository.
- Pushing, merging, releasing, or running automation on behalf of another
  project.

## How to apply

- When using the Linear MCP tools (`mcp__plugin_linear_linear__*` or any
  successor), only operate on issues whose `team` / `project` matches the
  one configured for this repo. Read team/project identity from
  `.tapps-mcp.yaml` or the current git remote — never from arbitrary search
  results that point at other workspaces.
- When in doubt about whether a target belongs to this project, **stop and
  ask the user** instead of writing.
- Updates to this agent itself flow through `tapps_upgrade` re-running in
  this project, never via cross-project agent edits.
