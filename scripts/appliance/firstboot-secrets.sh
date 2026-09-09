#!/usr/bin/env bash
#
# firstboot-secrets.sh -- mint the appliance's tier-1 secrets, once (TAP-6573).
#
# On the FIRST boot this writes $HOMEIQ_STATE_DIR/.env (default
# /var/lib/homeiq/.env) with a freshly generated value for every key below, at
# mode 0600. On EVERY LATER boot it checks that file and leaves it alone. It is
# never rewritten in place: re-minting POSTGRES_PASSWORD after postgres_data has
# initialised locks the appliance out of its own database.
#
# See docs/architecture/adr-appliance-secret-store.md (Accepted 2026-08-26) for
# why tier 1 is a root-owned file rather than a row in the store it bootstraps.
#
# What is generated
# -----------------
# The ADR's tier-1 six, plus HOMEIQ_SECRET_DEK (the 256-bit key that seals the
# tier-2 table), plus the three further keys the compose files gate with
# ${VAR:?required} -- ADMIN_PASSWORD, HOMEIQ_MCP_READ_TOKENS, INFLUXDB_PASSWORD.
# Without those three `docker compose config` cannot render at all, so the union
# is what an appliance actually needs to boot.
#
# POSTGRES_USER is the one deliberate exception: it is a fixed, non-secret
# account name ("homeiq"), not a credential. Randomising it would buy nothing
# and would break every operator runbook that names it. Every other value here
# is 256 bits of randomness, different on every install.
#
# The compose marker list is PINNED below rather than derived at runtime -- a
# boot script that greps the repo it is not shipped with would be deriving from
# nothing. tests/test_firstboot_secrets.py compares the pin against the live
# compose files, so adding a ${NEW_KEY:?required} anywhere turns the suite red.
#
# Environment
# -----------
#   HOMEIQ_STATE_DIR   Directory holding .env. Default /var/lib/homeiq.
#                      Overridable so the tests can run unprivileged against a
#                      scratch directory. On an appliance this script runs as
#                      root and the file is root-owned; run by an ordinary user
#                      the owner is that user and the mode is still 0600.
#
# Usage
# -----
#   firstboot-secrets.sh                      generate on first boot, else check
#   firstboot-secrets.sh --list-keys          print the generated key names
#   firstboot-secrets.sh --list-compose-markers
#                                             print the pinned ${VAR:?required} set
#
# Exit codes
# ----------
#   0   generated, or the existing file passed its check
#   78  preflight-failure -- the file exists but a key is missing or empty. The
#       stack must not start. No default is ever substituted and the file is not
#       repaired, because a repaired POSTGRES_PASSWORD is an unopenable database.
#       Mirrors homeiq_ha.secrets.states.EXIT_CODES[PREFLIGHT_FAILURE].
#   2   bad usage
#
# Nothing here ever prints a generated value. There is no `set -x`: it would put
# every secret in the boot log, which is the exact failure this file exists to
# prevent.

set -euo pipefail

STATE_DIR="${HOMEIQ_STATE_DIR:-/var/lib/homeiq}"
ENV_FILE="${STATE_DIR}/.env"

# Kept in step with homeiq_ha.secrets.states.EXIT_CODES by
# test_val063_the_script_preflight_exit_code_matches_the_module_constant.
EXIT_PREFLIGHT_FAILURE=78
EXIT_USAGE=2

# The account name is fixed and public; see the header.
POSTGRES_USER_VALUE="homeiq"

# Order is the order they are written to the file.
GENERATED_KEYS=(
  POSTGRES_USER
  POSTGRES_PASSWORD
  INFLUXDB_TOKEN
  INFLUXDB_PASSWORD
  API_KEY
  ADMIN_API_JWT_SECRET
  ADMIN_PASSWORD
  GF_SECURITY_ADMIN_PASSWORD
  HOMEIQ_MCP_READ_TOKENS
  HOMEIQ_SECRET_DEK
)

