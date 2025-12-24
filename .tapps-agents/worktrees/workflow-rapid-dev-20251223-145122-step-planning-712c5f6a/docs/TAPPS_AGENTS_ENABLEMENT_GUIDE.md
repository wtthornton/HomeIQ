# TappsCodingAgents Enablement Guide for HomeIQ

**Quick guide on what's enabled and how it works**

---

## ✅ What's Already Enabled (No Action Required)

### 1. Cursor Rules (Automatically Active)

All rules with `alwaysApply: true` are **automatically loaded** by Cursor when you start a chat. No configuration needed!

**Active Rules:**
- ✅ `.cursor/rules/simple-mode.mdc` - Simple Mode orchestration (always applied)
- ✅ `.cursor/rules/tapps-agents-workflow-selection.mdc` - Workflow selection guide (always applied)
- ✅ `.cursor/rules/README.mdc` - Overview of all rules (always applied)
- ✅ `.cursor/rules/epic-31-architecture.mdc` - Architecture patterns (always applied)

**How it works:**
- Cursor automatically loads all `.mdc` files in `.cursor/rules/` 
- Rules with `alwaysApply: true` are included in every chat context
- Rules guide Cursor AI on when to use Simple Mode, workflows, etc.

**No action needed** - These are active right now! ✅

---

## 🎯 How It Gets Used

### Option 1: Simple Mode (Most Common) - **YOU USE THIS**

You (or Cursor AI) invoke Simple Mode using `@simple-mode` commands:

```bash
# Build a feature
@simple-mode *build "Create new InfluxDB query endpoint"

# Review code
@simple-mode *review services/websocket-ingestion/src/main.py

# Fix a bug
@simple-mode *fix services/data-api/src/main.py "Fix connection timeout"

# Generate tests
@simple-mode *test services/data-api/src/main.py
```

**What happens behind the scenes:**
1. Cursor AI sees your request
2. Reads the `simple-mode.mdc` rule (already loaded)
3. Understands it should orchestrate multiple agents
4. Executes the workflow: enhancer → planner → architect → implementer → reviewer → tester
5. Provides you with results

**You don't need to do anything special** - just use `@simple-mode` commands!

---

### Option 2: Custom Workflows - **YOU EXECUTE THESE**

For HomeIQ-specific patterns, you run workflows via CLI:

```bash
# Create a new microservice
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "Create weather-api service"

# Run quality audit across services
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-quality-audit.yaml

# Integrate a service
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-integration.yaml --prompt "Integrate ESPN sports data"
```

**What happens:**
1. You run the command
2. TappsCodingAgents loads the workflow YAML
3. Executes steps in sequence (with quality gates)
4. Produces results (code, tests, documentation)

**You run these manually** when you need HomeIQ-specific patterns.

---

### Option 3: Direct Agent Commands - **YOU OR CURSOR USE THESE**

For single-step operations:

```bash
# Enhance a prompt
python -m tapps_agents.cli enhancer enhance "Add device health monitoring"

# Analyze an error
python -m tapps_agents.cli debugger analyze-error "Connection timeout" --file services/data-api/src/main.py

# Review code directly
python -m tapps_agents.cli reviewer review services/websocket-ingestion/src/main.py
```

**Use when:** You need a single agent's capability (not a full workflow).

---

## 🤖 How Cursor AI Decides What to Use

The **`tapps-agents-workflow-selection.mdc`** rule (already active) guides Cursor AI:

```
User Request
    │
    ├─ Single file operation? (review, test, fix)
    │   └─ YES → Simple Mode (*review, *test, *fix)
    │
    ├─ Standard feature/bug fix?
    │   └─ YES → Simple Mode (*build, *fix)
    │
    ├─ Single-step operation?
    │   └─ YES → Direct Agent Command
    │
    └─ Pattern 3+ times? OR HomeIQ-specific?
        └─ YES → Custom Workflow
```

**Cursor AI automatically:**
1. Reads your request
2. Checks the workflow selection rule (already loaded)
3. Decides: Simple Mode → Direct Agent → Custom Workflow
4. Executes the appropriate command

**You don't need to decide** - Cursor AI uses the rules to choose!

---

## 📋 Quick Start Examples

### Example 1: You Want to Build a Feature

**You type:**
```
Create a new endpoint to query device health metrics from InfluxDB
```

**Cursor AI (using rules) decides:**
- This is a standard feature → Use Simple Mode
- Executes: `@simple-mode *build "Create new endpoint to query device health metrics from InfluxDB"`

**Result:** Feature built with tests, reviews, documentation ✅

---

### Example 2: You Want to Create a New Microservice

**You type:**
```
Create a new microservice for weather data
```

**Cursor AI (using rules) decides:**
- This is a HomeIQ-specific pattern (microservice creation)
- Should use custom workflow: `homeiq-microservice-creation.yaml`
- Executes: `python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "Create weather-api service"`

**Result:** Microservice created with Docker, tests, Epic 31 patterns ✅

---

### Example 3: You Want to Review Code

**You type:**
```
Review the websocket-ingestion service code quality
```

**Cursor AI (using rules) decides:**
- This is a single file/service review → Use Simple Mode
- Executes: `@simple-mode *review services/websocket-ingestion/src/main.py`

**Result:** Quality scores, issues identified, improvement suggestions ✅

---

## 🔍 Verification: Is It Working?

### Check 1: Rules Are Loaded

**In Cursor Chat, type:**
```
What workflow should I use to create a new microservice?
```

**Expected response:** Cursor AI should reference the `homeiq-microservice-creation.yaml` workflow.

---

### Check 2: Simple Mode Is Available

**In Cursor Chat, type:**
```
@simple-mode *help
```

**Expected response:** Simple Mode help information showing available commands.

---

### Check 3: Custom Workflows Exist

**In terminal, run:**
```bash
ls workflows/custom/
```

**Expected output:**
```
homeiq-microservice-creation.yaml
homeiq-quality-audit.yaml
homeiq-service-integration.yaml
```

---

## 🎓 Summary

| Component | Enabled? | How It Works |
|-----------|----------|--------------|
| **Cursor Rules** | ✅ Yes (automatic) | Files in `.cursor/rules/` with `alwaysApply: true` are loaded automatically |
| **Simple Mode** | ✅ Yes (ready) | Use `@simple-mode *build`, `*review`, `*fix`, `*test` commands |
| **Custom Workflows** | ✅ Yes (created) | Run via CLI: `python -m tapps_agents.cli orchestrator workflow workflows/custom/...` |
| **Workflow Selection** | ✅ Yes (automatic) | Cursor AI uses rules to decide when to use what |

**Bottom line:** Everything is already enabled! Just use `@simple-mode` commands, and Cursor AI will handle the rest using the rules we created.

---

## 📚 Related Documentation

- [Integration Strategy](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md) - Complete strategy document
- [Quick Reference](./TAPPS_AGENTS_QUICK_REFERENCE.md) - Quick decision guide
- [Usage Guide](./TAPPS_AGENTS_USAGE_GUIDE.md) - Detailed usage examples
- [Custom Workflows Guide](./HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md) - Creating new workflows

