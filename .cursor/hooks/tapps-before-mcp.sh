#!/usr/bin/env bash
# TappsMCP beforeMCPExecution hook
# Logs MCP tool invocations for observability.
INPUT=$(cat)
PY="import sys,json; d=json.load(sys.stdin)"
PY="$PY; print(d.get('tool','unknown'))"
TOOL=$(echo "$INPUT" | python3 -c "$PY" 2>/dev/null)
echo "[TappsMCP] MCP tool invoked: $TOOL" >&2
exit 0
