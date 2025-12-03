# Root Directory Markdown File Cleanup Script
# Purpose: Categorize and move root .md files to appropriate locations

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

$ErrorActionPreference = "Stop"

# Define file categorization rules
$fileMappings = @{
    # Analysis files → implementation/analysis/
    "AI_AUTOMATION_SERVICE_ANALYSIS.md" = "implementation/analysis/"
    "DEVICE_DISPLAY_RESEARCH_SUMMARY.md" = "implementation/analysis/"
    "DOCUMENTATION_AUDIT_REPORT.md" = "implementation/analysis/"
    "DEPENDENCY_UPGRADE_REPORT.md" = "implementation/analysis/"
    
    # Verification files → implementation/verification/
    "INTEGRATION_TEST_REVIEW_AND_DEPLOYMENT.md" = "implementation/verification/"
    "EMBEDDING_TEST_README.md" = "implementation/verification/"
    
    # Status/Completion reports → implementation/
    "DEPLOYMENT_DEVICE_DATABASE.md" = "implementation/"
    "DEPLOYMENT_STATUS.md" = "implementation/"
    "IMPLEMENTATION_COMPLETE_SUMMARY.md" = "implementation/"
    "IMPLEMENTATION_SUMMARY.md" = "implementation/"
    "ENTITY_VALIDATION_FIX_STATUS.md" = "implementation/"
    "MCP_IMPLEMENTATION_SUMMARY.md" = "implementation/"
    "PHASE1_EXECUTION_SUMMARY.md" = "implementation/"
    "PHASE_3_UPGRADE_PLAN.md" = "implementation/"
    "QUICK_FIX_IMPLEMENTED.md" = "implementation/"
    "TRAINING_SESSION_COMPLETE_SUMMARY.md" = "implementation/"
    "COMPLETE_QUERY_DETAILS.md" = "implementation/"
    
    # Reference documentation → docs/
    "CLAUDE.md" = "docs/"
    "COMMIT_EXECUTION_GUIDE.md" = "docs/"
    "CREATE_GITHUB_ISSUES.md" = "docs/"
    "DOCKER_COMPOSE_UPDATE.md" = "docs/"
    "GITHUB_ISSUES.md" = "docs/"
    
    # Keep at root (standard project files)
    "README.md" = "ROOT"
    "CHANGELOG.md" = "ROOT"
    "CONTRIBUTING.md" = "ROOT"
    "COMMIT_PLAN.md" = "ROOT"  # Temporary planning file, can stay
}

# Files to keep at root
$keepAtRoot = @("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "COMMIT_PLAN.md")

Write-Host "=== Root Directory Markdown File Cleanup ===" -ForegroundColor Cyan
Write-Host ""

# Get all .md files in root
$rootFiles = Get-ChildItem -Path . -Filter "*.md" -File -Depth 0

$movedCount = 0
$skippedCount = 0
$errors = @()

foreach ($file in $rootFiles) {
    $fileName = $file.Name
    
    # Skip files that should stay at root
    if ($keepAtRoot -contains $fileName) {
        if ($Verbose) {
            Write-Host "SKIP: $fileName (stays at root)" -ForegroundColor Yellow
        }
        $skippedCount++
        continue
    }
    
    # Check if file has a mapping
    if ($fileMappings.ContainsKey($fileName)) {
        $targetDir = $fileMappings[$fileName]
        
        if ($targetDir -eq "ROOT") {
            if ($Verbose) {
                Write-Host "SKIP: $fileName (stays at root)" -ForegroundColor Yellow
            }
            $skippedCount++
            continue
        }
        
        # Ensure target directory exists
        if (-not (Test-Path $targetDir)) {
            if (-not $DryRun) {
                New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            }
            Write-Host "CREATE: $targetDir" -ForegroundColor Green
        }
        
        $targetPath = Join-Path $targetDir $fileName
        
        # Check if target already exists
        if (Test-Path $targetPath) {
            Write-Host "WARN: Target exists: $targetPath" -ForegroundColor Yellow
            Write-Host "      Skipping move of $fileName" -ForegroundColor Yellow
            $skippedCount++
            continue
        }
        
        if ($DryRun) {
            Write-Host "DRY-RUN: Would move $fileName → $targetPath" -ForegroundColor Cyan
        } else {
            try {
                Move-Item -Path $file.FullName -Destination $targetPath -Force
                Write-Host "MOVE: $fileName → $targetPath" -ForegroundColor Green
                $movedCount++
            } catch {
                Write-Host "ERROR: Failed to move $fileName - $_" -ForegroundColor Red
                $errors += "$fileName : $_"
            }
        }
    } else {
        # File not in mapping - categorize by pattern
        $targetDir = $null
        
        if ($fileName -match "_(ANALYSIS|RESEARCH|DIAGNOSIS|AUDIT)") {
            $targetDir = "implementation/analysis/"
        } elseif ($fileName -match "_(VERIFICATION|TEST|REVIEW)") {
            $targetDir = "implementation/verification/"
        } elseif ($fileName -match "_(COMPLETE|SUMMARY|STATUS|PLAN|IMPLEMENTATION)") {
            $targetDir = "implementation/"
        } elseif ($fileName -match "_(GUIDE|REFERENCE|DOCUMENTATION)") {
            $targetDir = "docs/"
        } else {
            Write-Host "UNMAPPED: $fileName (no automatic categorization)" -ForegroundColor Yellow
            $skippedCount++
            continue
        }
        
        if ($targetDir) {
            if (-not (Test-Path $targetDir)) {
                if (-not $DryRun) {
                    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
                }
            }
            
            $targetPath = Join-Path $targetDir $fileName
            
            if (Test-Path $targetPath) {
                Write-Host "WARN: Target exists: $targetPath" -ForegroundColor Yellow
                Write-Host "      Skipping move of $fileName" -ForegroundColor Yellow
                $skippedCount++
                continue
            }
            
            if ($DryRun) {
                Write-Host "DRY-RUN: Would move $fileName → $targetPath (pattern match)" -ForegroundColor Cyan
            } else {
                try {
                    Move-Item -Path $file.FullName -Destination $targetPath -Force
                    Write-Host "MOVE: $fileName → $targetPath (pattern match)" -ForegroundColor Green
                    $movedCount++
                } catch {
                    Write-Host "ERROR: Failed to move $fileName - $_" -ForegroundColor Red
                    $errors += "$fileName : $_"
                }
            }
        }
    }
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Files moved: $movedCount" -ForegroundColor Green
Write-Host "Files skipped: $skippedCount" -ForegroundColor Yellow

if ($errors.Count -gt 0) {
    Write-Host "Errors: $($errors.Count)" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

if ($DryRun) {
    Write-Host ""
    Write-Host "This was a DRY RUN. No files were actually moved." -ForegroundColor Yellow
    Write-Host "Run without -DryRun to perform the actual moves." -ForegroundColor Yellow
}

