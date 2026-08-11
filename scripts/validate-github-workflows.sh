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
        # Assignment form, not ((ERRORS++)): a post-increment evaluates to the
        # OLD value, so the first one returns exit status 1 and `set -e` kills
        # the run. That is what limited this script to its first finding.
        ERRORS=$((ERRORS + 1))
    else
        echo "  ✅ Valid YAML syntax"
    fi
    
    # Check for common issues
    #
    # There was a `curl -f` warning here reading "may not be available in
    # containers". It confused the -f flag with curl being installed, so it
    # fired on af-agent-gate.yml's `curl -fsS --max-time 10 ... || <handle>`,
    # which is the correct way to write that call. The availability concern it
    # was reaching for is what the docker-exec check below actually tests.
    if grep -q "docker compose exec.*curl" "$workflow" 2>/dev/null; then
        echo "  ⚠️  Warning: Uses curl in docker exec (may fail)"
        WARNINGS=$((WARNINGS + 1))
    fi
    
    # Check for missing script references
    # Extract the scripts/... token itself. The previous sed pulled whatever sat
    # between the first pair of quotes, so an unquoted `run: bash scripts/x.sh`
    # left the whole line in script_path, failed the scripts/* test, and was
    # skipped — the check never fired on any workflow in this repo.
    #
    # The lookbehind keeps this to repo-root-relative paths. Without it,
    # af-agent-gate.yml's `.agentforge-kit/clients/.../scripts/af_publish.py`
    # matches on its tail and is reported missing, when in fact that tree is
    # checked out into place at runtime and the reference is correct.
    while IFS= read -r script_path; do
        [ -n "$script_path" ] || continue
        if [ ! -f "$PROJECT_ROOT/$script_path" ]; then
            echo "  ⚠️  Warning: Referenced script not found: $script_path"
            WARNINGS=$((WARNINGS + 1))
        fi
    done < <(grep -oP "(?<![A-Za-z0-9_./-])scripts/[A-Za-z0-9_./-]+" "$workflow" 2>/dev/null | sort -u)
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
