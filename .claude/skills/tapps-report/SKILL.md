---
name: tapps-report
user-invocable: true
model: claude-haiku-4-5-20251001
description: >-
  Generate a quality report across Python files in the project.
  Scores multiple files and presents an aggregate summary.
allowed-tools: mcp__tapps-mcp__tapps_report
argument-hint: "[file-path or empty for project-wide]"
---

Generate a quality report using TappsMCP:

1. Call `mcp__tapps-mcp__tapps_report` with an optional file path
2. If no file path, a project-wide report scores up to 20 files
3. Present results in a table: file | score | pass/fail | top issue
4. Highlight any files scoring below the quality gate threshold
5. Suggest priority fixes for the lowest-scoring files
