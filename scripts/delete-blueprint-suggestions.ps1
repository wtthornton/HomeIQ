# Delete all Blueprint Suggestions via API
# Usage: .\scripts\delete-blueprint-suggestions.ps1

$baseUrl = "http://localhost:8039/api/blueprint-suggestions"

Write-Host "Deleting all blueprint suggestions..." -ForegroundColor Yellow

try {
    $response = Invoke-RestMethod -Uri "$baseUrl/suggestions/all" -Method Delete -ContentType "application/json"
    
    Write-Host "Success! Deleted $($response.deleted) suggestions" -ForegroundColor Green
    Write-Host "Status: $($response.status)" -ForegroundColor Green
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "HTTP Status: $statusCode" -ForegroundColor Red
        
        try {
            $errorBody = $_.ErrorDetails.Message | ConvertFrom-Json
            Write-Host "Error Detail: $($errorBody.detail)" -ForegroundColor Red
        } catch {
            Write-Host "Error Detail: $($_.ErrorDetails.Message)" -ForegroundColor Red
        }
    }
}
