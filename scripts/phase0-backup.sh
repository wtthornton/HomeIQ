#!/bin/bash
# Phase 0: Pre-Deployment Preparation - Comprehensive Backup Script
# HomeIQ Rebuild and Deployment - Phase 0 Story 1
#
# Purpose: Create complete backups of all Docker volumes, configuration files,
#          and Docker images before starting the rebuild process
#
# Usage: ./scripts/phase0-backup.sh
#
# Author: TappsCodingAgents - Implementer
# Date: 2026-02-04

set -euo pipefail  # Exit on error, undefined variables, and pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="${PROJECT_ROOT}/backups/phase0_${TIMESTAMP}"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Counters for summary
SUCCESS_COUNT=0
WARNING_COUNT=0
ERROR_COUNT=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
    WARNING_COUNT=$((WARNING_COUNT + 1))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    ERROR_COUNT=$((ERROR_COUNT + 1))
}

# Error handling
error_exit() {
    log_error "$1"
    log_error "Backup failed! Check ${LOG_FILE} for details"
    exit 1
}

# Create backup directory structure
create_backup_structure() {
    # Create log directory FIRST before any logging
    mkdir -p "$(dirname "$LOG_FILE")"

    log_info "Creating backup directory structure..."

    mkdir -p "$BACKUP_DIR"/{volumes,configs,docker-images,checksums}
    mkdir -p "$BACKUP_DIR"/diagnostics

    # Initialize log file
    cat > "$LOG_FILE" << EOF
HomeIQ Phase 0 Backup Log
========================
Started: $(date)
Backup Directory: $BACKUP_DIR
Host: $(hostname)
User: $(whoami)

EOF

    log_success "Backup directory created: $BACKUP_DIR"
}

# Backup Docker volumes
backup_docker_volumes() {
    log_info "=== Task 1.1: Backing up Docker volumes ==="

    # Backup InfluxDB data volume
    log_info "Backing up InfluxDB data volume..."
    if docker volume inspect homeiq_influxdb_data > /dev/null 2>&1; then
        INFLUXDB_BACKUP="${BACKUP_DIR}/volumes/influxdb_data_${TIMESTAMP}.tar.gz"

        MSYS_NO_PATHCONV=1 docker run --rm \
            -v homeiq_influxdb_data:/data \
            -v "${BACKUP_DIR}/volumes:/backup" \
            alpine tar czf "/backup/influxdb_data_${TIMESTAMP}.tar.gz" -C /data . \
            2>&1 | tee -a "$LOG_FILE"

        if [ -f "$INFLUXDB_BACKUP" ] && [ -s "$INFLUXDB_BACKUP" ]; then
            INFLUXDB_SIZE=$(du -h "$INFLUXDB_BACKUP" | cut -f1)
            log_success "InfluxDB volume backed up (Size: $INFLUXDB_SIZE)"
        else
            error_exit "InfluxDB backup file is missing or empty"
        fi
    else
        log_warning "InfluxDB volume 'homeiq_influxdb_data' not found"
    fi

    # Backup SQLite data volume
    log_info "Backing up SQLite data volume..."
    if docker volume inspect homeiq_sqlite-data > /dev/null 2>&1; then
        SQLITE_BACKUP="${BACKUP_DIR}/volumes/sqlite_data_${TIMESTAMP}.tar.gz"

        MSYS_NO_PATHCONV=1 docker run --rm \
            -v homeiq_sqlite-data:/data \
            -v "${BACKUP_DIR}/volumes:/backup" \
            alpine tar czf "/backup/sqlite_data_${TIMESTAMP}.tar.gz" -C /data . \
            2>&1 | tee -a "$LOG_FILE"

        if [ -f "$SQLITE_BACKUP" ] && [ -s "$SQLITE_BACKUP" ]; then
            SQLITE_SIZE=$(du -h "$SQLITE_BACKUP" | cut -f1)
            log_success "SQLite volume backed up (Size: $SQLITE_SIZE)"
        else
            error_exit "SQLite backup file is missing or empty"
        fi
    else
        log_warning "SQLite volume 'homeiq_sqlite-data' not found"
    fi

    # List all HomeIQ volumes for reference
    log_info "Documenting all HomeIQ Docker volumes..."
    docker volume ls --filter name=homeiq > "${BACKUP_DIR}/volumes/all_volumes.txt"
    log_success "Volume inventory saved"
}

