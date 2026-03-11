#!/usr/bin/env bash
# auto-bugfix.sh — Thin wrapper for auto-bugfix.ps1 (config-driven).
# Invokes the PowerShell script with homeiq-default.yaml. Epic 52.
#
# Usage:
#   ./scripts/auto-bugfix.sh [--bugs N] [--branch NAME] [--target-dir PATH]
#   ./scripts/auto-bugfix.sh --bugs 1 --chain
#   ./scripts/auto-bugfix.sh --bugs 3 --no-dashboard

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_PATH="auto-fix-pipeline/config/example/homeiq-default.yaml"

# Convert common long args to PowerShell style
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --bugs)        ARGS+=(-Bugs "$2"); shift 2 ;;
    --branch)      ARGS+=(-Branch "$2"); shift 2 ;;
    --target-dir)  ARGS+=(-TargetDir "$2"); shift 2 ;;
    --base)        ARGS+=(-Base "$2"); shift 2 ;;
    --chain)       ARGS+=(-Chain); shift ;;
    --chain-phases) ARGS+=(-ChainPhases "$2"); shift 2 ;;
    --no-dashboard) ARGS+=(-NoDashboard); shift ;;
    --rotate)      shift ;;  # Script uses rotate by default; --rotate is no-op
    --target-unit) ARGS+=(-TargetUnit "$2"); shift 2 ;;
    --worktree)    ARGS+=(-Worktree); shift ;;
    -h|--help)
      echo "Usage: $0 [--bugs N] [--branch NAME] [--target-dir PATH] [--base BRANCH]"
      echo "       [--chain] [--chain-phases PHASES] [--no-dashboard] [--worktree]"
      echo "Invokes: scripts/auto-bugfix.ps1 -ConfigPath $CONFIG_PATH"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$PROJECT_ROOT"

if command -v pwsh &>/dev/null; then
  pwsh -ExecutionPolicy Bypass -File "$SCRIPT_DIR/auto-bugfix.ps1" -ConfigPath "$CONFIG_PATH" "${ARGS[@]}"
elif command -v powershell &>/dev/null; then
  powershell -ExecutionPolicy Bypass -File "$SCRIPT_DIR/auto-bugfix.ps1" -ConfigPath "$CONFIG_PATH" "${ARGS[@]}"
else
  echo "ERROR: pwsh or powershell required. Install PowerShell Core (pwsh) or Windows PowerShell."
  exit 1
fi
