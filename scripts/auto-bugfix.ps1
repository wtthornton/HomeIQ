# auto-bugfix.ps1 -- Find bugs, fix them, and open a PR using Claude Code headless mode.
#
# Usage:
#   .\scripts\auto-bugfix.ps1 [-Bugs 5] [-Branch "auto/bugfix"] [-TargetDir "domains/"] [-Base "master"]
#   .\scripts\auto-bugfix.ps1 -Bugs 1 -Chain          # Run bugfix + refactor + test
#   .\scripts\auto-bugfix.ps1 -Bugs 3 -NoDashboard    # Skip live dashboard
#   .\scripts\auto-bugfix.ps1 -Bugs 3 -NoRotate       # Scan entire repo instead of rotating
#
# Requirements:
#   - claude CLI installed and authenticated
#   - git configured with push access
#   - gh CLI installed (for PR creation)

param(
    [int]$Bugs = 5,
    [string]$Branch = "auto/bugfix-$(Get-Date -Format 'yyyyMMdd-HHmmss')",
    [string]$TargetDir = "",
    [string]$Base = "master",
    [switch]$Chain,
    [string]$ChainPhases = "fix,refactor,test",
    [switch]$NoDashboard,
    [switch]$NoRotate,
    [string]$TargetUnit = "",
    [switch]$Worktree,
    [string]$Model = "claude-sonnet-4-6",
    [double]$MaxCost = 2.00
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectRoot

# --- Rotate mode: pick next scan unit from manifest ---
$ScanManifest = Join-Path $ProjectRoot "docs/scan-manifest.json"
$ScanUnitId = ""
$ScanUnitName = ""
$ScanUnitHint = ""

$UseRotate = (-not $NoRotate) -or [bool]$TargetUnit
if ($UseRotate -and -not (Test-Path $ScanManifest)) {
    if ($TargetUnit) {
        Write-Error "ERROR: Scan manifest not found at $ScanManifest"
        exit 1
    }
    Write-Host "  Rotate: scan manifest not found, falling back to full-repo scan." -ForegroundColor Yellow
    $UseRotate = $false
}

if ($UseRotate) {
    $rotateScript = @"
import json, sys
from datetime import datetime, timezone

with open(r'$ScanManifest') as f:
    manifest = json.load(f)

target_unit = '$TargetUnit'
now = datetime.now(timezone.utc)

best_unit = None
best_score = -1

for unit in manifest['units']:
    if target_unit and unit['id'] != target_unit:
        continue

    if unit['last_scanned']:
        last = datetime.fromisoformat(unit['last_scanned'])
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days = max((now - last).total_seconds() / 86400, 0.1)
    else:
        days = 365

    bug_boost = 1 + unit['total_bugs_found'] / 5
    fp_penalty = 1 - (unit['false_positives'] / max(unit['total_bugs_found'], 1)) * 0.3
    score = unit['priority_weight'] * days * bug_boost * max(fp_penalty, 0.5)

    if score > best_score:
        best_score = score
        best_unit = unit

if not best_unit:
    print('ERROR', file=sys.stderr)
    sys.exit(1)

print(f"{best_unit['id']}|{best_unit['path']}|{best_unit['name']}|{best_unit['scan_hint']}")
"@

    $rotateResult = $rotateScript | python3 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "ERROR: Failed to pick scan unit from manifest"
        exit 1
    }

    $parts = $rotateResult -split '\|', 4
    $ScanUnitId = $parts[0]
    $TargetDir = $parts[1]
    $ScanUnitName = $parts[2]
    $ScanUnitHint = $parts[3]
    Write-Host "  Rotate: selected unit '$ScanUnitId' ($ScanUnitName)" -ForegroundColor Cyan
}

