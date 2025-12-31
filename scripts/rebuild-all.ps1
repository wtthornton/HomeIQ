# Rebuild and Redeploy All Docker Containers
# Ensures ALL containers are stopped before rebuilding

param(
    [switch]$Force = $false
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

# Colors for output
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Stop all containers comprehensively
function Stop-AllContainers {
    Write-Info "Stopping all Docker containers..."
    
    Push-Location $ProjectRoot
    
    try {
        # Step 1: Stop all containers managed by docker-compose.yml (including production profile)
        Write-Info "Stopping containers from docker-compose.yml..."
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose --profile production down --remove-orphans --timeout 30 2>&1 | Out-Null
        } else {
            & docker compose --profile production down --remove-orphans --timeout 30 2>&1 | Out-Null
        }
        
        # Step 2: Stop any remaining running containers (including those not in compose file)
        Write-Info "Checking for remaining running containers..."
        $runningContainers = docker ps -q
        
        if ($runningContainers) {
            Write-Info "Found $($runningContainers.Count) running container(s), stopping them..."
            docker stop $runningContainers 2>&1 | Out-Null
            Start-Sleep -Seconds 2
        } else {
            Write-Info "No remaining running containers found"
        }
        
        # Step 3: Verify all containers are stopped
        $stillRunning = docker ps -q
        if ($stillRunning) {
            Write-Warning "Some containers are still running, forcing stop..."
            docker stop $stillRunning --time 0 2>&1 | Out-Null
            Start-Sleep -Seconds 1
        }
        
        # Final verification
        $finalCheck = docker ps -q
        if ($finalCheck) {
            Write-Error "Failed to stop all containers. Remaining containers: $finalCheck"
            return $false
        }
        
        Write-Success "All containers stopped successfully"
        return $true
    }
    catch {
        Write-Error "Error stopping containers: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

# Rebuild all containers
function Build-AllContainers {
    Write-Info "Building all Docker containers..."
    
    Push-Location $ProjectRoot
    
    try {
        $env:DOCKER_BUILDKIT = "1"
        $env:COMPOSE_DOCKER_CLI_BUILD = "1"
        
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose build --parallel
        } else {
            & docker compose build --parallel
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All containers built successfully"
            return $true
        } else {
            Write-Error "Build failed with exit code $LASTEXITCODE"
            return $false
        }
    }
    catch {
        Write-Error "Error building containers: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

# Deploy all containers
function Deploy-AllContainers {
    Write-Info "Deploying all Docker containers..."
    
    Push-Location $ProjectRoot
    
    try {
        # Remove any containers with network errors first
        Write-Info "Removing containers with network issues..."
        $containersWithIssues = @("electricity-pricing", "carbon-intensity", "air-quality")
        foreach ($container in $containersWithIssues) {
            docker compose rm -f $container 2>&1 | Out-Null
        }
        
        # Deploy with production profile to include profile-based services
        if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
            & docker-compose --profile production up -d
        } else {
            & docker compose --profile production up -d
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "All containers deployed successfully"
            return $true
        } else {
            Write-Error "Deployment failed with exit code $LASTEXITCODE"
            return $false
        }
    }
    catch {
        Write-Error "Error deploying containers: $_"
        return $false
    }
    finally {
        Pop-Location
    }
}

# Main execution
function Main {
    Write-Info "Starting complete rebuild and redeploy process..."
    Write-Info "Project root: $ProjectRoot"
    
    # Step 1: Stop all containers
    if (-not (Stop-AllContainers)) {
        Write-Error "Failed to stop all containers. Aborting."
        exit 1
    }
    
    # Step 2: Build all containers
    if (-not (Build-AllContainers)) {
        Write-Error "Build failed. Aborting."
        exit 1
    }
    
    # Step 3: Deploy all containers
    if (-not (Deploy-AllContainers)) {
        Write-Error "Deployment failed. Aborting."
        exit 1
    }
    
    Write-Success "Complete rebuild and redeploy completed successfully!"
    
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Check container status: docker compose ps"
    Write-Host "  2. View logs: docker compose logs -f"
    Write-Host "  3. Check health dashboard: http://localhost:3000"
}

# Run main function
Main

