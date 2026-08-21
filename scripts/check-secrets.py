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
        re.compile(
            r"""VITE_\w*(?:KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['"]?[A-Za-z0-9_\-/.]{8,}""",
            re.IGNORECASE,
        ),
        "VITE_ secret env var with hardcoded value",
    ),
    # Generic API key assignments (not in comments)
    (
        re.compile(
            r"""(?:api[_-]?key|apikey|secret[_-]?key)\s*[:=]\s*['"][A-Za-z0-9_\-/.]{16,}['"]""",
            re.IGNORECASE,
        ),
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
    # Password assignments carrying a real value.
    #
    # Added after a plaintext MQTT broker password sat committed for nine
    # months and this scanner reported the file CLEAN: the generic rule above
    # only matches keys literally named api_key/apikey/secret_key, and the
    # value was 14 characters against its 16-character floor. Two independent
    # reasons to miss it. A gate blind to the thing it is supposed to catch
    # reads as coverage while providing none (TAP-6399).
    #
    # Placeholders are excluded by PLACEHOLDER_VALUES rather than by length,
    # because real passwords are often short and placeholders often long.
    (
        re.compile(
            r"""(?:password|passwd|pwd)['\"]?\s*[:=]\s*['\"](?![$&])[^'\"]{4,}['\"]""",
            re.IGNORECASE,
        ),
        "Hardcoded password",
    ),
    # The rule above requires a quoted value, which is the shape the committed
    # broker config used. It cannot see the bare form:
    #     MQTT_PASSWORD=Zt7pQm4wLx
    # and that is not hypothetical — admin-api's config writer emits exactly
    # `f"{key}={value}\n"` into a read-write bind mount, so a credential written
    # back through it would land in the one shape the scanner missed.
    #
    # Restricted to config-shaped files by _is_config_file, because unquoted
    # matching in source code produces nonsense: `password=None`, `password: str`
    # and `password = get_password()` are all four-plus characters and none is a
    # secret.
    (
        re.compile(
            r"""(?:password|passwd|pwd)\s*[:=]\s*(?![$&{'\"])([^\s'\"#]{4,})""",
            re.IGNORECASE,
        ),
        "Hardcoded password (unquoted)",
    ),
]
# The `(?![$&])` above rejects a value that is a variable reference rather than
# a literal: PGPASSWORD="$TEST_PASSWORD" names a secret, it does not contain one.

# Substrings that mark a value as a placeholder rather than a live secret.
# Checked case-insensitively against the matched line.
PLACEHOLDER_VALUES = (
    "replace-with",
    "replace_with",
    "your-",
    "your_",
    "<your",
    "changeme",
    "change-me",
    "example",
    "placeholder",
    "dummy",
    "xxxx",
    "****",
    "${",
    "{{",
    "os.getenv",
    "os.environ",
    "process.env",
)

# Judged against the CAPTURED VALUE of the unquoted rule, by exact match — never
# as a substring of the line.
#
# Both properties are load-bearing, and getting either wrong is a silent
# weakening rather than a visible failure:
#
#   * Shared with the quoted rule, "undefined" silenced
#     `PASSWORD = "s3cretValue"  # undefined behavior here`.
#   * Matched as a substring, "=false" silenced `DB_PASSWORD=Falsetto99xyz`,
#     "=none" silenced `Nonesuch7781`, and "=true" silenced `Truebeliever42` —
#     a bypass any real credential could fall into by accident, in exactly the
#     file type this rule exists to cover.
UNQUOTED_NON_VALUES = frozenset(
    {"none", "null", "true", "false", "undefined", "str", "bool", "int", "nil", "empty"}
)

# Files/patterns to always skip (in addition to pre-commit exclude)
SKIP_PATTERNS = {
    # This scanner's own test corpus. It necessarily contains one live-looking
    # example of every pattern the scanner detects — that is what makes it a
    # test of a detector rather than a test that nothing matches. Without this
    # entry the hook blocks every commit that touches those vectors.
    "test_check_secrets.py",
    ".env.example",
    ".env.template",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
}


def _is_config_file(path: Path) -> bool:
    """True for files where a bare `KEY=value` line carries a real value.

    Unquoted matching is only meaningful here. In source code the same shape is
    almost always something else — a default, a type annotation, a call.
    """
    if path.suffix.lower() in {".env", ".ini", ".cfg", ".conf", ".properties"}:
        return True
    name = path.name.lower()
    return name.startswith(".env") or ".env." in name or name.startswith("env.")


def _is_test_artifact(path: Path) -> bool:
    """True for test files, where a password literal is fixture data.

    Scoped to the password rule. Test suites legitimately hand literal values
    to a fixture, and a hook that fires on every one of them gets switched off —
    which leaves the repo with no scanner at all, the outcome this rule exists
    to prevent. The stricter rules (API key, bearer, AWS, private key) still
    apply to test files.
    """
    name = path.name.lower()
    parts = {part.lower() for part in path.parts}
    return (
        "tests" in parts
        or "test" in parts
        or "__tests__" in parts
        or name.startswith("test")
        or name == "conftest.py"
        or "_test." in name
        or ".test." in name
        or ".spec." in name
    )


def _is_placeholder(line: str) -> bool:
    """True when a password-shaped line carries a template value, not a secret.

    A scanner that fires on every `.env.example` gets switched off, which is how
    a repo ends up with no scanner at all.
    """
    lowered = line.lower()
    return any(marker in lowered for marker in PLACEHOLDER_VALUES)


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
            if not pattern.search(line):
                continue
            # Placeholder filtering applies to the password rule alone. Applied
            # to every rule it suppressed real findings, because marker words
            # like "example" appear inside legitimate secret shapes such as
            # AKIAIOSFODNN7EXAMPLE.
            if reason.startswith("Hardcoded password"):
                if _is_placeholder(line) or _is_test_artifact(path):
                    continue
                if reason.endswith("(unquoted)"):
                    if not _is_config_file(path):
                        continue
                    value = pattern.search(line).group(1)
                    if value.lower().rstrip(",;") in UNQUOTED_NON_VALUES:
                        continue
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
        print(
            f"\n{total_findings} potential secret(s) found. "
            "Remove hardcoded values and use environment variables instead."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
