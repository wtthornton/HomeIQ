---
name: tapps-domain-security
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Security-focused TAPPS workflow: playbook, library docs, security scan, and CVE check. Use when implementing auth, secrets, input validation, or pre-release security passes.
allowed-tools: mcp__nlt-build__tapps_session_start mcp__nlt-build__tapps_domain_playbook mcp__nlt-build__tapps_lookup_docs mcp__nlt-build__tapps_quick_check mcp__nlt-build__tapps_validate_changed mcp__nlt-build__tapps_checklist mcp__nlt-build__tapps_security_scan mcp__nlt-build__tapps_dependency_scan
argument-hint: "[file-path or scope]"
---

Domain playbook workflow — same quality gate as the standard TAPPS pipeline.

1. **Session bootstrap.** Call `tapps_session_start()` if not already called this session.
2. **Load playbook.** Call `tapps_domain_playbook(domain="security")` (or read bundled checklist from the response). Follow its workflow and checklist.
3. **Library docs.** For each entry in `lookup_hints`, call `tapps_lookup_docs(library=..., topic=...)` before using those APIs.
4. **Domain tools.** Run the tools listed in `recommended_tools` on changed files in scope.
5. **Edit loop.** After each Python file change, call `tapps_quick_check(file_path=...)`.
4b. Run `tapps_security_scan` on sensitive changed files.
4c. Run `tapps_dependency_scan` when lockfiles or dependencies changed.
6. **Close out.** Invoke `/tapps-finish-task` with the task_type=security. Do not declare done without validate + checklist.

