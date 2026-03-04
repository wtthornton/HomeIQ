# ensure-network.ps1 — Create the homeiq-network Docker bridge if it doesn't exist.
# Idempotent: safe to run multiple times.

$NetworkName = "homeiq-network"

$null = docker network inspect $NetworkName 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Network '$NetworkName' already exists."
} else {
    docker network create $NetworkName --driver bridge
    Write-Host "[CREATED] Network '$NetworkName' created."
}
