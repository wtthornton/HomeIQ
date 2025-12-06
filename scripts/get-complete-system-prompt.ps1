# Get Complete System Prompt from HA AI Agent Service
# Usage: .\scripts\get-complete-system-prompt.ps1 -ConversationId "576b114c"

param(
    [Parameter(Mandatory=$true)]
    [string]$ConversationId,
    
    [Parameter(Mandatory=$false)]
    [switch]$RefreshContext,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "complete-system-prompt.txt"
)

$ServiceUrl = "http://localhost:8030"
$ApiEndpoint = "$ServiceUrl/api/v1/conversations/$ConversationId/debug/prompt"

# Build query parameters
$QueryParams = @()
if ($RefreshContext) {
    $QueryParams += "refresh_context=true"
}

if ($QueryParams.Count -gt 0) {
    $ApiEndpoint += "?" + ($QueryParams -join "&")
}

Write-Host "Fetching complete system prompt for conversation: $ConversationId" -ForegroundColor Cyan
Write-Host "Endpoint: $ApiEndpoint" -ForegroundColor Gray

try {
    # Fetch the prompt breakdown
    $response = Invoke-RestMethod -Uri $ApiEndpoint -Method Get -ContentType "application/json"
    
    if ($response) {
        Write-Host ""
        Write-Host "Successfully fetched prompt breakdown!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Breakdown:" -ForegroundColor Yellow
        Write-Host "  - Conversation ID: $($response.conversation_id)" -ForegroundColor White
        Write-Host "  - Debug ID: $($response.debug_id)" -ForegroundColor White
        Write-Host "  - Base System Prompt: $($response.base_system_prompt.Length) chars" -ForegroundColor White
        Write-Host "  - Injected Context: $($response.injected_context.Length) chars" -ForegroundColor White
        Write-Host "  - Preview Context: $($response.preview_context.Length) chars" -ForegroundColor White
        Write-Host "  - Complete System Prompt: $($response.complete_system_prompt.Length) chars" -ForegroundColor Green
        Write-Host "  - User Message: $($response.user_message.Length) chars" -ForegroundColor White
        Write-Host "  - Conversation History: $($response.conversation_history.Count) messages" -ForegroundColor White
        Write-Host "  - Token Counts:" -ForegroundColor White
        Write-Host "    * System: $($response.token_counts.system_tokens)" -ForegroundColor White
        Write-Host "    * History: $($response.token_counts.history_tokens)" -ForegroundColor White
        Write-Host "    * New Message: $($response.token_counts.new_message_tokens)" -ForegroundColor White
        $totalTokens = $response.token_counts.total_tokens
        $maxTokens = $response.token_counts.max_input_tokens
        $withinBudget = $response.token_counts.within_budget
        $color = if ($withinBudget) { "Green" } else { "Red" }
        Write-Host "    * Total: $totalTokens / $maxTokens" -ForegroundColor $color
        
        # Save complete system prompt to file
        $response.complete_system_prompt | Out-File -FilePath $OutputFile -Encoding utf8
        Write-Host ""
        Write-Host "Complete system prompt saved to: $OutputFile" -ForegroundColor Green
        
        # Also save as JSON for full breakdown
        $JsonFile = $OutputFile -replace '\.txt$', '.json'
        $response | ConvertTo-Json -Depth 10 | Out-File -FilePath $JsonFile -Encoding utf8
        Write-Host "Full breakdown (JSON) saved to: $JsonFile" -ForegroundColor Green
        
        # Display first 500 chars of complete prompt
        Write-Host ""
        Write-Host "Preview of Complete System Prompt (first 500 chars):" -ForegroundColor Yellow
        $separator = [string]::new('-', 80)
        Write-Host $separator -ForegroundColor Gray
        $previewLength = [Math]::Min(500, $response.complete_system_prompt.Length)
        Write-Host $response.complete_system_prompt.Substring(0, $previewLength) -ForegroundColor White
        if ($response.complete_system_prompt.Length -gt 500) {
            $truncatedMsg = "... (truncated, see $OutputFile for full content)"
            Write-Host $truncatedMsg -ForegroundColor Gray
        }
        Write-Host $separator -ForegroundColor Gray
        
    } else {
        Write-Host "No data returned from API" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "Error fetching prompt breakdown:" -ForegroundColor Red
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode
        Write-Host "  Status Code: $statusCode" -ForegroundColor Red
        
        try {
            $errorStream = $_.Exception.Response.GetResponseStream()
            $reader = New-Object System.IO.StreamReader($errorStream)
            $errorBody = $reader.ReadToEnd()
            Write-Host "  Error Details: $errorBody" -ForegroundColor Red
        } catch {
            $errorMsg = $_.Exception.Message
            Write-Host "  Error Message: $errorMsg" -ForegroundColor Red
        }
    } else {
        $errorMsg = $_.Exception.Message
        Write-Host "  Error Message: $errorMsg" -ForegroundColor Red
    }
    exit 1
}
