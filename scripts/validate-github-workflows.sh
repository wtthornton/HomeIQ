#!/bin/bash
# Validate GitHub Actions Workflows
# Checks for common issues in workflow files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WORKFLOWS_DIR="$PROJECT_ROOT/.github/workflows"

echo "🔍 Validating GitHub Actions Workflows..."
echo ""

ERRORS=0
WARNINGS=0

# Check if workflows directory exists
if [ ! -d "$WORKFLOWS_DIR" ]; then
    echo "❌ Workflows directory not found: $WORKFLOWS_DIR"
    exit 1
fi

# Check each workflow file
for workflow in "$WORKFLOWS_DIR"/*.yml "$WORKFLOWS_DIR"/*.yaml; do
    if [ ! -f "$workflow" ]; then
        continue
    fi
    
    filename=$(basename "$workflow")
    echo "📄 Checking $filename..."
    
    # Check for basic YAML syntax
    if ! python3 -c "import yaml; yaml.safe_load(open('$workflow'))" 2>/dev/null; then
        echo "  ❌ Invalid YAML syntax"
        ((ERRORS++))
    else
        echo "  ✅ Valid YAML syntax"
    fi
    
    # Check for common issues
    if grep -q "curl -f" "$workflow" 2>/dev/null; then
        echo "  ⚠️  Warning: Uses 'curl -f' (may not be available in containers)"
        ((WARNINGS++))
    fi
    
    if grep -q "docker compose exec.*curl" "$workflow" 2>/dev/null; then
        echo "  ⚠️  Warning: Uses curl in docker exec (may fail)"
        ((WARNINGS++))
    fi
    
    # Check for missing script references
    while IFS= read -r script_ref; do
        script_path=$(echo "$script_ref" | sed -E "s/.*['\"]([^'\"]+)['\"].*/\1/")
        if [[ "$script_path" == scripts/* ]]; then
            if [ ! -f "$PROJECT_ROOT/$script_path" ]; then
                echo "  ⚠️  Warning: Referenced script not found: $script_path"
                ((WARNINGS++))
            fi
        fi
    done < <(grep -E "scripts/[^ ]+" "$workflow" 2>/dev/null || true)
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Summary:"
echo "  Errors: $ERRORS"
echo "  Warnings: $WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ Validation failed with $ERRORS error(s)"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo ""
    echo "⚠️  Validation passed with $WARNINGS warning(s)"
    exit 0
else
    echo ""
    echo "✅ All workflows validated successfully"
    exit 0
fi
