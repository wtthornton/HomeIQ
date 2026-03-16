---
name: tapps-validate
user-invocable: true
model: claude-haiku-4-5-20251001
description: Validate all changed files meet quality thresholds before declaring work complete.
allowed-tools: mcp__tapps-mcp__tapps_validate_changed
disable-model-invocation: true
---

Validate changed files using TappsMCP:

1. Identify the Python files you changed in this session (from git status or your edit history)
2. Call `mcp__tapps-mcp__tapps_validate_changed` with explicit `file_paths` (comma-separated) scoped to only those files. **Never call without `file_paths`** - auto-detect scans all git-changed files and can be very slow in large repos. Default is quick mode; only use `quick=false` as a last resort (pre-release, security audit).
3. Display each file with its score and pass/fail status
4. If any file fails, list it with the top issue preventing it from passing
5. Confirm explicitly when all changed files pass before declaring work done
6. If any files fail, do NOT mark the task as complete
