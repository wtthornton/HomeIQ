---
name: tapps-init
description: >-
  Bootstrap TappsMCP in a project. Creates AGENTS.md, TECH_STACK.md,
  platform rules, hooks, agents, skills, and MCP config.
mcp_tools:
  - tapps_init
  - tapps_doctor
---

Bootstrap TappsMCP in a new or existing project:

1. Call `tapps_init` to run the full bootstrap pipeline
2. Review the created files (AGENTS.md, TECH_STACK.md, platform rules, hooks)
3. If any issues are reported, call `tapps_doctor` to diagnose
4. Verify that MCP config has tool auto-approval rules
5. Confirm the project is ready for the TappsMCP quality workflow
