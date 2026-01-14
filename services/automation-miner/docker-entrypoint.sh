#!/bin/sh
set -e

# Fix permissions for data directory
if [ -d "/app/data" ]; then
    chown -R appuser:appgroup /app/data
    chmod -R 755 /app/data
fi

# Create data directory if it doesn't exist
mkdir -p /app/data
chown -R appuser:appgroup /app/data
chmod -R 755 /app/data

# Switch to appuser and run the application
exec su-exec appuser "$@"
