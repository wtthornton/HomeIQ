#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Test Docker builds for all services to verify compilation with new contexts.

.DESCRIPTION
    This script builds all Docker services to verify they compile correctly
    after fixing absolute paths in Dockerfiles. It tests both production and
    development Dockerfiles where applicable.

.PARAMETER Services
    Optional array of specific service names to test. If not provided, tests all services.

.PARAMETER SkipCache
    Skip using Docker build cache (clean build).

.EXAMPLE
    .\scripts\test-docker-builds.ps1
    # Test all services

.EXAMPLE
    .\scripts\test-docker-builds.ps1 -Services @("websocket-ingestion", "data-api")
    # Test specific services only
#>

param(
    [string[]]$Services = @(),
    [switch]$SkipCache = $false
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

# Get all services from docker-compose.yml
function Get-ServicesFromCompose {
    $composeFile = "docker-compose.yml"
    if (-not (Test-Path $composeFile)) {
        throw "docker-compose.yml not found in current directory"
    }
    
    $content = Get-Content $composeFile -Raw
    $services = @()
    
    # Extract service names from docker-compose.yml
    $matches = [regex]::Matches($content, '(?m)^\s+(\w+):\s*$')
    foreach ($match in $matches) {
        $serviceName = $match.Groups[1].Value
        # Filter out non-service entries (like 'networks', 'volumes', etc.)
        if ($serviceName -notin @("networks", "volumes", "configs", "secrets", "x-")) {
            $services += $serviceName
        }
    }
    
    return $services | Sort-Object -Unique
}

# Test a single service build
function Test-ServiceBuild {
    param(
        [string]$ServiceName,
        [string]$Dockerfile = "Dockerfile",
        [string]$Context = "services/$ServiceName",
        [switch]$SkipCache
    )
    
    Write-Info -Message "`n[Testing] $ServiceName ($Dockerfile)"
    Write-Info -Message "  Context: $Context"
    
    $buildArgs = @(
        "build",
        "-f", "$Context/$Dockerfile",
        "-t", "homeiq-test-$ServiceName:test",
        $Context
    )
    
    if ($SkipCache) {
        $buildArgs += "--no-cache"
    }
    
    try {
        $output = & docker $buildArgs 2>&1
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Success -Message "  ✓ Build successful"
            return $true
        } else {
            $outputText = if ($output -is [array]) { $output -join "`n" } else { $output.ToString() }
            Write-ErrorMsg -Message "  ✗ Build failed (exit code: $exitCode)"
            Write-ErrorMsg -Message "  Output: $outputText"
            return $false
        }
    } catch {
        Write-ErrorMsg -Message "  ✗ Build error: $_"
        return $false
    }
}

# Main execution
Write-Info -Message "=========================================="
Write-Info -Message "Docker Build Test Suite"
Write-Info -Message "=========================================="
Write-Info -Message ""

# Get list of services to test
if ($Services.Count -eq 0) {
    Write-Info -Message "Discovering services from docker-compose.yml..."
    $allServices = Get-ServicesFromCompose
    Write-Info -Message "Found $($allServices.Count) services"
} else {
    $allServices = $Services
    Write-Info -Message "Testing $($allServices.Count) specified service(s)"
}

if ($SkipCache) {
    Write-Warning -Message "Cache disabled - performing clean builds"
}

Write-Info -Message ""

# Track results
$results = @{
    Total = 0
    Passed = 0
    Failed = 0
    FailedServices = @()
}

# Test each service
foreach ($service in $allServices) {
    $results.Total++
    
    $servicePath = "services/$service"
    
    # Check if service directory exists
    if (-not (Test-Path $servicePath)) {
        Write-Warning -Message "  ⚠ Service directory not found: $servicePath (skipping)"
        continue
    }
    
    # Test production Dockerfile
    $dockerfile = "Dockerfile"
    if (Test-Path "$servicePath/$dockerfile") {
        $passed = Test-ServiceBuild -ServiceName $service -Dockerfile $dockerfile -Context $servicePath -SkipCache:$SkipCache
        if (-not $passed) {
            $results.Failed++
            $results.FailedServices += "$service (production)"
        } else {
            $results.Passed++
        }
    } else {
        Write-Warning -Message "  ⚠ Dockerfile not found: $servicePath/$dockerfile (skipping)"
    }
    
    # Test dev Dockerfile if it exists
    $devDockerfile = "Dockerfile.dev"
    if (Test-Path "$servicePath/$devDockerfile") {
        $passed = Test-ServiceBuild -ServiceName "$service-dev" -Dockerfile $devDockerfile -Context $servicePath -SkipCache:$SkipCache
        if (-not $passed) {
            $results.Failed++
            $results.FailedServices += "$service (dev)"
        } else {
            $results.Passed++
        }
    }
}

# Summary
Write-Info -Message "`n=========================================="
Write-Info -Message "Build Test Summary"
Write-Info -Message "=========================================="
Write-Info -Message "Total builds tested: $($results.Total)"
Write-Success -Message "Passed: $($results.Passed)"
if ($results.Failed -gt 0) {
    Write-ErrorMsg -Message "Failed: $($results.Failed)"
    Write-ErrorMsg -Message "`nFailed services:"
    foreach ($failed in $results.FailedServices) {
        Write-ErrorMsg -Message "  - $failed"
    }
    exit 1
} else {
    Write-Success -Message "`n✓ All builds passed!"
    exit 0
}
