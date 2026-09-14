---
name: tapps-security
user-invocable: true
model: claude-sonnet-4-6
description: >-
  Run a comprehensive security audit including vulnerability scanning
  and dependency CVE checks. Use when reviewing security-sensitive changes,
  before a security audit, or before a production release.
allowed-tools: >-
  mcp__nlt-build__tapps_security_scan
  mcp__nlt-build__tapps_dependency_scan
argument-hint: "[file-path]"
---
<!-- upgrade-policy: overwrite. tapps_upgrade replaces this file wholesale on every run and local edits are lost (tapps_init leaves an existing copy alone; upgrade does not). Fold the change upstream into the platform template, or pin the whole directory with an upgrade_skip_files token. -->

Run a comprehensive security audit using TappsMCP:

1. Call `mcp__nlt-build__tapps_security_scan` on the target file to detect vulnerabilities
2. Call `mcp__nlt-build__tapps_dependency_scan` to check for known CVEs in dependencies
3. Group all findings by severity (critical, high, medium, low)
4. Suggest a prioritized fix order starting with the highest-severity issues
