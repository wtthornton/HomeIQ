#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 69a96eb2
# TappsMCP PreToolUse hook — Linear cache-first read gate (TAP-1224)
# Gates raw mcp__plugin_linear_linear__list_issues calls behind a recent
# tapps_linear_snapshot_get sentinel for the same (team, project, state,
# label, limit) slice (within 300s). Mode is baked in at install time:
# "warn" logs to .cache-gate-violations.jsonl and allows; "block" exits 2.
# Bypass with TAPPS_LINEAR_SKIP_CACHE_GATE=1 (logged to .bypass-log.jsonl).
MODE="warn"
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYBIN" ]; then
  # No python available — cannot compute key; fail-open for portability.
  exit 0
fi
PARSED=$(echo "$INPUT" | "$PYBIN" -c "
import sys, json, hashlib
try:
    d = json.load(sys.stdin)
except Exception:
    print('')
    print('')
    print('')
    print('')
    sys.exit(0)
name = d.get('tool_name') or d.get('toolName') or ''
inp = d.get('tool_input') or d.get('toolInput') or {}
team = (inp.get('team') or '').strip()
project = (inp.get('project') or '').strip()
state = (inp.get('state') or '').strip()
label = (inp.get('label') or '').strip()
try:
    limit = int(inp.get('limit') or 50)
except Exception:
    limit = 50
# Open-bucket alias: tapps-mcp's TTL bucket 'open' covers backlog, unstarted,
# started, triage. The skill tells agents to snapshot_get(state='open') and
# then list_issues with a concrete state. TAP-4588: canonicalize any open
# alias ('' / 'open' / bucket member) to ONE token so the payload key and the
# sentinel key converge — matching server _canonical_state. limit is dropped
# from the hash (enforced at read time via the superset fallback). Same logic
# on both sides — see server_linear_tools._resolve_cache_key.
OPEN_BUCKET = ('backlog', 'unstarted', 'started', 'triage')
state_lc = state.lower()
def _canon_state(s):
    s_lc = (s or '').strip().lower()
    if s_lc == '' or s_lc == 'open' or s_lc in OPEN_BUCKET:
        return 'open'
    return s_lc
def _key_for(state_part: str) -> str:
    canon = _canon_state(state_part)
    filt = {k: v for k, v in sorted({
        'state': canon, 'label': label,
    }.items()) if v not in (None, '')}
    payload = json.dumps(filt, sort_keys=True, default=str).encode('utf-8')
    fhash = hashlib.sha256(payload).hexdigest()[:16]
    parts = [
        (team.replace('/', '_') or '_'),
        (project.replace('/', '_') or '_'),
        (canon.replace('/', '_') or 'any'),
        fhash,
    ]
    return '__'.join(parts)
key = _key_for(state)
# With canonicalization every open-bucket alias resolves to the same key, so
# the alias set is a singleton ({key}). We still emit the bucket variants and
# de-dup so the set matches the Python _alias_keys contract byte-for-byte.
alias_keys = []
if not team or not project:
    key = ''
else:
    if state_lc in OPEN_BUCKET or state_lc in ('open', ''):
        for m in OPEN_BUCKET:
            alias_keys.append(_key_for(m))
        alias_keys.append(_key_for('open'))
        alias_keys.append(_key_for(''))
    # de-dup while preserving order; drop the exact key
    seen = {key}
    alias_keys = [k for k in alias_keys if not (k in seen or seen.add(k))]
print(name)
print(key)
print(team)
print(project)
print('|'.join(alias_keys))
" 2>/dev/null)
TOOL=$(echo "$PARSED" | sed -n '1p')
KEY=$(echo "$PARSED" | sed -n '2p')
CALL_TEAM=$(echo "$PARSED" | sed -n '3p')
CALL_PROJECT=$(echo "$PARSED" | sed -n '4p')
case "$TOOL" in
  mcp__plugin_linear_linear__list_issues|list_issues) ;;
  *) exit 0 ;;
esac
if [ -z "$KEY" ]; then
  exit 0
fi
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
if [ "${TAPPS_LINEAR_SKIP_CACHE_GATE:-0}" = "1" ]; then
  mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
  echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"bypass\":\"TAPPS_LINEAR_SKIP_CACHE_GATE\",\"key\":\"${KEY}\"}" \
    >> "$ROOT/.tapps-mcp/.bypass-log.jsonl" 2>/dev/null
  exit 0
