#!/bin/bash

# InfluxDB secondary-bucket provisioning script.
#
# Mounted into /docker-entrypoint-initdb.d/ on the influxdb service — the
# official influxdb:2.x image runs every *.sh file there once, after
# DOCKER_INFLUXDB_INIT_MODE=setup has already created the primary org, user,
# bucket, and admin token. This script must NOT recreate any of those (the
# org/bucket already exist by the time it runs, and `influx org create`/
# `influx bucket create` on an existing name would fail under `set -e`).
#
# It provisions buckets that need a retention distinct from the primary
# bucket's, so InfluxDB itself enforces the limit instead of a declared
# policy nothing reads (TAP-7586). INFLUXDB_ROOM_OCCUPANCY_BUCKET and
# INFLUXDB_ROOM_OCCUPANCY_RETENTION are the single source of truth, shared
# with websocket-ingestion's Settings
# (domains/core-platform/websocket-ingestion/src/config.py) via the same
# env var names — both default to "room_occupancy" / "90d" so they agree
# even when unset.

set -e

echo "Provisioning secondary InfluxDB buckets..."

influx bucket create \
  --name "${INFLUXDB_ROOM_OCCUPANCY_BUCKET:-room_occupancy}" \
  --org "${DOCKER_INFLUXDB_INIT_ORG:-homeiq}" \
  --retention "${INFLUXDB_ROOM_OCCUPANCY_RETENTION:-90d}" \
  --token "${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}" \
  --host http://localhost:8086

echo "InfluxDB secondary bucket provisioning complete!"