# Verify volume backups
verify_volume_backups() {
    log_info "Verifying volume backups..."

    local verification_failed=false

    # Verify InfluxDB backup
    if [ -f "${BACKUP_DIR}/volumes/influxdb_data_${TIMESTAMP}.tar.gz" ]; then
        if tar -tzf "${BACKUP_DIR}/volumes/influxdb_data_${TIMESTAMP}.tar.gz" > /dev/null 2>&1; then
            log_success "InfluxDB backup verified (can be extracted)"
        else
            log_error "InfluxDB backup is corrupted"
            verification_failed=true
        fi
    fi

    # Verify SQLite backup
    if [ -f "${BACKUP_DIR}/volumes/sqlite_data_${TIMESTAMP}.tar.gz" ]; then
        if tar -tzf "${BACKUP_DIR}/volumes/sqlite_data_${TIMESTAMP}.tar.gz" > /dev/null 2>&1; then
            log_success "SQLite backup verified (can be extracted)"
        else
            log_error "SQLite backup is corrupted"
            verification_failed=true
        fi
    fi

    if [ "$verification_failed" = true ]; then
        error_exit "Backup verification failed"
    fi
}

# Backup configuration files
backup_configuration_files() {
    log_info "=== Task 1.2: Backing up configuration files ==="

    cd "$PROJECT_ROOT"

    # Backup .env file
    if [ -f ".env" ]; then
        cp .env "${BACKUP_DIR}/configs/.env.backup_${TIMESTAMP}"
        log_success ".env file backed up"
    else
        log_warning ".env file not found"
    fi

    # Backup docker-compose.yml
    if [ -f "docker-compose.yml" ]; then
        cp docker-compose.yml "${BACKUP_DIR}/configs/docker-compose.yml.backup_${TIMESTAMP}"
        log_success "docker-compose.yml backed up"
    else
        log_warning "docker-compose.yml not found"
    fi

    # Backup all docker-compose variants
    for compose_file in docker-compose*.yml docker-compose*.yaml; do
        if [ -f "$compose_file" ]; then
            cp "$compose_file" "${BACKUP_DIR}/configs/${compose_file}.backup_${TIMESTAMP}"
            log_success "$compose_file backed up"
        fi
    done

    # Backup infrastructure directory
    if [ -d "infrastructure" ]; then
        cp -r infrastructure "${BACKUP_DIR}/configs/infrastructure.backup_${TIMESTAMP}"
        log_success "infrastructure/ directory backed up"
    else
        log_warning "infrastructure/ directory not found"
    fi

    # Backup requirements files
    if [ -f "requirements-base.txt" ]; then
        cp requirements-base.txt "${BACKUP_DIR}/configs/requirements-base.txt.backup_${TIMESTAMP}"
        log_success "requirements-base.txt backed up"
    fi

    # Backup package.json
    if [ -f "package.json" ]; then
        cp package.json "${BACKUP_DIR}/configs/package.json.backup_${TIMESTAMP}"
        log_success "package.json backed up"
    fi

    # Capture git status
    log_info "Capturing git status..."
    if command -v git &> /dev/null; then
        git status > "${BACKUP_DIR}/configs/git_status_${TIMESTAMP}.txt" 2>&1
        git log --oneline -10 > "${BACKUP_DIR}/configs/git_log_recent_${TIMESTAMP}.txt" 2>&1 || true
        git diff HEAD > "${BACKUP_DIR}/configs/git_diff_${TIMESTAMP}.txt" 2>&1 || true
        log_success "Git status captured"
    else
        log_warning "Git not available, skipping git status"
    fi
}

# Export Docker images
export_docker_images() {
    log_info "=== Task 1.3: Exporting Docker images list ==="

    # Export detailed images list
    log_info "Exporting detailed Docker images list..."
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}\t{{.ID}}" \
        | grep -E "homeiq|REPOSITORY" > "${BACKUP_DIR}/docker-images/current_images.txt"

    # Export machine-readable format
    docker images --format "{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}\t{{.ID}}" \
        | grep homeiq > "${BACKUP_DIR}/docker-images/current_images_detailed.txt"

    log_success "Docker images list exported"

    # Count images
    IMAGE_COUNT=$(docker images --format "{{.Repository}}" | grep homeiq | sort -u | wc -l)
    log_info "Found $IMAGE_COUNT unique HomeIQ images"

    # Tag current images for safety
    log_info "Tagging current images as 'pre-rebuild'..."
    local tagged_count=0

    for img in $(docker images --format "{{.Repository}}" | grep homeiq | sort -u); do
        if docker tag "${img}:latest" "${img}:pre-rebuild" 2>&1 | tee -a "$LOG_FILE"; then
            tagged_count=$((tagged_count + 1))
        else
            log_warning "Failed to tag $img"
        fi
    done

    log_success "Tagged $tagged_count images as 'pre-rebuild'"

    # Export tagged images list
    docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.ID}}" \
        | grep -E "homeiq.*pre-rebuild|REPOSITORY" > "${BACKUP_DIR}/docker-images/pre_rebuild_tags.txt"
}

