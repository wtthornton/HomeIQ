# =============================================================================
# HomeIQ SQLite Cutover - Dry-Run Report (PowerShell)
# =============================================================================
#
# Story 6.5 preparation script. Produces a report of everything that will
# change on cutover day. Does NOT make any modifications.
#
# Prerequisites:
#   - PostgreSQL stability check must pass (check-pg-stability.sh)
#
# Usage:
#   .\scripts\sqlite-cutover.ps1
#   .\scripts\sqlite-cutover.ps1 -SkipStability
#   .\scripts\sqlite-cutover.ps1 -JsonOutput
#
# =============================================================================

param(
    [switch]$SkipStability,
    [switch]$JsonOutput,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

if ($Help) {
    Write-Host "Usage: .\sqlite-cutover.ps1 [-SkipStability] [-JsonOutput]"
    Write-Host ""
    Write-Host "Dry-run report for SQLite cutover (Story 6.5)."
    Write-Host "Does NOT make any changes."
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -SkipStability  Skip PostgreSQL stability check"
    Write-Host "  -JsonOutput     Output as JSON"
    exit 0
}

# ---------------------------------------------------------------------------
# Database files with dual SQLite/PostgreSQL code
# ---------------------------------------------------------------------------

$DatabaseFiles = @(
    "domains\core-platform\data-api\src\database.py"
    "domains\automation-core\ai-automation-service-new\src\database\__init__.py"
    "domains\automation-core\ha-ai-agent-service\src\database.py"
    "domains\automation-core\ai-query-service\src\database\__init__.py"
    "domains\ml-engine\ai-training-service\src\database\__init__.py"
    "domains\ml-engine\rag-service\src\database\session.py"
    "domains\ml-engine\device-intelligence-service\src\core\database.py"
    "domains\energy-analytics\proactive-agent-service\src\database.py"
    "domains\blueprints\automation-miner\src\miner\database.py"
    "domains\blueprints\blueprint-index\src\database.py"
    "domains\blueprints\blueprint-suggestion-service\src\database.py"
    "domains\device-management\ha-setup-service\src\database.py"
    "domains\pattern-analysis\ai-pattern-service\src\database\__init__.py"
    "domains\pattern-analysis\api-automation-edge\src\registry\spec_registry.py"
)

# ---------------------------------------------------------------------------
# Step 0: Stability gate
# ---------------------------------------------------------------------------

$timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-dd HH:mm:ss UTC")

if (-not $JsonOutput) {
    Write-Host "============================================================" -ForegroundColor White
    Write-Host "  HomeIQ SQLite Cutover - Dry-Run Report" -ForegroundColor White
    Write-Host "  $timestamp" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor White
    Write-Host ""
}

if (-not $SkipStability) {
    if (-not $JsonOutput) {
        Write-Host "--- Step 0: PostgreSQL Stability Gate ---" -ForegroundColor White
    }
    $stabilityScript = Join-Path $ScriptDir "check-pg-stability.sh"
    if (Test-Path $stabilityScript) {
        if (-not $JsonOutput) {
            Write-Host "  [INFO] Run check-pg-stability.sh manually in bash to verify stability." -ForegroundColor Yellow
            Write-Host "         Proceeding with report generation." -ForegroundColor Yellow
            Write-Host ""
        }
    } else {
        if (-not $JsonOutput) {
            Write-Host "  [WARN] Stability script not found at $stabilityScript" -ForegroundColor Yellow
            Write-Host ""
        }
    }
}

# ---------------------------------------------------------------------------
# Step 1: Database files
# ---------------------------------------------------------------------------

if (-not $JsonOutput) {
    Write-Host "--- Step 1: Database Files with SQLite Fallback Code ---" -ForegroundColor White
    Write-Host "  These files contain dual SQLite/PostgreSQL code." -ForegroundColor Gray
    Write-Host "  On cutover day, the SQLite branches will be removed." -ForegroundColor Gray
    Write-Host ""
}

$dbFileCount = 0
$foundDbFiles = @()

foreach ($f in $DatabaseFiles) {
    $fullPath = Join-Path $ProjectRoot $f
    if (Test-Path $fullPath) {
        $dbFileCount++
        $foundDbFiles += $f
        if (-not $JsonOutput) {
            $content = Get-Content $fullPath -Raw
            $sqliteLines = ($content | Select-String -Pattern "sqlite|aiosqlite|PRAGMA|_is_postgres|StaticPool" -AllMatches).Matches.Count
            Write-Host "  [$dbFileCount] $f  ($sqliteLines SQLite-related matches)" -ForegroundColor Cyan
        }
    } else {
        if (-not $JsonOutput) {
            Write-Host "  [MISSING] $f" -ForegroundColor Yellow
        }
    }
}

if (-not $JsonOutput) {
    Write-Host ""
    Write-Host "  Total database files to modify: $dbFileCount" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Step 2: Compose env vars
# ---------------------------------------------------------------------------

if (-not $JsonOutput) {
    Write-Host "--- Step 2: Compose Environment Variables to Remove ---" -ForegroundColor White
    Write-Host "  SQLite-related env vars in compose files." -ForegroundColor Gray
    Write-Host ""
}

$composeFiles = Get-ChildItem -Path (Join-Path $ProjectRoot "domains") -Recurse -Filter "compose.yml"
$composeChanges = @()

foreach ($cf in $composeFiles) {
    $lineNum = 0
    foreach ($line in (Get-Content $cf.FullName)) {
        $lineNum++
        if ($line -match "(?i)(sqlite|SQLITE_)") {
            $relPath = $cf.FullName.Replace("$ProjectRoot\", "")
            $entry = "${relPath}:${lineNum}: $($line.Trim())"
            $composeChanges += $entry
            if (-not $JsonOutput) {
                Write-Host "  - $entry" -ForegroundColor Yellow
            }
        }
    }
}

if (-not $JsonOutput) {
    Write-Host ""
    Write-Host "  Total env var lines to review: $($composeChanges.Count)" -ForegroundColor White
    Write-Host ""
}

# Volume references
if (-not $JsonOutput) {
    Write-Host "--- Step 2b: Docker Volumes to Remove ---" -ForegroundColor White
    Write-Host ""
}

$volumeChanges = @()
foreach ($cf in $composeFiles) {
    $lineNum = 0
    foreach ($line in (Get-Content $cf.FullName)) {
        $lineNum++
        if ($line -match "sqlite-data") {
            $relPath = $cf.FullName.Replace("$ProjectRoot\", "")
            $entry = "${relPath}:${lineNum}: $($line.Trim())"
            $volumeChanges += $entry
            if (-not $JsonOutput) {
                Write-Host "  - $entry" -ForegroundColor Yellow
            }
        }
    }
}

if (-not $JsonOutput) {
    Write-Host ""
    Write-Host "  Total volume references: $($volumeChanges.Count)" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Step 3: requirements.txt with aiosqlite
# ---------------------------------------------------------------------------

if (-not $JsonOutput) {
    Write-Host "--- Step 3: requirements.txt Files with aiosqlite ---" -ForegroundColor White
    Write-Host "  aiosqlite can be removed from these files on cutover day." -ForegroundColor Gray
    Write-Host ""
}

$reqFiles = Get-ChildItem -Path (Join-Path $ProjectRoot "domains") -Recurse -Filter "requirements.txt"
$aiosqliteFiles = @()

foreach ($rf in $reqFiles) {
    $content = Get-Content $rf.FullName
    $match = $content | Where-Object { $_ -match "aiosqlite" }
    if ($match) {
        $relPath = $rf.FullName.Replace("$ProjectRoot\", "")
        $aiosqliteFiles += $relPath
        if (-not $JsonOutput) {
            Write-Host "  - $relPath  ($($match.Trim()))" -ForegroundColor Cyan
        }
    }
}

if (-not $JsonOutput) {
    Write-Host ""
    Write-Host "  Total requirements.txt to update: $($aiosqliteFiles.Count)" -ForegroundColor White
    Write-Host ""
}

# ---------------------------------------------------------------------------
# Step 4: Summary
# ---------------------------------------------------------------------------

if (-not $JsonOutput) {
    Write-Host "============================================================" -ForegroundColor White
    Write-Host "  Cutover Day Summary" -ForegroundColor White
    Write-Host "============================================================" -ForegroundColor White
    Write-Host ""
    Write-Host "  Database files to refactor:      $dbFileCount" -ForegroundColor White
    Write-Host "  Compose env var lines to review: $($composeChanges.Count)" -ForegroundColor White
    Write-Host "  Docker volume references:        $($volumeChanges.Count)" -ForegroundColor White
    Write-Host "  requirements.txt to update:      $($aiosqliteFiles.Count)" -ForegroundColor White
    Write-Host ""
    Write-Host "  NOTE: This is a DRY-RUN report. No changes were made." -ForegroundColor Yellow
    Write-Host "  Cutover target: earliest 2026-03-10" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Cutover day checklist: docs\operations\sqlite-cutover-checklist.md" -ForegroundColor Gray
    Write-Host ""
}

# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

if ($JsonOutput) {
    $jsonTimestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

    $result = @{
        timestamp = $jsonTimestamp
        status = "DRY_RUN"
        cutover_target = "2026-03-10"
        database_files = $foundDbFiles
        compose_env_var_lines = $composeChanges.Count
        volume_references = $volumeChanges.Count
        aiosqlite_requirements = $aiosqliteFiles
        summary = @{
            database_files_count = $dbFileCount
            compose_changes_count = $composeChanges.Count
            volume_references_count = $volumeChanges.Count
            requirements_count = $aiosqliteFiles.Count
        }
    }

    $result | ConvertTo-Json -Depth 3
}
