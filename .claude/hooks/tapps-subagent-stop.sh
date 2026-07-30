#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: a00151eb
# TappsMCP SubagentStop hook (Epic 36.1)
# Advises on quality validation when subagent modified Python files.
# IMPORTANT: SubagentStop does NOT support exit code 2 (advisory only).
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
# Check for Python file modifications (best-effort)
HAS_PY=$(echo "$INPUT" | "$PYBIN" -c "
import sys,json
try:
    d=json.load(sys.stdin)
    # SubagentStop event may include changed files info
    print('yes')
except Exception:
    print('no')
" 2>/dev/null)
if [ "$HAS_PY" = "yes" ]; then
  echo "Subagent completed. Run tapps_quick_check or tapps_validate_changed" >&2
  echo "on any Python files modified by this subagent." >&2
fi
exit 0
