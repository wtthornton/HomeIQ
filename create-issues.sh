#!/bin/bash
# Script to create all 13 GitHub issues for test coverage improvement
# Requires GitHub CLI (gh) to be installed and authenticated

set -e

echo "🚀 Creating 13 GitHub Issues for Test Coverage Improvement"
echo "============================================================"
echo ""

# Check if gh is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed"
    echo "📖 Please install it from: https://cli.github.com/"
    echo "   Or use Method 1 or 2 from CREATE_GITHUB_ISSUES.md"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub"
    echo "🔑 Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI is installed and authenticated"
echo ""

# Function to create an issue
create_issue() {
    local title="$1"
    local labels="$2"
    local issue_num="$3"

    echo "📝 Creating Issue #${issue_num}: ${title}"

    # Extract the issue content from GITHUB_ISSUES.md
    # This is a placeholder - actual content would be extracted
    gh issue create \
        --title "${title}" \
        --label "${labels}" \
        --body "See GITHUB_ISSUES.md Issue #${issue_num} for complete details, code templates, and acceptance criteria.

This issue is part of the comprehensive test coverage improvement initiative.

**Quick Links:**
- Full details: https://github.com/wtthornton/HomeIQ/blob/main/GITHUB_ISSUES.md#issue-${issue_num}
- Test suite README: https://github.com/wtthornton/HomeIQ/blob/main/tests/shared/README.md

**Status:** Ready for implementation"

    echo "✅ Created: ${title}"
    echo ""
}

echo "Creating P0 - Critical Issues (5 issues)..."
echo "--------------------------------------------"

create_issue "[P0] Add AI Automation UI Test Suite (Vitest + React Testing Library)" \
    "testing,P0,enhancement" \
    "1"

create_issue "[P0] Add OpenVINO Service ML Tests (Embedding & NER Validation)" \
    "testing,P0,enhancement,AI" \
    "2"

create_issue "[P0] Add ML Service Algorithm Tests (Clustering & Anomaly Detection)" \
    "testing,P0,enhancement,AI" \
    "3"

create_issue "[P0] Add AI Core Service Orchestration Tests" \
    "testing,P0,enhancement,AI" \
    "4"

create_issue "[P0] 🚨 Add AI Code Executor Security Tests (CRITICAL)" \
    "testing,P0,security,enhancement" \
    "5"

echo ""
echo "Creating P1 - High Priority Issues (4 issues)..."
echo "--------------------------------------------------"

create_issue "[P1] Add Integration Test Suite with Testcontainers" \
    "testing,P1,enhancement" \
    "6"

create_issue "[P1] Add Performance Test Suite (pytest-benchmark)" \
    "testing,P1,enhancement" \
    "7"

create_issue "[P1] Add Database Migration Tests" \
    "testing,P1,enhancement" \
    "8"

create_issue "[P1] Add Health Dashboard Frontend Tests" \
    "testing,P1,enhancement" \
    "9"

echo ""
echo "Creating P2 - Medium Priority Issues (4 issues)..."
echo "----------------------------------------------------"

create_issue "[P2] Add Log Aggregator Tests" \
    "testing,P2,enhancement" \
    "10"

create_issue "[P2] Add Disaster Recovery Tests" \
    "testing,P2,enhancement" \
    "11"

create_issue "[P2] Setup CI/CD Test Pipeline" \
    "testing,P2,enhancement,ci/cd" \
    "12"

create_issue "[P2] Add Mutation Testing Baseline" \
    "testing,P2,enhancement" \
    "13"

echo ""
echo "============================================================"
echo "✅ Successfully created all 13 GitHub issues!"
echo ""
echo "📊 Summary:"
echo "   - P0 (Critical): 5 issues"
echo "   - P1 (High): 4 issues"
echo "   - P2 (Medium): 4 issues"
echo ""
echo "🔗 View issues: https://github.com/wtthornton/HomeIQ/issues?q=is%3Aissue+is%3Aopen+label%3Atesting"
echo ""
echo "📖 For detailed information, see:"
echo "   - GITHUB_ISSUES.md (complete documentation)"
echo "   - tests/shared/README.md (test suite overview)"
echo ""
echo "🚀 Next steps:"
echo "   1. Review and prioritize P0 issues"
echo "   2. Assign to sprint/developers"
echo "   3. Start with AI Automation UI or Security tests"

# Script to create GitHub issues from markdown templates
# Use 2025 patterns, architecture and versions for decisions

ISSUES_DIR=".github-issues"

# Function to create a single issue
create_issue() {
    local file=$1
    local title=$(head -n 1 "$file" | sed 's/^# //')
    local body=$(tail -n +2 "$file")

    echo "Creating issue: $title"
    gh issue create --title "$title" --body "$body"
}

# Create issues for each service
for issue_file in "$ISSUES_DIR"/*.md; do
    if [ -f "$issue_file" ]; then
        create_issue "$issue_file"
        sleep 1  # Rate limiting
    fi
done

echo "All issues created successfully!"
