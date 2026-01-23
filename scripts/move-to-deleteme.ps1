# HomeIQ Repository Cleanup - Move to Deleteme Script
# Executes the cleanup plan by moving files to deleteme/ folder

param(
    [switch]$DryRun,
    [int]$Phase = 0,  # 0 = all phases
    [switch]$All
)

$ErrorActionPreference = "Continue"
$script:MoveCount = 0
$script:ErrorCount = 0

function Write-PhaseHeader {
    param($Message)
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host $Message -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
}

function Safe-Move {
    param(
        [string]$Source,
        [string]$Destination,
        [string]$Description
    )
    
    if (-not (Test-Path $Source)) {
        Write-Host "  [SKIP] $Description - Source not found: $Source" -ForegroundColor Yellow
        return
    }
    
    $destDir = Split-Path $Destination -Parent
    if (-not (Test-Path $destDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $destDir -Force | Out-Null
        }
    }
    
    if ($DryRun) {
        Write-Host "  [DRY RUN] Would move: $Source -> $Destination" -ForegroundColor Gray
        $script:MoveCount++
    } else {
        try {
            Move-Item -Path $Source -Destination $Destination -Force -ErrorAction Stop
            Write-Host "  [OK] Moved: $Description" -ForegroundColor Green
            $script:MoveCount++
        } catch {
            Write-Host "  [ERROR] Failed to move: $Source - $($_.Exception.Message)" -ForegroundColor Red
            $script:ErrorCount++
        }
    }
}

# Phase 1: Create Deleteme Structure
function Execute-Phase1 {
    Write-PhaseHeader "Phase 1: Create Deleteme Structure"
    
    $dirs = @(
        "deleteme",
        "deleteme\docs",
        "deleteme\implementation",
        "deleteme\services-archive",
        "deleteme\scripts",
        "deleteme\other"
    )
    
    foreach ($dir in $dirs) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        Write-Host "  [OK] Created directory: $dir" -ForegroundColor Green
    }
}

# Phase 2: Documentation Cleanup
function Execute-Phase2 {
    Write-PhaseHeader "Phase 2: Documentation Cleanup"
    
    # Step 2.1: Planning & Design Artifacts
    Write-Host "Step 2.1: Moving Planning & Design Artifacts..." -ForegroundColor Yellow
    
    Safe-Move "docs\prd" "deleteme\docs\prd" "PRD directory"
    Safe-Move "docs\stories" "deleteme\docs\stories" "Stories directory"
    Safe-Move "docs\architecture\decisions" "deleteme\docs\architecture-decisions" "Architecture decisions"
    Safe-Move "docs\design-system" "deleteme\docs\design-system" "Design system"
    
    # Step 2.2: Historical & Assessment Documents
    Write-Host "`nStep 2.2: Moving Historical & Assessment Documents..." -ForegroundColor Yellow
    
    Safe-Move "docs\qa" "deleteme\docs\qa" "QA assessments"
    Safe-Move "docs\archive" "deleteme\docs\archive" "Archive directory"
    Safe-Move "docs\research" "deleteme\docs\research" "Research artifacts"
    Safe-Move "docs\suggestions" "deleteme\docs\suggestions" "Suggestions artifacts"
    Safe-Move "docs\migration" "deleteme\docs\migration" "Migration guides"
    Safe-Move "docs\testing" "deleteme\docs\testing" "Testing strategy docs"
    
    # Step 2.3: Knowledge Base Cache
    Write-Host "`nStep 2.3: Moving Knowledge Base Cache..." -ForegroundColor Yellow
    
    Safe-Move "docs\kb" "deleteme\docs\kb" "Knowledge base cache"
    
    # Step 2.4: Current Documentation (Guides)
    Write-Host "`nStep 2.4: Moving Current Documentation (Guides)..." -ForegroundColor Yellow
    
    Safe-Move "docs\current" "deleteme\docs\current" "Current documentation"
    
    # Move Epic-specific deployment guides
    $epicGuides = @(
        @{Source = "docs\deployment\EPIC_39_DEPLOYMENT_GUIDE.md"; Dest = "deleteme\docs\deployment\EPIC_39_DEPLOYMENT_GUIDE.md"},
        @{Source = "docs\deployment\AI5_INFLUXDB_BUCKETS_SETUP.md"; Dest = "deleteme\docs\deployment\AI5_INFLUXDB_BUCKETS_SETUP.md"}
    )
    
    foreach ($guide in $epicGuides) {
        if (Test-Path $guide.Source) {
            $destDir = Split-Path $guide.Dest -Parent
            if (-not (Test-Path $destDir)) {
                if (-not $DryRun) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
            }
            Safe-Move $guide.Source $guide.Dest "Epic guide: $(Split-Path $guide.Source -Leaf)"
        }
    }
    
    # Step 2.5: Clean Up Architecture Directory
    Write-Host "`nStep 2.5: Cleaning Up Architecture Directory..." -ForegroundColor Yellow
    
    $keepFiles = @("database-schema.md", "influxdb-schema.md", "event-flow-architecture.md")
    
    if (Test-Path "docs\architecture") {
        Get-ChildItem "docs\architecture" -File | Where-Object {
            $keepFiles -notcontains $_.Name
        } | ForEach-Object {
            $dest = "deleteme\docs\architecture\$($_.Name)"
            Safe-Move $_.FullName $dest "Architecture file: $($_.Name)"
        }
        
        # Move subdirectories
        Get-ChildItem "docs\architecture" -Directory | ForEach-Object {
            Safe-Move $_.FullName "deleteme\docs\architecture\$($_.Name)" "Architecture subdirectory: $($_.Name)"
        }
    }
}

