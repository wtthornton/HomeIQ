"""
Threat Pattern Library for Skills Guard (Epic 70, Story 70.2).

100+ regex patterns across 10 threat categories for detecting malicious content
in agent-generated skills. Ported from Hermes skills_guard.py with
HomeIQ-specific additions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ThreatCategory(StrEnum):
    """Categories of threats detected in skills."""

    PROMPT_INJECTION = "prompt_injection"
    HA_DANGEROUS_SERVICE = "ha_dangerous_service"
    EXFILTRATION = "exfiltration"
    DESTRUCTIVE = "destructive"
    PERSISTENCE = "persistence"
    NETWORK = "network"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SUPPLY_CHAIN = "supply_chain"
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
        patterns.append(
            ThreatPattern(
                category=cat,
                pattern=re.compile(regex, flags),
                severity=sev,
                description=desc,
            )
        )

    # --- Prompt Injection (20 patterns) ---
    pi = ThreatCategory.PROMPT_INJECTION
    add(
        pi,
        "critical",
        "Role hijacking attempt",
        r"(you are now|act as|pretend to be|ignore previous|disregard|forget all)",
    )
    add(
        pi,
        "critical",
        "Instruction override",
        r"(ignore (all |any )?instructions|new instructions|override (system|prompt))",
    )
    add(
        pi,
        "high",
        "System prompt extraction",
        r"(reveal|show|print|output|display).{0,20}(system prompt|instructions|rules)",
    )
    add(pi, "high", "Jailbreak attempt", r"(DAN|do anything now|no restrictions|no limitations|unrestricted mode)")
    add(pi, "high", "Context manipulation", r"(begin new|start over|reset context|clear instructions)")
    add(pi, "medium", "Delimiter injection", r"(```system|<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\])")
    add(pi, "medium", "Encoding evasion (base64)", r"(base64|atob|btoa|decode\()")
    add(pi, "high", "Indirect injection", r"(when you see this|if you read this|execute the following)")
    add(pi, "medium", "Token manipulation", r"(split across|character by character|spell out|one letter at a time)")
    add(pi, "high", "Persona injection", r"(from now on|henceforth|going forward).{0,30}(you (will|must|should|are))")
    add(pi, "high", "Developer/debug mode escalation", r"(developer mode|debug mode|god mode|admin mode|root mode)")
    add(
        pi,
        "critical",
        "Safety guardrail removal",
        r"(bypass|disable|turn off|remove|skip).{0,25}(safety|filter|guardrail|moderation|content policy)",
    )
    add(
        pi,
        "medium",
        "Hypothetical framing jailbreak",
        r"(hypothetically|purely fictional|for research purposes only|this is only a test).{0,40}"
        r"(how (to|would)|explain|describe)",
    )
    add(
        pi,
        "high",
        "Prompt leak via repeat/translate",
        r"(repeat|translate|summarize|echo).{0,25}(everything above|the text above|your (prompt|instructions))",
    )
    add(
        pi,
        "medium",
        "Tool invocation injection",
        r"(call the .{0,25}tool|invoke .{0,25}tool|\"?(tool_call|function_call)\"?\s*[:=])",
    )
    add(
        pi,
        "high",
        "Memory/skill poisoning",
        r"(remember (this|that)|store the following|save (this )?to (memory|your skills)).{0,40}"
        r"(always|never|whenever)",
    )
    add(
        pi,
        "medium",
        "Chain-of-thought extraction",
        r"(show|reveal|print|dump).{0,25}(chain of thought|scratchpad|hidden (reasoning|thoughts))",
    )
    add(pi, "high", "Instruction smuggled in HTML comment", r"<!--.{0,60}(ignore|instruction|system).{0,60}-->")
    add(pi, "medium", "Escape-sequence obfuscation", r"((\\x[0-9a-fA-F]{2}){4,}|(\\u[0-9a-fA-F]{4}){4,})")
    add(
        pi,
        "high",
        "Authority impersonation",
        r"(as (an? )?(administrator|owner|developer|openai|anthropic)|i am the (owner|admin|developer))",
    )

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
    add(
        ex,
        "critical",
        "Cloud metadata endpoint access",
        r"(169\.254\.169\.254|metadata\.google\.internal|/latest/meta-data)",
    )
    add(ex, "high", "Clipboard/keystroke capture", r"(pyperclip|xclip|pynput|keyboard\.(record|on_press))")
    add(ex, "high", "Screen capture", r"(ImageGrab|screencapture|scrot\b|pyautogui\.screenshot)")
    add(ex, "high", "Email/SMTP data sending", r"(smtplib|sendmail\b|smtp\.[a-z0-9-]+\.[a-z]{2,}|mailto:)")
    add(ex, "high", "Paste-site upload", r"(pastebin|gist\.github|transfer\.sh|0x0\.st|file\.io)")

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
    add(de, "critical", "Filesystem wipe/format", r"(mkfs(\.\w+)?\b|fdisk\b|diskpart\b|shred\s+-)")
    add(
        de,
        "high",
        "Git history destruction",
        r"git\s+(push\s+--force|reset\s+--hard|clean\s+-[a-z]*f|filter-branch)",
    )
    add(
        de,
        "high",
        "Container/orchestrator teardown",
        r"(docker\s+(rm\b|kill\b|system\s+prune)|kubectl\s+delete|docker-compose\s+down\s+-v)",
    )
    add(
        de,
        "critical",
        "Host security controls disabled",
        r"(iptables\s+-F|ufw\s+disable|setenforce\s+0|systemctl\s+(stop|disable)\s+(firewalld|apparmor))",
    )
    add(de, "high", "Bootloader/kernel tampering", r"(grub-install|update-grub|/boot/|modprobe\s+-r)")

    # --- Structural (10 patterns) ---
    st = ThreatCategory.STRUCTURAL
    add(st, "medium", "Excessive size (>50KB reference)", r".{50000,}", re.DOTALL)
    add(st, "low", "Binary content", r"[\x00-\x08\x0b\x0c\x0e-\x1f]{10,}")
    add(st, "medium", "Deeply nested YAML", r"(\n\s{20,}-|\n\s{20,}\w)")
    add(st, "low", "Excessive repetition", r"(.{20,})\1{5,}")
    add(st, "medium", "Excessive line length", r"[^\n]{5000,}")
    add(st, "medium", "Link flooding", r"(https?://\S+\s+){20,}")
    add(st, "high", "Embedded HTML/script markup", r"<\s*(script|iframe|object|embed)\b")
    add(st, "high", "Inline base64 data URI payload", r"data:[a-z]+/[a-z0-9.+-]+;base64,")
    add(st, "medium", "YAML alias flooding (billion laughs)", r"(\*\w+[,\s]){20,}")
    add(st, "medium", "Multiple frontmatter blocks", r"(\n---[ \t]*\n){3,}")

    # --- Unicode Abuse (10 patterns) ---
    ua = ThreatCategory.UNICODE_ABUSE
    add(ua, "high", "Zero-width characters", r"[\u200b\u200c\u200d\ufeff\u200e\u200f]")
    add(ua, "high", "Directional override (BiDi)", r"[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]")
    add(ua, "medium", "Homograph attack (Cyrillic lookalikes)", r"[\u0400-\u04ff]")
    add(ua, "medium", "Invisible separators", r"[\u2000-\u200a\u205f\u3000]")
    add(ua, "low", "Tag characters", r"[\U000e0001-\U000e007f]")
    add(ua, "medium", "Soft hyphen / invisible formatting", r"[\u00ad\u034f\u061c\u180e]")
    add(ua, "medium", "Variation-selector steganography", r"[\ufe00-\ufe0f]{4,}")
    add(ua, "medium", "Combining-mark abuse (Zalgo)", r"[\u0300-\u036f]{5,}")
    add(ua, "medium", "Fullwidth lookalike characters", r"[\uff01-\uff5e]{3,}")
    add(ua, "medium", "Mathematical alphanumeric obfuscation", r"[\U0001d400-\U0001d7ff]")

    # --- Persistence (10 patterns) ---
    pe = ThreatCategory.PERSISTENCE
    add(pe, "high", "Cron persistence", r"(@reboot|/etc/cron\.[a-z]+|crontab\s+-e)")
    add(pe, "high", "Systemd unit installation", r"(/etc/systemd/system|systemctl\s+(enable|daemon-reload))")
    add(pe, "high", "Shell profile modification", r"(\.bashrc|\.zshrc|\.profile\b|/etc/profile\.d)")
    add(pe, "critical", "SSH key injection", r"(ssh-rsa\s+AAAA|ssh-ed25519\s+AAAA|>>\s*\S*authorized_keys)")
    add(
        pe,
        "high",
        "Windows autorun/scheduled task",
        r"(HKEY_(LOCAL_MACHINE|CURRENT_USER)|CurrentVersion\\+Run|schtasks\s+/create)",
    )
    add(pe, "high", "macOS launch agent/daemon", r"(LaunchAgents|LaunchDaemons|launchctl\s+load)")
    add(
        pe,
        "high",
        "HA persistent config/component write",
        r"(\.storage/|custom_components/\S*__init__\.py|>>\s*\S*configuration\.yaml)",
    )
    add(pe, "critical", "Python import hook persistence", r"(sitecustomize|usercustomize|site-packages/\S*\.pth)")
    add(pe, "critical", "Dynamic linker hijack", r"(LD_PRELOAD|LD_LIBRARY_PATH|DYLD_INSERT_LIBRARIES)")
    add(pe, "high", "Detached background process", r"(nohup\b|setsid\b|disown\b|screen\s+-dm|tmux\s+new-session\s+-d)")

    # --- Network (10 patterns) ---
    nw = ThreatCategory.NETWORK
    add(nw, "critical", "Reverse shell", r"(nc\s+-e|ncat\s+--exec|bash\s+-i\s*>&|/dev/tcp/|socat\s+\S*exec)")
    add(nw, "critical", "Bind shell / inbound listener", r"(nc\s+-l|socket\.bind|http\.server|SimpleHTTPServer)")
    add(nw, "high", "Port scanning", r"(nmap\b|masscan\b|portscan|socket\.connect_ex)")
    add(nw, "critical", "Download-and-execute pipeline", r"(curl|wget)\s[^\n|]{0,80}\|\s*(ba)?sh")
    add(nw, "high", "Anonymizing proxy / Tor", r"(\.onion\b|torsocks|socks5://|proxychains)")
    add(nw, "high", "Tunneling service", r"(localtunnel|serveo\.net|cloudflared\s+tunnel|frp[cs]\s+-c)")
    add(nw, "high", "Covert DNS/ICMP channel", r"(hping\b|iodine\b|dnscat|ping\s+-p\b)")
    add(nw, "medium", "Raw IP endpoint", r"\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b")
    add(
        nw,
        "medium",
        "Private network address scan",
        r"(192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.)",
    )
    add(nw, "medium", "External websocket connection", r"wss?://(?!localhost|127\.0\.0\.1)")

    # --- Privilege Escalation (10 patterns) ---
    pv = ThreatCategory.PRIVILEGE_ESCALATION
    add(pv, "critical", "Sudoers/passwordless escalation", r"(pkexec\b|doas\s|sudoers|NOPASSWD)")
    add(pv, "critical", "SUID/SGID manipulation", r"(chmod\s+[ug]?\+s|chmod\s+[24]\d{3}|find\s+\S*-perm\s+-[24]000)")
    add(pv, "high", "Linux capability grant", r"(setcap\b|cap_sys_admin|cap_setuid)")
    add(pv, "critical", "Container escape", r"(--privileged\b|/var/run/docker\.sock|nsenter\b|docker\s+run\S*\s-v\s*/:)")
    add(pv, "critical", "Kernel module loading", r"(insmod\b|modprobe\s+(?!-r)|/lib/modules)")
    add(pv, "high", "Namespace/chroot escape", r"(unshare\s+-|chroot\s+/|pivot_root)")
    add(pv, "critical", "Credential store access", r"(/etc/shadow|/etc/passwd|lsass|security\s+dump-keychain)")
    add(pv, "high", "Access-token harvesting", r"(HA_TOKEN|long.?lived.?access.?token|Authorization:\s*Bearer)")
    add(pv, "critical", "Admin account creation/promotion", r"(is_admin\s*[:=]\s*true|auth_provider|user\.create)")
    add(pv, "critical", "Root UID assumption", r"(setuid\(0\)|seteuid\(0\)|os\.setuid)")

    # --- Supply Chain (10 patterns) ---
    sc = ThreatCategory.SUPPLY_CHAIN
    add(sc, "critical", "Package installation", r"(pip3?\s+install|npm\s+install|yarn\s+add|apt-get\s+install)")
    add(sc, "critical", "Install from URL/VCS", r"(pip3?\s+install\s+(git\+|https?://)|npm\s+install\s+https?://)")
    add(sc, "critical", "Untrusted package index", r"(--index-url|--extra-index-url|--trusted-host|--registry\s)")
    add(
        sc,
        "high",
        "HACS custom repository",
        r"(hacs[^\n]{0,40}custom.{0,3}repositor|custom.{0,3}repositor[^\n]{0,40}hacs"
        r"|add[^\n]{0,20}custom[^\n]{0,20}repositor)",
    )
    add(sc, "medium", "Dependency integrity override", r"(--force-reinstall|--ignore-installed|--no-deps)")
    add(sc, "critical", "Remote installer script", r"(curl|wget)\s[^\n]{0,80}(install\.sh|get-pip|setup\.sh)")
    add(sc, "critical", "Dynamic remote code import", r"(__import__\s*\(|importlib\.import_module|exec\s*\(\s*requests)")
    add(sc, "critical", "Unsafe deserialization", r"(pickle\.loads?|marshal\.loads|yaml\.load\s*\((?!.*Loader))")
    add(sc, "high", "Git remote/submodule injection", r"(git\s+remote\s+(add|set-url)|\.gitmodules|git\s+submodule\s+add)")
    add(
        sc,
        "high",
        "Certificate/signature verification bypass",
        r"(--no-check-certificate|verify\s*=\s*False|--insecure\b|--allow-unauthenticated)",
    )

    return patterns


THREAT_PATTERNS: list[ThreatPattern] = _build_patterns()
