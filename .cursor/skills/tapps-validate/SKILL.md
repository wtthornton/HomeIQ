---
name: tapps-validate
description: Validate all changed files meet quality thresholds before declaring work complete.
mcp_tools:
  - tapps_validate_changed
---

Validate all changed files using TappsMCP:

1. Call `tapps_validate_changed` to get the list of changed files and their scores
2. Display each file with its score and pass/fail status
3. If any file fails, list it with the top issue preventing it from passing
4. Confirm explicitly when all changed files pass before declaring work done
5. If any files fail, do NOT mark the task as complete
