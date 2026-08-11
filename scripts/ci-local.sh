#!/usr/bin/env bash
#
# ci-local.sh — reproduce .github/workflows/reusable-group-ci.yml steps 3-8 locally.
#
# The workflow's 46 (domain, service) matrix jobs are the ground truth this repo
# is judged by, and a full round trip through GitHub Actions costs ~20 minutes.
# This runs the same eight steps against the same inputs so a fix can be proven
# in seconds instead.
#
# Fidelity notes — where this deliberately matches CI, and where it cannot:
#   * `pytest` console script, never `python -m pytest`. The two disagree: the
#     module form prepends cwd to sys.path, the console script does not, so four
#     services pass under one and fail under the other. CI runs the console
#     script; so do we.
#   * Python 3.12 (/usr/bin/python3.12) to match setup-python's pin. The repo's
#     own .venv is 3.13.
#   * pgvector/pgvector:pg17, matching the workflow's service container.
#   * Host port is configurable (default 55432) because 5432 is usually taken by
#     the dev stack's homeiq-postgres. CI has the whole port to itself.
#
# Usage:
#   scripts/ci-local.sh                       # every matrix service, all lanes
#   scripts/ci-local.sh weather-api           # one service
#   scripts/ci-local.sh --lanes lint,format   # cheap lanes over everything
#   scripts/ci-local.sh --baseline            # write scripts/ci-baseline.json
#
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

WORK_DIR="${CI_LOCAL_WORK_DIR:-/tmp/homeiq-ci-local}"
VENV_ROOT="$WORK_DIR/venvs"
LOG_ROOT="$WORK_DIR/logs"
PY="${CI_LOCAL_PYTHON:-/usr/bin/python3.12}"
RUFF_VERSION="0.15.15"

PG_CONTAINER="${CI_LOCAL_PG_CONTAINER:-homeiq-ci-local-pg}"
PG_IMAGE="pgvector/pgvector:pg17"
PG_PORT="${CI_LOCAL_PG_PORT:-55432}"
PG_USER=homeiq
PG_PASSWORD=homeiq_test
PG_DB=homeiq_test

ALL_LANES="lint,format,dockerfile,libs,deps,schema,tests,alembic"
LANES="$ALL_LANES"
FILTER=""
BASELINE=0
KEEP_PG=0

while [ $# -gt 0 ]; do
  case "$1" in
    --lanes)    LANES="$2"; shift 2 ;;
    # --baseline only turns on the JSON write. It deliberately does NOT choose
    # lanes: it used to force deps+tests on, which silently overrode an explicit
    # --lanes and turned a "capture the numbers" run into a two-hour, 13 GB
    # build of 46 virtualenvs.
    --baseline) BASELINE=1; shift ;;
    --keep-pg)  KEEP_PG=1; shift ;;
    --python)   PY="$2"; shift 2 ;;
    -h|--help)  sed -n '2,30p' "$0"; exit 0 ;;
    -*)         echo "unknown flag: $1" >&2; exit 2 ;;
    *)          FILTER="$1"; shift ;;
  esac
done

has_lane() { [[ ",$LANES," == *",$1,"* ]]; }

mkdir -p "$VENV_ROOT" "$LOG_ROOT"

# ---------------------------------------------------------------------------
# Matrix — parsed from the group workflows rather than hardcoded, so this file
# cannot drift away from what CI actually runs.
# ---------------------------------------------------------------------------
matrix() {
  "$PY" - <<'PYEOF'
import glob, json, re
for path in sorted(glob.glob(".github/workflows/ci-*.yml")):
    text = open(path).read()
    domain = re.search(r"^\s+domain_dir:\s*(\S+)\s*$", text, re.M)
    services = re.search(r"^\s+services:\s*'(\[.*\])'\s*$", text, re.M)
    if not (domain and services):
        continue
    for svc in json.loads(services.group(1)):
        print(f"{domain.group(1)} {svc}")
PYEOF
}

# ---------------------------------------------------------------------------
# Throwaway postgres, matching the workflow's service container.
# ---------------------------------------------------------------------------
pg_up() {
  if [ -n "$(docker ps -q -f name="^${PG_CONTAINER}$")" ]; then return 0; fi
  docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true
  echo "  [pg] starting $PG_IMAGE on :$PG_PORT"
  docker run -d --name "$PG_CONTAINER" \
    -e POSTGRES_USER="$PG_USER" -e POSTGRES_PASSWORD="$PG_PASSWORD" -e POSTGRES_DB="$PG_DB" \
    -p "$PG_PORT:5432" "$PG_IMAGE" >/dev/null || return 1
  for _ in $(seq 1 30); do
    docker exec "$PG_CONTAINER" pg_isready -U "$PG_USER" -d "$PG_DB" >/dev/null 2>&1 && return 0
    sleep 1
  done
  echo "  [pg] never became ready" >&2
  return 1
}

pg_down() { [ "$KEEP_PG" = 1 ] || docker rm -f "$PG_CONTAINER" >/dev/null 2>&1 || true; }

