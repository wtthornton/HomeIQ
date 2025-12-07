# Get Debug Prompt by Debug ID (Troubleshooting ID)
# Usage: .\scripts\get-debug-prompt-by-debug-id.ps1 -DebugId "d6ab6135-5de5-416b-a181-f95ad2806b20"

param(
    [Parameter(Mandatory=$true)]
    [string]$DebugId,
    
    [Parameter(Mandatory=$false)]
    [switch]$RefreshContext,
    
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "debug_prompt_output.json"
)

$ServiceUrl = "http://localhost:8030"

Write-Host "Finding conversation by Debug ID: $DebugId" -ForegroundColor Cyan

# First, get all conversations and find the one with matching debug_id
try {
    $conversations = Invoke-RestMethod -Uri "$ServiceUrl/api/v1/conversations?limit=100" -Method Get
    
    $foundConversation = $null
    foreach ($conv in $conversations.conversations) {
        # Get full conversation details to check debug_id
        try {
            $fullConv = Invoke-RestMethod -Uri "$ServiceUrl/api/v1/conversations/$($conv.conversation_id)" -Method Get
            if ($fullConv.debug_id -eq $DebugId) {
                $foundConversation = $fullConv
                Write-Host "Found conversation: $($fullConv.conversation_id)" -ForegroundColor Green
                break
            }
        } catch {
            # Skip if we can't get details
            continue
        }
    }
    
    if (-not $foundConversation) {
        Write-Host "Conversation with Debug ID '$DebugId' not found" -ForegroundColor Red
        Write-Host "Available conversations:" -ForegroundColor Yellow
        foreach ($conv in $conversations.conversations) {
            Write-Host "  - $($conv.conversation_id)" -ForegroundColor Gray
        }
        exit 1
    }
    
    $conversationId = $foundConversation.conversation_id
    
    # Now get the debug prompt breakdown
    $ApiEndpoint = "$ServiceUrl/api/v1/conversations/$conversationId/debug/prompt"
    
    # Build query parameters
    $QueryParams = @()
    if ($RefreshContext) {
        $QueryParams += "refresh_context=true"
    }
    
    if ($QueryParams.Count -gt 0) {
        $ApiEndpoint += "?" + ($QueryParams -join "&")
    }
    
    Write-Host "Fetching debug prompt breakdown..." -ForegroundColor Cyan
    Write-Host "Endpoint: $ApiEndpoint" -ForegroundColor Gray
    
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
        Write-Host "  - Full Assembled Messages: $($response.full_assembled_messages.Count) messages" -ForegroundColor White
        Write-Host "  - Token Counts:" -ForegroundColor White
        Write-Host "    * System: $($response.token_counts.system_tokens)" -ForegroundColor White
        Write-Host "    * History: $($response.token_counts.history_tokens)" -ForegroundColor White
        Write-Host "    * New Message: $($response.token_counts.new_message_tokens)" -ForegroundColor White
        $totalTokens = $response.token_counts.total_tokens
        $maxTokens = $response.token_counts.max_input_tokens
        $withinBudget = $response.token_counts.within_budget
        $color = if ($withinBudget) { "Green" } else { "Red" }
        Write-Host "    * Total: $totalTokens / $maxTokens" -ForegroundColor $color
        
        # Save to JSON file
        $response | ConvertTo-Json -Depth 20 | Out-File -FilePath $OutputFile -Encoding utf8
        Write-Host ""
        Write-Host "Full breakdown saved to: $OutputFile" -ForegroundColor Green
        
        return $response
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

