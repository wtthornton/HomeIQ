# TappsMCP SubagentStart hook
# Injects TappsMCP awareness into spawned subagents.
$null = $input | Out-Null
Write-Output "[TappsMCP] This project uses TappsMCP for code quality."
Write-Output "Available MCP tools: tapps_quick_check, tapps_score_file, tapps_validate_changed."
exit 0
