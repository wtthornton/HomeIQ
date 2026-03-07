#!/usr/bin/env bash
# auto-bugfix-parallel.sh — Run multiple auto-bugfix scans in parallel using git worktrees.
#
# Each scan unit gets its own worktree + branch, running concurrently.
# Results: one PR per scan unit, merged independently.
#
# Usage:
#   ./scripts/auto-bugfix-parallel.sh                              # Top 3 units by priority
#   ./scripts/auto-bugfix-parallel.sh --max-parallel 4             # Run 4 at once
#   ./scripts/auto-bugfix-parallel.sh --units "libs,core-platform" # Specific units
#   ./scripts/auto-bugfix-parallel.sh --all                        # All 14 units (batched)
#   ./scripts/auto-bugfix-parallel.sh --bugs 3                     # 3 bugs per unit
#   ./scripts/auto-bugfix-parallel.sh --dry-run                    # Show what would run
#   ./scripts/auto-bugfix-parallel.sh --cleanup                    # Remove worktrees + branches
#
# Requirements:
#   - claude CLI, git, gh, python3
#   - Clean working tree on master

set -euo pipefail

# --- Defaults ---
MAX_PARALLEL=3
NUM_BUGS=1
UNITS=""
ALL=false
BASE_BRANCH="master"
CHAIN=false
CHAIN_PHASES="fix,refactor,test"
DRY_RUN=false
CLEANUP=false
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --max-parallel)  MAX_PARALLEL="$2";    shift 2 ;;
    --bugs)          NUM_BUGS="$2";        shift 2 ;;
    --units)         UNITS="$2";           shift 2 ;;
    --all)           ALL=true;             shift ;;
    --base)          BASE_BRANCH="$2";     shift 2 ;;
    --chain)         CHAIN=true;           shift ;;
    --chain-phases)  CHAIN=true; CHAIN_PHASES="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=true;         shift ;;
    --cleanup)       CLEANUP=true;         shift ;;
    -h|--help)
      echo "Usage: $0 [--max-parallel N] [--bugs N] [--units LIST] [--all] [--base BRANCH] [--chain] [--dry-run] [--cleanup]"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_ROOT"
WORKTREE_BASE="$PROJECT_ROOT/.worktrees"
SCAN_MANIFEST="$PROJECT_ROOT/docs/scan-manifest.json"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# --- Cleanup mode ---
if [[ "$CLEANUP" == "true" ]]; then
  echo "=== Cleaning up bugfix worktrees ==="
  if [[ -d "$WORKTREE_BASE" ]]; then
    for d in "$WORKTREE_BASE"/bugfix-*; do
      [[ -d "$d" ]] || continue
      echo "  Removing worktree: $d"
      git worktree remove "$d" --force 2>/dev/null || rm -rf "$d"
    done
    rmdir "$WORKTREE_BASE" 2>/dev/null || true
  fi
  git worktree prune
  echo "  Pruned stale references."

  # List bugfix branches
  branches=$(git branch --list "auto/bugfix-*" 2>/dev/null | sed 's/^[* ]*//')
  if [[ -n "$branches" ]]; then
    echo ""
    echo "  Bugfix branches:"
    echo "$branches" | sed 's/^/    /'
    read -rp "  Delete these branches? (y/N) " confirm
    if [[ "$confirm" == "y" ]]; then
      echo "$branches" | while IFS= read -r b; do
        git branch -D "$b" 2>/dev/null && echo "    Deleted $b"
      done
    fi
  fi
  echo ""
  echo "Cleanup complete."
  exit 0
fi

# --- Preflight ---
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

CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "$BASE_BRANCH" ]]; then
  echo "Switching to '$BASE_BRANCH'..."
  git checkout "$BASE_BRANCH"
fi

# --- Select scan units ---
if [[ ! -f "$SCAN_MANIFEST" ]]; then
  echo "ERROR: Scan manifest not found at $SCAN_MANIFEST"
  exit 1
fi

