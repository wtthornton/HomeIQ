# HomeIQ Repository Cleanup - Expanded Move to Deleteme Script
# Comprehensive cleanup of all non-essential files and folders

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
    if ($destDir -and -not (Test-Path $destDir)) {
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

# Phase 1: Ensure Deleteme Structure
function Execute-Phase1 {
    Write-PhaseHeader "Phase 1: Ensure Deleteme Structure"
    
    $dirs = @(
        "deleteme",
        "deleteme\docs",
        "deleteme\docs\workflows",
        "deleteme\docs\planning",
        "deleteme\docs\prototype",
        "deleteme\docs\requirements",
        "deleteme\docs\reviews",
        "deleteme\docs\implementation",
        "deleteme\implementation",
        "deleteme\implementation\github-issues",
        "deleteme\services-archive",
        "deleteme\scripts",
        "deleteme\other",
        "deleteme\tools",
        "deleteme\examples",
        "deleteme\src",
        "deleteme\github-issues"
    )
    
    foreach ($dir in $dirs) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
        Write-Host "  [OK] Created directory: $dir" -ForegroundColor Green
    }
}

# Phase 2: Documentation Cleanup (Expanded)
function Execute-Phase2 {
    Write-PhaseHeader "Phase 2: Documentation Cleanup (Expanded)"
    
    # Move cleanup/guide documents (historical)
    Write-Host "Moving cleanup/guide documents..." -ForegroundColor Yellow
    $cleanupDocs = @(
        "docs\BRANCH_CLEANUP_GUIDE.md",
        "docs\CLEANUP_PROCESS_IMPROVEMENT.md",
        "docs\DOCUMENTATION_CLEANUP_SUMMARY.md"
    )
    foreach ($doc in $cleanupDocs) {
        Safe-Move $doc "deleteme\docs\$($doc.Replace('docs\', ''))" "Cleanup guide: $(Split-Path $doc -Leaf)"
    }
    
    # Move planning artifacts
    Write-Host "`nMoving planning artifacts..." -ForegroundColor Yellow
    Safe-Move "docs\planning" "deleteme\docs\planning" "Planning directory"
    
    # Move prototype artifacts
    Write-Host "`nMoving prototype artifacts..." -ForegroundColor Yellow
    Safe-Move "docs\prototype" "deleteme\docs\prototype" "Prototype directory"
    
    # Move requirements (planning artifacts)
    Write-Host "`nMoving requirements..." -ForegroundColor Yellow
    Safe-Move "docs\requirements" "deleteme\docs\requirements" "Requirements directory"
    
    # Move review reports
    Write-Host "`nMoving review reports..." -ForegroundColor Yellow
    Safe-Move "docs\reviews" "deleteme\docs\reviews" "Reviews directory"
    
    # Move implementation guides from docs (should be in implementation/)
    Write-Host "`nMoving implementation guides from docs..." -ForegroundColor Yellow
    Safe-Move "docs\implementation" "deleteme\docs\implementation" "Implementation guides in docs"
    
    # Move old workflow outputs (keep only recent ones - last 5)
    Write-Host "`nMoving old workflow outputs..." -ForegroundColor Yellow
    if (Test-Path "docs\workflows\simple-mode") {
        $workflowDirs = Get-ChildItem "docs\workflows\simple-mode" -Directory | 
            Sort-Object LastWriteTime -Descending | 
            Select-Object -Skip 5
        
        foreach ($dir in $workflowDirs) {
            Safe-Move $dir.FullName "deleteme\docs\workflows\simple-mode\$($dir.Name)" "Old workflow: $($dir.Name)"
        }
    }
    
    # Move other non-essential docs
    Write-Host "`nMoving other non-essential documentation..." -ForegroundColor Yellow
    $otherDocs = @(
        "docs\AI_AGENT_CRASH_QUICK_START.md",
        "docs\DATASET_RESEARCH_RECOMMENDATIONS.md",
        "docs\DEVELOPMENT.md",
        "docs\MULTIPLE_INSTALLATIONS_WARNING.md",
        "docs\QUICK_FIX_AI_AGENT_CRASHES.md",
        "docs\requirements.md",
        "docs\TAPPS_AGENTS_CONTEXT7_AUTO_ENHANCEMENT.md"
    )
    foreach ($doc in $otherDocs) {
        if (Test-Path $doc) {
            Safe-Move $doc "deleteme\docs\$(Split-Path $doc -Leaf)" "Doc: $(Split-Path $doc -Leaf)"
        }
    }
    
    # Move deployment fix notes (historical)
    Write-Host "`nMoving historical deployment notes..." -ForegroundColor Yellow
    $deploymentDocs = @(
        "docs\deployment\DEPLOYMENT_FIXES_DECEMBER_2025.md",
        "docs\deployment\SYNERGIES_API_DEPLOYMENT_NOTES.md"
    )
    foreach ($doc in $deploymentDocs) {
        if (Test-Path $doc) {
            $destDir = "deleteme\docs\deployment"
            if (-not (Test-Path $destDir)) {
                if (-not $DryRun) {
                    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
                }
            }
            Safe-Move $doc "$destDir\$(Split-Path $doc -Leaf)" "Deployment note: $(Split-Path $doc -Leaf)"
        }
    }
}

