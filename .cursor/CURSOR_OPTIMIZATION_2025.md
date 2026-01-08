# Cursor IDE Optimization - January 2025

**Last Updated:** January 8, 2025 (actually 2026)  
**Cursor Version:** 1.7+  
**Project:** HomeIQ

## Overview

This document summarizes the Cursor IDE optimizations applied to the HomeIQ project based on 2025/2026 best practices.

## Configuration Summary

### 1. Rules (`.cursor/rules/`)

**19 optimized rule files** organized by type:

#### Always-Apply Rules (10)
| Rule | Purpose |
|------|---------|
| `README.mdc` | Rules overview |
| `simple-mode.mdc` | TappsCodingAgents primary interface |
| `simple-mode-tool-invocation.mdc` | Tool invocation helper |
| `tapps-agents-command-guide.mdc` | AI agent command guide |
| `tapps-agents-workflow-selection.mdc` | Workflow selection |
| `command-reference.mdc` | Complete command reference |
| `context7.mdc` | Context7 auto-invoke |
| `epic-31-architecture.mdc` | Architecture patterns |
| `powershell-commands.mdc` | Windows commands |
| `project-structure.mdc` | File organization |

#### Glob-Based Rules (5)
| Rule | Applies To |
|------|------------|
| `code-quality.mdc` | Code files (*.py, *.js, *.ts, etc.) |
| `development-environment.mdc` | Config, Docker files |
| `documentation-standards.mdc` | Markdown files |
| `security-best-practices.mdc` | Code and config |
| `epic-31-architecture.mdc` | Service directories |

#### Manual/Agent-Requested Rules (4)
| Rule | Purpose |
|------|---------|
| `agent-capabilities.mdc` | 13 workflow agents |
| `quick-reference.mdc` | Quick commands |
| `workflow-presets.mdc` | Workflow presets |
| `project-profiling.mdc` | Project profiling |

### 2. Custom Commands (`.cursor/commands/`)

**6 custom slash commands** for common workflows:

| Command | Usage | Description |
|---------|-------|-------------|
| `/review-service` | `/review-service` | Review HomeIQ microservice |
| `/build-feature` | `/build-feature` | Build feature with full workflow |
| `/fix-bug` | `/fix-bug` | Debug and fix bugs |
| `/quality-check` | `/quality-check` | Quick quality check |
| `/generate-tests` | `/generate-tests` | Generate tests |
| `/health-check` | `/health-check` | Check service health |

### 3. MCP Servers (`.cursor/mcp.json`)

**4 MCP servers configured:**

| Server | Purpose |
|--------|---------|
| **Context7** | Library documentation lookup |
| **Playwright** | Browser automation for E2E testing |
| **FileSystem** | File operations |
| **GitHub** | GitHub integration |

### 4. Ignore Patterns (`.cursorignore`)

**Comprehensive ignore patterns** for optimal indexing:
- Archive directories
- Build artifacts and logs
- Test artifacts and coverage
- Simulation data
- Node modules
- Python cache
- IDE files

## Best Practices Applied

### Rule Organization (2025/2026 Standards)

1. **Frontmatter on all rules** - Every `.mdc` file has proper YAML frontmatter
2. **Appropriate rule types**:
   - `alwaysApply: true` for critical guidance
   - `globs` for file-type-specific rules
   - `description` only for manual/agent-requested rules
3. **Rules under 500 lines** - Large rules split into composable parts
4. **Concrete examples** - Rules include code examples and templates

### Command Organization

1. **Descriptive names** - Commands named for their purpose
2. **Clear instructions** - Each command has step-by-step guidance
3. **Parameters documented** - Input parameters clearly defined
4. **Platform-specific guidance** - PowerShell vs Bash alternatives

### Performance Optimizations

1. **Comprehensive `.cursorignore`** - Excludes large/generated files
2. **Archive directories excluded** - Historical content not indexed
3. **Node modules excluded** - Large dependency folders ignored
4. **Build artifacts excluded** - Generated files not indexed

## Usage Guide

### Using Simple Mode (Primary Interface)

```
@simple-mode *build "Create new feature"
@simple-mode *review {file}
@simple-mode *fix {file} "Fix description"
@simple-mode *test {file}
```

### Using Custom Commands

Type `/` in Cursor chat to see available commands:
- `/review-service` - Review a microservice
- `/build-feature` - Build with full workflow
- `/fix-bug` - Debug and fix
- `/quality-check` - Quick quality check
- `/generate-tests` - Generate tests
- `/health-check` - Check service health

### Using MCP Tools

MCP tools are automatically available:
- **Context7**: `mcp_Context7_resolve-library-id`, `mcp_Context7_query-docs`
- **Playwright**: `mcp_Playwright_browser_*` tools
- **FileSystem**: `mcp_FileSystem_*` tools
- **GitHub**: `mcp_GitHub_*` tools

## Quality Standards

| Metric | Standard | Critical Services |
|--------|----------|-------------------|
| Overall Score | ≥ 70 | ≥ 80 |
| Security | ≥ 7.0/10 | ≥ 8.0/10 |
| Maintainability | ≥ 7.0/10 | ≥ 8.0/10 |
| Test Coverage | ≥ 80% | ≥ 90% |

## Changes Made

### BMAD Removal
- ✅ Deleted `.bmad-core/` directory
- ✅ Deleted `.cursor/rules/bmad/` directory
- ✅ Deleted `bmad-workflow.mdc`
- ✅ Updated all rules to remove BMAD references

### New Custom Commands
- ✅ Created 6 project-specific commands
- ✅ Added PowerShell-friendly alternatives

### MCP Enhancement
- ✅ Added Playwright MCP server
- ✅ Added FileSystem MCP server
- ✅ Added GitHub MCP server

### Documentation Updates
- ✅ Updated QUICK_REFERENCE.md for Epic 31
- ✅ Removed deprecated enrichment-pipeline references
- ✅ Added PowerShell command examples

## References

- [Cursor Rules Documentation](https://docs.cursor.com/en/context/rules)
- [Cursor Commands Documentation](https://docs.cursor.com/en/agent/chat/commands)
- [Cursor Changelog](https://cursor.com/changelog/)
- [TappsCodingAgents Guide](.cursor/rules/tapps-agents-command-guide.mdc)
