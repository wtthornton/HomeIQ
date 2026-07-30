---
name: tapps-docs-generate
description: >-
  Quick doc generation: README, llms.txt, changelog. Use for a minimal
  generate pass; prefer tapps-docs-bootstrap for new projects.
allowed-tools: >-
  mcp__nlt-project-docs__docs_generate_readme
  mcp__nlt-project-docs__docs_generate_llms_txt
  mcp__nlt-project-docs__docs_generate_changelog
  mcp__nlt-project-docs__docs_generate_runbook
  mcp__nlt-project-docs__docs_generate_postmortem
---

Generate documentation artifacts:

1. `mcp__nlt-project-docs__docs_generate_readme(merge=true)`
2. `mcp__nlt-project-docs__docs_generate_llms_txt(mode="compact")`
3. `mcp__nlt-project-docs__docs_generate_changelog` when git tags exist
4. For operational docs: `docs_generate_runbook` / `docs_generate_postmortem` with structured fields
