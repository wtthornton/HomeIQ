# How to Use TappsCodingAgents in HomeIQ

**Quick Reference Guide** - Get started with TappsCodingAgents in your HomeIQ project.

> **📖 New to TappsCodingAgents?** Start with the [Integration Strategy](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md) to understand when to use Simple Mode, direct agents, or custom workflows.

## Table of Contents

- [Quick Start](#quick-start)
- [Simple Mode (Recommended)](#simple-mode-recommended)
- [Custom Workflows](#custom-workflows)
- [Enhancer Agent (Prompt Enhancement)](#enhancer-agent-prompt-enhancement)
- [Reviewer Agent (Code Review)](#reviewer-agent-code-review)
- [Other Useful Agents](#other-useful-agents)
- [Common Use Cases](#common-use-cases)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1. Verify Installation

```powershell
# Check if TappsCodingAgents is installed
python -c "import tapps_agents; print('✅ Installed')"

# Check available commands
python -m tapps_agents.cli --help
```

### 2. Check Your Configuration

HomeIQ is already configured with:
- ✅ 8 domain experts (IoT, Time-Series, AI/ML, etc.)
- ✅ Knowledge bases in `.tapps-agents/knowledge/`
- ✅ Enhancement configuration in `.tapps-agents/enhancement-config.yaml`

---

## Simple Mode (Recommended)

**Best for:** Most development tasks (features, reviews, fixes, tests)

Simple Mode is the **primary interface** for TappsCodingAgents in Cursor. It automatically orchestrates multiple agents through structured workflows.

### Quick Commands

```powershell
# Build new feature (orchestrates: enhancer → planner → architect → implementer → reviewer → tester)
@simple-mode *build "Create new InfluxDB query endpoint"

# Review code quality
@simple-mode *review services/websocket-ingestion/src/main.py

# Fix bug (orchestrates: debugger → implementer → tester)
@simple-mode *fix services/data-api/src/main.py "Fix connection timeout"

# Generate tests
@simple-mode *test services/data-api/src/main.py

# Full SDLC workflow
@simple-mode *full "Build complete REST API"
```

### Why Use Simple Mode?

- ✅ **Automatic Orchestration** - Multiple agents coordinated automatically
- ✅ **Quality Gates** - Automatic quality checks with loopbacks
- ✅ **Expert Consultation** - HomeIQ domain experts consulted automatically
- ✅ **Natural Language** - Plain English commands, no complex syntax

**Learn More:** See [Simple Mode Guide](../.cursor/rules/simple-mode.mdc) and [Integration Strategy](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md)

---

## Custom Workflows

**Best for:** HomeIQ-specific patterns, multi-service operations, repeatable workflows

HomeIQ includes custom workflows for common patterns:

### Available Workflows

```powershell
# Create new microservice (Docker, InfluxDB, Epic 31 patterns)
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "Create weather-api service"

# Integrate service with existing infrastructure
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-integration.yaml --prompt "Integrate external API"

# Multi-service quality audit
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-quality-audit.yaml
```

### When to Use Custom Workflows

- ✅ Creating new microservices (use `homeiq-microservice-creation.yaml`)
- ✅ Integrating services with HomeIQ infrastructure (use `homeiq-service-integration.yaml`)
- ✅ Quality audits across multiple services (use `homeiq-quality-audit.yaml`)
- ✅ Patterns repeated 3+ times (create new workflow)

**Learn More:** See [Custom Workflows Guide](./HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md) and [Quick Reference](./TAPPS_AGENTS_QUICK_REFERENCE.md)

---

## Enhancer Agent (Prompt Enhancement)

**Best for:** Transforming simple prompts into comprehensive, context-aware prompts

### Quick Enhancement (Fast)

```powershell
# Simple one-liner - quick enhancement
python -m tapps_agents.cli enhancer enhance-quick "Add device health monitoring"

# With markdown output
python -m tapps_agents.cli enhancer enhance-quick "Add device health monitoring" --format markdown
```

### Full Enhancement (Comprehensive)

```powershell
# Full 7-stage enhancement with all context
python -m tapps_agents.cli enhancer enhance "Create new InfluxDB query endpoint for device metrics"

# Save to file
python -m tapps_agents.cli enhancer enhance "Create new InfluxDB query endpoint" --output enhanced-prompt.md

# JSON format for programmatic use
python -m tapps_agents.cli enhancer enhance "Add weather data integration" --format json
```

### Stage-by-Stage Enhancement

```powershell
# Enhance only specific stages
python -m tapps_agents.cli enhancer enhance-stage "Add device health monitoring" --stages analysis,requirements,architecture
```

### Resume Session

```powershell
# If enhancement was interrupted, resume it
python -m tapps_agents.cli enhancer enhance-resume session-12345.json
```

### Example Output

**Input:**
```
"Add device health monitoring"
```

**Enhanced Output:**
```markdown
# Enhanced Prompt: Add Device Health Monitoring

## Analysis
- Domain: IoT & Home Automation, Device Intelligence
- Complexity: Medium
- Estimated Effort: 2-3 days

## Requirements
1. Real-time device health metrics (battery, response time, connectivity)
2. Health scoring algorithm (0-100 scale)
3. Alert system for degraded devices
4. Historical health trends

## Architecture
- New service: `device-health-service` (Port 8011)
- Database: InfluxDB (health_metrics bucket)
- API: REST endpoint `/api/health/devices`
- Frontend: Health dashboard component

## Codebase Context
- Related files: `services/device-intelligence-service/`, `services/data-api/`
- Patterns: Follow existing InfluxDB write patterns
- Dependencies: Use existing device metadata from SQLite

## Quality Standards
- Type hints required
- Unit tests for health scoring
- Integration tests for API endpoints
- Documentation: API docs + user guide

## Implementation Strategy
1. Create health metrics schema in InfluxDB
2. Implement health scoring service
3. Add REST API endpoints
4. Create frontend dashboard component
5. Add alerting logic

## Expert Recommendations
- IoT Expert: Use Home Assistant device registry for device metadata
- Time-Series Expert: Use InfluxDB downsampling for historical trends
- Security Expert: Ensure health data doesn't expose sensitive device info
```

---

## Reviewer Agent (Code Review)

**Best for:** Code quality analysis, security scanning, type checking

### Review a File

```powershell
# Review a Python file
python -m tapps_agents.cli reviewer review services/websocket-ingestion/src/main.py

# Score only (no LLM feedback, faster)
python -m tapps_agents.cli reviewer score services/websocket-ingestion/src/main.py

# Review with JSON output
python -m tapps_agents.cli reviewer review services/data-api/src/main.py --format json
```

### Lint a File

```powershell
# Run Ruff linting on a file
python -m tapps_agents.cli reviewer lint services/websocket-ingestion/src/main.py
```

### Type Check a File

```powershell
# Run mypy type checking
python -m tapps_agents.cli reviewer type-check services/websocket-ingestion/src/main.py
```

### Review Multiple Files

```powershell
# Review all Python files in a directory
python -m tapps_agents.cli reviewer review services/websocket-ingestion/ --recursive
```

### Example Output

```json
{
  "file": "services/websocket-ingestion/src/main.py",
  "scoring": {
    "complexity_score": 7.5,
    "security_score": 9.0,
    "maintainability_score": 8.0,
    "test_coverage_score": 6.0,
    "performance_score": 8.5,
    "linting_score": 9.0,
    "type_checking_score": 7.0,
    "overall_score": 78.5
  },
  "feedback": {
    "strengths": [
      "Good error handling",
      "Clear function structure"
    ],
    "issues": [
      "Missing type hints on line 45",
      "Complex function on line 120 (cyclomatic complexity: 12)"
    ],
    "recommendations": [
      "Add type hints for better maintainability",
      "Consider breaking down complex function"
    ]
  },
  "passed": true
}
```

---

## Other Useful Agents

### Planner Agent

**Best for:** Breaking down features into user stories

```powershell
# Create a story for a new feature
python -m tapps_agents.cli planner create-story "Add device health monitoring" --priority high

# List all stories
python -m tapps_agents.cli planner list-stories
```

### Architect Agent

**Best for:** System design and architecture decisions

```powershell
# Design a new service
python -m tapps_agents.cli architect design "Device health monitoring service"

# Review architecture
python -m tapps_agents.cli architect review docs/architecture.md
```

### Analyst Agent

**Best for:** Requirements analysis and research

```powershell
# Analyze requirements
python -m tapps_agents.cli analyst analyze "Device health monitoring requirements"
```

### Ops Agent

**Best for:** Security scanning, deployment, infrastructure

```powershell
# Security scan
python -m tapps_agents.cli ops security-scan services/

# Dependency analysis
python -m tapps_agents.cli ops dependency-analysis
```

---

## Common Use Cases

### Use Case 1: Starting a New Feature

```powershell
# Step 1: Enhance your initial prompt
python -m tapps_agents.cli enhancer enhance "Add device health monitoring" --output feature-plan.md

# Step 2: Create user stories
python -m tapps_agents.cli planner create-story "Add device health monitoring" --priority high

# Step 3: Design architecture
python -m tapps_agents.cli architect design "Device health monitoring service"
```

### Use Case 2: Code Review Before Commit

```powershell
# Review all changed files
python -m tapps_agents.cli reviewer review services/websocket-ingestion/ --recursive

# Check for type errors
python -m tapps_agents.cli reviewer type-check services/websocket-ingestion/src/main.py

# Lint check
python -m tapps_agents.cli reviewer lint services/websocket-ingestion/src/main.py
```

### Use Case 3: Understanding Complex Code

```powershell
# Get detailed analysis
python -m tapps_agents.cli analyst analyze "How does websocket-ingestion process events?"

# Review with context
python -m tapps_agents.cli reviewer review services/websocket-ingestion/src/main.py --format json
```

### Use Case 4: Security Audit

```powershell
# Full security scan
python -m tapps_agents.cli ops security-scan services/

# Check dependencies
python -m tapps_agents.cli ops dependency-analysis
```

---

## Integration with Cursor IDE

### Using in Cursor Chat

You can reference TappsCodingAgents in Cursor:

```
@TappsCodingAgents enhance this prompt: "Add device health monitoring"
```

### Using CLI in Cursor Terminal

1. Open terminal in Cursor (`Ctrl + ~`)
2. Run any TappsCodingAgents command
3. Results appear in terminal

---

## Configuration

### Customize Enhancement Stages

Edit `.tapps-agents/enhancement-config.yaml`:

```yaml
enhancement:
  stages:
    analysis:
      enabled: true
    requirements:
      enabled: true
    architecture:
      enabled: true
    codebase_context:
      enabled: true
      tier: TIER3  # Deep context
      max_related_files: 20
    quality:
      enabled: true
    implementation:
      enabled: true
    synthesis:
      enabled: true
```

### Add More Experts

Edit `.tapps-agents/experts.yaml` to add domain-specific experts.

### Add Knowledge Base Content

Add markdown files to `.tapps-agents/knowledge/{domain}/` for RAG retrieval.

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'tapps_agents'"

**Solution:**
```powershell
cd C:\cursor\TappsCodingAgents
python -m pip install -e .
```

### Issue: "Enhancer Agent not finding experts"

**Solution:**
1. Check `.tapps-agents/experts.yaml` exists
2. Verify expert IDs match `domains.md`
3. Check knowledge base has files: `.tapps-agents/knowledge/{domain}/*.md`

### Issue: "Reviewer Agent timeout"

**Solution:**
- Large files may timeout
- Use `--max-file-size` flag
- Or review specific functions instead of whole file

### Issue: "Type checking fails"

**Solution:**
- Ensure mypy is installed: `pip install mypy`
- Check `pyproject.toml` has mypy config
- Run: `python -m tapps_agents.cli reviewer type-check <file>`

---

## Getting Help

### View Agent Help

```powershell
# General help
python -m tapps_agents.cli --help

# Agent-specific help
python -m tapps_agents.cli enhancer --help
python -m tapps_agents.cli reviewer --help
python -m tapps_agents.cli planner --help
```

### Documentation

**HomeIQ Integration:**
- [Integration Strategy](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md) - Complete strategy for using TappsCodingAgents with HomeIQ
- [Custom Workflows Guide](./HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md) - Creating HomeIQ-specific workflows
- [Quick Reference](./TAPPS_AGENTS_QUICK_REFERENCE.md) - Quick decision guide

**TappsCodingAgents Framework:**
- [Enhancer Agent Guide](../../TappsCodingAgents/docs/ENHANCER_AGENT.md)
- [Reviewer Agent Guide](../../TappsCodingAgents/docs/README.md)
- [Deployment Guide](implementation/TAPPS_AGENTS_DEPLOYMENT.md)

---

## Quick Reference Card

```powershell
# ENHANCER - Prompt Enhancement
python -m tapps_agents.cli enhancer enhance-quick "your prompt"
python -m tapps_agents.cli enhancer enhance "your prompt" --output file.md

# REVIEWER - Code Review
python -m tapps_agents.cli reviewer review <file>
python -m tapps_agents.cli reviewer score <file>
python -m tapps_agents.cli reviewer lint <file>
python -m tapps_agents.cli reviewer type-check <file>

# PLANNER - User Stories
python -m tapps_agents.cli planner create-story "feature" --priority high

# ARCHITECT - System Design
python -m tapps_agents.cli architect design "service name"

# ANALYST - Requirements
python -m tapps_agents.cli analyst analyze "requirement"

# OPS - Security & Deployment
python -m tapps_agents.cli ops security-scan <directory>
python -m tapps_agents.cli ops dependency-analysis
```

---

## Next Steps

1. **Try Enhancer Agent** - Start with a simple prompt enhancement
2. **Review Your Code** - Use Reviewer Agent on existing code
3. **Plan a Feature** - Use Planner + Architect for new features
4. **Customize Experts** - Add domain-specific knowledge to `.tapps-agents/knowledge/`

Happy coding! 🚀

