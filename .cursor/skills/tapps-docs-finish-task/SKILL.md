---
name: tapps-docs-finish-task
description: >-
  Doc-work finish bundle: drift, links, cross-refs, completeness, optional
  release gate. Use when documentation edits are complete before merge/release.
mcp_tools:
  - docs_check_drift
  - docs_check_links
  - docs_check_cross_refs
  - docs_check_completeness
  - docs_release_gate
  - tapps_checklist
---

Run drift → links → cross_refs → completeness; add `docs_release_gate` for releases; finish with `tapps_checklist(task_type=documentation)`.