# --- Dashboard state management ---
$DashboardStateFile = Join-Path $ProjectRoot "scripts/.dashboard-state.json"
$DashboardHtml = Join-Path $ProjectRoot "scripts/dashboard.html"
$StartTime = Get-Date
$StartIso = $StartTime.ToString("o")
$Script:DashboardLog = [System.Collections.Generic.List[object]]::new()
$Script:ToolCalls = [System.Collections.Generic.List[object]]::new()
$Script:Usage = @{ input_tokens = 0; output_tokens = 0; total_cost_usd = 0; turns_used = 0; max_turns = 0 }
$Script:CurrentTool = @{ name = ""; target = ""; elapsed_s = 0 }

function Write-Dashboard {
    param(
        [int]$Step = 1,
        [string]$Status = "running",
        [string]$Message = "",
        [object]$BugsList = $null,
        [int]$BugsFound = -1,
        [int]$BugsFixed = -1,
        [int]$FilesChanged = -1,
        [string]$Validation = "",
        [string]$PrUrl = ""
    )

    if ($NoDashboard) { return }

    # Build current_tool from the last running tool call
    $curTool = @{ name = ""; target = ""; elapsed_s = 0 }
    if ($Script:ToolCalls.Count -gt 0) {
        $last = $Script:ToolCalls[-1]
        if ($last.status -eq "running") {
            $curTool.name = $last.tool_name
            $curTool.target = $last.target
            $curTool.elapsed_s = $last.duration_s
        }
    }

    $state = @{
        branch        = $Branch
        base          = $Base
        target_bugs   = $Bugs
        start_time    = $StartTime.ToString("yyyy-MM-dd HH:mm:ss")
        start_iso     = $StartIso
        project_root  = $ProjectRoot
        scan_unit     = if ($ScanUnitId) { "$ScanUnitId ($ScanUnitName)" } else { $null }
        total_steps   = $totalSteps
        current_step  = $Step
        status        = $Status
        status_message = $Message
        bugs_found    = if ($BugsFound -ge 0) { $BugsFound } else { $null }
        bugs_fixed    = if ($BugsFixed -ge 0) { $BugsFixed } else { $null }
        files_changed = if ($FilesChanged -ge 0) { $FilesChanged } else { $null }
        validation    = if ($Validation) { $Validation } else { $null }
        pr_url        = if ($PrUrl) { $PrUrl } else { $null }
        bugs          = if ($BugsList) { $BugsList } else { @() }
        log           = $Script:DashboardLog
        tool_calls    = $Script:ToolCalls
        usage         = $Script:Usage
        current_tool  = $curTool
        model         = $Model
        max_cost      = $MaxCost
    }

    $stateJson = $state | ConvertTo-Json -Depth 10
    $stateJson | Out-File -FilePath $DashboardStateFile -Encoding utf8 -Force

    # Also write a self-contained HTML with embedded state (avoids file:// CORS issues)
    $DashboardLiveHtml = Join-Path $ProjectRoot "scripts/dashboard-live.html"
    $templateContent = Get-Content $DashboardHtml -Raw
    $injectedHtml = $templateContent -replace '<script>', "<script>`nwindow.__DASHBOARD_STATE__ = $stateJson;`n"
    [System.IO.File]::WriteAllText($DashboardLiveHtml, $injectedHtml, [System.Text.UTF8Encoding]::new($false))
}

function Add-LogEntry {
    param(
        [string]$Msg,
        [string]$Level = "info"
    )
    $entry = @{
        time  = (Get-Date).ToString("HH:mm:ss")
        msg   = $Msg
        level = $Level
    }
    $Script:DashboardLog.Add($entry) | Out-Null
    # Also write to console
    $color = switch ($Level) {
        "success" { "Green" }
        "error"   { "Red" }
        "warn"    { "Yellow" }
        default   { "Gray" }
    }
    Write-Host "  [$($entry.time)] $Msg" -ForegroundColor $color
}

# --- Dot-source stream parser module ---
. "$ProjectRoot/scripts/auto-bugfix-stream.ps1"

