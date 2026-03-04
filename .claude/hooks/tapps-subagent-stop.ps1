# TappsMCP SubagentStop hook (Epic 36.1)
# Advises on quality validation when subagent modified Python files.
# IMPORTANT: SubagentStop does NOT support exit code 2 (advisory only).
$rawInput = @($input) -join "`n"
$msg = "Subagent completed. Run tapps_quick_check or tapps_validate_changed"
Write-Host $msg -ForegroundColor Yellow
$msg2 = "on any Python files modified by this subagent."
Write-Host $msg2 -ForegroundColor Yellow
exit 0
