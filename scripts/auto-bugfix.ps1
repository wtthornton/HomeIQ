# auto-bugfix.ps1 — Find bugs, fix them, and open a PR using Claude Code headless mode.
#
# Usage:
#   .\scripts\auto-bugfix.ps1 [-Bugs 5] [-Branch "auto/bugfix"] [-TargetDir "domains/"] [-Base "master"]
#
# Requirements:
#   - claude CLI installed and authenticated
#   - git configured with push access
#   - gh CLI installed (for PR creation)

param(
    [int]$Bugs = 5,
    [string]$Branch = "auto/bugfix-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [string]$TargetDir = "",
    [string]$Base = "master"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

# --- Preflight checks ---
foreach ($cmd in @("claude", "git", "gh")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "ERROR: '$cmd' is not installed or not in PATH."
        exit 1
    }
}

$dirty = git status --porcelain --ignore-submodules
if ($dirty) {
    Write-Error "ERROR: Working tree is dirty. Commit or stash changes first."
    exit 1
}

Write-Host "=== Auto Bug Fix Pipeline ===" -ForegroundColor Cyan
Write-Host "  Project:  $ProjectRoot"
Write-Host "  Bugs:     $Bugs"
Write-Host "  Branch:   $Branch"
Write-Host "  Base:     $Base"
Write-Host ""

# --- Step 1: Create feature branch ---
$currentBranch = (git branch --show-current).Trim()
if ($currentBranch -ne $Base) {
    Write-Host "[1/5] Switching to '$Base' and creating branch '$Branch'..." -ForegroundColor Yellow
    git checkout $Base
} else {
    Write-Host "[1/5] Already on '$Base'. Creating branch '$Branch'..." -ForegroundColor Yellow
}
git checkout -b $Branch

# --- Step 2: Find bugs with Claude Code ---
$scopeHint = ""
if ($TargetDir) {
    $scopeHint = "Focus your search on files under '$TargetDir'."
}

$findPrompt = @"
You are a senior Python developer doing a bug audit of the HomeIQ project.
Use the project's CLAUDE.md and your knowledge of the codebase structure to guide your search.

The project has 50 microservices under domains/ organized into 9 domain groups,
with shared libraries under libs/ (homeiq-patterns, homeiq-resilience, homeiq-observability, homeiq-data, homeiq-ha).
Key services: websocket-ingestion (8001), data-api (8006), admin-api (8004), health-dashboard (3000).

Find exactly $Bugs real, distinct bugs in the Python source code. $scopeHint

For each bug, identify:
1. File path and line number
2. What the bug is (be specific - off-by-one, missing null check, race condition, wrong operator, etc.)
3. Why it's a bug (what breaks or could break)

Rules:
- Only report REAL bugs that would cause incorrect behavior, crashes, or data loss at runtime.
- Do NOT report style issues, missing docstrings, type hints, or theoretical concerns.
- Do NOT report bugs in test files.
- Each bug must be in a different file.
- Prioritize bugs in Tier 1 critical services and shared libraries.

Output a JSON array with objects: {"file": "...", "line": N, "description": "...", "severity": "high|medium|low"}
Output ONLY the JSON array, no other text.
"@

Write-Host "[2/5] Scanning codebase for $Bugs bugs..." -ForegroundColor Yellow
$mcpConfig = Join-Path $ProjectRoot ".mcp.json"
$rawOutput = claude --print --max-turns 3 --mcp-config $mcpConfig $findPrompt 2>$null

# Extract JSON array from response
$jsonMatch = [regex]::Match($rawOutput, '\[[\s\S]*?\]')
if (-not $jsonMatch.Success) {
    Write-Error "ERROR: Failed to extract bug list JSON from Claude output."
    $rawOutput | Out-File -FilePath "$env:TEMP\auto-bugfix-raw.txt"
    Write-Host "Raw output saved to $env:TEMP\auto-bugfix-raw.txt"
    git checkout $Base
    git branch -D $Branch
    exit 1
}

$bugsJson = $jsonMatch.Value

try {
    $bugsList = $bugsJson | ConvertFrom-Json
    $bugCount = $bugsList.Count
} catch {
    Write-Error "ERROR: Invalid JSON in bug list."
    git checkout $Base
    git branch -D $Branch
    exit 1
}

Write-Host "  Found $bugCount bugs." -ForegroundColor Green
$bugsList | Format-Table -AutoSize

