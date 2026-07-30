---
name: tapps-docs-bootstrap
description: >-
  Bootstrap README, CONTRIBUTING, onboarding for new projects. Use when
  creating a README, onboarding guide, or initial doc scaffold.
mcp_tools:
  - docs_session_start
  - docs_module_map
  - docs_generate_readme
  - docs_generate_contributing
  - docs_generate_onboarding
  - docs_check_completeness
---

1. `docs_session_start` → `docs_module_map` → `docs_generate_readme(merge=true)` → `docs_generate_contributing` → `docs_generate_onboarding` → `docs_check_completeness` (target ≥ 80).
