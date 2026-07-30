---
name: tapps-flow-develop
description: >-
  Standard feature/bugfix development flow via the shared TAPPS pipeline.
  Use when starting daily implementation work and you want session start,
  lookup docs, quick_check loop, and finish-task without a domain specialist.
mcp_tools:
  - tapps_session_start
  - tapps_lookup_docs
  - tapps_quick_check
  - tapps_validate_changed
  - tapps_checklist
---

1. `tapps_session_start()`
2. `tapps_lookup_docs` before each external library API
3. Edit loop: `tapps_quick_check` after Python edits
4. `/tapps-finish-task` with `task_type=feature` or `bugfix`
