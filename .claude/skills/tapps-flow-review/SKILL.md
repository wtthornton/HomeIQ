---
name: tapps-flow-review
user-invocable: true
model: claude-sonnet-4-6
description: >-
  QA/review flow: parallel review pipeline or single-file review ending in checklist.
  Use when reviewing PRs, audit findings, or validating another agent's changes.
allowed-tools: mcp__nlt-build__tapps_validate_changed mcp__nlt-build__tapps_checklist mcp__nlt-build__tapps_security_scan
argument-hint: "[file paths]"
---
<!-- upgrade-policy: overwrite. tapps_upgrade replaces this file wholesale on every run and local edits are lost (tapps_init leaves an existing copy alone; upgrade does not). Fold the change upstream into the platform template, or pin the whole directory with an upgrade_skip_files token. -->

Prefer `/tapps-review-pipeline` for multiple Python files. Otherwise:

1. `tapps_security_scan` + `tapps_quick_check` on targets
2. `/tapps-finish-task` with `task_type=review` or `qa`
