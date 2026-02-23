#!/bin/bash
# tapps-batch-review.sh - Review a service directory's Python files
# Usage: ./scripts/tapps-batch-review.sh <service_name> <output_dir>

SERVICE="$1"
OUTPUT_DIR="${2:-c:/cursor/HomeIQ/docs/tapps-review-results}"
PROJECT_ROOT="c:/cursor/HomeIQ"
SERVICE_DIR="$PROJECT_ROOT/services/$SERVICE/src"

mkdir -p "$OUTPUT_DIR"

call_tapps() {
    local tool_name="$1"
    local params="$2"
    [ -z "$params" ] && params="{}"
    printf '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"review","version":"1.0"}},"id":1}\n{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n{"jsonrpc":"2.0","method":"tools/call","params":{"name":"%s","arguments":%s},"id":2}\n' "$tool_name" "$params" | TAPPS_MCP_PROJECT_ROOT="$PROJECT_ROOT" tapps-mcp serve 2>/dev/null | tail -1
}

# Check service exists
if [ ! -d "$PROJECT_ROOT/services/$SERVICE" ]; then
    echo "{\"service\":\"$SERVICE\",\"error\":\"directory not found\"}" > "$OUTPUT_DIR/$SERVICE.json"
    exit 1
fi

# Find Python files (main source files, not tests)
if [ -d "$SERVICE_DIR" ]; then
    PY_FILES=$(find "$SERVICE_DIR" -name "*.py" -not -path "*/test*" -not -path "*/__pycache__/*" 2>/dev/null | sort)
else
    # Try alternate structures
    PY_FILES=$(find "$PROJECT_ROOT/services/$SERVICE" -maxdepth 3 -name "*.py" -not -path "*/test*" -not -path "*/__pycache__/*" -not -path "*/node_modules/*" 2>/dev/null | sort)
fi

if [ -z "$PY_FILES" ]; then
    echo "{\"service\":\"$SERVICE\",\"files\":0,\"note\":\"no python files found\"}" > "$OUTPUT_DIR/$SERVICE.json"
    exit 0
fi

FILE_COUNT=$(echo "$PY_FILES" | wc -l | tr -d ' ')
echo "Reviewing $SERVICE ($FILE_COUNT Python files)..."

# Score each file
RESULTS="[]"
ISSUES=""
PASS_COUNT=0
FAIL_COUNT=0

for f in $PY_FILES; do
    REL_PATH="${f#$PROJECT_ROOT/}"
    echo "  Scoring: $REL_PATH"

    # Use quick check for speed
    RESULT=$(call_tapps "tapps_quick_check" "{\"file_path\":\"$f\",\"preset\":\"standard\"}")

    # Extract structured content
    GATE_PASSED=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); sc=r.get('structuredContent',{}); data=sc.get('data',{}); print(data.get('gate',{}).get('passed','unknown'))" 2>/dev/null)
    OVERALL_SCORE=$(echo "$RESULT" | python -c "import sys,json; d=json.load(sys.stdin); r=d.get('result',{}); sc=r.get('structuredContent',{}); data=sc.get('data',{}); print(data.get('score',{}).get('overall',data.get('gate',{}).get('score','?')))" 2>/dev/null)

    if [ "$GATE_PASSED" = "True" ] || [ "$GATE_PASSED" = "true" ]; then
        PASS_COUNT=$((PASS_COUNT + 1))
        STATUS="PASS"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        STATUS="FAIL"
        ISSUES="$ISSUES\n  $REL_PATH (score: $OVERALL_SCORE)"
    fi

    echo "    -> $STATUS (score: $OVERALL_SCORE)"
done

# Write summary
cat > "$OUTPUT_DIR/$SERVICE.txt" << SUMMARY
=== TAPPS Review: $SERVICE ===
Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Files: $FILE_COUNT
Passed: $PASS_COUNT
Failed: $FAIL_COUNT

SUMMARY

if [ -n "$ISSUES" ]; then
    echo -e "Issues:$ISSUES" >> "$OUTPUT_DIR/$SERVICE.txt"
fi

echo ""
echo "=== $SERVICE Summary: $PASS_COUNT pass / $FAIL_COUNT fail out of $FILE_COUNT files ==="
