---
name: tapps-docs-refresh
description: >-
  Full documentation refresh workflow (cross-refs, API, diagrams, validation).
  Use when refreshing project docs, auditing doc health, or pre-release doc pass.
mcp_tools:
  - docs_session_start
  - docs_check_cross_refs
  - docs_check_links
  - docs_generate_doc_index
  - docs_generate_purpose
  - docs_generate_onboarding
  - docs_generate_llms_txt
  - docs_generate_api
  - docs_generate_architecture
  - docs_generate_interactive_diagrams
  - docs_check_completeness
  - docs_check_freshness
  - docs_check_drift
  - docs_check_diataxis
  - docs_check_style
---

Run phases from `docs/tutorials/05-docs-refresh-workflow.md`: navigation → narrative → API/diagrams → verification (completeness ≥ 98, cross-refs ≥ 90) → optional style pass. Exclude `docs/archive/**`.