# --- Preflight checks ---
foreach ($cmd in @("claude", "git", "gh")) {
    if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
        Write-Error "ERROR: '$cmd' is not installed or not in PATH."
        exit 1
    }
}

if (-not $Worktree) {
    $dirty = git status --porcelain --ignore-submodules
    if ($dirty) {
        Write-Error "ERROR: Working tree is dirty. Commit or stash changes first. (Use -Worktree to skip this check)"
        exit 1
    }
}

$totalSteps = if ($Chain) { 7 } else { 5 }

# --- Open dashboard ---
if (-not $NoDashboard) {
    Write-Dashboard -Step 1 -Message "Initializing pipeline..."
    Add-LogEntry "Pipeline starting" "info"
    Add-LogEntry "Opening dashboard in browser..." "info"
    $DashboardLiveHtml = Join-Path $ProjectRoot "scripts/dashboard-live.html"
    Start-Process $DashboardLiveHtml
}

Write-Host "=== Auto Bug Fix Pipeline ===" -ForegroundColor Cyan
Write-Host "  Project:  $ProjectRoot"
Write-Host "  Bugs:     $Bugs"
Write-Host "  Branch:   $Branch"
Write-Host "  Base:     $Base"
Write-Host "  Model:    $Model"
Write-Host "  Budget:   `$$MaxCost"
if ($Chain) { Write-Host "  Chain:    $ChainPhases" -ForegroundColor Magenta }
if ($ScanUnitId) { Write-Host "  Unit:     $ScanUnitId ($ScanUnitName)" -ForegroundColor Magenta }
Write-Host ""

# --- Step 1: Create feature branch ---
if ($Worktree) {
    # In worktree mode, we're already on the right branch
    $Branch = (git branch --show-current).Trim()
    Add-LogEntry "Worktree mode: already on branch '$Branch'" "info"
    Write-Dashboard -Step 1 -Message "Worktree mode: on branch '$Branch'"
    Write-Host "[1/$totalSteps] Worktree mode: already on branch '$Branch'" -ForegroundColor Yellow
} else {
    Add-LogEntry "Creating feature branch '$Branch'" "info"
    Write-Dashboard -Step 1 -Message "Creating feature branch..."

    $currentBranch = (git branch --show-current).Trim()
    if ($currentBranch -ne $Base) {
        Write-Host "[1/$totalSteps] Switching to '$Base' and creating branch '$Branch'..." -ForegroundColor Yellow
        git checkout $Base
    } else {
        Write-Host "[1/$totalSteps] Already on '$Base'. Creating branch '$Branch'..." -ForegroundColor Yellow
    }
    git checkout -b $Branch

    Add-LogEntry "Branch '$Branch' created" "success"
}
Write-Dashboard -Step 1 -Status "running" -Message "Branch created. Starting scan..."

# --- Step 2: Find bugs with Claude Code ---
$scopeHint = ""
if ($TargetDir) {
    $scopeHint = "Focus your search EXCLUSIVELY on files under '$TargetDir'."
    if ($ScanUnitHint) {
        $scopeHint += "`n$ScanUnitHint"
    }
}

# Load prompt overrides if they exist (Feature 12: Self-Improving Prompts)
$promptOverrides = ""
$overridesFile = Join-Path $ProjectRoot "docs/FIND_PROMPT_OVERRIDES.md"
if (Test-Path $overridesFile) {
    $promptOverrides = "`n`nADDITIONAL RULES FROM PREVIOUS RUNS:`n$(Get-Content $overridesFile -Raw)"
    Add-LogEntry "Loaded prompt overrides from FIND_PROMPT_OVERRIDES.md" "info"
}

$findPrompt = @"
You are a senior Python developer doing a FAST bug audit of the HomeIQ project.

TURN BUDGET: You have limited turns. Be efficient. Do NOT spend more than 2-3 turns on TappsMCP tools.

STEP 1 (2-3 turns max): Quick TappsMCP scan.
- Call mcp__tapps-mcp__tapps_security_scan on 1-2 key Python files in the target area.
- Call mcp__tapps-mcp__tapps_quick_check on 1-2 different key Python files.
- Do NOT scan more than 3 files total with TappsMCP tools.

