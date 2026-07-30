#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 0d76c000
# TappsMCP PreToolUse hook (Bash) - destructive command guard (opt-in)
# Blocks commands containing rm -rf, format c:, etc. Exit 2 = block, 0 = allow.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYBIN" ]; then
  # TAP-1785: enforcement gate fails closed when python is unavailable.
  ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
  mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
  echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"hook\":\"tapps-pre-bash\",\"reason\":\"no_python\"}" \
    >> "$ROOT/.tapps-mcp/.bypass-log.jsonl" 2>/dev/null
  echo "TappsMCP: Blocked — no python interpreter available to evaluate destructive-command guard." >&2
  exit 2
fi
CMD=$(echo "$INPUT" | "$PYBIN" -c "
import sys, json
try:
    d = json.load(sys.stdin)
    ti = d.get('tool_input', {}) or {}
    cmd = ti.get('command', '') or ti.get('cmd', '')
    if not cmd and isinstance(ti.get('args'), list):
        cmd = ' '.join(str(a) for a in ti['args'])
    print(cmd if isinstance(cmd, str) else '')
except Exception:
    print('')
" 2>/dev/null)
# Blocklist (substring match, case-insensitive for format/del).
# Fork-bomb signature ":(){"  is matched as a QUOTED literal substring
# because bare ( / ) terminate case alternatives early and cause a bash
# syntax error. The substring ":(){" is distinctive enough on its own.
BLOCK=0
case "$CMD" in
  *rm\ -rf*|*rm\ -fr*|*rm\ -r\ -f*|*rm\ -rf\ /*) BLOCK=1 ;;
  *format\ c:*|*format\ c:/*|*format\ C:*|*format\ C:/*) BLOCK=1 ;;
  *del\ /f\ /s\ /q*|*del\ /s\ /q*|*rd\ /s\ /q*) BLOCK=1 ;;
  *":(){"*) BLOCK=1 ;;
esac
if [ "$BLOCK" = 1 ]; then
  echo "TappsMCP: Blocked potentially destructive command." >&2
  exit 2
fi
exit 0
