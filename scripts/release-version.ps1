# Release Version Script for HomeIQ (PowerShell)
# Creates semantic version tags and triggers GitHub Actions release workflow
#
# Usage:
#   .\scripts\release-version.ps1 -Version "1.2.3" -Message "Release message"
#   .\scripts\release-version.ps1 -Version "1.2.3-beta.1" -Message "Beta release message"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    
    [Parameter(Mandatory=$false)]
    [string]$Message
)

# Default message if not provided
if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "Release version $Version"
}

# Validate semantic version format
$versionPattern = '^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?$'
if ($Version -notmatch $versionPattern) {
    Write-Host "Error: Invalid semantic version format: $Version" -ForegroundColor Red
    Write-Host "Expected format: MAJOR.MINOR.PATCH[-PRERELEASE]" -ForegroundColor Yellow
    Write-Host "Example: 1.2.3 or 1.2.3-beta.1" -ForegroundColor Yellow
    exit 1
}

# Check if we're on master branch
$currentBranch = git rev-parse --abbrev-ref HEAD
if ($currentBranch -ne "master") {
    Write-Host "Warning: You are not on the master branch (current: $currentBranch)" -ForegroundColor Yellow
    $continue = Read-Host "Continue anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        exit 1
    }
}

# Check if working directory is clean
$status = git status --porcelain
if ($status) {
    Write-Host "Error: Working directory is not clean. Please commit or stash changes first." -ForegroundColor Red
    Write-Host "Uncommitted changes:" -ForegroundColor Yellow
    Write-Host $status
    exit 1
}

# Check if tag already exists
$tagExists = git rev-parse "v$Version" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Error: Tag v$Version already exists" -ForegroundColor Red
    exit 1
}

# Create and push tag
Write-Host "Creating tag v$Version..." -ForegroundColor Green
git tag -a "v$Version" -m $Message

Write-Host "Pushing tag to origin..." -ForegroundColor Green
git push origin "v$Version"

Write-Host ""
Write-Host "✅ Successfully created and pushed tag v$Version" -ForegroundColor Green
Write-Host ""
Write-Host "GitHub Actions will now:" -ForegroundColor Cyan
Write-Host "  1. Build Docker images for all services"
Write-Host "  2. Tag images with semantic versions"
Write-Host "  3. Push to GitHub Container Registry (ghcr.io)"
Write-Host "  4. Run security scans"
Write-Host "  5. Create GitHub release"
Write-Host ""
Write-Host "Monitor progress at: https://github.com/wtthornton/HomeIQ/actions" -ForegroundColor Cyan