# Phase 3: Implementation Notes Cleanup
function Execute-Phase3 {
    Write-PhaseHeader "Phase 3: Implementation Notes Cleanup"
    
    # Create subdirectories
    $implDirs = @(
        "deleteme\implementation\status-reports",
        "deleteme\implementation\completion-reports",
        "deleteme\implementation\fix-reports",
        "deleteme\implementation\session-summaries"
    )
    
    foreach ($dir in $implDirs) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    # Move status reports
    Write-Host "Moving status reports..." -ForegroundColor Yellow
    Get-ChildItem "implementation" -File -Filter "*_STATUS.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\status-reports\$($_.Name)" "Status report: $($_.Name)"
    }
    Get-ChildItem "implementation" -File -Filter "DEPLOYMENT_*.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\status-reports\$($_.Name)" "Deployment report: $($_.Name)"
    }
    
    # Move completion reports
    Write-Host "`nMoving completion reports..." -ForegroundColor Yellow
    Get-ChildItem "implementation" -File -Filter "*_COMPLETE.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\completion-reports\$($_.Name)" "Completion report: $($_.Name)"
    }
    Get-ChildItem "implementation" -File -Filter "EPIC_*_COMPLETE.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\completion-reports\$($_.Name)" "Epic completion: $($_.Name)"
    }
    
    # Move fix reports
    Write-Host "`nMoving fix reports..." -ForegroundColor Yellow
    Get-ChildItem "implementation" -File -Filter "*_FIX_*.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\fix-reports\$($_.Name)" "Fix report: $($_.Name)"
    }
    Get-ChildItem "implementation" -File -Filter "*_FIXES_*.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\fix-reports\$($_.Name)" "Fixes report: $($_.Name)"
    }
    
    # Move session summaries
    Write-Host "`nMoving session summaries..." -ForegroundColor Yellow
    Get-ChildItem "implementation" -File -Filter "SESSION_*.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\session-summaries\$($_.Name)" "Session summary: $($_.Name)"
    }
    Get-ChildItem "implementation" -File -Filter "*_SUMMARY.md" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\implementation\session-summaries\$($_.Name)" "Summary: $($_.Name)"
    }
    
    # Move subdirectories
    Write-Host "`nMoving implementation subdirectories..." -ForegroundColor Yellow
    Safe-Move "implementation\analysis" "deleteme\implementation\analysis" "Analysis directory"
    Safe-Move "implementation\verification" "deleteme\implementation\verification" "Verification directory"
    Safe-Move "implementation\archive" "deleteme\implementation\archive" "Implementation archive"
}

# Phase 4: Service Archive Cleanup
function Execute-Phase4 {
    Write-PhaseHeader "Phase 4: Service Archive Cleanup"
    
    Safe-Move "services\archive" "deleteme\services-archive" "Services archive directory"
}

