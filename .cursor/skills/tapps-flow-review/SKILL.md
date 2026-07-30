---
name: tapps-flow-review
description: >-
  QA/review flow: parallel review pipeline or single-file review ending in checklist.
  Use when reviewing PRs, audit findings, or validating another agent's changes.
mcp_tools:
  - tapps_validate_changed
  - tapps_checklist
  - tapps_security_scan
---

Prefer `/tapps-review-pipeline` for multiple Python files. Otherwise:

1. `tapps_security_scan` + `tapps_quick_check` on targets
2. `/tapps-finish-task` with `task_type=review` or `qa`
