#!/bin/bash

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