# Step 6. ON_ERROR_STOP=1 so a failing statement fails the step — without it
# psql prints ERROR lines and still exits 0, which is how the memory schema came
# up with zero tables while this step reported green.
SCHEMA_ERRORS=0
schema_init() {
  local log="$LOG_ROOT/schema.log"
  docker exec -i -e PGPASSWORD="$PG_PASSWORD" "$PG_CONTAINER" \
    psql -v ON_ERROR_STOP=1 -U "$PG_USER" -d "$PG_DB" \
    < infrastructure/postgres/init-schemas.sql > "$log" 2>&1
  local rc=$?
  # No `|| echo 0`: grep -c always prints a count, and exits 1 merely to signal
  # "zero matches" — the fallback would append a second line and corrupt the total.
  SCHEMA_ERRORS=$(grep -c "^ERROR" "$log" 2>/dev/null)
  SCHEMA_ERRORS=${SCHEMA_ERRORS:-0}
  echo "  [schema] exit=$rc errors=$SCHEMA_ERRORS (log: $log)"
  return $rc
}

# ---------------------------------------------------------------------------
# Per-service venv. Cached across runs — creating 46 of these is the single
# most expensive thing here, and requirements change rarely.
# ---------------------------------------------------------------------------
venv_for() {
  local svc="$1" venv="$VENV_ROOT/$1"
  if [ ! -x "$venv/bin/pytest" ] && [ ! -d "$venv" ]; then
    "$PY" -m venv "$venv" >/dev/null 2>&1 || return 1
    "$venv/bin/pip" install -q --upgrade pip >/dev/null 2>&1
  fi
  echo "$venv"
}

# Step 5a. One pip invocation for all six libs, not a loop: they depend on each
# other and none is published, so installing them one at a time makes the first
# alphabetically (homeiq-data) look for homeiq-resilience on PyPI and 404.
libs_install() {
  local venv="$1" log="$2"
  "$venv/bin/pip" install -q libs/homeiq-*/ >"$log" 2>&1
}

STATIC_TESTS=0
static_test_count() {
  STATIC_TESTS=$(find "$1/tests" -name '*.py' -exec grep -hcE "^[[:space:]]*(async )?def test_" {} \; 2>/dev/null \
    | paste -sd+ | bc 2>/dev/null)
  STATIC_TESTS=${STATIC_TESTS:-0}
}

# ---------------------------------------------------------------------------
# Counters feeding the SCORE line.
# ---------------------------------------------------------------------------
N_SERVICES=0
LINT_FAIL=0; FORMAT_FAIL=0
LIBS_STATUS="SKIP"
TEST_FAIL=0; TEST_RAN=0
ALEMBIC_FAIL=0; ALEMBIC_RAN=0
DOCKERFILE_STATUS="SKIP"
BASELINE_ROWS=""

DB_URL="postgresql+asyncpg://$PG_USER:$PG_PASSWORD@localhost:$PG_PORT/$PG_DB"

