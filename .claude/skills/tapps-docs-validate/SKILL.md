---
name: tapps-docs-validate
description: >-
  Validate documentation quality. Checks drift, freshness, links, and
  Diataxis balance. Use for a lighter validation pass than tapps-docs-finish-task.
allowed-tools: >-
  mcp__nlt-project-docs__docs_check_drift
  mcp__nlt-project-docs__docs_check_freshness
  mcp__nlt-project-docs__docs_check_links
  mcp__nlt-project-docs__docs_check_diataxis
---

Validate documentation quality across the project:

1. `mcp__nlt-project-docs__docs_check_drift`
2. `mcp__nlt-project-docs__docs_check_freshness`
3. `mcp__nlt-project-docs__docs_check_links`
4. `mcp__nlt-project-docs__docs_check_diataxis`
5. Present pass/fail with specific fixes
