#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 5a2c3acd
# TappsMCP PostToolUse hook — Linear cache-gate sentinel writer (TAP-1224)
# Writes a per-(team, project, state, label, limit) sentinel on BOTH
# cached=true and cached=false responses from tapps_linear_snapshot_get.
# Paired with tapps-pre-linear-list.sh which reads the sentinel to gate
# downstream list_issues calls.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYBIN" ]; then
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
ALIASES=$(echo "$PARSED" | sed -n '5p')
case "$TOOL" in
  mcp__tapps-mcp__tapps_linear_snapshot_get|mcp__nlt-linear-issues__tapps_linear_snapshot_get|tapps_linear_snapshot_get) ;;
  *) exit 0 ;;
esac
if [ -z "$KEY" ]; then
  exit 0
fi
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
mkdir -p "$ROOT/.tapps-mcp" 2>/dev/null
NOW=$(date +%s)
echo "$NOW" > "$ROOT/.tapps-mcp/.linear-snapshot-sentinel-${KEY}" 2>/dev/null
# TAP-1374: also write bucket-alias sentinels so a snapshot for state='open'
# (a tapps-mcp TTL bucket alias) unlocks list_issues for any open-bucket
# member state without self-tripping the gate.
if [ -n "$ALIASES" ]; then
  IFS='|' read -r -a _ALIAS_KEYS <<< "$ALIASES"
  for ak in "${_ALIAS_KEYS[@]}"; do
    [ -z "$ak" ] && continue
    echo "$NOW" > "$ROOT/.tapps-mcp/.linear-snapshot-sentinel-${ak}" 2>/dev/null
  done
fi
exit 0
