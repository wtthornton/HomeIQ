#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 6934aae7
# TappsMCP PostToolUse hook — Linear gate sentinel writer (TAP-981 / TAP-1328)
# Writes .tapps-mcp/.linear-validate-sentinel ONLY when the validate call
# returned agent_ready=true. Failed validations no longer unlock save_issue.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
PARSED=$(echo "$INPUT" | "$PYBIN" -c   "import sys,json
try:
    d=json.load(sys.stdin)
    tool=d.get('tool_name') or d.get('toolName') or ''
    resp=d.get('tool_response') or d.get('toolResponse') or {}
    if isinstance(resp,str):
        try: resp=json.loads(resp)
        except Exception: resp={}
    data=resp.get('data') if isinstance(resp,dict) else None
    ready=False
    if isinstance(data,dict) and data.get('agent_ready') is True:
        ready=True
    elif isinstance(resp,dict) and resp.get('agent_ready') is True:
        ready=True
    print(tool)
    print('1' if ready else '0')
except Exception:
    print('')
    print('0')" 2>/dev/null)
TOOL=$(echo "$PARSED" | sed -n '1p')
READY=$(echo "$PARSED" | sed -n '2p')
case "$TOOL" in
  mcp__docs-mcp__docs_validate_linear_issue|mcp__nlt-linear-issues__docs_validate_linear_issue|docs_validate_linear_issue) ;;
  *) exit 0 ;;
esac
if [ "$READY" != "1" ]; then
  exit 0
fi
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
date +%s > "$ROOT/.tapps-mcp/.linear-validate-sentinel" 2>/dev/null
exit 0
