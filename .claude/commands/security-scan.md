# Security Scan Command

Scan code for security vulnerabilities and provide remediation recommendations.

## Usage

```
@security-scan <file-path>
```

Or with natural language:
```
Scan src/api/auth.py for security issues
Check for vulnerabilities in src/utils/helpers.py
Audit the security of the authentication module
```

## What It Does

1. **Scans Code**: Analyzes code for security vulnerabilities
2. **Checks Dependencies**: Audits dependencies for known vulnerabilities
3. **Identifies Issues**: Finds security issues and weaknesses
4. **Provides Fixes**: Recommends specific security fixes
5. **Prioritizes**: Ranks issues by severity

## Examples

```
@security-scan src/api/auth.py
@security-scan src/utils/helpers.py
@security-scan . --dependencies
```

## Features

- **Vulnerability Detection**: Finds common security issues
- **Dependency Audit**: Checks for vulnerable dependencies
- **Severity Ranking**: Prioritizes issues by severity
- **Fix Recommendations**: Provides specific fixes
- **Best Practices**: Suggests security best practices

## Output

- Security scan report
- Vulnerability list with severity
- Fix recommendations
- Dependency audit results

## Integration

- **Cursor**: Use `@reviewer *security-scan <file>` (Cursor Skill)
- **Claude Desktop**: Use `@security-scan <file>` (this command)
- **CLI**: Use `tapps-agents reviewer security-scan <file>`

