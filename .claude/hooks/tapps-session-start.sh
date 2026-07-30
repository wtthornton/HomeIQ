#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 319e1ea6
# TappsMCP SessionStart hook (startup/resume)
# Directs the agent to call tapps_session_start as the first MCP action.
# TAP-1379: Short-circuits on subsequent fires within the same Claude session
# (resume/compact re-fire the SessionStart hook; emitting the REQUIRED prompt
# every time caused agents to re-call tapps_session_start ~23x per session).
INPUT=$(cat)
SID=$(printf '%s' "$INPUT" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
SENTINEL_DIR="${TAPPS_PROJECT_ROOT:-.}/.tapps-mcp"
if [ -n "$SID" ]; then
  SENTINEL="$SENTINEL_DIR/.session-start-fired-$SID"
  if [ -f "$SENTINEL" ]; then
    # Already prompted the agent for this Claude session; stay silent on resume.
    exit 0
  fi
  mkdir -p "$SENTINEL_DIR" 2>/dev/null || true
  : > "$SENTINEL" 2>/dev/null || true
fi
# ADR-0005: Kill MCP server processes older than 2 hours to prevent zombie
# accumulation. Claude Code spawns a new tapps-mcp/docsmcp process per session
# but does not consistently reap old children — after several sessions this
# becomes a significant resource and Postgres connection leak.
# ADR-0005: Kill stale MCP server processes to prevent zombie accumulation.
# Also reap project-.venv launches (missing httpx/httpcore) that break nlt-memory.
# DO NOT REMOVE — see docs/adr/0005-mcp-server-zombie-cleanup-hook-on-session-start.md
if command -v ps &>/dev/null && command -v awk &>/dev/null; then
    OLD_PIDS=$(ps -eo pid,etimes,cmd 2>/dev/null | \
        awk '$2 > 7200 && /tapps-mcp|docsmcp|tapps-platform/ && /serve/ && !/--transport http|--transport=http/ {print $1}')
    VENV_PIDS=$(ps -eo pid,cmd 2>/dev/null | \
        awk '/\.venv\/bin\/(tapps-mcp|docsmcp|tapps-platform)/ && /serve/ {print $1}')
    NLT_DUP_PIDS=$(ps -eo pid,etimes,cmd 2>/dev/null | \
        awk '/serve --profile nlt-/ && !/--transport http|--transport=http/ {
            pid=$1; age=$2;
            rest=$0;
            sub(/^.*serve --profile /, "", rest);
            sub(/ .*$/, "", rest);
            prof=rest;
            if (prof == "") next;
            if (!(prof in keeper)) {
                keeper[prof]=pid; youngest[prof]=age; dups[prof]="";
            } else if (age < youngest[prof]) {
                dups[prof]=dups[prof] " " keeper[prof];
                keeper[prof]=pid; youngest[prof]=age;
            } else {
                dups[prof]=dups[prof] " " pid;
            }
        }
        END {
            for (p in dups) {
                gsub(/^ /, "", dups[p]);
                if (dups[p] != "") print dups[p];
            }
        }') || NLT_DUP_PIDS=
    NLT_STALE_PIDS=$(ps -eo pid,etimes,cmd 2>/dev/null | \
        awk '$2 > 45 && /serve --profile nlt-/ && !/--transport http|--transport=http/ {print $1}')
    ZOMBIE_PIDS=$({
    echo "$OLD_PIDS"
    echo "$VENV_PIDS"
    echo "$NLT_DUP_PIDS"
    echo "$NLT_STALE_PIDS"
    } | sort -u | grep -E '^[0-9]+$' || true)
    if [ -n "$ZOMBIE_PIDS" ]; then
        echo "[TappsMCP] Reaping stale MCP serve PIDs: $ZOMBIE_PIDS" >&2
        echo "$ZOMBIE_PIDS" | xargs kill 2>/dev/null || true
    fi
fi
# TAP-1927: Pre-warm the brain tools-list cache so _negotiate_profile_locked
# can skip the live MCP tools/list round-trip on the first bridge call.
# Runs in the background (does not block session start) and is best-effort
# (curl failure leaves the cache absent; bridge falls through to live fetch).
if [ -n "${TAPPS_MCP_MEMORY_BRAIN_HTTP_URL:-}" ] && command -v curl &>/dev/null; then
    _BRAIN_PROFILE="${TAPPS_BRAIN_PROFILE:-}"
    _CACHE_DIR="${TAPPS_PROJECT_ROOT:-.}/.tapps-mcp"
    _SAFE_PROFILE=$(printf '%s' "$_BRAIN_PROFILE" | tr -c 'A-Za-z0-9_-' '_')
    _CACHE_FILE="$_CACHE_DIR/.brain-tools-list.${_SAFE_PROFILE}.json"
    mkdir -p "$_CACHE_DIR" 2>/dev/null || true
    _BRAIN_URL="${TAPPS_MCP_MEMORY_BRAIN_HTTP_URL%/}/v1/tools/list"
    if [ -n "$_BRAIN_PROFILE" ]; then
        _BRAIN_URL="${_BRAIN_URL}?profile=${_BRAIN_PROFILE}"
    fi
    curl -sf --max-time 1 "$_BRAIN_URL" -o "$_CACHE_FILE" 2>/dev/null &
fi
echo "REQUIRED: Call tapps_session_start() NOW as your first action."
echo "This initializes project context for all TappsMCP quality tools."
echo "Tools called without session_start will have degraded accuracy."
# TAP-3578: Prior-session pipeline gap reminder from disk telemetry.
PROJECT="${TAPPS_PROJECT_ROOT:-${CLAUDE_PROJECT_DIR:-.}}"
USAGE_HINT=""
if command -v tapps-mcp >/dev/null 2>&1; then
  USAGE_HINT=$(tapps-mcp usage-gaps-hint --project-root "$PROJECT" 2>/dev/null || true)
elif command -v uv >/dev/null 2>&1 && [ -f "$PROJECT/pyproject.toml" ]; then
  USAGE_HINT=$(cd "$PROJECT" && uv run tapps-mcp usage-gaps-hint 2>/dev/null || true)
fi
if [ -n "$USAGE_HINT" ]; then
  echo "TappsMCP prior-session reminder: $USAGE_HINT"
fi
exit 0
