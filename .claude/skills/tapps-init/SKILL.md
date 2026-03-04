---
name: tapps-init
description: >-
  Bootstrap TappsMCP in a project. Creates AGENTS.md, TECH_STACK.md,
  platform rules, hooks, agents, skills, and MCP config.
allowed-tools: mcp__tapps-mcp__tapps_init, mcp__tapps-mcp__tapps_doctor
argument-hint: "[project-root]"
---

Bootstrap TappsMCP in a new or existing project:

1. Call `mcp__tapps-mcp__tapps_init` to run the full bootstrap pipeline
2. Review the created files (AGENTS.md, TECH_STACK.md, platform rules, hooks)
3. If any issues are reported, call `mcp__tapps-mcp__tapps_doctor` to diagnose
4. Verify that `.claude/settings.json` has MCP tool auto-approval rules
5. Confirm the project is ready for the TappsMCP quality workflow
