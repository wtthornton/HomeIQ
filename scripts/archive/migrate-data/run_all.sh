#!/bin/bash
# HomeIQ SQLite to PostgreSQL Migration Orchestrator
# Run this from the project root after PostgreSQL is up and schemas are created.

set -euo pipefail

POSTGRES_URL="${POSTGRES_URL:-postgresql+psycopg://homeiq:homeiq-secure-2026@localhost:5432/homeiq}"
DATA_DIR="${DATA_DIR:-./data}"

echo "=== HomeIQ SQLite to PostgreSQL Migration ==="
echo "Target: $POSTGRES_URL"
echo "Data directory: $DATA_DIR"
echo ""

# Migration order matches the epic execution order
MIGRATIONS=(
    "core|${DATA_DIR}/metadata.db|devices,entities,automations,automation_executions,services,statistics_meta,user_team_preferences"
    "automation|${DATA_DIR}/ai_automation.db|suggestions,automation_versions,plans,compiled_artifacts,deployments,training_runs,synergy_opportunities,synergy_feedback"
    "agent|${DATA_DIR}/ha_ai_agent.db|conversations,messages"
    "blueprints|${DATA_DIR}/blueprint_index.db|indexed_blueprints"
    "blueprints|${DATA_DIR}/blueprint_suggestions.db|blueprint_suggestions"
    "blueprints|${DATA_DIR}/miner.db|community_automations,miner_state"
    "energy|${DATA_DIR}/proactive_agent.db|suggestions,invalid_suggestion_reports"
    "devices|${DATA_DIR}/device_intelligence.db|device_intelligence"
    "devices|${DATA_DIR}/ha-setup.db|setup_sessions"
    "patterns|${DATA_DIR}/api-automation-edge.db|spec_versions"
    "rag|${DATA_DIR}/rag_service.db|rag_knowledge"
)

TOTAL=0
PASSED=0
FAILED=0

for migration in "${MIGRATIONS[@]}"; do
    IFS='|' read -r schema source tables <<< "$migration"

    if [ ! -f "$source" ]; then
        echo "SKIP: $source not found"
        continue
    fi

    echo "--- Migrating $source -> schema '$schema' ---"
    if python scripts/migrate-data/migrate_template.py \
        --source "sqlite:///$source" \
        --target "$POSTGRES_URL" \
        --schema "$schema" \
        --tables "$tables"; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
    ((TOTAL++))
done

echo ""
echo "=== Migration Summary ==="
echo "Total: $TOTAL | Passed: $PASSED | Failed: $FAILED"

if [ "$FAILED" -gt 0 ]; then
    echo "WARNING: Some migrations failed. Check logs above."
    exit 1
fi

echo "All migrations completed successfully!"
