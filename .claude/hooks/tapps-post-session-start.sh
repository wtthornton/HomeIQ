#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: b03ed009
# TappsMCP PostToolUse hook — session-start sentinel writer.
# Writes .session-start-done-<SID> AFTER tapps_session_start actually returns,
# proving the tool ran (not merely that the SessionStart hook fired). The
# pre-session-start gate reads this sentinel to release TappsMCP quality tools.
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
case "$TOOL" in
  *tapps_session_start) ;;
  *) exit 0 ;;
esac
SID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
[ -z "$SID" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
: > "$ROOT/.tapps-mcp/.session-start-done-$SID" 2>/dev/null
# Best-effort GC of sentinels left by prior Claude sessions (older than 1 day).
find "$ROOT/.tapps-mcp" -maxdepth 1 -name '.session-start-done-*' -mtime +1 -delete 2>/dev/null || true
exit 0
