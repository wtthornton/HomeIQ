#!/usr/bin/env bash
# Nightly read-only audit of the HA init agent, via the ha-setup-service
# gateway. Writes a dated report artifact; safe to run at any time (the
# audit endpoint issues zero writes).
#
# Cron (installed by feat/ha-init-agent-activation):
#   15 3 * * * /home/wtthornton/code/HomeIQ/scripts/init-agent-nightly-audit.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${REPO_ROOT}/.tapps-mcp"
OUT_FILE="${OUT_DIR}/init-audit-$(date -u +%Y%m%d).json"

mkdir -p "${OUT_DIR}"

if curl -sf -m 120 http://localhost:8024/api/v1/init/audit -o "${OUT_FILE}.tmp"; then
    mv "${OUT_FILE}.tmp" "${OUT_FILE}"
    echo "init audit written to ${OUT_FILE}"
else
    rm -f "${OUT_FILE}.tmp"
    echo "init audit FAILED at $(date -u +%FT%TZ)" >&2
    exit 1
fi
