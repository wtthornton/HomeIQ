"""
Scan output extraction tests for the auto-fix pipeline.

Mirrors the extraction logic in scripts/auto-bugfix.ps1:
- Primary: content between <<<BUGS>>> and <<<END_BUGS>>>
- Fallback: JSON array [{...}] in raw output

See: docs/workflows/auto-bugfix-scan-format.md
"""

import json
import re
from typing import Any

import pytest


def extract_bugs_json(raw_output: str) -> str | None:
    """
    Extract bug list JSON from scan output. Matches scripts/auto-bugfix.ps1 logic.

    Returns the JSON string (content between markers or fallback array), or None if not found.
    """
    # Primary: content between <<<BUGS>>> and <<<END_BUGS>>>
    match = re.search(r"<<<BUGS>>>\s*([\s\S]*?)\s*<<<END_BUGS>>>", raw_output)
    if match:
        return match.group(1).strip()

    # Fallback: JSON array in raw output
    match = re.search(r"\[\s*\{[\s\S]*\}\s*\]", raw_output)
    if match:
        return match.group(0)

    return None


def parse_bugs(bugs_json: str) -> list[dict[str, Any]]:
    """
    Parse bug list JSON to list of dicts. Each bug has file, line, description, severity.
    """
    data = json.loads(bugs_json)
    if not isinstance(data, list):
        raise ValueError("Expected JSON array")
    return data


class TestScanOutputExtraction:
    """BUGS marker and fallback extraction tests."""

    def test_extract_via_bugs_markers(self) -> None:
        """Extract JSON between <<<BUGS>>> and <<<END_BUGS>>>."""
        raw = '''Some preamble text.
<<<BUGS>>>
[{"file": "src/foo.py", "line": 42, "description": "Bug here", "severity": "high"}]
<<<END_BUGS>>>
More text after.'''
        result = extract_bugs_json(raw)
        assert result is not None
        bugs = parse_bugs(result)
        assert len(bugs) == 1
        assert bugs[0]["file"] == "src/foo.py"
        assert bugs[0]["line"] == 42
        assert bugs[0]["description"] == "Bug here"
        assert bugs[0]["severity"] == "high"

    def test_extract_via_bugs_markers_with_whitespace(self) -> None:
        """Extract when markers have surrounding whitespace."""
        raw = "<<<BUGS>>>\n\n[{}]\n<<<END_BUGS>>>"
        result = extract_bugs_json(raw)
        assert result is not None
        assert parse_bugs(result) == [{}]

    def test_extract_via_fallback_array(self) -> None:
        """Fallback: extract JSON array when markers absent."""
        raw = 'Here is the list:\n[{"file":"a.py","line":1,"description":"x","severity":"low"}]'
        result = extract_bugs_json(raw)
        assert result is not None
        bugs = parse_bugs(result)
        assert len(bugs) == 1
        assert bugs[0]["file"] == "a.py"

    def test_extract_empty_list_via_markers(self) -> None:
        """Extract empty array between markers."""
        raw = "<<<BUGS>>>\n[]\n<<<END_BUGS>>>"
        result = extract_bugs_json(raw)
        assert result is not None
        assert parse_bugs(result) == []

    def test_no_extraction_when_no_json(self) -> None:
        """Return None when no parseable JSON present."""
        raw = "Just prose with no JSON or markers."
        assert extract_bugs_json(raw) is None

    def test_invalid_json_raises(self) -> None:
        """Invalid JSON raises on parse."""
        raw = "<<<BUGS>>>\n{invalid}\n<<<END_BUGS>>>"
        result = extract_bugs_json(raw)
        assert result is not None
        with pytest.raises(json.JSONDecodeError):
            parse_bugs(result)
