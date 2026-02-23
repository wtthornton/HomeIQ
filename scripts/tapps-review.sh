#!/bin/bash
# tapps-review.sh - Helper script to invoke tapps-mcp tools via JSON-RPC
# Usage: ./scripts/tapps-review.sh <tool_name> [json_params]

TAPPS_PROJECT_ROOT="${TAPPS_MCP_PROJECT_ROOT:-c:/cursor/HomeIQ}"

call_tapps() {
    local tool_name="$1"
    local params="$2"

    if [ -z "$params" ]; then
        params="{}"
    fi

    printf '{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"review","version":"1.0"}},"id":1}\n{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}\n{"jsonrpc":"2.0","method":"tools/call","params":{"name":"%s","arguments":%s},"id":2}\n' "$tool_name" "$params" | TAPPS_MCP_PROJECT_ROOT="$TAPPS_PROJECT_ROOT" tapps-mcp serve 2>/dev/null | tail -1
}

# Execute
call_tapps "$1" "$2"
