<!-- tapps-generated: v1.9.0 -->
# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| latest  | Yes       |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it
responsibly:

1. **Do NOT open a public issue.** Security vulnerabilities should be reported
   privately.
2. Use [GitHub's private vulnerability reporting](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing/privately-reporting-a-security-vulnerability)
   to submit your report.
3. Include:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

## Response Timeline

- **Acknowledgment:** Within 48 hours of report
- **Assessment:** Within 1 week
- **Fix or mitigation:** Within 2 weeks for critical issues

## Security Measures

This project uses automated security scanning:

- **Bandit** — static analysis for common security issues in Python
- **Secret scanning** — detection of hardcoded API keys, tokens, and passwords
- **pip-audit** — dependency vulnerability scanning against the PyPI advisory database
- **CodeQL** — GitHub's semantic code analysis engine
- **Dependabot** — automated dependency updates with grouped security patches

## Scope

This policy applies to the latest release and the main development branch.
Older versions receive security patches on a best-effort basis.