STEP 2 (5-8 turns): Read code and find bugs.
- Use Glob to find Python files in the target area, then Read the most important ones.
- Look for: logic errors, race conditions, wrong operators, missing null checks, security issues.
- Combine what TappsMCP found with your own code review.
$scopeHint

Find exactly $Bugs real, distinct bugs. Each bug must be in a different file.

Rules:
- Only REAL bugs that cause incorrect behavior, crashes, or data loss at runtime.
- Do NOT report style issues, missing docstrings, type hints, or theoretical concerns.
- Do NOT report bugs in test files.
$promptOverrides

STEP 3 (FINAL turn): Output your results.
CRITICAL: You MUST output the bug list JSON wrapped in these exact markers on your LAST turn.
Do NOT spend additional turns after producing this output.

<<<BUGS>>>
[{"file": "path/to/file.py", "line": 42, "description": "what the bug is", "severity": "high|medium|low"}]
<<<END_BUGS>>>
"@

Write-Host "[2/$totalSteps] Scanning codebase for $Bugs bugs (TappsMCP + code review)..." -ForegroundColor Yellow
Add-LogEntry "Scanning with TappsMCP security_scan + quick_check + code review..." "info"
Write-Dashboard -Step 2 -Message "Scanning for $Bugs bugs (TappsMCP + review)..."

$mcpConfig = Join-Path $ProjectRoot ".mcp.json"
# Budget allocation: Scan 30%, Fix 40%, Refactor/Test 15%, Feedback 15%
$scanBudget = [math]::Round($MaxCost * 0.30, 2)
$fixBudget  = [math]::Round($MaxCost * 0.40, 2)
$chainBudget = [math]::Round($MaxCost * 0.15, 2)
$feedbackBudget = [math]::Round($MaxCost * 0.15, 2)

$bugsJson = ""
$scanAttempts = 2
$scanAllowedTools = "Read,Grep,Glob,Bash,mcp__tapps-mcp__tapps_security_scan,mcp__tapps-mcp__tapps_quick_check,mcp__tapps-mcp__tapps_score_file"

$retryPrompt = @"
You are a senior Python developer. Find exactly $Bugs real bugs in the HomeIQ project.
Do NOT use any MCP tools. Only use Read, Grep, and Glob to find and inspect Python files.
$scopeHint

Rules:
- Only REAL bugs (crashes, data loss, incorrect behavior). No style issues.
- Each bug in a different file. No test files.
$promptOverrides

Output your results wrapped in these EXACT markers:

<<<BUGS>>>
[{"file": "path/to/file.py", "line": 42, "description": "what the bug is", "severity": "high|medium|low"}]
<<<END_BUGS>>>
"@

for ($attempt = 1; $attempt -le $scanAttempts; $attempt++) {
    if ($attempt -gt 1) {
        Add-LogEntry "Retrying scan (attempt $attempt/$scanAttempts) -- direct code review only..." "warn"
        Write-Dashboard -Step 2 -Message "Retry ${attempt}: direct code review..."
    }

    # First attempt: 20 turns with TappsMCP; retry: 25 turns, no MCP, just code reading
    $scanTurns = if ($attempt -eq 1) { 20 } else { 25 }
    $currentPrompt = if ($attempt -eq 1) { $findPrompt } else { $retryPrompt }
    $currentTools = if ($attempt -eq 1) { $scanAllowedTools } else { "Read,Grep,Glob" }
    $rawOutput = $currentPrompt | Invoke-ClaudeStream -MaxTurns $scanTurns -McpConfig $mcpConfig -AllowedTools $currentTools -StepNumber 2 -StepLabel "Scan" -Model $Model -MaxBudget $scanBudget

    # Extract JSON array - try delimited markers first, fall back to greedy regex
    $jsonMatch = [regex]::Match($rawOutput, '<<<BUGS>>>\s*([\s\S]*?)\s*<<<END_BUGS>>>')
    if ($jsonMatch.Success) {
        $bugsJson = $jsonMatch.Groups[1].Value.Trim()
        Add-LogEntry 'Extracted bug list via BUGS markers' "info"
        break
    }

    $jsonMatch = [regex]::Match($rawOutput, '\[\s*\{[\s\S]*\}\s*\]')
    if ($jsonMatch.Success) {
        $bugsJson = $jsonMatch.Value
        Add-LogEntry "Extracted bug list via fallback regex" "warn"
        break
    }

    Add-LogEntry "Attempt ${attempt}: no JSON found in scan output" "warn"
    $rawOutput | Out-File -FilePath "$env:TEMP\auto-bugfix-raw-attempt$attempt.txt"
}