run_service() {
  local domain="$1" svc="$2" dir="domains/$1/$2"
  local lint_rc="-" fmt_rc="-" test_rc="-" alembic_rc="-" collected="-"

  N_SERVICES=$((N_SERVICES + 1))
  echo "── $domain/$svc"

  if has_lane lint; then
    ruff check "$dir/" >"$LOG_ROOT/$svc.lint.log" 2>&1; lint_rc=$?
    [ "$lint_rc" -ne 0 ] && LINT_FAIL=$((LINT_FAIL + 1))
    echo "  [lint]   exit=$lint_rc"
  fi

  if has_lane format; then
    ruff format --check "$dir/" >"$LOG_ROOT/$svc.format.log" 2>&1; fmt_rc=$?
    [ "$fmt_rc" -ne 0 ] && FORMAT_FAIL=$((FORMAT_FAIL + 1))
    echo "  [format] exit=$fmt_rc"
  fi

  static_test_count "$dir"

  local has_tests=0
  [ -d "$dir/tests" ] && [ -n "$(find "$dir/tests" -name 'test_*.py' -o -name '*_test.py' 2>/dev/null)" ] && has_tests=1

  if has_lane deps || has_lane tests || has_lane alembic; then
    local venv; venv="$(venv_for "$svc")" || { echo "  [venv]   FAILED"; return; }

    if has_lane libs; then
      libs_install "$venv" "$LOG_ROOT/$svc.libs.log" || echo "  [libs]   FAILED (see $LOG_ROOT/$svc.libs.log)"
    fi

    if has_lane deps && [ -f "$dir/requirements.txt" ]; then
      "$venv/bin/pip" install -q -r "$dir/requirements.txt" >"$LOG_ROOT/$svc.deps.log" 2>&1
      local deps_rc=$?
      # Mirrors CI's install step exactly — keep this list in sync with the
      # "Install dependencies" step in reusable-group-ci.yml, or a service can
      # pass here and fail there (which is how the pytest-cov gap hid).
      "$venv/bin/pip" install -q pytest pytest-asyncio pytest-timeout pytest-cov >>"$LOG_ROOT/$svc.deps.log" 2>&1
      echo "  [deps]   exit=$deps_rc"
      [ "$deps_rc" -ne 0 ] && { echo "  [tests]  SKIPPED (deps failed)"; record_row "$domain" "$svc" "$lint_rc" "$fmt_rc" "DEPSFAIL" "$STATIC_TESTS" "-"; return; }
    fi

    if has_lane tests && [ "$has_tests" = 1 ]; then
      # Parse pytest's own "collected N items" line rather than counting output
      # lines: most services set addopts in pytest.ini (often -v), which overrides
      # the -q here and turns the listing into an indented tree. The summary line
      # is emitted in every verbosity mode.
      collected=$(cd "$dir" && "$venv/bin/pytest" tests/ --collect-only -q -p no:cacheprovider 2>/dev/null \
        | grep -oE "collected [0-9]+ item" | grep -oE "[0-9]+" | head -1)
      collected=${collected:-0}
      TEST_RAN=$((TEST_RAN + 1))
      ( cd "$dir" && POSTGRES_URL="$DB_URL" DATABASE_URL="$DB_URL" TEST_DATABASE_URL="$DB_URL" \
          "$venv/bin/pytest" tests/ -q --timeout=300 -p no:cacheprovider ) \
        >"$LOG_ROOT/$svc.test.log" 2>&1
      test_rc=$?
      [ "$test_rc" -ne 0 ] && TEST_FAIL=$((TEST_FAIL + 1))
      echo "  [tests]  exit=$test_rc collected=$collected static=$STATIC_TESTS"
      tail -3 "$LOG_ROOT/$svc.test.log" | sed 's/^/           /'
    fi

    if has_lane alembic && [ -f "$dir/alembic.ini" ]; then
      ALEMBIC_RAN=$((ALEMBIC_RAN + 1))
      ( cd "$dir" && POSTGRES_URL="$DB_URL" DATABASE_URL="$DB_URL" \
          "$venv/bin/python" -m alembic upgrade head \
          && POSTGRES_URL="$DB_URL" DATABASE_URL="$DB_URL" "$venv/bin/python" -m alembic downgrade base \
          && POSTGRES_URL="$DB_URL" DATABASE_URL="$DB_URL" "$venv/bin/python" -m alembic upgrade head ) \
        >"$LOG_ROOT/$svc.alembic.log" 2>&1
      alembic_rc=$?
      [ "$alembic_rc" -ne 0 ] && ALEMBIC_FAIL=$((ALEMBIC_FAIL + 1))
      echo "  [alembic] exit=$alembic_rc"
    fi
  fi

  record_row "$domain" "$svc" "$lint_rc" "$fmt_rc" "$test_rc" "$STATIC_TESTS" "$collected"
}

record_row() {
  BASELINE_ROWS="$BASELINE_ROWS{\"domain\":\"$1\",\"service\":\"$2\",\"lint_rc\":\"$3\",\"format_rc\":\"$4\",\"test_rc\":\"$5\",\"static_tests\":$6,\"collected\":\"$7\"},"
}

# ---------------------------------------------------------------------------
main() {
  if has_lane dockerfile; then
    "$PY" scripts/validate-dockerfile-libs.py --strict >"$LOG_ROOT/dockerfile.log" 2>&1
    local rc=$?
    DOCKERFILE_STATUS=$([ $rc -eq 0 ] && echo OK || echo FAIL)
    echo "[dockerfile-libs] exit=$rc"
  fi

  if has_lane schema || has_lane tests || has_lane alembic; then
    pg_up && { has_lane schema && schema_init; } || true
  fi

  if has_lane libs; then
    local probe="$VENV_ROOT/_libs_probe"
    [ -d "$probe" ] || "$PY" -m venv "$probe" >/dev/null 2>&1
    libs_install "$probe" "$LOG_ROOT/libs-probe.log"
    local n; n=$("$probe/bin/pip" list 2>/dev/null | grep -c "^homeiq")
    LIBS_STATUS=$([ "$n" = 6 ] && echo OK || echo "FAIL($n/6)")
    echo "[shared-libs] $LIBS_STATUS"
  fi

  while read -r domain svc; do
    [ -z "$svc" ] && continue
    if [ -n "$FILTER" ] && [ "$svc" != "$FILTER" ] && [ "$domain/$svc" != "$FILTER" ]; then continue; fi
    run_service "$domain" "$svc"
  done < <(matrix)

  if [ "$BASELINE" = 1 ]; then
    printf '{"generated_by":"scripts/ci-local.sh --baseline","services":[%s]}\n' "${BASELINE_ROWS%,}" \
      | "$PY" -m json.tool > scripts/ci-baseline.json
    echo "[baseline] wrote scripts/ci-baseline.json"
  fi

  echo
  echo "SCORE: lint_fail=$LINT_FAIL/$N_SERVICES format_fail=$FORMAT_FAIL/$N_SERVICES libs_install=$LIBS_STATUS schema_errors=$SCHEMA_ERRORS test_fail=$TEST_FAIL/$TEST_RAN alembic_fail=$ALEMBIC_FAIL/$ALEMBIC_RAN dockerfile=$DOCKERFILE_STATUS"
}

trap pg_down EXIT
main
