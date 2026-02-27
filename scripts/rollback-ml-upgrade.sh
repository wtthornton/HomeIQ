#!/usr/bin/env bash
# rollback-ml-upgrade.sh — Backup and restore .pkl model files for Phase 3 ML upgrade
# Usage:
#   ./scripts/rollback-ml-upgrade.sh backup        # Before upgrading: save .pkl + tag Docker images
#   ./scripts/rollback-ml-upgrade.sh restore        # Rollback: restore .pkl + revert requirements + rebuild
#   ./scripts/rollback-ml-upgrade.sh verify         # Health-check all ML services after backup or restore
#   ./scripts/rollback-ml-upgrade.sh full-rollback  # One-shot: restore .pkl, revert git, rebuild, verify

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
MODELS_BASE="$PROJECT_ROOT/domains/ml-engine/device-intelligence-service"
BACKUP_DIR="$PROJECT_ROOT/backups/phase3-ml-models-$(date +%Y%m%d)"
GIT_TAG="phase-3-pre-upgrade-$(date +%Y%m%d)"

# Services affected by Phase 3
ML_IMAGES=(
    "homeiq/device-intelligence-service"
    "homeiq/ml-service"
    "homeiq/ai-pattern-service"
    "homeiq/ha-ai-agent-service"
)

HEALTH_ENDPOINTS=(
    "http://localhost:8007/health"   # device-intelligence-service
    "http://localhost:8005/health"   # ml-service
    "http://localhost:8035/health"   # ai-pattern-service
    "http://localhost:8030/health"   # ha-ai-agent-service
)

# ── backup ────────────────────────────────────────────────────────────────────

backup() {
    echo "=== Phase 3 ML Model Backup ==="
    echo "Backing up .pkl files to: $BACKUP_DIR"

    mkdir -p "$BACKUP_DIR"

    # 1. Backup root models
    if [ -d "$MODELS_BASE/models" ]; then
        mkdir -p "$BACKUP_DIR/models"
        cp -v "$MODELS_BASE/models/"*.pkl "$BACKUP_DIR/models/" 2>/dev/null || echo "No root .pkl files found"
        # Also grab metadata if present
        cp -v "$MODELS_BASE/models/model_metadata.json" "$BACKUP_DIR/models/" 2>/dev/null || true
    fi

    # 2. Backup home-type models
    if [ -d "$MODELS_BASE/data/models/home_type_models" ]; then
        for type_dir in "$MODELS_BASE/data/models/home_type_models"/*/; do
            type_name=$(basename "$type_dir")
            mkdir -p "$BACKUP_DIR/home_type_models/$type_name"
            cp -v "$type_dir"*.pkl "$BACKUP_DIR/home_type_models/$type_name/" 2>/dev/null || true
        done
    fi

    # 3. Tag Docker images so we can restore without rebuilding
    echo ""
    echo "Tagging current Docker images with :pre-phase3 ..."
    for img in "${ML_IMAGES[@]}"; do
        if docker image inspect "${img}:latest" >/dev/null 2>&1; then
            docker tag "${img}:latest" "${img}:pre-phase3"
            echo "  Tagged ${img}:pre-phase3"
        else
            echo "  SKIP ${img}:latest (not found locally)"
        fi
    done

    # 4. Record manifest
    cat > "$BACKUP_DIR/MANIFEST.txt" <<EOF
Phase 3 ML Model Backup
Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
Git commit: $(git -C "$PROJECT_ROOT" rev-parse HEAD 2>/dev/null || echo "unknown")
Git tag: $GIT_TAG
File count: $(find "$BACKUP_DIR" -name "*.pkl" | wc -l)
Total size: $(du -sh "$BACKUP_DIR" | cut -f1)

Library versions at backup time (from requirements.txt):
  scikit-learn: $(grep scikit-learn "$MODELS_BASE/requirements.txt" || echo "not found")
  numpy:        $(grep numpy "$MODELS_BASE/requirements.txt" || echo "not found")
  pandas:       $(grep pandas "$MODELS_BASE/requirements.txt" || echo "not found")
  joblib:       $(grep joblib "$MODELS_BASE/requirements.txt" || echo "not found")
EOF

    echo ""
    echo "Backup complete. $(find "$BACKUP_DIR" -name "*.pkl" | wc -l) .pkl files saved."
    echo "Manifest: $BACKUP_DIR/MANIFEST.txt"
    echo ""
    echo "Next: tag git state before upgrading:"
    echo "  git tag $GIT_TAG"
}

# ── restore ───────────────────────────────────────────────────────────────────

restore() {
    # Find most recent backup
    LATEST_BACKUP=$(ls -d "$PROJECT_ROOT/backups/phase3-ml-models-"* 2>/dev/null | sort -r | head -1)

    if [ -z "$LATEST_BACKUP" ]; then
        echo "ERROR: No Phase 3 ML model backup found in $PROJECT_ROOT/backups/"
        exit 1
    fi

    echo "=== Phase 3 ML Model Restore ==="
    echo "Restoring from: $LATEST_BACKUP"

    # 1. Restore root models
    if [ -d "$LATEST_BACKUP/models" ]; then
        mkdir -p "$MODELS_BASE/models"
        cp -v "$LATEST_BACKUP/models/"*.pkl "$MODELS_BASE/models/" 2>/dev/null || true
        cp -v "$LATEST_BACKUP/models/model_metadata.json" "$MODELS_BASE/models/" 2>/dev/null || true
    fi

    # 2. Restore home-type models
    if [ -d "$LATEST_BACKUP/home_type_models" ]; then
        for type_dir in "$LATEST_BACKUP/home_type_models"/*/; do
            type_name=$(basename "$type_dir")
            target="$MODELS_BASE/data/models/home_type_models/$type_name"
            mkdir -p "$target"
            cp -v "$type_dir"*.pkl "$target/" 2>/dev/null || true
        done
    fi

    echo ""
    PKL_COUNT=$(find "$MODELS_BASE" -name "*.pkl" | wc -l)
    echo "Restore complete. $PKL_COUNT .pkl files on disk."
}