if (-not $bugsJson) {
    Add-LogEntry "Failed to extract bug list JSON after $scanAttempts attempts" "error"
    Write-Dashboard -Step 2 -Status "error" -Message "Failed to extract bug list after $scanAttempts attempts"
    Write-Error "ERROR: Failed to extract bug list JSON from Claude output."
    Write-Host "Raw output saved to $env:TEMP\auto-bugfix-raw-attempt*.txt"
    if (-not $Worktree) { git checkout $Base; git branch -D $Branch }
    exit 1
}

try {
    $bugsList = $bugsJson | ConvertFrom-Json
    $bugCount = $bugsList.Count
} catch {
    Add-LogEntry "Invalid JSON in bug list" "error"
    Write-Dashboard -Step 2 -Status "error" -Message "Invalid JSON in bug list"
    Write-Error "ERROR: Invalid JSON in bug list."
    if (-not $Worktree) { git checkout $Base; git branch -D $Branch }
    exit 1
}

Write-Host "  Found $bugCount bugs." -ForegroundColor Green
$bugsList | Format-Table -AutoSize

# Build dashboard bug list with pending status
$dashBugs = [System.Collections.Generic.List[object]]::new()
foreach ($b in $bugsList) {
    $dashBugs.Add(@{
        file        = $b.file
        line        = $b.line
        description = $b.description
        severity    = $b.severity
        fix_status  = "pending"
    }) | Out-Null
}

Add-LogEntry "Found $bugCount bugs" "success"
foreach ($b in $bugsList) {
    Add-LogEntry "  Bug: $($b.file):$($b.line) - $($b.description)" "info"
}
Write-Dashboard -Step 2 -Message "Found $bugCount bugs. Starting fixes..." -BugsList $dashBugs -BugsFound $bugCount

# --- Step 3: Fix bugs with Claude Code ---
$fixMaxTurns = [math]::Min($bugCount * 5 + 5, 30)  # 5 turns per bug + 5 for validation, cap at 30
Write-Host ""
Write-Host "[3/$totalSteps] Fixing bugs..." -ForegroundColor Yellow
Add-LogEntry "Fixing $bugCount bugs (Claude Code headless, max $fixMaxTurns turns)..." "info"
Write-Dashboard -Step 3 -Message "Fixing $bugCount bugs..." -BugsList $dashBugs -BugsFound $bugCount

$fixPrompt = @"
You are a senior Python developer. Fix the following bugs in this codebase.

BUGS TO FIX:
$bugsJson

For each bug:
1. Read the file to understand the full context.
2. Make the minimal, correct fix. Do not refactor surrounding code.
3. Verify your fix doesn't break anything obvious.

After fixing ALL bugs, validate your work:
1. Call mcp__tapps-mcp__tapps_quick_check on each changed file.
2. If any fix involves security, API design, or database logic, call mcp__tapps-mcp__tapps_consult_expert with a question about your approach.
3. Call mcp__tapps-mcp__tapps_validate_changed() to batch-validate all changes.
4. If validation fails, fix the issues before finishing.

After validation passes, provide a summary of what you changed and the validation results.
"@

