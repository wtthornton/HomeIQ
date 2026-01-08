# Monitor Blueprint Indexing Progress

param(
    [string]$JobId = "009dcc37-69df-4a53-b7a3-d1d1b749cd54"
)

Write-Host "`n=== Blueprint Indexing Monitor ===" -ForegroundColor Yellow
Write-Host "Job ID: $JobId`n" -ForegroundColor Cyan

while ($true) {
    try {
        # Check job status
        $job = Invoke-RestMethod -Uri "http://localhost:8038/api/blueprints/index/job/$JobId"
        
        # Check overall status
        $status = Invoke-RestMethod -Uri "http://localhost:8038/api/blueprints/status"
        
        Write-Host "[$(Get-Date -Format 'HH:mm:ss')] Job Status: $($job.status)" -ForegroundColor $(if ($job.status -eq "completed") { "Green" } elseif ($job.status -eq "failed") { "Red" } else { "Yellow" })
        Write-Host "  Processed: $($job.processed_items) / Total: $($job.total_items)" -ForegroundColor Gray
        Write-Host "  Indexed: $($job.indexed_items), Failed: $($job.failed_items)" -ForegroundColor Gray
        Write-Host "  Total Blueprints in DB: $($status.total_blueprints)" -ForegroundColor Cyan
        
        if ($job.status -eq "completed" -or $job.status -eq "failed") {
            Write-Host "`nIndexing $($job.status)!" -ForegroundColor $(if ($job.status -eq "completed") { "Green" } else { "Red" })
            if ($job.error_message) {
                Write-Host "Error: $($job.error_message)" -ForegroundColor Red
            }
            break
        }
        
        Start-Sleep -Seconds 10
    }
    catch {
        Write-Host "Error monitoring: $($_.Exception.Message)" -ForegroundColor Red
        Start-Sleep -Seconds 10
    }
}