# Phase 3: Implementation Notes Cleanup (Expanded)
function Execute-Phase3 {
    Write-PhaseHeader "Phase 3: Implementation Notes Cleanup (Expanded)"
    
    # Move github-issues from implementation
    Write-Host "Moving github-issues from implementation..." -ForegroundColor Yellow
    Safe-Move "implementation\github-issues" "deleteme\implementation\github-issues" "GitHub issues docs"
    
    # Move API documentation (might be essential, but moving for review)
    Write-Host "`nMoving API documentation from implementation..." -ForegroundColor Yellow
    Safe-Move "implementation\HomeIQ_API_Driven_Automations_Docs" "deleteme\implementation\HomeIQ_API_Driven_Automations_Docs" "API documentation"
    
    # Move remaining implementation files
    Write-Host "`nMoving remaining implementation files..." -ForegroundColor Yellow
    $implFiles = @(
        "implementation\AUTOMATION_MISMATCH_RESOLVED.md",
        "implementation\BEADS_BD_ISSUES_AND_RECOMMENDATIONS.md",
        "implementation\HA_2026_1_AUTOMATION_LAYER_IMPLEMENTATION_PLAN.md",
        "implementation\NEXT_STEPS.md",
        "implementation\PATTERN_ANALYSIS_VERIFICATION_STEPS.md"
    )
    foreach ($file in $implFiles) {
        if (Test-Path $file) {
            Safe-Move $file "deleteme\implementation\$(Split-Path $file -Leaf)" "Implementation file: $(Split-Path $file -Leaf)"
        }
    }
}

# Phase 4: GitHub Issues Cleanup
function Execute-Phase4 {
    Write-PhaseHeader "Phase 4: GitHub Issues Cleanup"
    
    # Move .github-issues directory (critical issues tracking - moving for review)
    Write-Host "Moving .github-issues directory..." -ForegroundColor Yellow
    Safe-Move ".github-issues" "deleteme\github-issues" "GitHub issues tracking"
}

# Phase 5: Examples Cleanup
function Execute-Phase5 {
    Write-PhaseHeader "Phase 5: Examples Cleanup"
    
    # Move examples directory (demo/example files)
    Write-Host "Moving examples directory..." -ForegroundColor Yellow
    Safe-Move "examples" "deleteme\examples" "Examples directory"
}

# Phase 6: Tools Cleanup
function Execute-Phase6 {
    Write-PhaseHeader "Phase 6: Tools Cleanup"
    
    # Move ask_ai_improvement (might be non-essential)
    Write-Host "Moving ask_ai_improvement..." -ForegroundColor Yellow
    Safe-Move "tools\ask_ai_improvement" "deleteme\tools\ask_ai_improvement" "Ask AI improvement tools"
    
    # Move test/debug scripts
    Write-Host "`nMoving test/debug scripts..." -ForegroundColor Yellow
    $testScripts = @(
        "tools\ask-ai-continuous-improvement-unit-test.py",
        "tools\ask-ai-continuous-improvement.py",
        "tools\monitor_openvino_loading.py",
        "tools\test_scoring_fixes.py",
        "tools\verify-pattern-synergy-integration.py"
    )
    foreach ($script in $testScripts) {
        if (Test-Path $script) {
            Safe-Move $script "deleteme\tools\$(Split-Path $script -Leaf)" "Test script: $(Split-Path $script -Leaf)"
        }
    }
    
    # Move documentation in tools
    Write-Host "`nMoving documentation in tools..." -ForegroundColor Yellow
    $toolDocs = @(
        "tools\ASK_AI_CONTINUOUS_IMPROVEMENT_README.md",
        "tools\ultimate_validate_command.md"
    )
    foreach ($doc in $toolDocs) {
        if (Test-Path $doc) {
            Safe-Move $doc "deleteme\tools\$(Split-Path $doc -Leaf)" "Tool doc: $(Split-Path $doc -Leaf)"
        }
    }
}