$fixPrompt | Invoke-ClaudeStream -MaxTurns $fixMaxTurns -McpConfig $mcpConfig -AllowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_checklist,mcp__tapps-mcp__tapps_quick_check,mcp__tapps-mcp__tapps_consult_expert,mcp__tapps-mcp__tapps_impact_analysis" -StepNumber 3 -StepLabel "Fix" -Model $Model -MaxBudget $fixBudget

# Check if anything was actually changed (ignore submodule drift)
$changes = git status --porcelain --ignore-submodules
if (-not $changes) {
    Add-LogEntry "No files were modified. Fixes may have failed." "error"
    Write-Dashboard -Step 3 -Status "error" -Message "No files were modified. Fixes may have failed."
    Write-Error "ERROR: No files were modified. Fixes may have failed."
    if (-not $Worktree) { git checkout $Base; git branch -D $Branch }
    exit 1
}

# Update bug statuses -- cross-reference changed files with bug list
$changedFilesList = @(git diff --name-only --ignore-submodules)
$changedFilesCount = $changedFilesList.Count
$bugsFixed = 0
foreach ($db in $dashBugs) {
    # Normalize: bug file path may be relative, changed files are repo-relative
    $bugFile = $db.file -replace '\\', '/'
    $matched = $changedFilesList | Where-Object { ($_ -replace '\\', '/') -like "*$bugFile" -or $bugFile -like "*$_" }
    if ($matched) {
        $db.fix_status = "fixed"
        $bugsFixed++
    } else {
        $db.fix_status = "unfixed"
    }
}

if ($bugsFixed -eq $bugCount) {
    Add-LogEntry "All $bugCount bugs fixed. $changedFilesCount files changed." "success"
} else {
    Add-LogEntry "$bugsFixed of $bugCount bugs fixed. $changedFilesCount files changed." "warn"
}
foreach ($f in $changedFilesList) {
    Add-LogEntry "  Modified: $f" "info"
}
Add-LogEntry "TAPPS validation completed" "success"
Write-Dashboard -Step 3 -Message "$bugsFixed/$bugCount bugs fixed and validated." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass"

# --- Chain Mode: Refactor Phase ---
if ($Chain -and $ChainPhases -match "refactor") {
    Write-Host ""
    Write-Host "[4/$totalSteps] Refactoring fixed files..." -ForegroundColor Magenta
    Add-LogEntry "Chain mode: refactoring fixed files..." "info"
    Write-Dashboard -Step 4 -Message "Refactoring fixed files..." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass"

    $changedFiles = (git diff --name-only --ignore-submodules) -join ", "
    $refactorPrompt = @"
You are a senior Python developer. Review and minimally refactor these recently-fixed files:
$changedFiles

Apply ONLY these improvements where clearly beneficial:
- Extract duplicated logic into a helper (only if 3+ identical blocks)
- Simplify overly complex conditionals
- Fix obvious naming issues (single-letter vars in non-loop contexts)
- Remove dead code (unreachable branches, unused imports)

Do NOT:
- Change any behavior or fix additional bugs
- Add docstrings, comments, or type hints
- Restructure modules or move code between files

Before refactoring, call mcp__tapps-mcp__tapps_impact_analysis on the main file to check blast radius.
Use mcp__tapps-mcp__tapps_dead_code to find unused imports/functions to remove.
After refactoring, run mcp__tapps-mcp__tapps_validate_changed() to verify quality improved.
Provide a summary of refactoring applied.
"@

    $refactorPrompt | Invoke-ClaudeStream -MaxTurns 15 -McpConfig $mcpConfig -AllowedTools "Read,Edit,Grep,Glob,Bash,mcp__tapps-mcp__tapps_validate_changed,mcp__tapps-mcp__tapps_quick_check,mcp__tapps-mcp__tapps_dead_code,mcp__tapps-mcp__tapps_impact_analysis,mcp__tapps-mcp__tapps_consult_expert" -StepNumber 4 -StepLabel "Refactor" -Model $Model -MaxBudget $chainBudget

    $refactorChanges = git diff --name-only --ignore-submodules
    if ($refactorChanges) {
        Add-LogEntry "Refactoring complete. Committing refactor changes." "success"
    } else {
        Add-LogEntry "No refactoring changes needed." "info"
    }
}

