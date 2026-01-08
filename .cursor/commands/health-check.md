# Health Check

Check health status of all HomeIQ services.

## PowerShell Commands (Windows)

```powershell
# Check all critical services
$services = @(
    @{Name="websocket-ingestion"; Port=8001},
    @{Name="data-api"; Port=8006},
    @{Name="ai-automation-service"; Port=8024},
    @{Name="health-dashboard"; Port=3000}
)

foreach ($svc in $services) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$($svc.Port)/health" -TimeoutSec 5
        Write-Host "[OK] $($svc.Name): $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "[FAIL] $($svc.Name): Not responding" -ForegroundColor Red
    }
}
```

## Bash Commands (Linux/Mac)

```bash
# Check all services
for port in 8001 8006 8024; do
    curl -s http://localhost:$port/health | jq .status
done

# Open dashboard
open http://localhost:3000
```

## Docker Status

```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs --tail=50 {{service_name}}

# Restart service
docker-compose restart {{service_name}}
```

## Parameters

- `service_name`: Optional - specific service to check
