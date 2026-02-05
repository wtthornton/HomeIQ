#!/bin/bash
# Error Aggregator - Collect errors from all containers
# Usage: ./aggregate-errors.sh

ERROR_LOG="${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/errors/all_errors_$(date +%Y%m%d_%H%M%S).log"

echo "Aggregating errors from all containers..."
echo "Output: $ERROR_LOG"

{
    echo "=== Error Aggregation - $(date) ==="
    echo ""

    for container in $(docker ps --filter name=homeiq --format "{{.Names}}"); do
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Container: $container"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Get errors from last hour
        docker logs "$container" --since 1h 2>&1 | \
            grep -i -E "error|exception|failed|critical|traceback" | \
            tail -20 || echo "No recent errors"

        echo ""
    done

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Aggregation completed: $(date)"
} | tee "$ERROR_LOG"

echo ""
echo "Error log saved: $ERROR_LOG"
