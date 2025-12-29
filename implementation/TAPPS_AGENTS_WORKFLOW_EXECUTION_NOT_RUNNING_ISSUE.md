# TappsCodingAgents Framework Issue: Workflow Execution Not Running Steps

**Created:** 2025-01-23  
**Status:** ⚠️ OPEN - Framework Issue  
**Priority:** High  
**Type:** Bug  
**Framework Component:** Orchestrator Agent / Workflow Executor  
**Related:** TAPPS_AGENTS_CUSTOM_WORKFLOW_EXECUTION_ISSUE.md

## Problem Summary

The `orchestrator workflow <file_path>` command successfully loads and initializes workflows but does not actually execute workflow steps. The workflow status shows "running" but no steps are executed, no artifacts are created, and the workflow never completes.

### Expected Behavior

When executing:
```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-validation.yaml
```

The workflow should:
1. Load and validate the workflow YAML file ✅ (working)
2. Initialize workflow state ✅ (working)
3. **Execute workflow steps** ❌ (NOT working)
4. Create artifacts as specified ❌ (NOT working)
5. Advance through steps until completion ❌ (NOT working)

### Actual Behavior

1. ✅ Workflow YAML file loads successfully
2. ✅ Workflow state is initialized (status: "running", current_step: "discover_services")
3. ❌ **No steps are executed** - workflow executor only calls `start()`, not `execute()`
4. ❌ No artifacts are created
5. ❌ Workflow remains in "running" state indefinitely
6. ❌ `workflow-resume` also doesn't execute steps (only resumes state)
7. ❌ `workflow-next` reports "No next step (workflow may be complete)" even though status is "running"

### Code Analysis

**Location:** `tapps_agents/agents/orchestrator/agent.py` (line 173-214)

The `_execute_workflow_from_file()` method only calls `start()`, not `execute()`:

```python
async def _execute_workflow_from_file(self, workflow_file_path: str) -> dict[str, Any]:
    # ... path resolution ...
    workflow = self.workflow_executor.load_workflow(workflow_path)
    self.current_workflow = workflow
    state = self.workflow_executor.start()  # ❌ Only starts, doesn't execute
    return {
        "success": True,
        "status": state.status,  # Returns "running"
        "current_step": state.current_step,
        # ...
    }
```

**Reference:** `tapps_agents/workflow/executor.py` (line 397-414)

The `WorkflowExecutor.execute()` method exists and is documented as:

```python
async def execute(
    self,
    workflow: Workflow | None = None,
    target_file: str | None = None,
    max_steps: int = 50,
) -> WorkflowState:
    """
    Execute a workflow end-to-end.

    Why this exists:
    - `start()` only initializes/persists workflow state.
    - The original CLI called `start()` and then stopped, leaving status as "running".

    This method runs the current step, records artifacts, advances to next,
    and repeats until completion/failure.
    """
```

**The Problem:** The orchestrator command calls `start()` but never calls `execute()`.

### Attempted Workarounds

1. ✅ `workflow workflows/custom/...yaml` - Starts workflow, doesn't execute
2. ✅ `workflow-resume` - Resumes workflow state, doesn't execute
3. ✅ `workflow-next` - Reports "No next step" even though workflow is "running"

### Impact

**Blocking:** Yes - Custom workflows cannot be executed via CLI

**Affected Use Cases:**
- Custom workflow execution (`workflows/custom/*.yaml`)
- Service validation workflows
- Quality audit workflows
- Any workflow requiring step execution

**Workflow Status:**
- Workflow file: `workflows/custom/homeiq-service-validation.yaml` ✅ Created
- Workflow structure: ✅ Valid YAML, correct format
- Workflow execution: ❌ **BLOCKED** - Steps don't execute

### Required Fix

#### Option 1: Call `execute()` Instead of `start()` (Recommended)

Modify `_execute_workflow_from_file()` to call `execute()`:

```python
async def _execute_workflow_from_file(self, workflow_file_path: str) -> dict[str, Any]:
    # ... path resolution ...
    workflow = self.workflow_executor.load_workflow(workflow_path)
    self.current_workflow = workflow
    
    # Execute workflow end-to-end
    state = await self.workflow_executor.execute(workflow, max_steps=50)  # ✅ Execute instead of start
    
    return {
        "success": True,
        "workflow_id": workflow.id,
        "status": state.status,
        "completed_steps": state.completed_steps,
        "message": f"Workflow '{workflow.name}' executed from {workflow_file_path}",
    }
```

#### Option 2: Add `--execute` Flag

Add an optional flag to control execution vs initialization:

```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/...yaml --execute
```

#### Option 3: Separate Commands

- `workflow <file_path>` - Load and start (current behavior)
- `workflow-execute <file_path>` - Load and execute end-to-end

### Testing

After fix, verify:

1. ✅ Workflow steps execute (check for agent invocations)
2. ✅ Artifacts are created (e.g., `services-inventory.json`)
3. ✅ Workflow completes (status: "completed" or "failed")
4. ✅ Step execution results are visible
5. ✅ Output files are created in expected locations

### Related Issues

- **TAPPS_AGENTS_CUSTOM_WORKFLOW_EXECUTION_ISSUE.md** - Original issue about custom workflow file support (RESOLVED - file path support added in 3.1.0)
- This issue is about step execution after workflow initialization

## Status

**BLOCKED** - Waiting for framework fix to call `execute()` method.

The workflow file is ready and valid, but execution is blocked until the orchestrator calls `execute()` instead of just `start()`.