ALL_LOWER=$(echo "$ALL" | tr '[:upper:]' '[:lower:]')
SELECTED=$(python3 -c "
import json, sys
from datetime import datetime, timezone

with open('$SCAN_MANIFEST') as f:
    manifest = json.load(f)

requested = '$UNITS'.split(',') if '$UNITS' else []
select_all = $([[ "$ALL" == "true" ]] && echo "True" || echo "False")
max_count = $MAX_PARALLEL

now = datetime.now(timezone.utc)
scored = []

for unit in manifest['units']:
    if requested and unit['id'] not in requested:
        continue
    if unit['last_scanned']:
        last = datetime.fromisoformat(unit['last_scanned'])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max((now - last).total_seconds() / 86400, 0.1)
    else:
        days = 365
    bug_boost = 1 + unit['total_bugs_found'] / 5
    fp_penalty = 1 - (unit['false_positives'] / max(unit['total_bugs_found'], 1)) * 0.3
    score = unit['priority_weight'] * days * bug_boost * max(fp_penalty, 0.5)
    scored.append((score, unit))

scored.sort(key=lambda x: x[0], reverse=True)

if requested:
    selected = [u for _, u in scored]
elif select_all:
    selected = [u for _, u in scored]
else:
    selected = [u for _, u in scored[:max_count]]

for u in selected:
    print(f\"{u['id']}|{u['path']}|{u['name']}|{u['scan_hint']}\")
" 2>/dev/null)

if [[ -z "$SELECTED" ]]; then
  echo "ERROR: No scan units selected."
  exit 1
fi

# Parse selected units
UNIT_IDS=()
UNIT_PATHS=()
UNIT_NAMES=()
while IFS='|' read -r uid upath uname uhint; do
  UNIT_IDS+=("$uid")
  UNIT_PATHS+=("$upath")
  UNIT_NAMES+=("$uname")
done <<< "$SELECTED"

UNIT_COUNT=${#UNIT_IDS[@]}

# --- Display plan ---
echo ""
echo "=== Auto-Bugfix Parallel ==="
echo "  Units:       $UNIT_COUNT"
echo "  Parallel:    $MAX_PARALLEL"
echo "  Bugs/unit:   $NUM_BUGS"
echo "  Base:        $BASE_BRANCH"
if [[ "$CHAIN" == "true" ]]; then echo "  Chain:       $CHAIN_PHASES"; fi
echo ""
echo "  Scan plan:"
for i in "${!UNIT_IDS[@]}"; do
  printf "    %-22s -> auto/bugfix-%s-%s\n" "${UNIT_IDS[$i]}" "${UNIT_IDS[$i]}" "$TIMESTAMP"
done
echo ""

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN: Would create $UNIT_COUNT worktrees and run scans."
  echo "Remove --dry-run to execute."
  exit 0
fi

# --- Create worktrees ---
mkdir -p "$WORKTREE_BASE"

# Ensure .worktrees is gitignored
if ! grep -q '\.worktrees/' "$PROJECT_ROOT/.gitignore" 2>/dev/null; then
  echo -e "\n# Parallel bugfix worktrees\n.worktrees/" >> "$PROJECT_ROOT/.gitignore"
  echo "  Added .worktrees/ to .gitignore"
fi

SCRIPT_PATH="$PROJECT_ROOT/scripts/auto-bugfix.sh"
MCP_CONFIG="$PROJECT_ROOT/.mcp.json"
PIDS=()
LOG_FILES=()
BRANCHES=()

run_scan() {
  local idx=$1
  local unit_id="${UNIT_IDS[$idx]}"
  local unit_path="${UNIT_PATHS[$idx]}"
  local branch="auto/bugfix-${unit_id}-${TIMESTAMP}"
  local wt_path="$WORKTREE_BASE/bugfix-${unit_id}"
  local log_file="$WORKTREE_BASE/bugfix-${unit_id}.log"

  # Clean stale worktree
  if [[ -d "$wt_path" ]]; then
    git worktree remove "$wt_path" --force 2>/dev/null || rm -rf "$wt_path"
  fi
  git branch -D "$branch" 2>/dev/null || true

  # Create worktree
  git worktree add "$wt_path" -b "$branch" "$BASE_BRANCH" 2>/dev/null
  if [[ $? -ne 0 ]]; then
    echo "  ERROR: Failed to create worktree for $unit_id" >&2
    return 1
  fi

  # Copy MCP config
  [[ -f "$MCP_CONFIG" ]] && cp "$MCP_CONFIG" "$wt_path/.mcp.json"

  # Build args
  local args=(
    --bugs "$NUM_BUGS"
    --branch "$branch"
    --target-dir "$unit_path"
    --base "$BASE_BRANCH"
    --rotate
    --target-unit "$unit_id"
    --no-dashboard
    --worktree
  )
  if [[ "$CHAIN" == "true" ]]; then
    args+=(--chain --chain-phases "$CHAIN_PHASES")
  fi

  # Run inside worktree
  (cd "$wt_path" && bash "$SCRIPT_PATH" "${args[@]}") > "$log_file" 2>&1
  return $?
}

# --- Launch scans with throttling ---
START_EPOCH=$(date +%s)
echo "Launching $UNIT_COUNT scans (max $MAX_PARALLEL concurrent)..."
echo ""

active_pids=()
active_units=()
results=()

for i in "${!UNIT_IDS[@]}"; do
  # Throttle: wait if at max parallel
  while [[ ${#active_pids[@]} -ge $MAX_PARALLEL ]]; do
    for pi in "${!active_pids[@]}"; do
      if ! kill -0 "${active_pids[$pi]}" 2>/dev/null; then
        wait "${active_pids[$pi]}" 2>/dev/null
        exit_code=$?
        results+=("${active_units[$pi]}|$exit_code")
        if [[ $exit_code -eq 0 ]]; then
          echo "  DONE: ${active_units[$pi]} (OK)"
        else
          echo "  DONE: ${active_units[$pi]} (FAILED)"
        fi
        unset 'active_pids[pi]'
        unset 'active_units[pi]'
        # Re-index arrays
        active_pids=("${active_pids[@]}")
        active_units=("${active_units[@]}")
        break
      fi
    done
    sleep 2
  done

  echo "  START: ${UNIT_IDS[$i]}"
  run_scan "$i" &
  active_pids+=($!)
  active_units+=("${UNIT_IDS[$i]}")
  BRANCHES+=("auto/bugfix-${UNIT_IDS[$i]}-${TIMESTAMP}")
done

# Wait for remaining
for pi in "${!active_pids[@]}"; do
  wait "${active_pids[$pi]}" 2>/dev/null
  exit_code=$?
  results+=("${active_units[$pi]}|$exit_code")
  if [[ $exit_code -eq 0 ]]; then
    echo "  DONE: ${active_units[$pi]} (OK)"
  else
    echo "  DONE: ${active_units[$pi]} (FAILED)"
  fi
done

# --- Report ---
END_EPOCH=$(date +%s)
ELAPSED=$((END_EPOCH - START_EPOCH))
ELAPSED_MIN=$((ELAPSED / 60))
ELAPSED_SEC=$((ELAPSED % 60))
ELAPSED_STR=$(printf "%02d:%02d" $ELAPSED_MIN $ELAPSED_SEC)

echo ""
echo "=== Parallel Scan Results ==="
echo "  Total time: $ELAPSED_STR"
echo ""

succeeded=0
failed=0

printf "%-22s %-8s %s\n" "UNIT" "STATUS" "LOG"
printf '%80s\n' | tr ' ' '-'

for r in "${results[@]}"; do
  IFS='|' read -r uid ecode <<< "$r"
  log="$WORKTREE_BASE/bugfix-${uid}.log"
  if [[ "$ecode" -eq 0 ]]; then
    ((succeeded++))
    printf "%-22s %-8s %s\n" "$uid" "OK" "$log"
  else
    ((failed++))
    printf "%-22s %-8s %s\n" "$uid" "FAIL" "$log"
  fi
done

echo ""
echo "Summary: $succeeded succeeded, $failed failed out of ${#results[@]} scans"

# --- Cleanup worktrees ---
echo ""
echo "Cleaning up worktrees..."
for uid in "${UNIT_IDS[@]}"; do
  wt="$WORKTREE_BASE/bugfix-${uid}"
  [[ -d "$wt" ]] && git worktree remove "$wt" --force 2>/dev/null && echo "  Removed: $wt"
done
git worktree prune 2>/dev/null
git checkout "$BASE_BRANCH" 2>/dev/null

echo ""
echo "=== Done ==="
echo "  Scans:   ${#results[@]} ($succeeded OK, $failed failed)"
echo "  Time:    $ELAPSED_STR"
echo "  Cleanup: ./scripts/auto-bugfix-parallel.sh --cleanup"
echo ""
if [[ $succeeded -gt 0 ]]; then
  echo "PRs created for successful scans. Review and merge them:"
  echo "  gh pr list --author @me"
fi
