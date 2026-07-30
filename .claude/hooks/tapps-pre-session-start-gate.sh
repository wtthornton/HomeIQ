#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 6a781275
# TappsMCP PreToolUse hook — session-start enforcement gate.
# Blocks TappsMCP quality tools until tapps_session_start has actually run this
# Claude session (proven by a tool-written .session-start-done-<SID> sentinel,
# not merely the SessionStart hook firing). Mode is baked in at install time:
# "warn" logs to .session-start-gate-violations.jsonl and allows; "block"
# exits 2. Bypass with TAPPS_SKIP_SESSION_START_GATE=1 (logged to
# .tapps-mcp/.bypass-log.jsonl).
MODE="warn"
INPUT=$(cat)
TOOL=$(printf '%s' "$INPUT" | sed -n 's/.*"tool_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
SID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
# Never gate session_start itself or cheap discovery/diagnostic tools — they
# establish the context or must stay reachable to repair a broken setup.
case "$TOOL" in
  *tapps_session_start|*tapps_server_info|*tapps_doctor|*tapps_usage|*tapps_stats) exit 0 ;;
esac
# Only gate the TappsMCP quality tool family (the matcher already scopes this;
# re-checked so a stray broad matcher can't over-block foreign tools).
case "$TOOL" in
  mcp__nlt-build__*|mcp__nlt-memory__*|mcp__nlt-setup__*|mcp__nlt-code-quality__*|mcp__nlt-platform-admin__*|mcp__tapps-mcp__*) ;;
  *) exit 0 ;;
esac
[ "$MODE" = "off" ] && exit 0
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
if [ "${TAPPS_SKIP_SESSION_START_GATE:-0}" = "1" ]; then
  mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
  echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"bypass\":\"TAPPS_SKIP_SESSION_START_GATE\",\"tool\":\"${TOOL}\"}" \
    >> "$ROOT/.tapps-mcp/.bypass-log.jsonl" 2>/dev/null
  exit 0
fi
# Unidentifiable session — cannot prove state; fail open rather than deadlock.
if [ -z "$SID" ]; then
  exit 0
fi
if [ -f "$ROOT/.tapps-mcp/.session-start-done-$SID" ]; then
  exit 0
fi
mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"tool\":\"${TOOL}\",\"mode\":\"${MODE}\",\"sid\":\"${SID}\"}" \
  >> "$ROOT/.tapps-mcp/.session-start-gate-violations.jsonl" 2>/dev/null
if [ "$MODE" = "warn" ]; then
  cat >&2 <<MSG
[TappsMCP refusal layer=hook-only/defense-in-depth] session-start gate (warn) — ${TOOL} was called before tapps_session_start ran this session.
Call tapps_session_start() first: it bootstraps project context, the checker matrix, and brain auth. Without it, quality verdicts are degraded.
This call is allowed (warn mode) but logged to .tapps-mcp/.session-start-gate-violations.jsonl.
MSG
  exit 0
fi
cat >&2 <<MSG
[TappsMCP refusal layer=hook-only/defense-in-depth] session-start gate (block) — ${TOOL} was called before tapps_session_start ran this session.
Call tapps_session_start() NOW, then retry: it bootstraps project context, the checker matrix, and brain auth. TappsMCP tools run degraded without it.
Emergency bypass: TAPPS_SKIP_SESSION_START_GATE=1 (logged to .tapps-mcp/.bypass-log.jsonl).
MSG
exit 2
