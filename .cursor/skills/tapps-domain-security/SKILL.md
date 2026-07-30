---
name: tapps-domain-security
description: >-
  Security-focused TAPPS workflow: playbook, library docs, security scan, and CVE check. Use when implementing auth, secrets, input validation, or pre-release security passes.
mcp_tools:
  - tapps_session_start
  - tapps_domain_playbook
  - tapps_lookup_docs
  - tapps_quick_check
  - tapps_validate_changed
  - tapps_checklist
  - tapps_security_scan
  - tapps_dependency_scan
---

Domain playbook workflow — same quality gate as the standard TAPPS pipeline.

1. **Session bootstrap.** Call `session_start()` if not already called this session.
2. **Load playbook.** Call `domain_playbook(domain="security")` (or read bundled checklist from the response). Follow its workflow and checklist.
3. **Library docs.** For each entry in `lookup_hints`, call `lookup_docs(library=..., topic=...)` before using those APIs.
4. **Domain tools.** Run the tools listed in `recommended_tools` on changed files in scope.
5. **Edit loop.** After each Python file change, call `quick_check(file_path=...)`.
4b. Run `security_scan` on sensitive changed files.
4c. Run `dependency_scan` when lockfiles or dependencies changed.
6. **Close out.** Invoke `/tapps-finish-task` with the task_type=security. Do not declare done without validate + checklist.

