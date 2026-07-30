#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: a058b1bb
# TappsMCP Cursor stop hook — TAP-3918 loop-metrics + optional followup (TAP-3921)
# Resolves project root from workspace_roots; transcript from agent-transcripts/.
# Requires tapps-mcp on PATH. See docs/TROUBLESHOOTING.md#cursor-stop-hook-env.
INPUT=$(cat)
TAPPS=$(command -v tapps-mcp 2>/dev/null)
if [ -z "$TAPPS" ]; then
  exit 0
fi
OUT=$(echo "$INPUT" | "$TAPPS" loop-metrics-record 2>/dev/null)
if [ -n "$OUT" ]; then
  echo "$OUT"
fi
exit 0
