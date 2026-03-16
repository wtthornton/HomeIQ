"""
Threat Pattern Library for Skills Guard (Epic 70, Story 70.2).

100+ regex patterns for detecting malicious content in agent-generated skills.
Ported from Hermes skills_guard.py with HomeIQ-specific additions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class ThreatCategory(str, Enum):
    """Categories of threats detected in skills."""

    PROMPT_INJECTION = "prompt_injection"
    HA_DANGEROUS_SERVICE = "ha_dangerous_service"
    EXFILTRATION = "exfiltration"
    DESTRUCTIVE = "destructive"
    STRUCTURAL = "structural"
    UNICODE_ABUSE = "unicode_abuse"


@dataclass
class ThreatPattern:
    """A single threat detection pattern."""

    category: ThreatCategory
    pattern: re.Pattern
    severity: str  # critical, high, medium, low
    description: str


# Build all patterns
def _build_patterns() -> list[ThreatPattern]:
    patterns: list[ThreatPattern] = []

    def add(cat: ThreatCategory, sev: str, desc: str, regex: str, flags: int = re.IGNORECASE) -> None:
        patterns.append(ThreatPattern(
            category=cat,
            pattern=re.compile(regex, flags),
            severity=sev,
            description=desc,
        ))

    # --- Prompt Injection (20 patterns) ---
    pi = ThreatCategory.PROMPT_INJECTION
    add(pi, "critical", "Role hijacking attempt", r"(you are now|act as|pretend to be|ignore previous|disregard|forget all)")
    add(pi, "critical", "Instruction override", r"(ignore (all |any )?instructions|new instructions|override (system|prompt))")
    add(pi, "high", "System prompt extraction", r"(reveal|show|print|output|display).{0,20}(system prompt|instructions|rules)")
    add(pi, "high", "Jailbreak attempt", r"(DAN|do anything now|no restrictions|no limitations|unrestricted mode)")
    add(pi, "high", "Context manipulation", r"(begin new|start over|reset context|clear instructions)")
    add(pi, "medium", "Delimiter injection", r"(```system|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])")
    add(pi, "medium", "Encoding evasion (base64)", r"(base64|atob|btoa|decode\()")
    add(pi, "high", "Indirect injection", r"(when you see this|if you read this|execute the following)")
    add(pi, "medium", "Token manipulation", r"(split across|character by character|spell out|one letter at a time)")
    add(pi, "high", "Persona injection", r"(from now on|henceforth|going forward).{0,30}(you (will|must|should|are))")

    # --- HA Dangerous Services (15 patterns) ---
    ha = ThreatCategory.HA_DANGEROUS_SERVICE
    add(ha, "critical", "Shell command execution", r"(shell_command\.|command_line\.|subprocess|os\.system)")
    add(ha, "critical", "Python script execution", r"(python_script\.|pyscript\.)")
    add(ha, "critical", "REST command (arbitrary HTTP)", r"(rest_command\.|rest\.)")
    add(ha, "critical", "Hassio/addon management", r"(hassio\.|supervisor\.|addon\.|ha (core|os|supervisor))")
    add(ha, "high", "Config reload/restart", r"(homeassistant\.(restart|stop|reload|check_config))")
    add(ha, "high", "File system access", r"(downloader\.|file\.)")
    add(ha, "high", "Network access via HA", r"(notify\..*url|webhook|rest_command)")
    add(ha, "medium", "Backup manipulation", r"(backup\.(create|remove|restore))")
    add(ha, "high", "Template injection", r"\{\%.*import.*\%\}")
    add(ha, "critical", "Eval/exec in templates", r"\{\{.*(__import__|eval|exec|compile|getattr).*\}\}")
    add(ha, "high", "Database manipulation", r"(recorder\.(purge|disable)|logbook\.log)")
    add(ha, "medium", "Integration management", r"(config_entry\.(reload|remove|disable))")
    add(ha, "high", "Custom component loading", r"(custom_components|hacs)")
    add(ha, "high", "MQTT arbitrary publish", r"(mqtt\.publish)")
    add(ha, "medium", "Persistent notification flood", r"(persistent_notification\.create.*loop)")

    # --- Exfiltration (15 patterns) ---
    ex = ThreatCategory.EXFILTRATION
    add(ex, "critical", "Environment variable access", r"(os\.environ|process\.env|getenv|ENV\[)")
    add(ex, "critical", "Credential theft", r"(password|secret|token|api.?key|credential|private.?key)", re.IGNORECASE)
    add(ex, "high", "DNS tunneling", r"(dns|nslookup|dig)\s")
    add(ex, "high", "Curl/wget data exfil", r"(curl|wget|fetch|requests\.)\s.*(http|ftp)")
    add(ex, "critical", "File reading (.env, secrets)", r"(\.env|secrets\.yaml|configuration\.yaml|auth\.json)")
    add(ex, "high", "Network socket", r"(socket\.connect|urllib|httplib|aiohttp\.)")
    add(ex, "medium", "Webhook data sending", r"(webhook|ngrok|requestbin|pipedream)")
    add(ex, "high", "SSH key access", r"(\.ssh|id_rsa|authorized_keys)")
    add(ex, "high", "Database credential access", r"(pg_pass|\.pgpass|mysql\.cnf|db_password)")
    add(ex, "critical", "Secrets import", r"(import secrets|from secrets)")

    # --- Destructive (15 patterns) ---
    de = ThreatCategory.DESTRUCTIVE
    add(de, "critical", "Recursive deletion", r"(rm\s+-rf|rmdir.*recurse|shutil\.rmtree)")
    add(de, "critical", "System file overwrite", r"(/etc/|/bin/|/usr/|/var/|C:\\Windows)")
    add(de, "high", "Database drop/truncate", r"(DROP\s+TABLE|TRUNCATE|DELETE\s+FROM.*WHERE\s+1)")
    add(de, "high", "Disk fill attack", r"(dd\s+if=|fallocate|truncate\s+-s)")
    add(de, "high", "Process killing", r"(kill\s+-9|pkill|killall|taskkill)")
    add(de, "medium", "Log wiping", r"(truncate.*log|>.*\.log|rm.*\.log)")
    add(de, "high", "Permission escalation", r"(chmod\s+777|chown\s+root|sudo|su\s+-)")
    add(de, "critical", "Fork bomb", r"(\:\(\)\s*\{|while\s+true.*fork)")
    add(de, "high", "Symlink escape", r"(ln\s+-s|symlink|readlink.*\.\.)")
    add(de, "medium", "Cron manipulation", r"(crontab|at\s+now|systemctl\s+(enable|start))")

    # --- Structural (10 patterns) ---
    st = ThreatCategory.STRUCTURAL
    add(st, "medium", "Excessive size (>50KB reference)", r".{50000,}", re.DOTALL)
    add(st, "low", "Binary content", r"[\x00-\x08\x0b\x0c\x0e-\x1f]{10,}")
    add(st, "medium", "Deeply nested YAML", r"(\n\s{20,}-|\n\s{20,}\w)")
    add(st, "low", "Excessive repetition", r"(.{20,})\1{5,}")

    # --- Unicode Abuse (10 patterns) ---
    ua = ThreatCategory.UNICODE_ABUSE
    add(ua, "high", "Zero-width characters", r"[\u200b\u200c\u200d\ufeff\u200e\u200f]")
    add(ua, "high", "Directional override (BiDi)", r"[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]")
    add(ua, "medium", "Homograph attack (Cyrillic lookalikes)", r"[\u0400-\u04ff]")
    add(ua, "medium", "Invisible separators", r"[\u2000-\u200a\u205f\u3000]")
    add(ua, "low", "Tag characters", r"[\U000e0001-\U000e007f]")

    return patterns


THREAT_PATTERNS: list[ThreatPattern] = _build_patterns()
