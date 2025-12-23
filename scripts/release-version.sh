#!/bin/bash
# Release Version Script for HomeIQ
# Creates semantic version tags and triggers GitHub Actions release workflow
#
# Usage:
#   ./scripts/release-version.sh 1.2.3 "Release message"
#   ./scripts/release-version.sh 1.2.3-beta.1 "Beta release message"

set -e

VERSION="$1"
MESSAGE="$2"

if [ -z "$VERSION" ]; then
    echo "Error: Version is required"
    echo "Usage: $0 <version> [message]"
    echo "Example: $0 1.2.3 'Release version 1.2.3'"
    exit 1
fi

# Validate semantic version format
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.-]+)?$ ]]; then
    echo "Error: Invalid semantic version format: $VERSION"
    echo "Expected format: MAJOR.MINOR.PATCH[-PRERELEASE]"
    echo "Example: 1.2.3 or 1.2.3-beta.1"
    exit 1
fi

# Default message if not provided
if [ -z "$MESSAGE" ]; then
    MESSAGE="Release version $VERSION"
fi

# Check if we're on master branch
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_BRANCH" != "master" ]; then
    echo "Warning: You are not on the master branch (current: $CURRENT_BRANCH)"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if working directory is clean
if ! git diff-index --quiet HEAD --; then
    echo "Error: Working directory is not clean. Please commit or stash changes first."
    exit 1
fi

# Check if tag already exists
if git rev-parse "v$VERSION" >/dev/null 2>&1; then
    echo "Error: Tag v$VERSION already exists"
    exit 1
fi

# Create and push tag
echo "Creating tag v$VERSION..."
git tag -a "v$VERSION" -m "$MESSAGE"

echo "Pushing tag to origin..."
git push origin "v$VERSION"

echo ""
echo "✅ Successfully created and pushed tag v$VERSION"
echo ""
echo "GitHub Actions will now:"
echo "  1. Build Docker images for all services"
echo "  2. Tag images with semantic versions"
echo "  3. Push to GitHub Container Registry (ghcr.io)"
echo "  4. Run security scans"
echo "  5. Create GitHub release"
echo ""
echo "Monitor progress at: https://github.com/wtthornton/HomeIQ/actions"

