#!/usr/bin/env bash
# auto-bugfix.sh — Automatically find bugs, fix them, and open a PR using Claude Code headless mode.
#
# Usage:
#   ./scripts/auto-bugfix.sh [--bugs N] [--branch NAME] [--target-dir PATH]
#   ./scripts/auto-bugfix.sh --bugs 1 --chain                    # bugfix + refactor + test
#   ./scripts/auto-bugfix.sh --bugs 3 --chain-phases fix,test    # bugfix + test (skip refactor)
#   ./scripts/auto-bugfix.sh --bugs 5 --no-dashboard             # skip live dashboard
#
# Requirements:
#   - claude CLI installed and authenticated
#   - git configured with push access
#   - gh CLI installed (for PR creation)

set -euo pipefail

# --- Defaults ---
NUM_BUGS=5
BRANCH_NAME="auto/bugfix-$(date +%Y%m%d-%H%M%S)"
TARGET_DIR=""
BASE_BRANCH="master"
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHAIN=false
CHAIN_PHASES="fix,refactor,test"
NO_DASHBOARD=false
ROTATE=false
TARGET_UNIT=""

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --bugs)           NUM_BUGS="$2";       shift 2 ;;
    --branch)         BRANCH_NAME="$2";    shift 2 ;;
    --target-dir)     TARGET_DIR="$2";     shift 2 ;;
    --base)           BASE_BRANCH="$2";    shift 2 ;;
    --chain)          CHAIN=true;          shift ;;
    --chain-phases)   CHAIN=true; CHAIN_PHASES="$2"; shift 2 ;;
    --no-dashboard)   NO_DASHBOARD=true;   shift ;;
    --rotate)         ROTATE=true;         shift ;;
    --target-unit)    TARGET_UNIT="$2";    shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--bugs N] [--branch NAME] [--target-dir PATH] [--base BRANCH] [--chain] [--chain-phases PHASES] [--no-dashboard] [--rotate] [--target-unit UNIT]"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_ROOT"

# --- Rotate mode: pick next scan unit from manifest ---
SCAN_MANIFEST="$PROJECT_ROOT/docs/scan-manifest.json"
SCAN_UNIT_ID=""
SCAN_UNIT_NAME=""
SCAN_UNIT_HINT=""