# --- Chain Mode: Test Phase ---
if ($Chain -and $ChainPhases -match "test") {
    $testStep = if ($ChainPhases -match "refactor") { 5 } else { 4 }
    Write-Host ""
    Write-Host "[$testStep/$totalSteps] Generating tests for fixed bugs..." -ForegroundColor Magenta
    Add-LogEntry "Chain mode: generating tests for fixed bugs..." "info"
    Write-Dashboard -Step $testStep -Message "Generating tests for fixed bugs..." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass"

    $testPrompt = @"
You are a senior Python developer. Write unit tests for these bug fixes:

BUGS THAT WERE FIXED:
$bugsJson

For each bug:
1. Read the fixed file to understand the fix.
2. Write a pytest test that would have FAILED before the fix and PASSES after.
3. Place tests in the appropriate tests/ directory near the source file.
4. Use pytest conventions: test_*.py files, test_* functions.
5. Mock external dependencies (databases, APIs, file I/O).

After writing tests, run: pytest <test_file> -v --tb=short to verify they pass.
Then run mcp__tapps-mcp__tapps_quick_check on each test file.
"@

    $testPrompt | Invoke-ClaudeStream -MaxTurns 20 -McpConfig $mcpConfig -AllowedTools "Read,Edit,Write,Grep,Glob,Bash,mcp__tapps-mcp__tapps_quick_check" -StepNumber 5 -StepLabel "Test" -Model $Model -MaxBudget $chainBudget

    $testChanges = git status --porcelain --ignore-submodules
    if ($testChanges) {
        Add-LogEntry "Test generation complete." "success"
    } else {
        Add-LogEntry "No tests were generated." "warn"
    }
}

# --- Step 4/6: Commit and create PR ---
$commitStep = if ($Chain) { 6 } else { 4 }
Write-Host ""
Write-Host "[$commitStep/$totalSteps] Committing and creating PR..." -ForegroundColor Yellow
Add-LogEntry "Committing changes and creating PR..." "info"
Write-Dashboard -Step $commitStep -Message "Committing and creating PR..." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass"

$changedFiles = (git diff --name-only --ignore-submodules) -join ", "
$commitPrefix = if ($Chain) { "fix+refactor+test" } else { "fix" }
$commitMsg = "$commitPrefix`: auto-fix $bugCount bugs across codebase`n`nBugs found and fixed by automated Claude Code analysis.`n`nFiles changed: $changedFiles"

# Stage only tracked changes, excluding submodules
git diff --name-only --ignore-submodules | ForEach-Object { git add -- $_ }
# Also stage new files from chain test phase, excluding submodules
git status --porcelain --ignore-submodules | Where-Object { $_ -match '^\?\?' } | ForEach-Object { git add -- $_.Substring(3) }
git commit -m $commitMsg
git push -u origin $Branch

Add-LogEntry "Pushed to origin/$Branch" "success"

# Build PR body
$diffFiles = (git diff --name-only "$Base...$Branch" | ForEach-Object { "- $_" }) -join "`n"
$chainNote = if ($Chain) { "`n`n### Chain Mode`nPhases executed: $ChainPhases" } else { "" }
$prBody = @"
## Automated Bug Fix

This PR was created by ``auto-bugfix.ps1`` using Claude Code in headless mode.
$chainNote

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

Add-LogEntry "PR created: $prUrl" "success"
Write-Dashboard -Step $commitStep -Message "PR created." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass" -PrUrl $prUrl

