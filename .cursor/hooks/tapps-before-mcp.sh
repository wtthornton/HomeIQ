#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: a2a806a0
# TappsMCP beforeMCPExecution hook
# Logs MCP tool invocations and reminds to call session_start.
INPUT=$(cat)
PY="import sys,json; d=json.load(sys.stdin); print(d.get('tool_name') or d.get('tool') or 'unknown')"
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
TOOL=$(echo "$INPUT" | "$PYBIN" -c "$PY" 2>/dev/null)
AGENT_MSG=""
case "$TOOL" in
  tapps_*)
    SID=$(printf '%s' "$INPUT" | sed -n 's/.*"conversation_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
    SENTINEL_DIR="${TAPPS_MCP_PROJECT_ROOT:-${DOCS_MCP_PROJECT_ROOT:-.}}/.tapps-mcp"
    if [ -n "$SID" ]; then
      SENTINEL="$SENTINEL_DIR/.cursor-mcp-session-$SID"
    else
      SENTINEL="$SENTINEL_DIR/.cursor-mcp-session-active"
    fi
    if [ "$TOOL" = "tapps_session_start" ]; then
      mkdir -p "$SENTINEL_DIR" 2>/dev/null || true
      : > "$SENTINEL" 2>/dev/null || true
    elif [ ! -f "$SENTINEL" ]; then
      AGENT_MSG="REMINDER: Call tapps_session_start() first for best results."
    fi
    ;;
esac
echo "[TappsMCP] MCP tool invoked: $TOOL" >&2
if [ -n "${AGENT_MSG:-}" ]; then
  "$PYBIN" -c 'import json,sys; print(json.dumps({"permission":"allow","agent_message":sys.argv[1]}))' "$AGENT_MSG"
else
  printf '%s\n' '{"permission":"allow"}'
fi
exit 0