# ── verify ────────────────────────────────────────────────────────────────────

verify() {
    echo "=== Phase 3 ML Service Health Check ==="
    local all_ok=true

    for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
        if curl -sf --max-time 5 "$endpoint" >/dev/null 2>&1; then
            echo "  OK   $endpoint"
        else
            echo "  FAIL $endpoint"
            all_ok=false
        fi
    done

    # Check library versions inside running containers
    echo ""
    echo "Library versions in running containers:"
    for container in homeiq-device-intelligence-service homeiq-ml-service homeiq-ai-pattern-service; do
        if docker inspect "$container" >/dev/null 2>&1; then
            echo "  $container:"
            docker exec "$container" python -c "
import importlib, sys
for lib in ['sklearn', 'numpy', 'pandas', 'scipy', 'joblib']:
    try:
        m = importlib.import_module(lib)
        print(f'    {lib}: {m.__version__}')
    except ImportError:
        pass
" 2>/dev/null || echo "    (container not running)"
        fi
    done

    if $all_ok; then
        echo ""
        echo "All services healthy."
    else
        echo ""
        echo "WARNING: One or more services unhealthy. Check logs with:"
        echo "  docker compose -f domains/ml-engine/compose.yml logs --tail 50"
        return 1
    fi
}

# ── full-rollback ─────────────────────────────────────────────────────────────

full_rollback() {
    echo "=== Phase 3 Full Rollback ==="
    echo "This will: restore .pkl files, revert requirements, rebuild containers."
    echo ""

    # 1. Restore .pkl files
    restore

    # 2. Check for pre-phase3 Docker images
    echo ""
    echo "Checking for pre-phase3 Docker images..."
    local has_tagged=false
    for img in "${ML_IMAGES[@]}"; do
        if docker image inspect "${img}:pre-phase3" >/dev/null 2>&1; then
            has_tagged=true
            break
        fi
    done

    if $has_tagged; then
        echo "Found :pre-phase3 tagged images. Restoring..."
        docker compose -f "$PROJECT_ROOT/domains/ml-engine/compose.yml" down 2>/dev/null || true
        docker compose -f "$PROJECT_ROOT/domains/pattern-analysis/compose.yml" down 2>/dev/null || true

        for img in "${ML_IMAGES[@]}"; do
            if docker image inspect "${img}:pre-phase3" >/dev/null 2>&1; then
                docker tag "${img}:pre-phase3" "${img}:latest"
                echo "  Restored ${img}:latest from :pre-phase3"
            fi
        done

        docker compose -f "$PROJECT_ROOT/domains/ml-engine/compose.yml" up -d
        docker compose -f "$PROJECT_ROOT/domains/pattern-analysis/compose.yml" up -d
    else
        echo "No :pre-phase3 images found. Reverting requirements and rebuilding..."

        # Find the git tag
        local tag
        tag=$(git -C "$PROJECT_ROOT" tag -l "phase-3-pre-upgrade-*" | sort -r | head -1)
        if [ -z "$tag" ]; then
            echo "ERROR: No phase-3-pre-upgrade-* git tag found. Manual rollback required."
            echo "  git log --oneline to find the pre-upgrade commit, then:"
            echo "  git checkout <commit> -- domains/ml-engine/*/requirements.txt"
            exit 1
        fi

        echo "Reverting requirements to tag: $tag"
        git -C "$PROJECT_ROOT" checkout "$tag" -- \
            domains/ml-engine/device-intelligence-service/requirements.txt \
            domains/ml-engine/ml-service/requirements.txt \
            domains/pattern-analysis/ai-pattern-service/requirements.txt \
            domains/automation-core/ha-ai-agent-service/requirements.txt

        echo "Rebuilding containers..."
        docker compose -f "$PROJECT_ROOT/domains/ml-engine/compose.yml" build
        docker compose -f "$PROJECT_ROOT/domains/ml-engine/compose.yml" up -d
        docker compose -f "$PROJECT_ROOT/domains/pattern-analysis/compose.yml" build
        docker compose -f "$PROJECT_ROOT/domains/pattern-analysis/compose.yml" up -d
    fi

    # 3. Wait for services to start then verify
    echo ""
    echo "Waiting 15s for services to start..."
    sleep 15
    verify
}

# ── main ──────────────────────────────────────────────────────────────────────

case "${1:-}" in
    backup)        backup ;;
    restore)       restore ;;
    verify)        verify ;;
    full-rollback) full_rollback ;;
    *)
        echo "Usage: $0 {backup|restore|verify|full-rollback}"
        echo ""
        echo "  backup        Save .pkl files + tag Docker images before upgrade"
        echo "  restore       Restore .pkl files from most recent backup"
        echo "  verify        Health-check all ML services"
        echo "  full-rollback Restore .pkl, revert requirements, rebuild, verify"
        exit 1
        ;;
esac
