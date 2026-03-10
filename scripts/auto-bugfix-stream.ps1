# auto-bugfix-stream.ps1 — Stream parser module for Claude Code stream-json output.
# Dot-sourced by auto-bugfix.ps1. Uses Add-LogEntry and Write-Dashboard from parent scope.

function Invoke-ClaudeStream {
    <#
    .SYNOPSIS
        Runs claude --print --output-format stream-json and processes events in real-time,
        updating the dashboard as tool calls and progress events arrive.

    .DESCRIPTION
        Accepts a prompt via pipeline, runs Claude with streaming JSON output, parses each
        line as a JSON event, and routes events to the dashboard. Returns the final result
        text as a string for downstream processing (e.g., JSON extraction).

    .PARAMETER Prompt
        The prompt text, passed via pipeline.

    .PARAMETER MaxTurns
        Maximum number of turns for claude --max-turns.

    .PARAMETER McpConfig
        Path to the MCP config file.

    .PARAMETER AllowedTools
        Comma-separated list of allowed tools.

    .PARAMETER StepNumber
        Current pipeline step number (for Write-Dashboard).

    .PARAMETER StepLabel
        Human-readable label for the current step (e.g., "Scan", "Fix").
    #>
    [CmdletBinding()]
    param(
        [Parameter(ValueFromPipeline = $true)]
        [string]$Prompt,

        [int]$MaxTurns = 10,

        [string]$McpConfig = "",

        [string]$AllowedTools = "",

        [int]$StepNumber = 0,

        [string]$StepLabel = "",

        [string]$Model = ""
    )

    begin {
        $promptLines = @()
    }

    process {
        $promptLines += $Prompt
    }

    end {
        $fullPrompt = $promptLines -join "`n"
        $stepStart = Get-Date

        # Shared state for ForEach-Object pipeline (use Script: scope so we can write from pipeline)
        $Script:_streamResultText = ""
        $Script:_streamAccumulatedText = ""   # All assistant text blocks, used as fallback
        $Script:_streamTurnsUsed = 0
        $Script:_streamCurrentToolName = ""
        $Script:_streamCurrentToolStart = $null
        $Script:_streamLastProgressWrite = [datetime]::MinValue
        $Script:_streamLastTextSnippet = [datetime]::MinValue
        $Script:_streamEventCount = 0

        # Build claude arguments
        $claudeArgs = @("--print", "--verbose", "--output-format", "stream-json", "--max-turns", $MaxTurns)
        if ($Model) {
            $claudeArgs += @("--model", $Model)
        }
        if ($McpConfig) {
            $claudeArgs += @("--mcp-config", $McpConfig)
        }
        if ($AllowedTools) {
            $claudeArgs += @("--allowedTools", $AllowedTools)
        }

        # Create stream log directory
        $streamLogDir = Join-Path $ProjectRoot "scripts/.stream-logs"
        if (-not (Test-Path $streamLogDir)) {
            New-Item -ItemType Directory -Path $streamLogDir -Force | Out-Null
        }
        $streamLogFile = Join-Path $streamLogDir "$($Branch -replace '[/\\:]', '-')-step$StepNumber.jsonl"

        # Write initial "connecting" status
        Add-LogEntry "[$StepLabel] Connecting to Claude..." "info"
        Write-Dashboard -Step $StepNumber -Message "Connecting to Claude..."

        try {
            # Use native PowerShell pipeline for TRUE real-time streaming.
            # ForEach-Object processes each line AS IT ARRIVES from claude stdout.
            # We suppress ForEach-Object output (Out-Null on the pipeline) and
            # accumulate the result in $Script:_streamResultText.
            $fullPrompt | claude @claudeArgs 2>$null | ForEach-Object {
                $line = $_
                $Script:_streamEventCount++

                # Log raw stream for debugging
                try { $line | Out-File -FilePath $streamLogFile -Append -Encoding utf8 } catch {}

                # Skip empty lines
                if ([string]::IsNullOrWhiteSpace($line)) { return }

                # Parse JSON
                $evt = $null
                try {
                    $evt = $line | ConvertFrom-Json -ErrorAction Stop
                } catch {
                    Write-Warning "Stream: skipping malformed JSON line"
                    return
                }

                $evtType = $evt.type

                # --- Handle event types ---

                # system event (session init)
                if ($evtType -eq "system") {
                    Add-LogEntry "[$StepLabel] Claude session started (streaming)" "info"
                    Write-Dashboard -Step $StepNumber -Message "Claude connected - analyzing..."
                    return
                }

                # assistant event — may contain tool_use blocks or text blocks
                if ($evtType -eq "assistant") {
                    $contentBlocks = $evt.message.content
                    if (-not $contentBlocks) { $contentBlocks = $evt.content }

                    # Track usage from assistant events
                    if ($evt.message -and $evt.message.usage) {
                        $Script:Usage.input_tokens = [Math]::Max($Script:Usage.input_tokens, [int]($evt.message.usage.input_tokens))
                        $Script:Usage.output_tokens = [Math]::Max($Script:Usage.output_tokens, [int]($evt.message.usage.output_tokens))
                    }

                    if ($contentBlocks -and $contentBlocks.Count -gt 0) {
                        foreach ($block in $contentBlocks) {
                            # tool_use block
                            if ($block.type -eq "tool_use") {
                                $toolName = $block.name
                                $toolInput = $block.input

                                # Extract a human-readable target from tool input
                                $target = ""
                                if ($toolInput.file_path) {
                                    $target = $toolInput.file_path
                                } elseif ($toolInput.path) {
                                    $target = $toolInput.path
                                } elseif ($toolInput.file) {
                                    $target = $toolInput.file
                                } elseif ($toolInput.pattern) {
                                    $target = $toolInput.pattern
                                } elseif ($toolInput.command) {
                                    $cmdStr = "$($toolInput.command)"
                                    $target = if ($cmdStr.Length -gt 60) { $cmdStr.Substring(0, 57) + "..." } else { $cmdStr }
                                } elseif ($toolInput.question) {
                                    $qStr = "$($toolInput.question)"
                                    $target = if ($qStr.Length -gt 60) { $qStr.Substring(0, 57) + "..." } else { $qStr }
                                }

                                # Truncate long paths to last 2 segments
                                if ($target -and $target.Contains("/") -and $target.Length -gt 50) {
                                    $segments = $target -split "[/\\]"
                                    if ($segments.Count -gt 2) {
                                        $target = ".../" + ($segments[-2..-1] -join "/")
                                    }
                                }

                                # Also handle Windows backslash paths
                                if ($target -and $target.Contains("\") -and $target.Length -gt 50) {
                                    $segments = $target -split "[/\\]"
                                    if ($segments.Count -gt 2) {
                                        $target = "...\" + ($segments[-2..-1] -join "\")
                                    }
                                }

                                # Complete previous tool call if any
                                if ($Script:_streamCurrentToolName -and $Script:_streamCurrentToolStart) {
                                    $dur = ((Get-Date) - $Script:_streamCurrentToolStart).TotalSeconds
                                    if ($Script:ToolCalls.Count -gt 0) {
                                        $Script:ToolCalls[-1].duration_s = [math]::Round($dur, 1)
                                        $Script:ToolCalls[-1].status = "complete"
                                    }
                                }

                                # Track new tool call
                                $Script:_streamCurrentToolName = $toolName
                                $Script:_streamCurrentToolStart = Get-Date

                                $Script:ToolCalls += @{
                                    tool_name  = $toolName
                                    target     = $target
                                    started_at = (Get-Date).ToString("o")
                                    duration_s = 0
                                    status     = "running"
                                }

                                $Script:_streamTurnsUsed++
                                $Script:Usage.turns_used = $Script:_streamTurnsUsed
                                $Script:Usage.max_turns = $MaxTurns

                                $displayName = $toolName -replace '^mcp__tapps-mcp__', 'tapps:'
                                $logMsg = if ($target) { "[$StepLabel] $displayName -> $target" } else { "[$StepLabel] $displayName" }
                                Add-LogEntry $logMsg "info"

                                # Update dashboard with current tool info
                                $Script:CurrentTool = @{ name = $displayName; target = $target; started_at = (Get-Date).ToString("o") }
                                Write-Dashboard -Step $StepNumber -Message "$displayName on $target"
                            }

                            # text block — accumulate for fallback result + extract progress snippets
                            if ($block.type -eq "text" -and $block.text) {
                                $Script:_streamAccumulatedText += $block.text + "`n"
                                $now = Get-Date
                                if (($now - $Script:_streamLastTextSnippet).TotalSeconds -ge 3) {
                                    $text = $block.text
                                    # Look for progress keywords
                                    $progressPatterns = @("scanning", "reading", "found", "checking", "fixing", "analyzing",
                                                         "running", "validating", "looking", "searching", "examining",
                                                         "reviewing", "processing", "detecting", "evaluating", "scoring")
                                    foreach ($pat in $progressPatterns) {
                                        if ($text -match "(?i)$pat") {
                                            $snippet = $text.Trim()
                                            if ($snippet.Length -gt 100) { $snippet = $snippet.Substring(0, 97) + "..." }
                                            Add-LogEntry "[$StepLabel] $snippet" "info"
                                            Write-Dashboard -Step $StepNumber -Message $snippet
                                            $Script:_streamLastTextSnippet = $now
                                            break
                                        }
                                    }
                                    # If no keyword match but we haven't updated in 8+ seconds, show thinking indicator
                                    if (($now - $Script:_streamLastProgressWrite).TotalSeconds -ge 8) {
                                        $elapsed = [math]::Round(($now - $stepStart).TotalSeconds, 0)
                                        Write-Dashboard -Step $StepNumber -Message "Claude thinking... (${elapsed}s elapsed)"
                                        $Script:_streamLastProgressWrite = $now
                                    }
                                }
                            }
                        }
                    }
                    return
                }

                # tool_progress event — update dashboard status (throttled to 1/sec)
                if ($evtType -eq "tool_progress") {
                    $now = Get-Date
                    if (($now - $Script:_streamLastProgressWrite).TotalSeconds -ge 1) {
                        $toolName = if ($evt.tool_name) { $evt.tool_name } elseif ($Script:_streamCurrentToolName) { $Script:_streamCurrentToolName } else { "tool" }
                        $elapsed = if ($evt.elapsed_time_seconds) { $evt.elapsed_time_seconds } else { 0 }
                        $displayName = $toolName -replace '^mcp__tapps-mcp__', 'tapps:'

                        # Update current tool duration
                        if ($Script:ToolCalls.Count -gt 0 -and $Script:ToolCalls[-1].status -eq "running") {
                            $Script:ToolCalls[-1].duration_s = [math]::Round($elapsed, 1)
                        }

                        Write-Dashboard -Step $StepNumber -Message "Running $displayName... ($([math]::Round($elapsed, 0))s)"
                        $Script:_streamLastProgressWrite = $now
                    }
                    return
                }

                # result event — capture final output (use accumulated text as fallback)
                if ($evtType -eq "result") {
                    $Script:_streamResultText = if ($evt.result) { $evt.result } else { $Script:_streamAccumulatedText }

                    # Complete last tool call
                    if ($Script:_streamCurrentToolName -and $Script:_streamCurrentToolStart -and $Script:ToolCalls.Count -gt 0) {
                        $dur = ((Get-Date) - $Script:_streamCurrentToolStart).TotalSeconds
                        $Script:ToolCalls[-1].duration_s = [math]::Round($dur, 1)
                        $Script:ToolCalls[-1].status = "complete"
                    }

                    # Extract stats from result event
                    $totalCost = if ($evt.total_cost_usd) { $evt.total_cost_usd } elseif ($evt.cost_usd) { $evt.cost_usd } else { 0 }
                    $numTurns = if ($evt.num_turns) { $evt.num_turns } else { $Script:_streamTurnsUsed }
                    $durationMs = if ($evt.duration_ms) { $evt.duration_ms } else { ((Get-Date) - $stepStart).TotalMilliseconds }
                    $durationSec = [math]::Round($durationMs / 1000, 1)

                    # Update usage stats
                    $Script:Usage.total_cost_usd += [double]$totalCost
                    $Script:Usage.turns_used = $numTurns
                    if ($evt.usage) {
                        $Script:Usage.input_tokens += [int]($evt.usage.input_tokens)
                        $Script:Usage.output_tokens += [int]($evt.usage.output_tokens)
                    }

                    # Clear current tool
                    $Script:CurrentTool = @{}

                    # Check for error
                    $isError = if ($evt.is_error) { $evt.is_error } else { $false }
                    if ($isError) {
                        Add-LogEntry "[$StepLabel] FAILED: $numTurns turns, ${durationSec}s, `$$([math]::Round($totalCost, 4))" "error"
                    } else {
                        Add-LogEntry "[$StepLabel] Complete: $numTurns turns, ${durationSec}s, `$$([math]::Round($totalCost, 4))" "success"
                    }

                    Write-Dashboard -Step $StepNumber -Message "$StepLabel complete ($numTurns turns, ${durationSec}s)"
                    return
                }

                # user event (tool results) — mark tool complete, show brief result
                if ($evtType -eq "user") {
                    if ($Script:_streamCurrentToolName -and $Script:_streamCurrentToolStart -and $Script:ToolCalls.Count -gt 0) {
                        $dur = ((Get-Date) - $Script:_streamCurrentToolStart).TotalSeconds
                        $Script:ToolCalls[-1].duration_s = [math]::Round($dur, 1)
                        $Script:ToolCalls[-1].status = "complete"
                        $displayName = $Script:_streamCurrentToolName -replace '^mcp__tapps-mcp__', 'tapps:'
                        Add-LogEntry "[$StepLabel] $displayName completed ($([math]::Round($dur, 1))s)" "info"
                        Write-Dashboard -Step $StepNumber -Message "$displayName completed ($([math]::Round($dur, 1))s)"
                        $Script:_streamCurrentToolName = ""
                        $Script:_streamCurrentToolStart = $null
                    }
                    return
                }
            }

            # If we got zero events, the pipeline may have returned plain text (non-streaming fallback)
            if ($Script:_streamEventCount -eq 0) {
                Add-LogEntry "[$StepLabel] Warning: No stream events received - claude may not support stream-json" "warn"
            }

        } catch {
            Add-LogEntry "[$StepLabel] Stream error: $_" "error"
            Write-Dashboard -Step $StepNumber -Message "Stream error: $_"
        } finally {
            # No cleanup needed
        }

        # Return the final result text
        return $Script:_streamResultText
    }
}
