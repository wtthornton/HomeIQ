#!/usr/bin/env bash
# Run an AgentForge integration-kit CLI against the homeiq project.
#
# Exists because a machine-global AGENTFORGE_API_KEY (exported into the systemd
# user session by unrelated NLT services) shadows this repo's key and makes every
# kit CLI fail with HTTP 401 key-invalid-or-revoked. This wrapper pins the key,
# URL, and slug from THIS repo so the kit never sees the global.
#
#   scripts/af.sh publish --gate-safe
#   scripts/af.sh publish --check-only
#   scripts/af.sh validate --tier quick
#   scripts/af.sh doctor
#
# Requires AGENTFORGE_REPO (or a sibling ../AgentForge checkout).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SLUG="homeiq"
LAYOUT="scout"

AGENTFORGE_REPO="${AGENTFORGE_REPO:-$(cd "${REPO_ROOT}/../AgentForge" 2>/dev/null && pwd || true)}"
if [[ -z "${AGENTFORGE_REPO}" || ! -d "${AGENTFORGE_REPO}/clients/agentforge-integration-kit" ]]; then
  echo "error: set AGENTFORGE_REPO to an AgentForge checkout (no kit found)" >&2
  exit 2
fi
KIT="${AGENTFORGE_REPO}/clients/agentforge-integration-kit/scripts"

# Read this repo's bearer from .env — never the ambient one. Matches the kit's
# documented precedence (dotenv beats a stale machine-global export).
key_from_env_file() {
  local env_file="${REPO_ROOT}/.env"
  [[ -f "${env_file}" ]] || return 1
  sed -nE 's/^AGENTFORGE_API_KEY[[:space:]]*=[[:space:]]*"?'"'"'?([^"'"'"'[:space:]]+).*/\1/p' "${env_file}" | head -1
}

AGENTFORGE_API_KEY="$(key_from_env_file || true)"
if [[ -z "${AGENTFORGE_API_KEY}" ]]; then
  echo "error: no AGENTFORGE_API_KEY in ${REPO_ROOT}/.env — see docs/AF-INTEGRATION.md" >&2
  exit 2
fi
export AGENTFORGE_API_KEY
export AGENTFORGE_URL="${AGENTFORGE_URL:-http://localhost:8010}"
export AGENTFORGE_PROJECT_SLUG="${SLUG}"

command="${1:-}"
[[ $# -gt 0 ]] && shift

case "${command}" in
  publish)
    exec uv run --project "${AGENTFORGE_REPO}" python "${KIT}/af_publish.py" \
      --slug "${SLUG}" --layout "${LAYOUT}" --repo-root "${REPO_ROOT}" "$@"
    ;;
  validate)
    exec uv run --project "${AGENTFORGE_REPO}" python "${KIT}/af_kit_validate.py" \
      --slug "${SLUG}" --base-url "${AGENTFORGE_URL}" "$@"
    ;;
  doctor)
    exec uv run --project "${AGENTFORGE_REPO}" python "${KIT}/af_doctor.py" \
      --slug "${SLUG}" --base-url "${AGENTFORGE_URL}" --repo-root "${REPO_ROOT}" "$@"
    ;;
  export)
    exec uv run --project "${AGENTFORGE_REPO}" python "${KIT}/af_export.py" \
      --slug "${SLUG}" --layout "${LAYOUT}" --repo-root "${REPO_ROOT}" "$@"
    ;;
  *)
    echo "usage: scripts/af.sh {publish|validate|doctor|export} [kit args...]" >&2
    exit 2
    ;;
esac
