---
name: tapps-gate
user-invocable: true
model: claude-haiku-4-5-20251001
description: Run a quality gate check and report pass/fail with blocking issues.
allowed-tools: mcp__tapps-mcp__tapps_quality_gate
argument-hint: "[file-path]"
disable-model-invocation: true
---

Run a quality gate check using TappsMCP:

1. Call `mcp__tapps-mcp__tapps_quality_gate` with the current project
2. Display the overall pass/fail result clearly
3. List each failing criterion with its actual vs. required value
4. If the gate fails, list the minimum changes required to pass
5. Do not declare work complete if the gate has not passed