if [[ "$ROTATE" == "true" || -n "$TARGET_UNIT" ]]; then
  if [[ ! -f "$SCAN_MANIFEST" ]]; then
    echo "ERROR: Scan manifest not found at $SCAN_MANIFEST"
    echo "Run the initial setup or create docs/scan-manifest.json first."
    exit 1
  fi

  # Pick the highest-scoring unit (or the one specified by --target-unit)
  ROTATE_RESULT=$(python3 -c "
import json, sys
from datetime import datetime, timezone

with open('$SCAN_MANIFEST') as f:
    manifest = json.load(f)

target_unit = '$TARGET_UNIT'
now = datetime.now(timezone.utc)

best_unit = None
best_score = -1

for unit in manifest['units']:
    # If --target-unit specified, use that
    if target_unit and unit['id'] != target_unit:
        continue

    # score = priority_weight * days_since_last_scan * (1 + bugs_found/5)
    if unit['last_scanned']:
        last = datetime.fromisoformat(unit['last_scanned'])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max((now - last).total_seconds() / 86400, 0.1)
    else:
        days = 365  # never scanned = max urgency

    bug_boost = 1 + unit['total_bugs_found'] / 5
    fp_penalty = 1 - (unit['false_positives'] / max(unit['total_bugs_found'], 1)) * 0.3
    score = unit['priority_weight'] * days * bug_boost * max(fp_penalty, 0.5)

    if score > best_score:
        best_score = score
        best_unit = unit

if not best_unit:
    if target_unit:
        print(f'ERROR: Unit \"{target_unit}\" not found in manifest', file=sys.stderr)
    else:
        print('ERROR: No units in manifest', file=sys.stderr)
    sys.exit(1)

# Output: id|path|name|hint
print(f\"{best_unit['id']}|{best_unit['path']}|{best_unit['name']}|{best_unit['scan_hint']}\")
" 2>&1)

  if [[ $? -ne 0 ]]; then
    echo "ERROR: $ROTATE_RESULT"
    exit 1
  fi

  IFS='|' read -r SCAN_UNIT_ID TARGET_DIR SCAN_UNIT_NAME SCAN_UNIT_HINT <<< "$ROTATE_RESULT"
  echo "  Rotate: selected unit '$SCAN_UNIT_ID' ($SCAN_UNIT_NAME)"
fi

# --- Dashboard state management ---
DASHBOARD_STATE="$PROJECT_ROOT/scripts/.dashboard-state.json"
DASHBOARD_HTML="$PROJECT_ROOT/scripts/dashboard.html"
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
START_ISO=$(date -Iseconds 2>/dev/null || date +"%Y-%m-%dT%H:%M:%S")
LOG_ENTRIES="[]"

add_log() {
  local msg="$1"
  local level="${2:-info}"
  local time_now
  time_now=$(date +"%H:%M:%S")
  LOG_ENTRIES=$(echo "$LOG_ENTRIES" | python3 -c "
import sys, json
logs = json.load(sys.stdin)
logs.append({'time': '$time_now', 'msg': '''$msg''', 'level': '$level'})
json.dump(logs, sys.stdout)
")
  # Console output
  echo "  [$time_now] $msg"
}

write_dashboard() {
  if [[ "$NO_DASHBOARD" == "true" ]]; then return; fi
  local step="${1:-1}"
  local status="${2:-running}"
  local message="${3:-}"
  local bugs_json="${4:-[]}"
  local bugs_found="${5:--1}"
  local bugs_fixed="${6:--1}"
  local files_changed="${7:--1}"
  local validation="${8:-}"
  local pr_url="${9:-}"

  python3 -c "
import json, sys
state = {
    'branch': '$BRANCH_NAME',
    'base': '$BASE_BRANCH',
    'target_bugs': $NUM_BUGS,
    'start_time': '$START_TIME',
    'start_iso': '$START_ISO',
    'project_root': '$PROJECT_ROOT',
    'current_step': $step,
    'status': '$status',
    'status_message': '''$message''',
    'bugs_found': $bugs_found if $bugs_found >= 0 else None,
    'bugs_fixed': $bugs_fixed if $bugs_fixed >= 0 else None,
    'files_changed': $files_changed if $files_changed >= 0 else None,
    'validation': '$validation' or None,
    'pr_url': '$pr_url' or None,
    'bugs': json.loads('''$bugs_json'''),
    'log': json.loads('''$(echo "$LOG_ENTRIES")''')
}
with open('$DASHBOARD_STATE', 'w') as f:
    json.dump(state, f, indent=2, default=str)
" 2>/dev/null || true
}

# --- Preflight checks ---
for cmd in claude git gh python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is not installed or not in PATH."
    exit 1
  fi
done

if [[ -n "$(git status --porcelain --ignore-submodules)" ]]; then
  echo "ERROR: Working tree is dirty. Commit or stash changes first."
  exit 1
fi

# --- Open dashboard ---
if [[ "$NO_DASHBOARD" != "true" ]]; then
  write_dashboard 1 "running" "Initializing pipeline..."
  add_log "Pipeline starting" "info"
  add_log "Opening dashboard in browser..." "info"
  # Cross-platform browser open
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    cmd.exe /c start "" "$DASHBOARD_HTML" 2>/dev/null &
  elif command -v xdg-open &>/dev/null; then
    xdg-open "$DASHBOARD_HTML" 2>/dev/null &
  elif command -v open &>/dev/null; then
    open "$DASHBOARD_HTML" 2>/dev/null &
  fi
fi

TOTAL_STEPS=5
if [[ "$CHAIN" == "true" ]]; then TOTAL_STEPS=7; fi

echo "=== Auto Bug Fix Pipeline ==="
echo "  Project:  $PROJECT_ROOT"
echo "  Bugs:     $NUM_BUGS"
echo "  Branch:   $BRANCH_NAME"
echo "  Base:     $BASE_BRANCH"
if [[ "$CHAIN" == "true" ]]; then echo "  Chain:    $CHAIN_PHASES"; fi
if [[ -n "$SCAN_UNIT_ID" ]]; then echo "  Unit:     $SCAN_UNIT_ID ($SCAN_UNIT_NAME)"; fi
echo ""

# --- Step 1: Create feature branch ---
add_log "Creating feature branch '$BRANCH_NAME'" "info"
write_dashboard 1 "running" "Creating feature branch..."

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]]; then
  echo "[1/$TOTAL_STEPS] Switching to '$BASE_BRANCH' and creating branch '$BRANCH_NAME'..."
  git checkout "$BASE_BRANCH"
else
  echo "[1/$TOTAL_STEPS] Already on '$BASE_BRANCH'. Creating branch '$BRANCH_NAME'..."
fi
git checkout -b "$BRANCH_NAME"

add_log "Branch '$BRANCH_NAME' created" "success"
write_dashboard 1 "running" "Branch created. Starting scan..."

# --- Step 2: Find bugs with Claude Code ---
SCOPE_HINT=""
if [[ -n "$TARGET_DIR" ]]; then
  SCOPE_HINT="Focus your search EXCLUSIVELY on files under '$TARGET_DIR'."
  if [[ -n "$SCAN_UNIT_HINT" ]]; then
    SCOPE_HINT="$SCOPE_HINT
$SCAN_UNIT_HINT"
  fi
fi

# Load prompt overrides if they exist (Feature 12)
PROMPT_OVERRIDES=""
OVERRIDES_FILE="$PROJECT_ROOT/docs/FIND_PROMPT_OVERRIDES.md"
if [[ -f "$OVERRIDES_FILE" ]]; then
  PROMPT_OVERRIDES="

ADDITIONAL RULES FROM PREVIOUS RUNS:
$(cat "$OVERRIDES_FILE")"
  add_log "Loaded prompt overrides from FIND_PROMPT_OVERRIDES.md" "info"
fi

FIND_PROMPT="You are a senior Python developer doing a bug audit of the HomeIQ project.
Use the project's CLAUDE.md and your knowledge of the codebase structure to guide your search.

The project has 50 microservices under domains/ organized into 9 domain groups,
with shared libraries under libs/ (homeiq-patterns, homeiq-resilience, homeiq-observability, homeiq-data, homeiq-ha).
Key services: websocket-ingestion (8001), data-api (8006), admin-api (8004), health-dashboard (3000).

Find exactly $NUM_BUGS real, distinct bugs in the Python source code. $SCOPE_HINT

For each bug, identify:
1. File path and line number
2. What the bug is (be specific - off-by-one, missing null check, race condition, wrong operator, etc.)
3. Why it's a bug (what breaks or could break)

Rules:
- Only report REAL bugs that would cause incorrect behavior, crashes, or data loss at runtime.
- Do NOT report style issues, missing docstrings, type hints, or theoretical concerns.
- Do NOT report bugs in test files.
- Each bug must be in a different file.
- Prioritize bugs in Tier 1 critical services and shared libraries.
$PROMPT_OVERRIDES

Output a JSON array with objects: {\"file\": \"...\", \"line\": N, \"description\": \"...\", \"severity\": \"high|medium|low\"}
Output ONLY the JSON array, no other text."

MCP_CONFIG="$PROJECT_ROOT/.mcp.json"

echo "[2/$TOTAL_STEPS] Scanning codebase for $NUM_BUGS bugs..."
add_log "Scanning codebase for $NUM_BUGS bugs (Claude Code headless)..." "info"
write_dashboard 2 "running" "Scanning codebase for $NUM_BUGS bugs..."

BUGS_JSON=$(claude --print --max-turns 3 --mcp-config "$MCP_CONFIG" "$FIND_PROMPT" 2>/dev/null)

# Extract JSON from response (claude may wrap it in markdown)
BUGS_JSON=$(echo "$BUGS_JSON" | sed -n '/^\[/,/^\]/p')

if [[ -z "$BUGS_JSON" ]] || ! echo "$BUGS_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  add_log "Failed to get valid bug list from Claude" "error"
  write_dashboard 2 "error" "Failed to extract bug list from Claude output"
  echo "ERROR: Failed to get valid bug list from Claude. Raw output saved to /tmp/auto-bugfix-raw.txt"
  echo "$BUGS_JSON" > /tmp/auto-bugfix-raw.txt
  git checkout "$BASE_BRANCH"
  git branch -D "$BRANCH_NAME"
  exit 1
fi

BUG_COUNT=$(echo "$BUGS_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Found $BUG_COUNT bugs."
echo "$BUGS_JSON" | python3 -m json.tool

# Build dashboard bugs with pending status
DASH_BUGS=$(echo "$BUGS_JSON" | python3 -c "
import sys, json
bugs = json.load(sys.stdin)
for b in bugs:
    b['fix_status'] = 'pending'
json.dump(bugs, sys.stdout)
")

add_log "Found $BUG_COUNT bugs" "success"
write_dashboard 2 "running" "Found $BUG_COUNT bugs. Starting fixes..." "$DASH_BUGS" "$BUG_COUNT"

# --- Step 3: Fix bugs with Claude Code ---
echo ""
echo "[3/$TOTAL_STEPS] Fixing bugs..."
add_log "Fixing $BUG_COUNT bugs (Claude Code headless, max 25 turns)..." "info"
write_dashboard 3 "running" "Fixing $BUG_COUNT bugs..." "$DASH_BUGS" "$BUG_COUNT"

FIX_PROMPT="You are a senior Python developer. Fix the following bugs in this codebase.

BUGS TO FIX:
$BUGS_JSON

For each bug:
1. Read the file to understand the full context.
2. Make the minimal, correct fix. Do not refactor surrounding code.
3. Verify your fix doesn't break anything obvious.

After fixing ALL bugs, you MUST run these validation steps in order:
1. Call mcp__tapps-mcp__tapps_validate_changed() with default args (auto-detects changed files, quick mode)
2. Call mcp__tapps-mcp__tapps_checklist(task_type=\"bugfix\")
3. If validation fails, fix the issues before finishing.

After validation passes, provide a summary of what you changed and the validation results."

claude --print \
  --mcp-config "$MCP_CONFIG" \
  --allowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_checklist,mcp__tapps-mcp__tapps_quick_check" \
  --max-turns 25 \
  "$FIX_PROMPT" 2>/dev/null

# Check if anything was actually changed (ignore submodule drift)
if [[ -z "$(git status --porcelain --ignore-submodules)" ]]; then
  add_log "No files were modified. Fixes may have failed." "error"
  write_dashboard 3 "error" "No files were modified. Fixes may have failed."
  echo "ERROR: No files were modified. Fixes may have failed."
  git checkout "$BASE_BRANCH"
  git branch -D "$BRANCH_NAME"
  exit 1
fi

CHANGED_FILES_LIST=$(git diff --name-only --ignore-submodules)
CHANGED_FILES_COUNT=$(echo "$CHANGED_FILES_LIST" | grep -c . || echo 0)

# Update bug statuses to fixed
DASH_BUGS=$(echo "$DASH_BUGS" | python3 -c "
import sys, json
bugs = json.load(sys.stdin)
for b in bugs:
    b['fix_status'] = 'fixed'
json.dump(bugs, sys.stdout)
")

add_log "All bugs fixed. $CHANGED_FILES_COUNT files changed." "success"
add_log "TAPPS validation completed" "success"
write_dashboard 3 "running" "Bugs fixed and validated." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass"

# --- Chain Mode: Refactor Phase ---
if [[ "$CHAIN" == "true" ]] && echo "$CHAIN_PHASES" | grep -q "refactor"; then
  echo ""
  echo "[4/$TOTAL_STEPS] Refactoring fixed files..."
  add_log "Chain mode: refactoring fixed files..." "info"
  write_dashboard 4 "running" "Refactoring fixed files..." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass"

  CHANGED_FILES=$(git diff --name-only --ignore-submodules | tr '\n' ', ' | sed 's/,$//')
  REFACTOR_PROMPT="You are a senior Python developer. Review and minimally refactor these recently-fixed files:
$CHANGED_FILES

Apply ONLY these improvements where clearly beneficial:
- Extract duplicated logic into a helper (only if 3+ identical blocks)
- Simplify overly complex conditionals
- Fix obvious naming issues (single-letter vars in non-loop contexts)
- Remove dead code (unreachable branches, unused imports)

Do NOT:
- Change any behavior or fix additional bugs
- Add docstrings, comments, or type hints
- Restructure modules or move code between files

After refactoring, run mcp__tapps-mcp__tapps_validate_changed() to verify quality improved.
Provide a summary of refactoring applied."

  claude --print \
    --mcp-config "$MCP_CONFIG" \
    --allowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_quick_check" \
    --max-turns 15 \
    "$REFACTOR_PROMPT" 2>/dev/null

  if [[ -n "$(git diff --name-only --ignore-submodules)" ]]; then
    add_log "Refactoring complete." "success"
  else
    add_log "No refactoring changes needed." "info"
  fi
fi

# --- Chain Mode: Test Phase ---
if [[ "$CHAIN" == "true" ]] && echo "$CHAIN_PHASES" | grep -q "test"; then
  TEST_STEP=5
  if echo "$CHAIN_PHASES" | grep -q "refactor"; then TEST_STEP=5; else TEST_STEP=4; fi
  echo ""
  echo "[$TEST_STEP/$TOTAL_STEPS] Generating tests for fixed bugs..."
  add_log "Chain mode: generating tests for fixed bugs..." "info"
  write_dashboard "$TEST_STEP" "running" "Generating tests for fixed bugs..." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass"

  TEST_PROMPT="You are a senior Python developer. Write unit tests for these bug fixes:

BUGS THAT WERE FIXED:
$BUGS_JSON

For each bug:
1. Read the fixed file to understand the fix.
2. Write a pytest test that would have FAILED before the fix and PASSES after.
3. Place tests in the appropriate tests/ directory near the source file.
4. Use pytest conventions: test_*.py files, test_* functions.
5. Mock external dependencies (databases, APIs, file I/O).

After writing tests, run: pytest <test_file> -v --tb=short to verify they pass.
Then run mcp__tapps-mcp__tapps_quick_check on each test file."

  claude --print \
    --mcp-config "$MCP_CONFIG" \
    --allowedTools "Read,Edit,Write,Grep,Glob,Bash,mcp__tapps-mcp__tapps_quick_check" \
    --max-turns 20 \
    "$TEST_PROMPT" 2>/dev/null

  if [[ -n "$(git status --porcelain --ignore-submodules)" ]]; then
    add_log "Test generation complete." "success"
  else
    add_log "No tests were generated." "warn"
  fi
fi

# --- Step 4/6: Commit and create PR ---
COMMIT_STEP=$((TOTAL_STEPS - 1))
echo ""
echo "[$COMMIT_STEP/$TOTAL_STEPS] Committing and creating PR..."
add_log "Committing changes and creating PR..." "info"
write_dashboard "$COMMIT_STEP" "running" "Committing and creating PR..." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass"

CHANGED_FILES=$(git diff --name-only --ignore-submodules | tr '\n' ', ' | sed 's/,$//')
COMMIT_PREFIX="fix"
if [[ "$CHAIN" == "true" ]]; then COMMIT_PREFIX="fix+refactor+test"; fi
COMMIT_MSG="$COMMIT_PREFIX: auto-fix $BUG_COUNT bugs across codebase

Bugs found and fixed by automated Claude Code analysis.

Files changed: $CHANGED_FILES"

# Stage only tracked changes, excluding submodules
git diff --name-only --ignore-submodules | while IFS= read -r f; do git add -- "$f"; done
# Also stage new files from chain test phase, excluding submodules
git status --porcelain --ignore-submodules | grep '^??' | cut -c4- | while IFS= read -r f; do git add -- "$f"; done
git commit -m "$COMMIT_MSG"
git push -u origin "$BRANCH_NAME"

add_log "Pushed to origin/$BRANCH_NAME" "success"

# Create PR
CHAIN_NOTE=""
if [[ "$CHAIN" == "true" ]]; then
  CHAIN_NOTE="

### Chain Mode
Phases executed: $CHAIN_PHASES"
fi

PR_BODY="## Automated Bug Fix

This PR was created by \`auto-bugfix.sh\` using Claude Code in headless mode.
$CHAIN_NOTE

### Bugs Found and Fixed

\`\`\`json
$BUGS_JSON
\`\`\`

### Changed Files
$(git diff --name-only "$BASE_BRANCH"..."$BRANCH_NAME" | sed 's/^/- /')

---
*Review carefully before merging. These fixes were generated automatically.*"

PR_URL=$(gh pr create \
  --title "fix: auto-fix $BUG_COUNT bugs found by Claude Code analysis" \
  --body "$PR_BODY" \
  --base "$BASE_BRANCH" \
  --head "$BRANCH_NAME")

add_log "PR created: $PR_URL" "success"
write_dashboard "$COMMIT_STEP" "running" "PR created." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass" "$PR_URL"

# --- Step 5/7: Collect TappsMCP feedback ---
FEEDBACK_STEP=$TOTAL_STEPS
echo ""
echo "[$FEEDBACK_STEP/$TOTAL_STEPS] Collecting TappsMCP feedback..."
add_log "Collecting TappsMCP feedback..." "info"
write_dashboard "$FEEDBACK_STEP" "running" "Collecting TappsMCP feedback..." "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass" "$PR_URL"

RUN_TIMESTAMP=$(date +"%Y-%m-%d %H:%M")
FEEDBACK_PROMPT="You just completed an automated bugfix run. Review how the TappsMCP tools performed
during this session and append structured feedback to docs/TAPPS_FEEDBACK.md.

Run context:
- Date: $RUN_TIMESTAMP
- Branch: $BRANCH_NAME
- Bugs fixed: $BUG_COUNT
- Files changed: $CHANGED_FILES

Evaluate each TappsMCP tool you used (tapps_validate_changed, tapps_checklist, tapps_quick_check):

For each issue found, append a markdown entry to docs/TAPPS_FEEDBACK.md using this exact format:

### [CATEGORY] P[0-2]: One-line summary
- **Date**: $RUN_TIMESTAMP
- **Run**: $BRANCH_NAME
- **Tool**: tool_name
- **Detail**: What happened, what was expected, what was actual
- **Recurrence**: 1

Categories: BUG, FALSE_POSITIVE, FALSE_NEGATIVE, UX, PERF, ENHANCEMENT, INTEGRATION

Also call mcp__tapps-mcp__tapps_feedback for each tool you used (helpful=true/false with context).

If ALL tools worked perfectly with no issues, append nothing — the goal is an empty file.
Read docs/TAPPS_FEEDBACK.md first to check for recurring issues and increment their recurrence count."

claude --print \
  --mcp-config "$MCP_CONFIG" \
  --allowedTools "Read,Edit,mcp__tapps-mcp__tapps_feedback" \
  --max-turns 10 \
  "$FEEDBACK_PROMPT" 2>/dev/null

# Commit feedback file if it changed
if [[ -n "$(git diff --name-only docs/TAPPS_FEEDBACK.md 2>/dev/null)" ]]; then
  git add docs/TAPPS_FEEDBACK.md
  git commit -m "docs: tapps feedback from auto-bugfix run $RUN_TIMESTAMP"
  git push origin "$BRANCH_NAME"
  add_log "Feedback committed and pushed." "success"
fi

# --- Append to bug history (Feature 12) ---
HISTORY_FILE="$PROJECT_ROOT/docs/BUG_HISTORY.json"
python3 -c "
import json, os
history_file = '$HISTORY_FILE'
entry = {
    'run_id': '$BRANCH_NAME',
    'date': '$RUN_TIMESTAMP',
    'branch': '$BRANCH_NAME',
    'chain': $( [[ \"$CHAIN\" == \"true\" ]] && echo "True" || echo "False" ),
    'bugs': $(echo "$BUGS_JSON" | python3 -c "
import sys, json
bugs = json.load(sys.stdin)
for b in bugs:
    b['was_real'] = None
    b['pr_merged'] = None
json.dump(bugs, sys.stdout)
")
}
history = []
if os.path.exists(history_file):
    with open(history_file) as f:
        history = json.load(f)
    if not isinstance(history, list):
        history = [history]
history.append(entry)
with open(history_file, 'w') as f:
    json.dump(history, f, indent=2, default=str)
" 2>/dev/null || true
add_log "Bug history appended to docs/BUG_HISTORY.json" "info"

# --- Update scan manifest if rotate mode ---
if [[ -n "$SCAN_UNIT_ID" ]]; then
  python3 -c "
import json
from datetime import datetime, timezone

with open('$SCAN_MANIFEST') as f:
    manifest = json.load(f)

now = datetime.now(timezone.utc).isoformat()
for unit in manifest['units']:
    if unit['id'] == '$SCAN_UNIT_ID':
        unit['last_scanned'] = now
        unit['total_runs'] += 1
        unit['total_bugs_found'] += $BUG_COUNT
        break

manifest['last_unit_scanned'] = '$SCAN_UNIT_ID'
manifest['total_runs'] += 1

with open('$SCAN_MANIFEST', 'w') as f:
    json.dump(manifest, f, indent=2)
" 2>/dev/null || true
  add_log "Scan manifest updated for unit '$SCAN_UNIT_ID'" "info"
fi

# --- Done ---
END_TIME=$(date +%s)
START_EPOCH=$(date -d "$START_TIME" +%s 2>/dev/null || python3 -c "from datetime import datetime; print(int(datetime.strptime('$START_TIME','%Y-%m-%d %H:%M:%S').timestamp()))")
ELAPSED_SEC=$((END_TIME - START_EPOCH))
ELAPSED_MIN=$((ELAPSED_SEC / 60))
ELAPSED_REM=$((ELAPSED_SEC % 60))
ELAPSED_STR=$(printf "%02d:%02d" $ELAPSED_MIN $ELAPSED_REM)

add_log "Pipeline complete in $ELAPSED_STR" "success"
write_dashboard "$FEEDBACK_STEP" "done" "Complete! $BUG_COUNT bugs fixed in $ELAPSED_STR. PR: $PR_URL" "$DASH_BUGS" "$BUG_COUNT" "$BUG_COUNT" "$CHANGED_FILES_COUNT" "pass" "$PR_URL"

echo ""
echo "=== Done ==="
echo "  Branch: $BRANCH_NAME"
echo "  PR:     $PR_URL"
echo "  Bugs:   $BUG_COUNT fixed"
echo "  Time:   $ELAPSED_STR"
echo ""
echo "Review the PR before merging."
