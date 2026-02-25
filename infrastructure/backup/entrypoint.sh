#!/bin/bash
# Entrypoint for the HomeIQ backup scheduler container.
# Sets up cron jobs and starts crond in the foreground.

set -euo pipefail

LOG_DIR="/var/log/backup"
mkdir -p "$LOG_DIR" "$BACKUP_DIR"

echo "=== HomeIQ Backup Scheduler ==="
echo "PostgreSQL Host: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "Database:        ${POSTGRES_DB}"
echo "Backup Dir:      ${BACKUP_DIR}"
echo "Retention:       ${BACKUP_RETENTION_DAYS} days"
echo "Daily Schedule:  ${DAILY_SCHEDULE}"
echo "Weekly Schedule: ${WEEKLY_SCHEDULE}"
echo ""

# Build environment export block for cron jobs (cron has minimal env)
ENV_FILE="/etc/backup-env.sh"
cat > "$ENV_FILE" <<EOF
export PG_HOST="${POSTGRES_HOST}"
export PG_PORT="${POSTGRES_PORT}"
export POSTGRES_USER="${POSTGRES_USER}"
export PGPASSWORD="${POSTGRES_PASSWORD}"
export POSTGRES_DB="${POSTGRES_DB}"
export BACKUP_DIR="${BACKUP_DIR}"
export BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS}"
EOF
chmod 600 "$ENV_FILE"

# Create the daily backup wrapper script
cat > /scripts/daily-backup.sh <<'DAILY_EOF'
#!/bin/bash
set -euo pipefail
source /etc/backup-env.sh
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting daily per-schema backup" >> /var/log/backup/daily.log
/scripts/backup-postgres.sh >> /var/log/backup/daily.log 2>&1
date +%s > /backups/.last_backup_timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Daily backup completed" >> /var/log/backup/daily.log
DAILY_EOF
chmod +x /scripts/daily-backup.sh

# Create the weekly full backup wrapper script
cat > /scripts/weekly-backup.sh <<'WEEKLY_EOF'
#!/bin/bash
set -euo pipefail
source /etc/backup-env.sh
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting weekly full backup" >> /var/log/backup/weekly.log
/scripts/backup-postgres.sh >> /var/log/backup/weekly.log 2>&1
date +%s > /backups/.last_backup_timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Weekly backup completed" >> /var/log/backup/weekly.log
WEEKLY_EOF
chmod +x /scripts/weekly-backup.sh

# Write crontab
CRONTAB_FILE="/etc/crontabs/root"
cat > "$CRONTAB_FILE" <<EOF
# HomeIQ Backup Schedule
# Daily per-schema backup
${DAILY_SCHEDULE} /scripts/daily-backup.sh
# Weekly full backup (Sunday)
${WEEKLY_SCHEDULE} /scripts/weekly-backup.sh
EOF

echo "Crontab installed:"
cat "$CRONTAB_FILE"
echo ""

# Wait for PostgreSQL to be reachable before starting cron
echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
MAX_ATTEMPTS=30
ATTEMPT=1
while [ "$ATTEMPT" -le "$MAX_ATTEMPTS" ]; do
    if pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        echo "PostgreSQL is ready."
        break
    fi
    echo "  Attempt ${ATTEMPT}/${MAX_ATTEMPTS} - PostgreSQL not ready, waiting 5s..."
    sleep 5
    ATTEMPT=$((ATTEMPT + 1))
done

if [ "$ATTEMPT" -gt "$MAX_ATTEMPTS" ]; then
    echo "WARNING: PostgreSQL not reachable after ${MAX_ATTEMPTS} attempts. Starting cron anyway."
fi

# Run an initial backup on first start if no backup exists yet
if [ ! -f /backups/.last_backup_timestamp ]; then
    echo "No previous backup found. Running initial backup..."
    /scripts/daily-backup.sh || echo "WARNING: Initial backup failed (will retry on schedule)"
fi

echo "Starting cron daemon in foreground..."
exec crond -f -l 2
