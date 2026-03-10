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

        [string]$StepLabel = ""
    )

    begin {
        $promptLines = @()
    }

    process {
        $promptLines += $Prompt
    }

    end {
        $fullPrompt = $promptLines -join "`n"
        $resultText = ""
        $stepStart = Get-Date
        $lastProgressWrite = [datetime]::MinValue
        $lastTextSnippet = [datetime]::MinValue
        $turnsUsed = 0
        $currentToolName = ""
        $currentToolTarget = ""
        $currentToolStart = $null

        # Build claude arguments
        $claudeArgs = @("--print", "--output-format", "stream-json", "--max-turns", $MaxTurns)
        if ($McpConfig) {
            $claudeArgs += @("--mcp-config", $McpConfig)
        }
        if ($AllowedTools) {
            $claudeArgs += @("--allowedTools", $AllowedTools)
        }

        # Create a temp file for the prompt to avoid pipeline encoding issues
        $promptFile = [System.IO.Path]::GetTempFileName()
        [System.IO.File]::WriteAllText($promptFile, $fullPrompt, [System.Text.UTF8Encoding]::new($false))

        # Create stream log directory
        $streamLogDir = Join-Path $ProjectRoot "scripts/.stream-logs"
        if (-not (Test-Path $streamLogDir)) {
            New-Item -ItemType Directory -Path $streamLogDir -Force | Out-Null
        }
        $streamLogFile = Join-Path $streamLogDir "$($Branch -replace '[/\\:]', '-')-step$StepNumber.jsonl"

        try {
            # Start claude process with stdin redirected from prompt file
            $psi = New-Object System.Diagnostics.ProcessStartInfo
            $psi.FileName = "claude"
            $psi.Arguments = $claudeArgs -join " "
            $psi.UseShellExecute = $false
            $psi.RedirectStandardInput = $true
            $psi.RedirectStandardOutput = $true
            $psi.RedirectStandardError = $true
            $psi.CreateNoWindow = $true
            $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8

            $proc = [System.Diagnostics.Process]::Start($psi)

            # Write prompt to stdin and close it
            $proc.StandardInput.Write($fullPrompt)
            $proc.StandardInput.Close()

            # Process stdout line by line
            while ($null -ne ($line = $proc.StandardOutput.ReadLine())) {
                # Log raw stream for debugging
                try { $line | Out-File -FilePath $streamLogFile -Append -Encoding utf8 } catch {}

                # Skip empty lines
                if ([string]::IsNullOrWhiteSpace($line)) { continue }

                # Parse JSON
                $evt = $null
                try {
                    $evt = $line | ConvertFrom-Json -ErrorAction Stop
                } catch {
                    Write-Warning "Stream: skipping malformed JSON line"
                    continue
                }

                $evtType = $evt.type

                # --- Handle event types ---

                # system event (session init)
                if ($evtType -eq "system") {
                    if ($StepLabel) {
                        Add-LogEntry "[$StepLabel] Claude session started" "info"
                    }
                    continue
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
                                    $segments = $target -split "/"
                                    if ($segments.Count -gt 2) {
                                        $target = ".../" + ($segments[-2..-1] -join "/")
                                    }
                                }

                                # Complete previous tool call if any
                                if ($currentToolName -and $currentToolStart) {
                                    $dur = ((Get-Date) - $currentToolStart).TotalSeconds
                                    # Update the last tool call entry status
                                    if ($Script:ToolCalls.Count -gt 0) {
                                        $Script:ToolCalls[-1].duration_s = [math]::Round($dur, 1)
                                        $Script:ToolCalls[-1].status = "complete"
                                    }
                                }

                                # Track new tool call
                                $currentToolName = $toolName
                                $currentToolTarget = $target
                                $currentToolStart = Get-Date

                                $Script:ToolCalls += @{
                                    tool_name  = $toolName
                                    target     = $target
                                    started_at = (Get-Date).ToString("o")
                                    duration_s = 0
                                    status     = "running"
                                }

                                $turnsUsed++
                                $Script:Usage.turns_used = $turnsUsed
                                $Script:Usage.max_turns = $MaxTurns

                                $displayName = $toolName -replace '^mcp__tapps-mcp__', 'tapps:'
                                $logMsg = if ($target) { "[$StepLabel] $displayName -> $target" } else { "[$StepLabel] $displayName" }
                                Add-LogEntry $logMsg "info"

                                # Update dashboard with current tool info
                                Write-Dashboard -Step $StepNumber -Message "$displayName on $target"
                            }

                            # text block — extract progress snippets (throttled)
                            if ($block.type -eq "text" -and $block.text) {
                                $now = Get-Date
                                if (($now - $lastTextSnippet).TotalSeconds -ge 5) {
                                    $text = $block.text
                                    # Look for progress keywords
                                    $progressPatterns = @("scanning", "reading", "found", "checking", "fixing", "analyzing", "running", "validating")
                                    foreach ($pat in $progressPatterns) {
                                        if ($text -match "(?i)$pat") {
                                            $snippet = $text.Trim()
                                            if ($snippet.Length -gt 80) { $snippet = $snippet.Substring(0, 77) + "..." }
                                            Add-LogEntry "[$StepLabel] $snippet" "info"
                                            $lastTextSnippet = $now
                                            break
                                        }
                                    }
                                }
                            }
                        }
                    }
                    continue
                }

                # tool_progress event — update dashboard status (throttled to 1/sec)
                if ($evtType -eq "tool_progress") {
                    $now = Get-Date
                    if (($now - $lastProgressWrite).TotalSeconds -ge 1) {
                        $toolName = if ($evt.tool_name) { $evt.tool_name } elseif ($currentToolName) { $currentToolName } else { "tool" }
                        $elapsed = if ($evt.elapsed_time_seconds) { $evt.elapsed_time_seconds } else { 0 }
                        $displayName = $toolName -replace '^mcp__tapps-mcp__', 'tapps:'

                        # Update current tool duration
                        if ($Script:ToolCalls.Count -gt 0 -and $Script:ToolCalls[-1].status -eq "running") {
                            $Script:ToolCalls[-1].duration_s = [math]::Round($elapsed, 1)
                        }

                        Write-Dashboard -Step $StepNumber -Message "Running $displayName... ($([math]::Round($elapsed, 0))s)"
                        $lastProgressWrite = $now
                    }
                    continue
                }

                # result event — capture final output
                if ($evtType -eq "result") {
                    $resultText = $evt.result
                    if (-not $resultText) { $resultText = "" }

                    # Complete last tool call
                    if ($currentToolName -and $currentToolStart -and $Script:ToolCalls.Count -gt 0) {
                        $dur = ((Get-Date) - $currentToolStart).TotalSeconds
                        $Script:ToolCalls[-1].duration_s = [math]::Round($dur, 1)
                        $Script:ToolCalls[-1].status = "complete"
                    }

                    # Extract stats from result event
                    $totalCost = if ($evt.total_cost_usd) { $evt.total_cost_usd } elseif ($evt.cost_usd) { $evt.cost_usd } else { 0 }
                    $numTurns = if ($evt.num_turns) { $evt.num_turns } else { $turnsUsed }
                    $durationMs = if ($evt.duration_ms) { $evt.duration_ms } else { ((Get-Date) - $stepStart).TotalMilliseconds }
                    $durationSec = [math]::Round($durationMs / 1000, 1)

                    # Update usage stats
                    $Script:Usage.total_cost_usd += [double]$totalCost
                    $Script:Usage.turns_used = $numTurns
                    if ($evt.usage) {
                        $Script:Usage.input_tokens += [int]($evt.usage.input_tokens)
                        $Script:Usage.output_tokens += [int]($evt.usage.output_tokens)
                    }

                    # Check for error
                    $isError = if ($evt.is_error) { $evt.is_error } else { $false }
                    if ($isError) {
                        Add-LogEntry "[$StepLabel] FAILED: $numTurns turns, ${durationSec}s, `$$([math]::Round($totalCost, 4))" "error"
                    } else {
                        Add-LogEntry "[$StepLabel] Complete: $numTurns turns, ${durationSec}s, `$$([math]::Round($totalCost, 4))" "success"
                    }

                    Write-Dashboard -Step $StepNumber -Message "$StepLabel complete ($numTurns turns, ${durationSec}s)"
                    continue
                }

                # user event (tool results) — track turn progression
                if ($evtType -eq "user") {
                    # Tool results come back as user messages; just continue
                    continue
                }
            }

            $proc.WaitForExit()

            # If process exited with error and we have no result, capture stderr
            if ($proc.ExitCode -ne 0 -and -not $resultText) {
                $stderr = $proc.StandardError.ReadToEnd()
                Add-LogEntry "[$StepLabel] Claude exited with code $($proc.ExitCode): $stderr" "error"
            }

        } catch {
            Add-LogEntry "[$StepLabel] Stream error: $_" "error"
            Write-Dashboard -Step $StepNumber -Message "Stream error: $_"
        } finally {
            # Cleanup temp file
            if (Test-Path $promptFile) { Remove-Item $promptFile -Force -ErrorAction SilentlyContinue }
            if ($proc -and -not $proc.HasExited) {
                try { $proc.Kill() } catch {}
            }
        }

        # Return the final result text
        return $resultText
    }
}
