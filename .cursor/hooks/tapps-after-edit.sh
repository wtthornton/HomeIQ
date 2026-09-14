#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.78
# tapps-mcp-hook-content-sha: c1ee6870
# TappsMCP afterFileEdit hook (fire-and-forget) — TAP-1330 import parity
# Detects external imports requiring tapps_lookup_docs. Advisory only.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
PARSED=$(TAPPS_HOOK_INPUT="$INPUT" "$PYBIN" - <<'PYEOF' 2>/dev/null
import os, json, re
from pathlib import Path

def _resolve(rel):
    candidate = Path(rel)
    if candidate.is_file():
        return candidate
    for root in (
        os.environ.get("TAPPS_MCP_PROJECT_ROOT"),
        os.environ.get("TAPPS_PROJECT_ROOT"),
        os.environ.get("CURSOR_PROJECT_DIR"),
        os.getcwd(),
    ):
        if not root:
            continue
        alt = Path(root) / rel
        if alt.is_file():
            return alt
    return candidate

# TAP-6598: "1" when an edit lands inside a managed SKILL.md's BEGIN/END
# block — that region is regenerated (and the edit lost) on tapps_upgrade.
def _managed_block_guard(f, tool, ti):
    if not f.endswith("SKILL.md"):
        return ""
    skill_path = _resolve(f)
    if not skill_path.is_file():
        return ""
    full = skill_path.read_text(encoding="utf-8", errors="replace")
    begin = full.find("<!-- BEGIN: tapps-skill")
    end = full.find("<!-- END: tapps-skill -->", begin if begin != -1 else 0)
    if begin == -1 or end == -1:
        return ""
    if tool == "Write":
        return "1"
    edits = ti.get("edits") if isinstance(ti.get("edits"), list) else [ti]
    for one in edits:
        snippet = one.get("new_string") or ""
        if snippet and snippet in full[begin:end]:
            return "1"
    return ""

try:
    d = json.loads(os.environ.get("TAPPS_HOOK_INPUT", "{}"))
    ti = d.get("tool_input") or d.get("toolInput") or {}
    tool = d.get("tool_name") or d.get("tool") or ""
    f = (
        d.get("file")
        or d.get("file_path")
        or ti.get("file_path")
        or ti.get("path")
        or ""
    )
    content = ti.get("content") or ti.get("new_string") or ""
    if not content and f:
        candidate = _resolve(f)
        if candidate.is_file():
            content = candidate.read_text(encoding="utf-8", errors="replace")
    print(f)
    libs: set[str] = set()
    if f.endswith((".py", ".pyi")):
        for m in re.finditer(
            r"^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)", content, re.M
        ):
            libs.add(m.group(1))
    elif f.endswith((".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")):
        # \x27/\x22: hex-coded quote chars — a literal quote here would
        # close this raw string early once the outer non-raw string unescapes it.
        js_import = r"^\s*import[^\x27\x22]*[\x27\x22]([^\x27\x22./][^\x27\x22]*)[\x27\x22]"
        for m in re.finditer(js_import, content, re.M):
            libs.add(m.group(1).split("/")[0])
    print(",".join(sorted(libs)))
    api = "0"
    if f.endswith((".py", ".pyi")):
        if re.search(r"^\s*(?:async\s+)?def\s+\w+|^\s*class\s+\w+", content, re.M):
            api = "1"
    print(api)
    print(_managed_block_guard(f, tool, ti))
except Exception:
    print("")
    print("")
    print("")
    print("")
PYEOF
)
FILE=$(echo "$PARSED" | sed -n '1p')
LIBS=$(echo "$PARSED" | sed -n '2p')
API=$(echo "$PARSED" | sed -n '3p')
SKILL_GUARD=$(echo "$PARSED" | sed -n '4p')
if [ "$SKILL_GUARD" = "1" ]; then
  echo "$FILE: this edit landed inside the BEGIN/END managed block — tapps_upgrade regenerates that region and the edit will be lost. Move project-specific content below the END marker instead." >&2
fi
case "$FILE" in
  *.py|*.pyi|*.ts|*.tsx|*.js|*.jsx|*.go|*.rs)
    echo "Edited: $FILE — run tapps_quick_check after this edit." >&2
    if [ -n "$LIBS" ]; then
      echo "Imports detected ($LIBS) — call tapps_lookup_docs(library=..., topic=...) **before editing** code that uses those APIs (TAP-1330). Retrospective lookups at finish-task do not excuse skipped pre-edit lookups." >&2
    fi
    if [ "$API" = "1" ]; then
      echo "Public API change detected ($FILE) — call docs_check_drift and docs_api_surface on nlt-project-docs when documenting (warn-only)." >&2
      echo "Blast radius ($FILE) — tapps_call_graph(symbol='...', query='callers') or tapps_impact_analysis(file_path='...', symbol='...', granularity='both') before changing callers (warn-only)." >&2
    fi
    ;;
  *)
    if [ -n "$FILE" ] && [ "$FILE" != "unknown" ]; then
      echo "File edited: $FILE"
      echo "Consider running tapps_quick_check to verify quality."
    fi
    ;;
esac
exit 0
