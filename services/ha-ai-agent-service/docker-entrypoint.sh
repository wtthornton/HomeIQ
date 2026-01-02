#!/bin/sh
set -e

DATA_DIR="/app/data"
DB_FILE="${DATA_DIR}/ha_ai_agent.db"
APP_USER="appuser"
APP_GROUP="appgroup"

echo "🔧 Fixing permissions for data directory..."
echo "   Running as: $(id)"
echo "   Data directory: ${DATA_DIR}"

mkdir -p "${DATA_DIR}"
chown -R "${APP_USER}:${APP_GROUP}" "${DATA_DIR}"
chmod 775 "${DATA_DIR}"

echo "✅ Data directory permissions fixed (owned by ${APP_USER}:${APP_GROUP})"

if [ -f "${DB_FILE}" ]; then
    echo "🔧 Fixing permissions for database file..."
    chown "${APP_USER}:${APP_GROUP}" "${DB_FILE}"
    chmod 664 "${DB_FILE}"
    echo "✅ Database file permissions fixed (owned by ${APP_USER}:${APP_GROUP})"
else
    echo "ℹ️  Database file does not exist yet, will be created by application"
fi

if su-exec "${APP_USER}" sh -c "[ -w '${DATA_DIR}' ]"; then
    echo "✅ Data directory is writable by ${APP_USER}"
else
    echo "❌ WARNING: Data directory is NOT writable by ${APP_USER}!"
fi

echo "🔄 Switching to ${APP_USER} and starting application..."
exec su-exec "${APP_USER}" "$@"
