# GitHub Issue: Playwright MCP Package Name Detection

## Issue Template

**Title:** Detection doesn't recognize @playwright/mcp package variant

**Labels:** `enhancement`, `detection`, `mcp`

---

## Description

The `detect_mcp_servers()` function only checks for `@playwright/mcp-server` package, but many configurations use `@playwright/mcp` (different package name). This causes false negative warnings for users with valid Playwright MCP configurations.

## Current Behavior

```python
# Current code (lines ~1238-1246)
optional_servers = {
    "Playwright": {
        "name": "Playwright MCP Server",
        "package": "@playwright/mcp-server",  # Only checks this variant
        ...
    }
}
```

## User's Valid Configuration (Undetected)

```json
{
  "mcpServers": {
    "Playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@0.0.35"]
    }
  }
}
```

Result: Playwright shows as "Not configured" despite being valid.

## Steps to Reproduce

1. Configure Playwright MCP using `@playwright/mcp` package
2. Run `tapps-agents doctor`
3. Observe Playwright shows as "Not configured"

## Expected Behavior

Both package variants should be detected:
- `@playwright/mcp-server`
- `@playwright/mcp`
- Versioned variants like `@playwright/mcp@0.0.35`

## Suggested Fix

Support multiple package name variants:

```python
optional_servers = {
    "Playwright": {
        "name": "Playwright MCP Server",
        "packages": ["@playwright/mcp-server", "@playwright/mcp"],  # Check both
        ...
    }
}

# Update detection logic to check all variants and versioned packages
for package in packages_to_check:
    if package in args:
        detected = True
        break
    # Check versioned packages (e.g., @playwright/mcp@0.0.35)
    for arg in args:
        if arg.startswith(package + "@"):
            detected = True
            break
```

## Impact

- **Severity:** Medium
- **Affected Users:** Users with `@playwright/mcp` configuration
- **Workaround:** Use `@playwright/mcp-server` package instead

## Additional Context

- Both packages are valid Playwright MCP implementations
- npm allows versioned package references in npx commands
- Detection should be flexible to handle ecosystem variations

## Checklist

- [ ] Add `packages` list support to server definitions
- [ ] Update detection logic for multiple variants
- [ ] Support versioned package detection (`@package@version`)
- [ ] Add unit tests for package variants
- [ ] Document supported package names