# --- Step 5/7: Collect TappsMCP feedback ---
$feedbackStep = if ($Chain) { 7 } else { 5 }
Write-Host ""
Write-Host "[$feedbackStep/$totalSteps] Collecting TappsMCP feedback..." -ForegroundColor Yellow
Add-LogEntry "Collecting TappsMCP feedback..." "info"
Write-Dashboard -Step $feedbackStep -Message "Collecting TappsMCP feedback..." -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass" -PrUrl $prUrl

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

If ALL tools worked perfectly with no issues, append nothing -- the goal is an empty file.
Read docs/TAPPS_FEEDBACK.md first to check for recurring issues and increment their recurrence count.
"@

$feedbackPrompt | Invoke-ClaudeStream -MaxTurns 10 -McpConfig $mcpConfig -AllowedTools "Read,Edit,mcp__tapps-mcp__tapps_feedback" -StepNumber $feedbackStep -StepLabel "Feedback" -Model $Model -MaxBudget $feedbackBudget

# Commit feedback file if it changed
$feedbackChanged = git diff --name-only docs/TAPPS_FEEDBACK.md
if ($feedbackChanged) {
    git add docs/TAPPS_FEEDBACK.md
    git commit -m "docs: tapps feedback from auto-bugfix run $runTimestamp"
    git push origin $Branch
    Add-LogEntry "Feedback committed and pushed." "success"
}

# --- Append to bug history (Feature 12) ---
$historyFile = Join-Path $ProjectRoot "docs/BUG_HISTORY.json"
$historyEntry = @{
    run_id    = $Branch
    date      = $runTimestamp
    branch    = $Branch
    chain     = [bool]$Chain
    bugs      = @($bugsList | ForEach-Object {
        @{
            file        = $_.file
            line        = $_.line
            description = $_.description
            severity    = $_.severity
            was_real    = $null
            pr_merged   = $null
        }
    })
}

if (Test-Path $historyFile) {
    $history = Get-Content $historyFile -Raw | ConvertFrom-Json
    # ConvertFrom-Json may return a single object, ensure it's an array
    if ($history -isnot [array]) { $history = @($history) }
} else {
    $history = @()
}
$history += $historyEntry
$history | ConvertTo-Json -Depth 10 | Out-File -FilePath $historyFile -Encoding utf8 -Force
Add-LogEntry "Bug history appended to docs/BUG_HISTORY.json" "info"

# --- Update scan manifest if rotate mode ---
if ($ScanUnitId) {
    $manifest = Get-Content $ScanManifest -Raw | ConvertFrom-Json
    $now = (Get-Date).ToUniversalTime().ToString("o")
    foreach ($unit in $manifest.units) {
        if ($unit.id -eq $ScanUnitId) {
            $unit.last_scanned = $now
            $unit.total_runs += 1
            $unit.total_bugs_found += $bugCount
            break
        }
    }
    $manifest.last_unit_scanned = $ScanUnitId
    $manifest.total_runs += 1
    $manifest | ConvertTo-Json -Depth 10 | Out-File -FilePath $ScanManifest -Encoding utf8 -Force
    Add-LogEntry "Scan manifest updated for unit '$ScanUnitId'" "info"
}

# --- Done ---
$elapsed = (Get-Date) - $StartTime
$elapsedStr = "{0:mm\:ss}" -f $elapsed
Add-LogEntry "Pipeline complete in $elapsedStr" "success"
Write-Dashboard -Step $feedbackStep -Status "done" -Message "Complete! $bugsFixed/$bugCount bugs fixed in $elapsedStr. PR: $prUrl" -BugsList $dashBugs -BugsFound $bugCount -BugsFixed $bugsFixed -FilesChanged $changedFilesCount -Validation "pass" -PrUrl $prUrl

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Green
Write-Host "  Branch: $Branch"
Write-Host "  PR:     $prUrl"
Write-Host "  Bugs:   $bugCount fixed"
Write-Host "  Time:   $elapsedStr"
Write-Host ""
Write-Host "Review the PR before merging."