# Phase 7: Source Directory Cleanup
function Execute-Phase7 {
    Write-PhaseHeader "Phase 7: Source Directory Cleanup"
    
    # Check if src/ is used or obsolete
    Write-Host "Moving src/ directory (if obsolete)..." -ForegroundColor Yellow
    
    # Check if files in src/ are referenced elsewhere
    $srcFiles = Get-ChildItem "src" -File -ErrorAction SilentlyContinue
    if ($srcFiles) {
        Write-Host "  [NOTE] Found files in src/: $($srcFiles.Count) files" -ForegroundColor Yellow
        Write-Host "  [NOTE] Moving for review - verify if these are used" -ForegroundColor Yellow
        
        # Move individual files
        foreach ($file in $srcFiles) {
            Safe-Move $file.FullName "deleteme\src\$($file.Name)" "Source file: $($file.Name)"
        }
    }
}

# Phase 8: Root Directory Additional Cleanup
function Execute-Phase8 {
    Write-PhaseHeader "Phase 8: Root Directory Additional Cleanup"
    
    # Move any remaining root-level markdown files (except README.md)
    Write-Host "Moving remaining root-level markdown files..." -ForegroundColor Yellow
    Get-ChildItem "." -File -Filter "*.md" -ErrorAction SilentlyContinue | Where-Object {
        $_.Name -ne "README.md" -and $_.Name -notlike "*.plan.md"
    } | ForEach-Object {
        Safe-Move $_.FullName "deleteme\other\$($_.Name)" "Root file: $($_.Name)"
    }
    
    # Move any .json config files that might be obsolete
    Write-Host "`nMoving obsolete config files..." -ForegroundColor Yellow
    $obsoleteConfigs = @(
        ".gitignore.quality",
        ".jscpd.json"
    )
    foreach ($config in $obsoleteConfigs) {
        if (Test-Path $config) {
            Safe-Move $config "deleteme\other\$config" "Config file: $config"
        }
    }
}

# Phase 9: Generate Summary
function Execute-Phase9 {
    Write-PhaseHeader "Phase 9: Generate Summary"
    
    # Generate summary
    Write-Host "Generating summary..." -ForegroundColor Yellow
    
    if (-not $DryRun) {
        $summary = @{
            "docs" = (Get-ChildItem "deleteme\docs" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "implementation" = (Get-ChildItem "deleteme\implementation" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "services_archive" = (Get-ChildItem "deleteme\services-archive" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "other" = (Get-ChildItem "deleteme\other" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "tools" = (Get-ChildItem "deleteme\tools" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "examples" = (Get-ChildItem "deleteme\examples" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "src" = (Get-ChildItem "deleteme\src" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "github_issues" = (Get-ChildItem "deleteme\github-issues" -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count
            "total" = 0
        }
        
        # Calculate total (handle potential errors)
        try {
            $summary.total = $summary.docs + $summary.implementation + $summary.services_archive + $summary.other + $summary.tools + $summary.examples + $summary.src + $summary.github_issues
        } catch {
            $summary.total = "Error calculating"
        }
        
        $summary | ConvertTo-Json -Depth 10 | Out-File "deleteme\MOVED_ITEMS_SUMMARY_EXPANDED.json" -Encoding UTF8
        Write-Host "  [OK] Summary saved to deleteme\MOVED_ITEMS_SUMMARY_EXPANDED.json" -ForegroundColor Green
    }
}

# Main execution
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "HomeIQ Repository Cleanup - Expanded Move to Deleteme" -ForegroundColor Cyan
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
    Execute-Phase7
    Execute-Phase8
    Execute-Phase9
} else {
    switch ($Phase) {
        1 { Execute-Phase1 }
        2 { Execute-Phase2 }
        3 { Execute-Phase3 }
        4 { Execute-Phase4 }
        5 { Execute-Phase5 }
        6 { Execute-Phase6 }
        7 { Execute-Phase7 }
        8 { Execute-Phase8 }
        9 { Execute-Phase9 }
    }
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Files moved: $script:MoveCount" -ForegroundColor Green
Write-Host "Errors: $script:ErrorCount" -ForegroundColor $(if ($script:ErrorCount -gt 0) { "Red" } else { "Green" })
Write-Host "`nExpanded cleanup complete! Review deleteme/ folder before final deletion.`n" -ForegroundColor Cyan