# Create backup manifest with checksums
create_backup_manifest() {
    log_info "=== Task 1.4: Creating backup manifest with checksums ==="

    cd "${BACKUP_DIR}"

    # Generate checksums for volume backups
    log_info "Generating SHA256 checksums..."
    if [ -d "volumes" ] && [ "$(ls -A volumes/*.tar.gz 2>/dev/null)" ]; then
        (cd volumes && sha256sum *.tar.gz > ../checksums/volume_checksums_${TIMESTAMP}.txt 2>&1) || \
            log_warning "Failed to generate volume checksums"
        log_success "Volume checksums generated"
    fi

    # Generate checksums for config files
    if [ -d "configs" ]; then
        find configs -type f -exec sha256sum {} \; > "checksums/config_checksums_${TIMESTAMP}.txt" 2>&1 || \
            log_warning "Failed to generate config checksums"
        log_success "Config file checksums generated"
    fi

    # Create comprehensive manifest
    log_info "Creating comprehensive backup manifest..."

    cat > "${BACKUP_DIR}/MANIFEST.md" << EOF
# HomeIQ Phase 0 Backup Manifest

**Backup ID:** phase0_${TIMESTAMP}
**Created:** $(date)
**Host:** $(hostname)
**User:** $(whoami)
**Project Root:** $PROJECT_ROOT

---

## Backup Contents

### Docker Volumes

$(if [ -f "volumes/influxdb_data_${TIMESTAMP}.tar.gz" ]; then
    echo "- ✅ InfluxDB Data: \`influxdb_data_${TIMESTAMP}.tar.gz\` ($(du -h "volumes/influxdb_data_${TIMESTAMP}.tar.gz" | cut -f1))"
else
    echo "- ❌ InfluxDB Data: NOT BACKED UP"
fi)

$(if [ -f "volumes/sqlite_data_${TIMESTAMP}.tar.gz" ]; then
    echo "- ✅ SQLite Data: \`sqlite_data_${TIMESTAMP}.tar.gz\` ($(du -h "volumes/sqlite_data_${TIMESTAMP}.tar.gz" | cut -f1))"
else
    echo "- ❌ SQLite Data: NOT BACKED UP"
fi)

### Configuration Files

$(ls -1 configs/ 2>/dev/null | sed 's/^/- /' || echo "- No config files backed up")

### Docker Images

- Total unique HomeIQ images: $(docker images --format "{{.Repository}}" | grep homeiq | sort -u | wc -l)
- Images tagged as \`pre-rebuild\`: $(docker images | grep pre-rebuild | wc -l)
- Images list: \`docker-images/current_images.txt\`

### Checksums

- Volume checksums: \`checksums/volume_checksums_${TIMESTAMP}.txt\`
- Config checksums: \`checksums/config_checksums_${TIMESTAMP}.txt\`

---

## Backup Statistics

- **Total Backup Size:** $(du -sh . | cut -f1)
- **Volume Backups:** $(find volumes -name "*.tar.gz" 2>/dev/null | wc -l)
- **Config Files:** $(find configs -type f 2>/dev/null | wc -l)
- **Success Count:** $SUCCESS_COUNT
- **Warning Count:** $WARNING_COUNT
- **Error Count:** $ERROR_COUNT

---

## Restoration Procedure

### 1. Stop All Services
\`\`\`bash
cd $PROJECT_ROOT
docker-compose --profile production down --remove-orphans
\`\`\`

### 2. Restore Docker Volumes

**InfluxDB Data:**
\`\`\`bash
docker run --rm -v homeiq_influxdb_data:/data -v ${BACKUP_DIR}/volumes:/backup \\
  alpine tar xzf /backup/influxdb_data_${TIMESTAMP}.tar.gz -C /data
\`\`\`

**SQLite Data:**
\`\`\`bash
docker run --rm -v homeiq_sqlite-data:/data -v ${BACKUP_DIR}/volumes:/backup \\
  alpine tar xzf /backup/sqlite_data_${TIMESTAMP}.tar.gz -C /data
\`\`\`

### 3. Restore Configuration Files
\`\`\`bash
cp ${BACKUP_DIR}/configs/.env.backup_${TIMESTAMP} $PROJECT_ROOT/.env
cp ${BACKUP_DIR}/configs/docker-compose.yml.backup_${TIMESTAMP} $PROJECT_ROOT/docker-compose.yml
\`\`\`

### 4. Restore Docker Images (if needed)
\`\`\`bash
# Retag pre-rebuild images back to latest
for img in \$(docker images --format "{{.Repository}}" | grep homeiq | sort -u); do
  docker tag \${img}:pre-rebuild \${img}:latest
done
\`\`\`

### 5. Restart Services
\`\`\`bash
cd $PROJECT_ROOT
docker-compose --profile production up -d
\`\`\`

### 6. Verify Restoration
\`\`\`bash
# Check service health
docker ps --format "table {{.Names}}\\t{{.Status}}"

# Verify data integrity
docker exec homeiq-influxdb influx query 'buckets()' || echo "InfluxDB verification needed"
\`\`\`

---

## Verification Checksums

To verify backup integrity before restoration:

\`\`\`bash
cd ${BACKUP_DIR}/checksums
sha256sum -c volume_checksums_${TIMESTAMP}.txt
sha256sum -c config_checksums_${TIMESTAMP}.txt
\`\`\`

All checksums should show "OK".

---

## Backup Log

Full backup log available at: \`${LOG_FILE}\`

EOF

    log_success "Backup manifest created: MANIFEST.md"
}

# Capture system diagnostics
capture_diagnostics() {
    log_info "Capturing system diagnostics..."

    # Docker version
    docker --version > "${BACKUP_DIR}/diagnostics/docker_version.txt" 2>&1
    docker compose version >> "${BACKUP_DIR}/diagnostics/docker_version.txt" 2>&1 || true

    # Container status
    docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" > "${BACKUP_DIR}/diagnostics/container_status.txt" 2>&1

    # Docker stats snapshot
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}" > "${BACKUP_DIR}/diagnostics/resource_usage.txt" 2>&1 || true

    # Volume list
    docker volume ls > "${BACKUP_DIR}/diagnostics/volumes_list.txt" 2>&1

    # Network list
    docker network ls > "${BACKUP_DIR}/diagnostics/networks_list.txt" 2>&1

    log_success "System diagnostics captured"
}

# Display backup summary
display_summary() {
    local BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

    echo ""
    echo "=========================================="
    echo "Phase 0 Backup Summary"
    echo "=========================================="
    echo ""
    echo "✅ Backup completed successfully!"
    echo ""
    echo "📦 Backup Location: $BACKUP_DIR"
    echo "📊 Backup Size: $BACKUP_SIZE"
    echo "📝 Manifest: ${BACKUP_DIR}/MANIFEST.md"
    echo "📋 Log File: ${LOG_FILE}"
    echo ""
    echo "Statistics:"
    echo "  ✅ Successes: $SUCCESS_COUNT"
    echo "  ⚠️  Warnings:  $WARNING_COUNT"
    echo "  ❌ Errors:    $ERROR_COUNT"
    echo ""
    echo "Contents:"
    echo "  - Docker Volumes: $(find "${BACKUP_DIR}/volumes" -name "*.tar.gz" 2>/dev/null | wc -l) archives"
    echo "  - Config Files:   $(find "${BACKUP_DIR}/configs" -type f 2>/dev/null | wc -l) files"
    echo "  - Docker Images:  $(docker images | grep pre-rebuild | wc -l) tagged"
    echo "  - Checksums:      $(find "${BACKUP_DIR}/checksums" -type f 2>/dev/null | wc -l) files"
    echo ""
    echo "Next Steps:"
    echo "  1. Review backup manifest: cat ${BACKUP_DIR}/MANIFEST.md"
    echo "  2. Verify checksums: cd ${BACKUP_DIR}/checksums && sha256sum -c *.txt"
    echo "  3. Proceed to Story 2: Diagnose websocket-ingestion service"
    echo ""
    echo "=========================================="
}

# Main execution
main() {
    # Create log directory FIRST before any logging
    mkdir -p "$(dirname "$LOG_FILE")"

    echo ""
    echo "╔════════════════════════════════════════╗"
    echo "║  HomeIQ Phase 0: Backup Script         ║"
    echo "║  Story 1: Create Comprehensive Backup  ║"
    echo "╚════════════════════════════════════════╝"
    echo ""

    log_info "Starting Phase 0 backup process..."
    log_info "Timestamp: $TIMESTAMP"

    # Execute backup tasks
    create_backup_structure
    backup_docker_volumes
    verify_volume_backups
    backup_configuration_files
    export_docker_images
    create_backup_manifest
    capture_diagnostics

    # Final summary
    display_summary

    # Exit with error if any errors occurred
    if [ $ERROR_COUNT -gt 0 ]; then
        log_error "Backup completed with $ERROR_COUNT errors"
        exit 1
    fi

    log_success "Phase 0 backup completed successfully!"
    exit 0
}

# Run main function
main "$@"
