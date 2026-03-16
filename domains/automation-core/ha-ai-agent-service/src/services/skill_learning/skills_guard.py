"""
Skills Guard — Security Scanner (Epic 70, Story 70.2).

Safety pair for skill learning. Every skill created or recalled is scanned
for malicious patterns before use. Ported from Hermes skills_guard.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .threat_patterns import THREAT_PATTERNS, ThreatCategory, ThreatPattern

logger = logging.getLogger(__name__)


@dataclass
class ScanFinding:
    """A single threat finding from a skill scan."""

    category: str
    severity: str
    description: str
    matched_text: str


@dataclass
class ScanResult:
    """Result of a skill security scan."""

    safe: bool
    findings: list[ScanFinding] = field(default_factory=list)
    scan_count: int = 0  # Number of patterns checked

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "critical")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "high")

    @property
    def verdict(self) -> str:
        if self.critical_count > 0:
            return "BLOCKED"
        if self.high_count > 0:
            return "WARNING"
        if self.findings:
            return "CAUTION"
        return "CLEAN"


class SkillsGuard:
    """Security scanner for agent-generated skills.

    Runs synchronously before skill storage (block on fail) and
    asynchronously on skill recall (warn on fail, exclude from context).
    """

    def __init__(self, patterns: list[ThreatPattern] | None = None):
        self.patterns = patterns or THREAT_PATTERNS

    def scan(self, content: str, name: str = "unnamed") -> ScanResult:
        """Scan skill content for threats.

        Args:
            content: The skill content (YAML frontmatter + markdown body).
            name: Skill name for logging.

        Returns:
            ScanResult with verdict and findings.
        """
        findings: list[ScanFinding] = []

        for pattern in self.patterns:
            matches = pattern.pattern.findall(content)
            if matches:
                matched_text = str(matches[0])[:100] if matches else ""
                findings.append(ScanFinding(
                    category=pattern.category.value,
                    severity=pattern.severity,
                    description=pattern.description,
                    matched_text=matched_text,
                ))

        safe = not any(f.severity in ("critical", "high") for f in findings)

        result = ScanResult(
            safe=safe,
            findings=findings,
            scan_count=len(self.patterns),
        )

        if not safe:
            logger.warning(
                "Skills Guard BLOCKED skill '%s': %d findings (%d critical, %d high)",
                name,
                len(findings),
                result.critical_count,
                result.high_count,
            )
        elif findings:
            logger.info(
                "Skills Guard CAUTION on skill '%s': %d low/medium findings",
                name, len(findings),
            )

        return result

    def is_safe_for_storage(self, content: str, name: str = "unnamed") -> bool:
        """Quick check: is this skill safe to store?

        Blocks on any critical or high severity finding.
        """
        result = self.scan(content, name)
        return result.safe

    def filter_safe_skills(
        self,
        skills: list[dict],
        content_key: str = "body",
        name_key: str = "name",
    ) -> list[dict]:
        """Filter a list of skills, excluding unsafe ones.

        Used during skill recall to exclude flagged skills from context.
        """
        safe_skills = []
        for skill in skills:
            content = skill.get(content_key, "")
            name = skill.get(name_key, "unnamed")
            result = self.scan(content, name)
            if result.safe:
                safe_skills.append(skill)
            else:
                logger.warning(
                    "Excluding unsafe skill '%s' from context: %s",
                    name, result.verdict,
                )
        return safe_skills
