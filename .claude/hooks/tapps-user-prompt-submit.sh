#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 2d5236e7
# TappsMCP UserPromptSubmit hook (TAP-975 / TAP-2000)
# Re-surfaces pipeline state per user turn so long sessions don't drift.
# Reads one sidecar:
#   .tapps-mcp/.session-start-marker   — Unix epoch of last tapps_session_start
# Checklist outcomes live in brain (checklist_outcome events via TAP-2000);
# call tapps_checklist or /tapps-finish-task — bash hooks cannot query brain.
# Stays SILENT when session_start was within 30 min.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
SS_MARKER="$PROJECT_DIR/.tapps-mcp/.session-start-marker"
NOW=$(date +%s)
NEED_SS=0
if [ ! -f "$SS_MARKER" ]; then
  NEED_SS=1
else
  SS=$(cat "$SS_MARKER" 2>/dev/null)
  if ! echo "$SS" | grep -Eq '^[0-9]+$'; then
    SS=0
  fi
  AGE=$((NOW - SS))
  # 1800s = 30 minute freshness window per TAP-975 AC.
  if [ "$AGE" -gt 1800 ]; then
    NEED_SS=1
  fi
fi
if [ "$NEED_SS" -eq 0 ]; then
  exit 0
fi
{
  echo "[TappsMCP] Pipeline-state reminder:"
  echo "  - tapps_session_start was not called within the last 30 min — call it before edits to refresh project context."
} >&2
exit 0