# --- Step 3: Fix bugs with Claude Code ---
Write-Host ""
Write-Host "[3/5] Fixing bugs..." -ForegroundColor Yellow

$fixPrompt = @"
You are a senior Python developer. Fix the following bugs in this codebase.

BUGS TO FIX:
$bugsJson

For each bug:
1. Read the file to understand the full context.
2. Make the minimal, correct fix. Do not refactor surrounding code.
3. Verify your fix doesn't break anything obvious.

After fixing ALL bugs, you MUST run these validation steps in order:
1. Call mcp__tapps-mcp__tapps_validate_changed() with default args (auto-detects changed files, quick mode)
2. Call mcp__tapps-mcp__tapps_checklist(task_type="bugfix")
3. If validation fails, fix the issues before finishing.

After validation passes, provide a summary of what you changed and the validation results.
"@

claude --print `
    --mcp-config $mcpConfig `
    --allowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_checklist,mcp__tapps-mcp__tapps_quick_check" `
    --max-turns 25 `
    $fixPrompt 2>$null

# Check if anything was actually changed
$changes = git status --porcelain
if (-not $changes) {
    Write-Error "ERROR: No files were modified. Fixes may have failed."
    git checkout $Base
    git branch -D $Branch
    exit 1
}

# --- Step 4: Commit and create PR ---
Write-Host ""
Write-Host "[4/5] Committing and creating PR..." -ForegroundColor Yellow

$changedFiles = (git diff --name-only) -join ", "
$commitMsg = "fix: auto-fix $bugCount bugs across codebase`n`nBugs found and fixed by automated Claude Code analysis.`n`nFiles changed: $changedFiles"

git add -A
git commit -m $commitMsg
git push -u origin $Branch

# Build PR body
$diffFiles = (git diff --name-only "$Base...$Branch" | ForEach-Object { "- $_" }) -join "`n"
$prBody = @"
## Automated Bug Fix

This PR was created by ``auto-bugfix.ps1`` using Claude Code in headless mode.

### Bugs Found and Fixed

``````json
$bugsJson
``````

### Changed Files
$diffFiles

---
*Review carefully before merging. These fixes were generated automatically.*
"@

$prUrl = gh pr create `
    --title "fix: auto-fix $bugCount bugs found by Claude Code analysis" `
    --body $prBody `
    --base $Base `
    --head $Branch

# --- Step 5: Collect TappsMCP feedback ---
Write-Host ""
Write-Host "[5/5] Collecting TappsMCP feedback..." -ForegroundColor Yellow

$runTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$feedbackPrompt = @"
You just completed an automated bugfix run. Review how the TappsMCP tools performed
during this session and append structured feedback to docs/TAPPS_FEEDBACK.md.

Run context:
- Date: $runTimestamp
- Branch: $Branch
- Bugs fixed: $bugCount
- Files changed: $changedFiles

Evaluate each TappsMCP tool you used (tapps_validate_changed, tapps_checklist, tapps_quick_check):

For each issue found, append a markdown entry to docs/TAPPS_FEEDBACK.md using this exact format:

### [CATEGORY] P[0-2]: One-line summary
- **Date**: $runTimestamp
- **Run**: $Branch
- **Tool**: tool_name
- **Detail**: What happened, what was expected, what was actual
- **Recurrence**: 1

Categories: BUG, FALSE_POSITIVE, FALSE_NEGATIVE, UX, PERF, ENHANCEMENT, INTEGRATION

Also call mcp__tapps-mcp__tapps_feedback for each tool you used (helpful=true/false with context).

If ALL tools worked perfectly with no issues, append nothing — the goal is an empty file.
Read docs/TAPPS_FEEDBACK.md first to check for recurring issues and increment their recurrence count.
"@

claude --print `
    --mcp-config $mcpConfig `
    --allowedTools "Read,Edit,mcp__tapps-mcp__tapps_feedback" `
    --max-turns 10 `
    $feedbackPrompt 2>$null

# Commit feedback file if it changed
$feedbackChanged = git diff --name-only docs/TAPPS_FEEDBACK.md
if ($feedbackChanged) {
    git add docs/TAPPS_FEEDBACK.md
    git commit -m "docs: tapps feedback from auto-bugfix run $runTimestamp"
    git push origin $Branch
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "  Branch: $Branch"
Write-Host "  PR:     $prUrl"
Write-Host "  Bugs:   $bugCount fixed"
Write-Host ""
Write-Host "Review the PR before merging."
