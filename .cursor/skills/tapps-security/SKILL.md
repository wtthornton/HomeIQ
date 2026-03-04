---
name: tapps-security
description: >-
  Run a comprehensive security audit on a Python file including vulnerability scanning,
  dependency CVE checks, and expert security consultation.
mcp_tools:
  - tapps_security_scan
  - tapps_dependency_scan
  - tapps_consult_expert
---

Run a comprehensive security audit using TappsMCP:

1. Call `tapps_security_scan` on the target file to detect vulnerabilities
2. Call `tapps_dependency_scan` to check for known CVEs in dependencies
3. Call `tapps_consult_expert` with domain "security" for additional guidance
4. Group all findings by severity (critical, high, medium, low)
5. Suggest a prioritized fix order starting with the highest-severity issues
