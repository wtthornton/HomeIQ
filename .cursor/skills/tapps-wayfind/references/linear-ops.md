# Wayfind Linear operations

Linear is the system of record for maps, tickets, claims, and blocking.

## Create / update

- **Writes:** always the `linear-issue` skill (docs-mcp generate → validate →
  save). Never call plugin `save_issue` directly.
- **Map parent:** create as a parent issue (or epic child story that owns the
  map). Title names the destination effort; body from `assets/map-template.md`.
- **Tickets:** children of the map. Body starts with `## Question`. Prefer
  labels `wayfinder:*` when the workspace has them.
- **Claim:** assign the ticket to the driving agent/user **before** work.
  Open + unassigned = unclaimed.
- **Blocking:** use Linear's native blocking/related relations so the frontier
  is visible in the UI. Wire edges in a **second pass** after create (ids needed).
- **Resolve:** comment with the answer → close → append gist to map
  Decisions-so-far (edit map via `linear-issue` update).

## Read

- **Multi-issue / frontier queries:** `linear-read` skill only (cache-first;
  never raw `list_issues` without `tapps_linear_snapshot_get`).
- **Single issue:** `get_issue(id=...)` is fine.
- **Frontier:** open children of the map that are unblocked and unclaimed.

## Brain (optional)

- Save resume/rationale with a key tied to the ticket id after resolve.
- Do **not** mirror status, assignee, or frontier into brain — Linear wins.
