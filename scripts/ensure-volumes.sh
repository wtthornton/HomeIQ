#!/bin/sh
# ensure-volumes.sh — Create Docker volumes shared across domain compose
# files if they don't exist. Idempotent: safe to run multiple times.
#
# Each of these is owned by one domain but mounted by others too. Every
# domain that shares one declares it `external: true` in its compose.yml
# (matching the homeiq-network pattern), so Compose never creates it
# itself -- it must exist before any domain starts, the same way
# ensure-network.sh pre-creates homeiq-network.
#
#   homeiq_logs        — owned by core-platform; also used by
#                         data-collectors and device-management.
#   ai_automation_data  — owned by ml-engine; also used by automation-core
#                         and pattern-analysis.

ensure_volume() {
  volume_name="$1"
  if docker volume inspect "$volume_name" >/dev/null 2>&1; then
    echo "[OK] Volume '$volume_name' already exists."
  else
    docker volume create "$volume_name"
    echo "[CREATED] Volume '$volume_name' created."
  fi
}

ensure_volume "${HOMEIQ_LOGS_VOLUME:-homeiq-core-platform_homeiq_logs}"
ensure_volume "${AI_AUTOMATION_DATA_VOLUME:-homeiq-ml-engine_ai_automation_data}"
