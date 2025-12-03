#!/bin/bash
# Simulation Framework Runner Script
#
# Convenience script to run simulation framework with common configurations.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMULATION_DIR="$(dirname "$SCRIPT_DIR")"

# Default values
MODE="standard"
HOMES=100
QUERIES=50
OUTPUT_DIR="simulation_results"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --homes)
            HOMES="$2"
            shift 2
            ;;
        --queries)
            QUERIES="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --quick)
            MODE="quick"
            HOMES=10
            QUERIES=5
            ;;
        --stress)
            MODE="stress"
            HOMES=1000
            QUERIES=500
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

cd "$SIMULATION_DIR"

echo "Running simulation framework..."
echo "  Mode: $MODE"
echo "  Homes: $HOMES"
echo "  Queries: $QUERIES"
echo "  Output: $OUTPUT_DIR"
echo ""

python cli.py \
    --mode "$MODE" \
    --homes "$HOMES" \
    --queries "$QUERIES" \
    --output-dir "$OUTPUT_DIR"

echo ""
echo "Simulation completed! Results in: $OUTPUT_DIR"