fi
SENTINEL="$ROOT/.tapps-mcp/.linear-snapshot-sentinel-${KEY}"
if [ -f "$SENTINEL" ]; then
  NOW=$(date +%s)
  SENT=$(cat "$SENTINEL" 2>/dev/null)
  if echo "$SENT" | grep -Eq '^[0-9]+$'; then
    AGE=$((NOW - SENT))
    if [ "$AGE" -le 300 ]; then
      exit 0
    fi
  fi
fi
# No matching sentinel (or stale). Determine violation category before logging.
# TAP-1411: cross-project reads (allowed by agent-scope.md) must NOT be
# treated as gate misses. Read expected team/project from .tapps-mcp.yaml
# (linear_team / linear_project flat keys); if the call's team/project differ,
# tag category=cross_project and pass through even in block mode.
EXPECTED_TEAM=""
EXPECTED_PROJECT=""
if [ -f "$ROOT/.tapps-mcp.yaml" ]; then
  EXPECTED_TEAM=$(grep -E '^linear_team:' "$ROOT/.tapps-mcp.yaml" 2>/dev/null | head -1 | sed -E 's/^linear_team:[[:space:]]*"?([^"]*)"?[[:space:]]*$/\1/')
  EXPECTED_PROJECT=$(grep -E '^linear_project:' "$ROOT/.tapps-mcp.yaml" 2>/dev/null | head -1 | sed -E 's/^linear_project:[[:space:]]*"?([^"]*)"?[[:space:]]*$/\1/')
fi
CATEGORY="gate_miss"
if [ -n "$EXPECTED_TEAM" ] && [ -n "$EXPECTED_PROJECT" ] && [ -n "$CALL_TEAM" ] && [ -n "$CALL_PROJECT" ]; then
  if [ "$CALL_TEAM" != "$EXPECTED_TEAM" ] || [ "$CALL_PROJECT" != "$EXPECTED_PROJECT" ]; then
    CATEGORY="cross_project"
  fi
fi
mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
echo "{\"ts\":\"$(date -u +%FT%TZ)\",\"key\":\"${KEY}\",\"mode\":\"${MODE}\",\"category\":\"${CATEGORY}\",\"call_team\":\"${CALL_TEAM}\",\"call_project\":\"${CALL_PROJECT}\"}" \
  >> "$ROOT/.tapps-mcp/.cache-gate-violations.jsonl" 2>/dev/null
# Cross-project reads pass through regardless of mode — agent-scope.md allows
# read-only access to other projects; the gate is for THIS project's writes.
if [ "$CATEGORY" = "cross_project" ]; then
  exit 0
fi
if [ "$MODE" = "warn" ]; then
  cat >&2 <<MSG
[TappsMCP refusal layer=hook-only/defense-in-depth] Primary gate is the tapps_linear_list_issues server tool (TAP-2008 Agent Gateway). This hook is the fallback layer — it fired because the raw Linear plugin was called directly instead of through the wrapper.
TappsMCP: Linear cache-first read rule (TAP-1224, warn mode) — no recent tapps_linear_snapshot_get for this (team, project, state) slice.
Route reads through the \`linear-read\` skill (TAP-1260):
  1. tapps_linear_snapshot_get(team, project, state)
  2. On cached=false: list_issues with the same filters, then tapps_linear_snapshot_put.
This call is allowed (warn mode) but logged to .tapps-mcp/.cache-gate-violations.jsonl.
See .claude/rules/linear-standards.md.
MSG
  exit 0
fi
cat >&2 <<MSG
[TappsMCP refusal layer=hook-only/defense-in-depth] Primary gate is the tapps_linear_list_issues server tool (TAP-2008 Agent Gateway). This hook is the fallback layer — it fired because the raw Linear plugin was called directly instead of through the wrapper.
TappsMCP: Blocked mcp__plugin_linear_linear__list_issues — no recent tapps_linear_snapshot_get for this (team, project, state) slice.
Route reads through the \`linear-read\` skill (TAP-1260):
  1. tapps_linear_snapshot_get(team, project, state)
  2. On cached=true: filter in memory (no Linear call).
  3. On cached=false: list_issues with the same filters, then tapps_linear_snapshot_put.
For a single-issue lookup, use mcp__plugin_linear_linear__get_issue(id=...) instead.
Or set TAPPS_LINEAR_SKIP_CACHE_GATE=1 for emergency bypass (logged).
See .claude/rules/linear-standards.md.
MSG
exit 2
