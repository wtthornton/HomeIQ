# HomeIQ Backup Scheduler Container
# Runs PostgreSQL backups on a configurable schedule.
#
# Default schedule:
#   - Daily incremental (per-schema) at 02:00 UTC
#   - Weekly full backup on Sunday at 01:00 UTC
#
# Build context must be the project root so scripts/ is accessible.
#
# Usage:
#   docker build -f infrastructure/backup/backup-cron.dockerfile -t homeiq-backup .

FROM postgres:17-alpine

# Install cron and bash (busybox cron is sufficient for Alpine)
RUN apk add --no-cache bash curl tini

# Environment defaults (override via docker-compose or .env)
ENV POSTGRES_HOST=homeiq-postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_USER=homeiq \
    POSTGRES_PASSWORD=homeiq \
    POSTGRES_DB=homeiq \
    BACKUP_DIR=/backups \
    BACKUP_RETENTION_DAYS=30 \
    DAILY_SCHEDULE="0 2 * * *" \
    WEEKLY_SCHEDULE="0 1 * * 0" \
    TZ=UTC

# Create backup directory
RUN mkdir -p /backups /scripts /var/log/backup

# Copy backup and restore scripts
COPY scripts/backup-postgres.sh /scripts/backup-postgres.sh
COPY scripts/restore-postgres.sh /scripts/restore-postgres.sh
RUN chmod +x /scripts/backup-postgres.sh /scripts/restore-postgres.sh

# Copy the entrypoint that sets up cron
COPY infrastructure/backup/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Healthcheck: verify cron is running and last backup is not stale
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD pgrep crond > /dev/null && \
        [ -f /backups/.last_backup_timestamp ] && \
        [ $(( $(date +%s) - $(cat /backups/.last_backup_timestamp) )) -lt 90000 ] \
    || exit 1

VOLUME ["/backups"]

ENTRYPOINT ["tini", "--"]
CMD ["/entrypoint.sh"]
