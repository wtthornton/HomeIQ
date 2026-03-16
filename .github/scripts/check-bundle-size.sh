#!/usr/bin/env bash
# Bundle size check — warns on >10% growth, fails on >20% growth
# Usage: ./check-bundle-size.sh <app-dir> <max-main-kb>
#
# Example:
#   ./check-bundle-size.sh domains/frontends/ai-automation-ui 300
#   ./check-bundle-size.sh domains/core-platform/health-dashboard 350

set -euo pipefail

APP_DIR="${1:?Usage: check-bundle-size.sh <app-dir> <max-main-kb>}"
MAX_MAIN_KB="${2:-300}"

cd "$APP_DIR"

echo "=== Bundle Size Check: $(basename "$APP_DIR") ==="

# Build the app
npm run build 2>&1 | tail -5

# Find the main entry chunk (index-*.js or main-*.js)
MAIN_CHUNK=$(find dist/assets/js -name 'index-*.js' -o -name 'main-*.js' 2>/dev/null | head -1)

if [ -z "$MAIN_CHUNK" ]; then
  echo "ERROR: No main chunk found in dist/assets/js/"
  exit 1
fi

MAIN_SIZE_KB=$(( $(stat -c%s "$MAIN_CHUNK" 2>/dev/null || stat -f%z "$MAIN_CHUNK") / 1024 ))

echo "Main chunk: $(basename "$MAIN_CHUNK") = ${MAIN_SIZE_KB} KB (limit: ${MAX_MAIN_KB} KB)"

# Total JS size
TOTAL_JS_KB=0
for f in dist/assets/js/*.js; do
  SIZE=$(( $(stat -c%s "$f" 2>/dev/null || stat -f%z "$f") / 1024 ))
  TOTAL_JS_KB=$(( TOTAL_JS_KB + SIZE ))
done
echo "Total JS: ${TOTAL_JS_KB} KB"

# Count chunks
CHUNK_COUNT=$(find dist/assets/js -name '*.js' | wc -l)
echo "Chunk count: ${CHUNK_COUNT}"

# Check threshold
WARN_KB=$(( MAX_MAIN_KB * 110 / 100 ))
FAIL_KB=$(( MAX_MAIN_KB * 120 / 100 ))

if [ "$MAIN_SIZE_KB" -gt "$FAIL_KB" ]; then
  echo "FAIL: Main chunk ${MAIN_SIZE_KB} KB exceeds hard limit ${FAIL_KB} KB (+20%)"
  exit 1
elif [ "$MAIN_SIZE_KB" -gt "$WARN_KB" ]; then
  echo "WARN: Main chunk ${MAIN_SIZE_KB} KB exceeds soft limit ${WARN_KB} KB (+10%)"
  exit 0
else
  echo "PASS: Main chunk within budget"
  exit 0
fi
