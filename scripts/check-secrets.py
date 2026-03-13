#!/usr/bin/env python3
"""Pre-commit hook: detect hardcoded secrets in staged files.

Scans for patterns like VITE_*_KEY=<value>, API keys, tokens, and
passwords that should never be committed. Exits non-zero if any
secret-like patterns are found.

Usage:
    python scripts/check-secrets.py [file ...]

Files are passed by pre-commit. If no files are given, exits 0.
"""

import re
import sys
from pathlib import Path

# Patterns that indicate a hardcoded secret (value present after =)
SECRET_PATTERNS: list[tuple[re.Pattern, str]] = [
    # VITE env vars with actual values (not empty or placeholder)
    (
        re.compile(r"""VITE_\w*(?:KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['"]?[A-Za-z0-9_\-/.]{8,}""", re.IGNORECASE),
        "VITE_ secret env var with hardcoded value",
    ),
    # Generic API key assignments (not in comments)
    (
        re.compile(r"""(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['"][A-Za-z0-9_\-/.]{16,}['"]""", re.IGNORECASE),
        "Hardcoded API key or secret",
    ),
    # Bearer tokens in code (not test files)
    (
        re.compile(r"""['"]Bearer\s+[A-Za-z0-9_\-/.]{20,}['"]"""),
        "Hardcoded Bearer token",
    ),
    # AWS-style keys
    (
        re.compile(r"""(?:AKIA|ASIA)[A-Z0-9]{16}"""),
        "AWS access key",
    ),
    # Private key blocks
    (
        re.compile(r"""-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----"""),
        "Private key",
    ),
]

# Files/patterns to always skip (in addition to pre-commit exclude)
SKIP_PATTERNS = {
    ".env.example",
    ".env.template",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}


def check_file(filepath: str) -> list[tuple[int, str, str]]:
    """Check a single file for secret patterns.

    Returns list of (line_number, line_content, reason) tuples.
    """
    path = Path(filepath)

    # Skip known safe files
    if path.name in SKIP_PATTERNS:
        return []
    if path.suffix in {".lock", ".svg", ".png", ".jpg", ".ico"}:
        return []

    findings: list[tuple[int, str, str]] = []
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeDecodeError):
        return []

    for line_no, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        # Skip comments
        if stripped.startswith(("#", "//", "*", "/*")):
            continue
        for pattern, reason in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append((line_no, line.rstrip(), reason))
                break  # One finding per line is enough

    return findings


def main() -> int:
    files = sys.argv[1:]
    if not files:
        return 0

    total_findings = 0
    for filepath in files:
        findings = check_file(filepath)
        for line_no, line, reason in findings:
            print(f"SECRET DETECTED: {filepath}:{line_no}: {reason}")
            print(f"  {line[:120]}")
            total_findings += 1

    if total_findings:
        print(f"\n{total_findings} potential secret(s) found. "
              "Remove hardcoded values and use environment variables instead.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