# The ${VAR:?required} markers across domains/*/compose.yml, sorted. Pinned, and
# checked against the live files by the test suite -- see the header.
COMPOSE_REQUIRED_MARKERS=(
  ADMIN_API_JWT_SECRET
  ADMIN_PASSWORD
  GF_SECURITY_ADMIN_PASSWORD
  HOMEIQ_MCP_READ_TOKENS
  INFLUXDB_PASSWORD
  INFLUXDB_TOKEN
  POSTGRES_PASSWORD
)

log() {
  printf 'firstboot-secrets: %s\n' "$1"
}

err() {
  printf 'firstboot-secrets: %s\n' "$1" >&2
}

# Identical in shape to scripts/setup-secure-env.sh:55 -- openssl when it is
# present, /dev/urandom when it is not. Never $RANDOM (16 bits, seeded from the
# pid and the clock) and never a date-derived value.
generate_secret() {
  openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32
}

value_for() {
  case "$1" in
    POSTGRES_USER) printf '%s' "$POSTGRES_USER_VALUE" ;;
    *) generate_secret ;;
  esac
}

# Write the file through a temp file in the same directory, so the final path
# either does not exist or is complete -- a half-written .env would fail
# preflight on the next boot and be unrepairable by design.
write_env_file() {
  (
    # 077 before the file is created, so it is never world-readable even for the
    # instant between creation and the explicit chmod below.
    umask 077
    mkdir -p "$STATE_DIR"

    local tmp
    tmp="$(mktemp "${ENV_FILE}.XXXXXX")"
    trap 'rm -f "$tmp"' EXIT

    {
      printf '# HomeIQ appliance tier-1 secrets. Generated once on first boot by\n'
      printf '# scripts/appliance/firstboot-secrets.sh (TAP-6573). Never edit by hand and\n'
      printf '# never regenerate: POSTGRES_PASSWORD is the credential postgres_data was\n'
      printf '# initialised with. POSTGRES_USER is a fixed non-secret account name; every\n'
      printf '# other value below is 256 bits of randomness, unique to this install.\n'
      local key
      for key in "${GENERATED_KEYS[@]}"; do
        printf '%s=%s\n' "$key" "$(value_for "$key")"
      done
    } >"$tmp"

    chmod 600 "$tmp"
    mv "$tmp" "$ENV_FILE"
  )
}

# The existing file is authoritative. A key that is absent or empty is a named
# preflight failure, not an invitation to fill the gap.
check_env_file() {
  local key
  for key in "${GENERATED_KEYS[@]}"; do
    if ! grep -qE "^${key}=.+$" "$ENV_FILE"; then
      err "preflight-failure: ${key} is missing or empty in ${ENV_FILE}"
      err "preflight-failure: the stack must not start. No default was substituted and"
      err "preflight-failure: the file was not repaired -- see the ADR's failure table."
      exit "$EXIT_PREFLIGHT_FAILURE"
    fi
  done
}

main() {
  case "${1-}" in
    --list-keys)
      printf '%s\n' "${GENERATED_KEYS[@]}"
      return 0
      ;;
    --list-compose-markers)
      printf '%s\n' "${COMPOSE_REQUIRED_MARKERS[@]}"
      return 0
      ;;
    -h | --help)
      sed -n '3,60p' "$0"
      return 0
      ;;
    "") ;;
    *)
      err "unknown argument: $1"
      exit "$EXIT_USAGE"
      ;;
  esac

  if [ -f "$ENV_FILE" ]; then
    check_env_file
    log "reusing existing tier-1 file ${ENV_FILE} (${#GENERATED_KEYS[@]} keys present)"
    return 0
  fi

  write_env_file
  log "generated ${#GENERATED_KEYS[@]} tier-1 keys into ${ENV_FILE} (mode 0600, owner $(id -un))"
}

main "$@"
