#!/usr/bin/env bash
# auto-bugfix.sh — Automatically find bugs, fix them, and open a PR using Claude Code headless mode.
#
# Usage:
#   ./scripts/auto-bugfix.sh [--bugs N] [--branch NAME] [--target-dir PATH]
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

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --bugs)       NUM_BUGS="$2";       shift 2 ;;
    --branch)     BRANCH_NAME="$2";    shift 2 ;;
    --target-dir) TARGET_DIR="$2";     shift 2 ;;
    --base)       BASE_BRANCH="$2";    shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--bugs N] [--branch NAME] [--target-dir PATH] [--base BRANCH]"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_ROOT"

# --- Preflight checks ---
for cmd in claude git gh; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "ERROR: '$cmd' is not installed or not in PATH."
    exit 1
  fi
done

if [[ -n "$(git status --porcelain --ignore-submodules)" ]]; then
  echo "ERROR: Working tree is dirty. Commit or stash changes first."
  exit 1
fi

echo "=== Auto Bug Fix Pipeline ==="
echo "  Project:  $PROJECT_ROOT"
echo "  Bugs:     $NUM_BUGS"
echo "  Branch:   $BRANCH_NAME"
echo "  Base:     $BASE_BRANCH"
echo ""

# --- Step 1: Create feature branch ---
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]]; then
  echo "[1/5] Switching to '$BASE_BRANCH' and creating branch '$BRANCH_NAME'..."
  git checkout "$BASE_BRANCH"
else
  echo "[1/5] Already on '$BASE_BRANCH'. Creating branch '$BRANCH_NAME'..."
fi
git checkout -b "$BRANCH_NAME"

# --- Step 2: Find bugs with Claude Code ---
SCOPE_HINT=""
if [[ -n "$TARGET_DIR" ]]; then
  SCOPE_HINT="Focus your search on files under '$TARGET_DIR'."
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

Output a JSON array with objects: {\"file\": \"...\", \"line\": N, \"description\": \"...\", \"severity\": \"high|medium|low\"}
Output ONLY the JSON array, no other text."

echo "[2/5] Scanning codebase for $NUM_BUGS bugs..."
BUGS_JSON=$(claude --print --max-turns 3 "$FIND_PROMPT" 2>/dev/null)

# Extract JSON from response (claude may wrap it in markdown)
BUGS_JSON=$(echo "$BUGS_JSON" | sed -n '/^\[/,/^\]/p')

if [[ -z "$BUGS_JSON" ]] || ! echo "$BUGS_JSON" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
  echo "ERROR: Failed to get valid bug list from Claude. Raw output saved to /tmp/auto-bugfix-raw.txt"
  echo "$BUGS_JSON" > /tmp/auto-bugfix-raw.txt
  git checkout "$BASE_BRANCH"
  git branch -D "$BRANCH_NAME"
  exit 1
fi

BUG_COUNT=$(echo "$BUGS_JSON" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "  Found $BUG_COUNT bugs."
echo "$BUGS_JSON" | python3 -m json.tool

# --- Step 3: Fix bugs with Claude Code ---
echo ""
echo "[3/5] Fixing bugs..."

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
  --allowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_checklist,mcp__tapps-mcp__tapps_quick_check" \
  --max-turns 25 \
  "$FIX_PROMPT" 2>/dev/null

# Check if anything was actually changed
if [[ -z "$(git status --porcelain)" ]]; then
  echo "ERROR: No files were modified. Fixes may have failed."
  git checkout "$BASE_BRANCH"
  git branch -D "$BRANCH_NAME"
  exit 1
fi

# --- Step 4: Commit and create PR ---
echo ""
echo "[4/5] Committing and creating PR..."

# Build commit message
CHANGED_FILES=$(git diff --name-only | tr '\n' ', ' | sed 's/,$//')
COMMIT_MSG="fix: auto-fix $BUG_COUNT bugs across codebase

Bugs found and fixed by automated Claude Code analysis.

Files changed: $CHANGED_FILES"

git add -A
git commit -m "$COMMIT_MSG"
git push -u origin "$BRANCH_NAME"

# Create PR
PR_BODY="## Automated Bug Fix

This PR was created by \`auto-bugfix.sh\` using Claude Code in headless mode.

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

# --- Step 5: Collect TappsMCP feedback ---
echo ""
echo "[5/5] Collecting TappsMCP feedback..."

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
  --allowedTools "Read,Edit,mcp__tapps-mcp__tapps_feedback" \
  --max-turns 10 \
  "$FEEDBACK_PROMPT" 2>/dev/null

# Commit feedback file if it changed
if [[ -n "$(git diff --name-only docs/TAPPS_FEEDBACK.md)" ]]; then
  git add docs/TAPPS_FEEDBACK.md
  git commit -m "docs: tapps feedback from auto-bugfix run $RUN_TIMESTAMP"
  git push origin "$BRANCH_NAME"
fi

echo ""
echo "=== Done ==="
echo "  Branch: $BRANCH_NAME"
echo "  PR:     $PR_URL"
echo "  Bugs:   $BUG_COUNT fixed"
echo ""
echo "Review the PR before merging."
