#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 643764c9
# TappsMCP PostToolUse hook — Linear list_issues auto-populate (TAP-1412)
# After a successful mcp__plugin_linear_linear__list_issues call, write the
# response into .tapps-mcp-cache/linear-snapshots/<key>.json so the next
# tapps_linear_snapshot_get returns cached=true. Eliminates the manual
# snapshot_put step that was being skipped.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYBIN" ]; then
  exit 0
fi
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
echo "$INPUT" | TAPPS_PROJECT_ROOT="$ROOT" "$PYBIN" -c "
import sys, os, json, hashlib, time
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
name = d.get('tool_name') or d.get('toolName') or ''
if name not in ('mcp__plugin_linear_linear__list_issues', 'list_issues'):
    sys.exit(0)
inp = d.get('tool_input') or d.get('toolInput') or {}
team = (inp.get('team') or '').strip()
project = (inp.get('project') or '').strip()
state = (inp.get('state') or '').strip()
label = (inp.get('label') or '').strip()
try:
    limit = int(inp.get('limit') or 50)
except Exception:
    limit = 50
if not team or not project:
    sys.exit(0)
# TAP-4588: canonicalize the open-bucket alias and drop limit from the hash so
# this writer's key matches server _resolve_cache_key / the reader.
OPEN_BUCKET = ('backlog', 'unstarted', 'started', 'triage')
def _canon_state(s):
    s_lc = (s or '').strip().lower()
    if s_lc == '' or s_lc == 'open' or s_lc in OPEN_BUCKET:
        return 'open'
    return s_lc
canon = _canon_state(state)
filt = {k: v for k, v in sorted({
    'state': canon, 'label': label,
}.items()) if v not in (None, '')}
payload = json.dumps(filt, sort_keys=True, default=str).encode('utf-8')
fhash = hashlib.sha256(payload).hexdigest()[:16]
key = '__'.join([
    team.replace('/', '_') or '_',
    project.replace('/', '_') or '_',
    (canon.replace('/', '_') or 'any'),
    fhash,
])
resp = d.get('tool_response') or d.get('toolResponse') or {}
if isinstance(resp, str):
    try:
        resp = json.loads(resp)
    except Exception:
        resp = {}
def _find_issues(o):
    if isinstance(o, list):
        if o and isinstance(o[0], dict) and any(
            k in o[0] for k in ('identifier', 'id', 'title')
        ):
            return o
        for e in o:
            r = _find_issues(e)
            if r is not None:
                return r
        return None
    if isinstance(o, dict):
        if isinstance(o.get('issues'), list):
            return o['issues']
        for v in o.values():
            r = _find_issues(v)
            if r is not None:
                return r
    return None
issues = _find_issues(resp) or []
# TAP-4588 poisoning guard: list_issues(state='open') (a tapps-mcp alias, not a
# real Linear state) returns [] — caching that empty list under the canonical
# 'open' key would make a later get falsely report 0 issues. Skip the write
# when the raw request state was an alias/invalid AND the result is empty.
VALID_LINEAR_STATES = (
    'backlog', 'unstarted', 'started', 'triage', 'completed', 'canceled'
)
state_lc = state.lower()
if not issues and state_lc and state_lc not in VALID_LINEAR_STATES:
    sys.exit(0)
# TTL aligned with server-side _ttl_for_state defaults (5 min open, 1 h closed).
ttl = 3600 if state_lc in ('completed', 'canceled') else 300
now = time.time()
out = {
    'issues': issues,
    'cached_at': now,
    'expires_at': now + ttl,
    'state': state or None,
    'team': team,
    'project': project,
    'auto_populated': True,
    'limit': limit,
}
root = os.environ.get('TAPPS_PROJECT_ROOT') or os.getcwd()
cache_dir = os.path.join(root, '.tapps-mcp-cache', 'linear-snapshots')
try:
    os.makedirs(cache_dir, exist_ok=True)
    target = os.path.join(cache_dir, key + '.json')
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(out, fh)
    os.replace(tmp, target)
    # Also drop a sentinel so a subsequent list_issues call passes the gate
    # without needing a snapshot_get round-trip first.
    sentinel_dir = os.path.join(root, '.tapps-mcp')
    os.makedirs(sentinel_dir, exist_ok=True)
    with open(os.path.join(sentinel_dir, '.linear-snapshot-sentinel-' + key), 'w') as fh:
        fh.write(str(int(now)))
except OSError:
    pass
" 2>/dev/null
exit 0
