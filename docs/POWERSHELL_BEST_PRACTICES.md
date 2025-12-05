# PowerShell Best Practices for HomeIQ

**Last Updated:** December 4, 2025  
**Purpose:** Guide for using PowerShell commands correctly in Windows environments

---

## ⚠️ CRITICAL: Do NOT Use Unix-Style curl Commands

### ❌ WRONG - This Does NOT Work in PowerShell

```powershell
# This will FAIL - curl is an alias for Invoke-WebRequest, not Unix curl
curl -s http://localhost:8024/health | ConvertFrom-Json | Select-Object -Property status
```

**Why it fails:**
- `curl` in PowerShell is an alias for `Invoke-WebRequest`, not Unix curl
- The `-s` flag doesn't exist for `Invoke-WebRequest`
- Piping directly to `ConvertFrom-Json` doesn't work with `Invoke-WebRequest` output

---

## ✅ CORRECT PowerShell Commands

### Health Check Commands

**Option 1: Using Invoke-RestMethod (Recommended)**
```powershell
# Simple health check
$response = Invoke-RestMethod -Uri "http://localhost:8024/health"
$response.status

# Get full response
Invoke-RestMethod -Uri "http://localhost:8024/health" | ConvertTo-Json
```

**Option 2: Using Invoke-WebRequest**
```powershell
# Get response and parse JSON
$response = Invoke-WebRequest -Uri "http://localhost:8024/health"
$json = $response.Content | ConvertFrom-Json
$json.status
```

**Option 3: One-liner with error handling**
```powershell
try {
    (Invoke-RestMethod -Uri "http://localhost:8024/health").status
} catch {
    Write-Error "Health check failed: $_"
}
```

### Service Health Checks

```powershell
# Check multiple services
$services = @(
    @{Name="websocket-ingestion"; Port=8001},
    @{Name="data-api"; Port=8006},
    @{Name="ai-automation-service"; Port=8024}
)

foreach ($service in $services) {
    try {
        $health = Invoke-RestMethod -Uri "http://localhost:$($service.Port)/health"
        Write-Host "$($service.Name): $($health.status)" -ForegroundColor Green
    } catch {
        Write-Host "$($service.Name): FAILED" -ForegroundColor Red
    }
}
```

### Docker Commands (Work the Same)

```powershell
# These work fine in PowerShell
docker-compose ps
docker logs ai-automation-service --tail 50
docker-compose up -d ai-automation-service
```

---

## PowerShell vs Bash Command Equivalents

| Bash Command | PowerShell Equivalent |
|--------------|----------------------|
| `curl http://localhost:8001/health` | `Invoke-RestMethod -Uri "http://localhost:8001/health"` |
| `curl -s http://localhost:8001/health \| jq .status` | `(Invoke-RestMethod -Uri "http://localhost:8001/health").status` |
| `curl -X POST http://localhost:8001/api -d '{"key":"value"}'` | `Invoke-RestMethod -Uri "http://localhost:8001/api" -Method Post -Body '{"key":"value"}' -ContentType "application/json"` |
| `curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api` | `Invoke-RestMethod -Uri "http://localhost:8001/api" -Headers @{Authorization="Bearer $TOKEN"}` |

---

## Common Patterns

### Check Service Health with Status

```powershell
function Test-ServiceHealth {
    param(
        [string]$ServiceName,
        [int]$Port
    )
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$Port/health" -TimeoutSec 5
        return @{
            Service = $ServiceName
            Status = $response.status
            Healthy = $response.status -eq "healthy"
        }
    } catch {
        return @{
            Service = $ServiceName
            Status = "unreachable"
            Healthy = $false
            Error = $_.Exception.Message
        }
    }
}

# Usage
Test-ServiceHealth -ServiceName "ai-automation-service" -Port 8024
```

### Get JSON Response and Filter

```powershell
# Get full response
$health = Invoke-RestMethod -Uri "http://localhost:8024/health"

# Access properties
$health.status
$health.service
$health.uptime

# Convert to JSON string
$health | ConvertTo-Json -Depth 10
```

### POST Request with JSON Body

```powershell
$body = @{
    yaml = "automation: ..."
    validate_entities = $true
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "http://localhost:8024/api/v1/yaml/validate" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

---

## Error Handling Best Practices

```powershell
# Always use try-catch for API calls
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8024/health"
    Write-Host "Service is healthy: $($response.status)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "Service not found" -ForegroundColor Yellow
    } elseif ($_.Exception.Response.StatusCode -eq 503) {
        Write-Host "Service unavailable" -ForegroundColor Red
    } else {
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    }
}
```

---

## Quick Reference

### ✅ DO Use:
- `Invoke-RestMethod` for GET requests that return JSON
- `Invoke-WebRequest` for GET requests that return HTML/text
- `ConvertFrom-Json` to parse JSON strings
- `ConvertTo-Json` to create JSON strings
- PowerShell native cmdlets and operators

### ❌ DON'T Use:
- Unix-style `curl` commands with flags like `-s`, `-X`, `-H`
- Piping `curl` directly to `ConvertFrom-Json`
- Bash-style command chaining with `|` and `&&`
- Unix-specific tools without PowerShell equivalents

---

## Testing Commands

### Verify Service is Running
```powershell
# Check if service responds
$response = Invoke-RestMethod -Uri "http://localhost:8024/health" -ErrorAction SilentlyContinue
if ($response) {
    Write-Host "Service is running" -ForegroundColor Green
} else {
    Write-Host "Service is not responding" -ForegroundColor Red
}
```

### Check Multiple Endpoints
```powershell
$endpoints = @(
    "http://localhost:8001/health",
    "http://localhost:8006/health",
    "http://localhost:8024/health"
)

$endpoints | ForEach-Object {
    try {
        $result = Invoke-RestMethod -Uri $_ -TimeoutSec 2
        [PSCustomObject]@{
            URL = $_
            Status = $result.status
            Healthy = $true
        }
    } catch {
        [PSCustomObject]@{
            URL = $_
            Status = "Error"
            Healthy = $false
        }
    }
}
```

---

## References

- [Microsoft: Invoke-RestMethod](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-restmethod)
- [Microsoft: Invoke-WebRequest](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/invoke-webrequest)
- [PowerShell JSON Handling](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/convertfrom-json)

---

**Remember:** When working in PowerShell on Windows, always use PowerShell-native cmdlets, not Unix-style commands!

