#!/usr/bin/env bash
# TappsMCP Memory Auto-Recall (Cursor — Epic 65.4)
# Injects relevant memories on sessionStart/preCompact. Graceful fallback: exit 0.
INPUT=$(cat)
DEFAULT_QUERY="project context architecture"
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
PY="import sys,json
try:
    d=json.load(sys.stdin)
    q=d.get('prompt','') or d.get('last_user_message','') or d.get('last_message','')
    if not q and 'messages' in d:
        ms=d.get('messages',[])
        if ms:
            last=ms[-1] if isinstance(ms[-1],dict) else {}
            q=last.get('content',last.get('text',''))
    if not q: q=d.get('context','') or '$DEFAULT_QUERY'
    q=(q or '')[:500]
    print(q)
except Exception:
    print('$DEFAULT_QUERY')
"
QUERY=$(echo "$INPUT" | "$PYBIN" -c "$PY" 2>/dev/null || echo "$DEFAULT_QUERY")
if [ "$QUERY" != "$DEFAULT_QUERY" ] && [ ${#QUERY} -lt 50 ]; then
  exit 0
fi
PROJ_PY="import sys,json
try:
    d=json.load(sys.stdin)
    roots=d.get('workspace_roots') or []
    if roots:
        print(roots[0])
    elif d.get('cwd'):
        print(d['cwd'])
    else:
        print('.')
except Exception:
    print('.')
"
PROJECT_DIR=$(echo "$INPUT" | "$PYBIN" -c "$PROJ_PY" 2>/dev/null || echo ".")
TAPPS=$(command -v tapps-mcp 2>/dev/null)
if [ -z "$TAPPS" ]; then
  exit 0
fi
OUT=$("$TAPPS" memory recall --query "$QUERY" --project-root "$PROJECT_DIR" \
  --max-results 5 --min-score 0.3 2>/dev/null)
if [ -n "$OUT" ]; then
  echo "$OUT"
fi
exit 0
