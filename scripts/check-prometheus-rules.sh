#!/usr/bin/env bash
# Validate Prometheus alert rules and run their unit tests.
#
# Rule files are only parsed when Prometheus loads them, so a syntax error or a
# broken expression ships silently and every alert in the file stops evaluating.
# The unit tests go further: they assert each alert actually fires on the
# condition it names, and stays quiet on the healthy case.
#
# Uses promtool from the pinned Prometheus image -- no TappsMCP involvement, so
# this runs on a hosted runner (see CLAUDE.md, CI Integration).

set -euo pipefail

PROM_IMAGE="${PROM_IMAGE:-prom/prometheus:v3.1.0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RULES_DIR="${REPO_ROOT}/infrastructure/prometheus"

run_promtool() {
  if command -v promtool >/dev/null 2>&1; then
    promtool "$@"
  else
    docker run --rm -v "${RULES_DIR}:/rules:ro" -w /rules \
      --entrypoint promtool "${PROM_IMAGE}" "$@"
  fi
}

# Rule files live beside prometheus.yml; test files live in tests/ and refer to
# them as ../<file>.yml, so both resolve from the same working directory.
mapfile -t rule_files < <(
  cd "${RULES_DIR}" && ls -1 *.yml | grep -v '^prometheus\.yml$'
)

if [ ${#rule_files[@]} -eq 0 ]; then
  echo "No Prometheus rule files found in ${RULES_DIR}" >&2
  exit 1
fi

echo "==> Checking rule syntax"
for f in "${rule_files[@]}"; do
  run_promtool check rules "$f"
done

mapfile -t test_files < <(
  cd "${RULES_DIR}" && find tests -name '*_test.yml' 2>/dev/null | sort
)

if [ ${#test_files[@]} -eq 0 ]; then
  echo "No Prometheus rule unit tests found -- alerts are unverified" >&2
  exit 1
fi

echo "==> Running rule unit tests"
for f in "${test_files[@]}"; do
  echo "--- $f"
  run_promtool test rules "$f"
done

echo "OK: ${#rule_files[@]} rule file(s) valid, ${#test_files[@]} test file(s) passed"