# Phase 5: Root Directory Cleanup
function Execute-Phase5 {
    Write-PhaseHeader "Phase 5: Root Directory Cleanup"
    
    # Move root-level markdown files (except README.md)
    Write-Host "Moving root-level markdown files..." -ForegroundColor Yellow
    Get-ChildItem "." -File -Filter "*.md" -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ne "README.md"
    } | ForEach-Object {
        Safe-Move $_.FullName "deleteme\other\$($_.Name)" "Root file: $($_.Name)"
    }
    
    # Move backup files
    Write-Host "`nMoving backup files..." -ForegroundColor Yellow
    Get-ChildItem "." -File -Filter ".env.backup*" -ErrorAction SilentlyContinue | ForEach-Object {
        Safe-Move $_.FullName "deleteme\other\$($_.Name)" "Backup file: $($_.Name)"
    }
    
    # Move old docker-compose files
    Write-Host "`nMoving old docker-compose files..." -ForegroundColor Yellow
    $oldDockerFiles = @(
        "docker-compose.complete.yml",
        "docker-compose.prod.yml"
    )
    
    foreach ($file in $oldDockerFiles) {
        if (Test-Path $file) {
            Safe-Move $file "deleteme\other\$file" "Old docker-compose: $file"
        }
    }
    
    # Move other root-level files from git status
    Write-Host "`nMoving other root-level files..." -ForegroundColor Yellow
    $otherFiles = @(
        "assistant_message.txt",
        "conversation_data.json",
        "automation_actions.yaml",
        "automation_from_ha.json",
        "debug_automation_error.py",
        "debug_automation_with_tapps.py"
    )
    
    foreach ($file in $otherFiles) {
        if (Test-Path $file) {
            Safe-Move $file "deleteme\other\$file" "Root file: $file"
        }
    }
}

# Phase 6: Scripts Cleanup (Manual review required)
function Execute-Phase6 {
    Write-PhaseHeader "Phase 6: Scripts Cleanup"
    Write-Host "  [NOTE] Scripts cleanup requires manual review" -ForegroundColor Yellow
    Write-Host "  [NOTE] No scripts moved automatically" -ForegroundColor Yellow
}

# Phase 8: Verification and Review
function Execute-Phase8 {
    Write-PhaseHeader "Phase 8: Verification and Review"
    
    # Generate summary
    Write-Host "Generating summary..." -ForegroundColor Yellow
    
    if (-not $DryRun) {
        $summary = @{
            "docs" = (Get-ChildItem "deleteme\docs" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "implementation" = (Get-ChildItem "deleteme\implementation" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "services_archive" = (Get-ChildItem "deleteme\services-archive" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "other" = (Get-ChildItem "deleteme\other" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "total" = 0
        }
        $summary.total = $summary.docs + $summary.implementation + $summary.services_archive + $summary.other
        
        $summary | ConvertTo-Json -Depth 10 | Out-File "deleteme\MOVED_ITEMS_SUMMARY.json" -Encoding UTF8
        Write-Host "  [OK] Summary saved to deleteme\MOVED_ITEMS_SUMMARY.json" -ForegroundColor Green
    }
    
    # Update .gitignore
    Write-Host "`nUpdating .gitignore..." -ForegroundColor Yellow
    if (Test-Path ".gitignore") {
        $gitignoreContent = Get-Content ".gitignore" -Raw -ErrorAction SilentlyContinue
        if ($gitignoreContent -and $gitignoreContent -notmatch "deleteme") {
            if (-not $DryRun) {
                Add-Content -Path ".gitignore" -Value "`n# Temporary folder for items pending deletion review`ndeleteme/"
                Write-Host "  [OK] Added deleteme/ to .gitignore" -ForegroundColor Green
            } else {
                Write-Host "  [DRY RUN] Would add deleteme/ to .gitignore" -ForegroundColor Gray
            }
        } else {
            Write-Host "  [SKIP] deleteme/ already in .gitignore or .gitignore not found" -ForegroundColor Yellow
        }
    }
}

# Main execution
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "HomeIQ Repository Cleanup - Move to Deleteme" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`n[DRY RUN MODE] - No files will be moved`n" -ForegroundColor Yellow
}

if ($Phase -eq 0 -or $All) {
    Execute-Phase1
    Execute-Phase2
    Execute-Phase3
    Execute-Phase4
    Execute-Phase5
    Execute-Phase6
    Execute-Phase8
} else {
    switch ($Phase) {
        1 { Execute-Phase1 }
        2 { Execute-Phase2 }
        3 { Execute-Phase3 }
        4 { Execute-Phase4 }
        5 { Execute-Phase5 }
        6 { Execute-Phase6 }
        8 { Execute-Phase8 }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Files moved: $script:MoveCount" -ForegroundColor Green
Write-Host "Errors: $script:ErrorCount" -ForegroundColor $(if ($script:ErrorCount -gt 0) { "Red" } else { "Green" })
Write-Host "`nCleanup complete! Review deleteme/ folder before final deletion.`n" -ForegroundColor Cyan
