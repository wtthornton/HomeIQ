#!/bin/sh
# ensure-network.sh — Create the homeiq-network Docker bridge if it doesn't exist.
# Idempotent: safe to run multiple times.

NETWORK_NAME="homeiq-network"

if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "[OK] Network '$NETWORK_NAME' already exists."
else
  docker network create "$NETWORK_NAME" --driver bridge
  echo "[CREATED] Network '$NETWORK_NAME' created."
fi
