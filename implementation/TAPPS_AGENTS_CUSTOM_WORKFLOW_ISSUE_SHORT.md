# Issue: Custom Workflow YAML Files Cannot Be Executed via CLI

## Problem

The TappsCodingAgents framework does not support executing custom workflow YAML files via CLI. Only preset workflows (rapid, full, fix, quality, etc.) are supported, not custom YAML files from `workflows/custom/` directory.

## Expected Behavior

Execute custom workflow YAML files via:

```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-validation.yaml
```

## Actual Behavior

Command fails with:
```
__main__.py orchestrator: error: argument command: invalid choice: 'workflow' (choose from workflow-list, *workflow-list, workflow-start, *workflow-start, workflow-status, *workflow-status, workflow-next, *workflow-next, workflow-skip, *workflow-skip, workflow-resume, *workflow-resume, gate, *gate, help, *help)
```

## Current CLI Structure

- `python -m tapps_agents.cli workflow` - Only supports presets (rapid, full, fix, quality, etc.), no file path support
- `python -m tapps_agents.cli orchestrator workflow-start <workflow_id>` - Requires workflow ID, not file path
- No command exists to load and execute custom YAML workflow files

## Impact

- Custom workflows in `workflows/custom/` cannot be executed
- Documentation references functionality that doesn't exist
- Users cannot leverage custom workflow definitions

## Proposed Solution

Add support for executing custom workflow YAML files. Options:

**Option 1:** Extend orchestrator command:
```bash
python -m tapps_agents.cli orchestrator workflow-execute <workflow_file_path>
```

**Option 2:** Extend workflow command to accept file paths:
```bash
python -m tapps_agents.cli workflow <preset_name|file_path>
```

**Option 3:** Add dedicated command:
```bash
python -m tapps_agents.cli workflow-load <workflow_file_path> [--auto]
```

## Implementation Requirements

1. File path resolution (relative/absolute paths)
2. YAML file loading and parsing using existing `WorkflowParser`
3. Integration with existing `WorkflowExecutor`
4. Support for all workflow features (gates, parallel steps, etc.)
5. Clear error handling (missing files, YAML errors, validation errors)

## Example Workflow File Structure

Custom workflows follow standard format:
```yaml
workflow:
  id: homeiq-service-validation
  name: "HomeIQ Service Validation"
  version: "1.0.0"
  type: brownfield
  settings:
    quality_gates: false
    code_scoring: true
  steps:
    - id: step1
      agent: analyst
      action: gather_requirements
      # ... step configuration
```

## Related Files

- Workflow files: `workflows/custom/*.yaml`
- Orchestrator Agent: `tapps_agents/agents/orchestrator/agent.py`
- CLI Commands: `tapps_agents/cli/commands/`

