#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.78
# tapps-mcp-hook-content-sha: c9dc8b49
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
HOOK_ERR=$(echo "$INPUT" | TAPPS_PROJECT_ROOT="$ROOT" "$PYBIN" -c "
import sys, os, json, hashlib, time
try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)
name = d.get('tool_name') or d.get('toolName') or ''
if name not in {'list_issues', 'mcp__claude_ai_Linear__list_issues', 'mcp__plugin_linear_linear__list_issues'}:
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
# Historically this hook required BOTH team and project and exited otherwise,
# so a team-only or project-only list_issues cached nothing — the cache stayed
# empty while the gate logged misses. The reader's _cache_key falls back to '_'
# for an empty segment exactly as this writer does, so every combination
# (including neither) produces a key the reader reproduces. No guard needed.
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
# TAP-6581: refusals used to be a bare sys.exit(0) — the cache silently did
# not get written and nobody could tell a refusal from a no-op. Every refusal
# now names itself on stderr (the wrapper forwards only these marked lines) and
# appends a durable record, mirroring the .cache-gate-violations.jsonl channel.
root = os.environ.get('TAPPS_PROJECT_ROOT') or os.getcwd()
def _refuse(reason, rows):
    line = (
        'tapps-post-linear-list: refused cache write'
        ' reason=' + reason + ' key=' + key + ' rows=' + str(rows)
    )
    sys.stderr.write(line + chr(10))
    try:
        d2 = os.path.join(root, '.tapps-mcp')
        os.makedirs(d2, exist_ok=True)
        rec = {
            'ts': time.time(), 'key': key, 'reason': reason, 'rows': rows,
            'hook': 'tapps-post-linear-list',
        }
        with open(
            os.path.join(d2, '.linear-cache-write-refusals.jsonl'),
            'a', encoding='utf-8',
        ) as fh:
            fh.write(json.dumps(rec) + chr(10))
    except OSError:
        pass
    sys.exit(0)
resp = d.get('tool_response') or d.get('toolResponse') or {}
if isinstance(resp, str):
    try:
        resp = json.loads(resp)
    except Exception:
        resp = {}
def _as_json(s):
    # TAP-5901: MCP hosts deliver the payload as
    # {'content': [{'type': 'text', 'text': '{"issues": [...]}'}]} — the issue
    # list lives inside a nested JSON *string*. Walking dicts and lists alone
    # returns nothing there, and the empty result used to be cached.
    t = s.strip()
    if not t or t[0] not in '[{':
        return None
    try:
        return json.loads(t)
    except Exception:
        return None
def _find_issues(o):
    if isinstance(o, str):
        parsed = _as_json(o)
        return None if parsed is None else _find_issues(parsed)
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
# Store the COMPACT projection, mirroring server_linear_tools_keys._compact_issue.
# The raw plugin payload carries description/comments/attachments/history; a
# 50-issue backlog of that shape blows past the Read tool's 25 k-token ceiling,
# which is what forced agents into the fallback parse. Keep the fields triage
# actually reads and synthesize statusType so compact consumers see one shape.
COMPACT_FIELDS = (
    'id', 'identifier', 'title', 'state', 'status', 'statusType',
    'priority', 'estimate', 'assignee', 'parent',
)
def _compact(it):
    out = {k: v for k, v in it.items() if k in COMPACT_FIELDS}
    if 'statusType' not in out:
        st = out.get('state')
        if isinstance(st, dict) and st.get('type'):
            out['statusType'] = st['type']
        elif isinstance(out.get('status'), dict) and out['status'].get('type'):
            out['statusType'] = out['status']['type']
    return out
issues = [
    _compact(i) if isinstance(i, dict) else i for i in (_find_issues(resp) or [])
]
# Poisoning guard: never write an empty issue list. TAP-4588 only skipped the
# write when the raw request state was an alias/invalid, which required a
# truthy state — but the linear-read skill tells agents to OMIT state and
# filter in memory, so state was '' and an unparseable response cached zero
# issues under the canonical 'open' key for 30 minutes (TAP-5901). A miss costs
# one API call; a poisoned hit makes the agent report an empty backlog. Fail
# open: no write, and the next read repopulates.
state_lc = state.lower()
if not issues:
    _refuse('empty_issue_list', 0)
# TAP-6581 contents-level guard. The guard above tests the CONTAINER (is the
# list empty?); a list of one-field rows from list_issues(fields=['id']) sailed
# past it and was served for the whole 30-min open-bucket TTL as if it were a
# full projection. _COMPACT_FIELDS is the ceiling of a compact row; identity +
# title is the floor. A row below the floor is neither addressable nor
# readable, so refuse the WRITE rather than let the reader discover it later.
IDENTITY_FIELDS = ('identifier', 'id')
def _row_ok(it):
    if not isinstance(it, dict):
        return False
    return any(k in it for k in IDENTITY_FIELDS) and 'title' in it
if not all(_row_ok(i) for i in issues):
    _refuse('rows_below_compact_floor', len(issues))
# TTL aligned with server-side _ttl_for_state defaults (30 min open, 1 h closed).
# Keep in lockstep with Settings.linear_cache_ttl_open_seconds /
# linear_cache_ttl_closed_seconds — a writer that expires sooner than the reader
# expects silently reintroduces the empty-cache symptom.
ttl = 3600 if state_lc in ('completed', 'canceled') else 1800
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
cache_dir = os.path.join(root, '.tapps-mcp-cache', 'linear-snapshots')
target = os.path.join(cache_dir, key + '.json')
# TAP-6581: a narrow fields= read must not DEGRADE a richer entry already
# cached under the same key. Richness = the fields guaranteed on EVERY row
# (their intersection); a strict subset of what is already stored is a
# downgrade and is refused. Equal or incomparable field sets still write, so
# a genuine refresh is never blocked.
def _guaranteed_fields(rows):
    covered = None
    for it in rows:
        if not isinstance(it, dict):
            return set()
        keys = set(it)
        covered = keys if covered is None else (covered & keys)
    return covered or set()
try:
    with open(target, encoding='utf-8') as fh:
        prior = json.load(fh)
except (OSError, ValueError):
    prior = None
if isinstance(prior, dict) and float(prior.get('expires_at') or 0) > time.time():
    prior_rows = prior.get('issues') or []
    if prior_rows:
        prior_fields = _guaranteed_fields(prior_rows)
        new_fields = _guaranteed_fields(issues)
        if new_fields < prior_fields:
            _refuse('would_degrade_cached_entry', len(issues))
try:
    os.makedirs(cache_dir, exist_ok=True)
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
" 2>&1 >/dev/null)
# TAP-6581: stderr was piped to /dev/null wholesale, so a refusal was
# indistinguishable from a successful write. Forward only our own marked lines
# (incidental interpreter noise stays suppressed, keeping the hook fail-open).
case "$HOOK_ERR" in
  *"tapps-post-linear-list: refused"*)
    printf '%s
' "$HOOK_ERR" >&2
    ;;
esac
exit 0
