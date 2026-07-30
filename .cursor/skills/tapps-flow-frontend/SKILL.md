---
name: tapps-flow-frontend
description: >-
  Frontend work flow combining UX playbook and standard finish pipeline.
  Use when the task is primarily UI/UX implementation or accessibility.
mcp_tools:
  - tapps_session_start
  - tapps_domain_playbook
  - tapps_lookup_docs
  - tapps_quick_check
  - tapps_validate_changed
  - tapps_checklist
---

1. Invoke `/tapps-domain-frontend` steps 1-5, **or** run this shortcut:
   - `tapps_domain_playbook(domain="user-experience")`
   - `tapps_lookup_docs` for UI libraries in scope
2. `/tapps-finish-task` with `task_type=frontend`
3. Optional persona: agency-agents Frontend Developer (voice only; TappsMCP owns gates)
