# Agent Customization Loader

This document explains how agents load and apply customizations.

## Customization Loading Process

When an agent activates, it follows this process:

1. **Load base agent configuration** from `.bmad-core/agents/{agent-id}.md`
2. **Check for customization file** at `.bmad-core/customizations/{agent-id}-custom.yaml`
3. **If customization exists:**
   - Load YAML customization file
   - Merge with base configuration
   - Apply overrides according to customization structure
4. **Activate with merged configuration**

## Customization File Location

```
.bmad-core/
  ├── agents/
  │   └── dev.md (base agent)
  └── customizations/
      └── dev-custom.yaml (user customizations - gitignored)
```

## Customization Merge Rules

### Persona Overrides

```yaml
persona_overrides:
  additional_principles:
    # Appended to base principles
    - "New principle 1"
    - "New principle 2"
  
  communication_style:
    # Overrides base communication style
    tone: "casual"
    verbosity: "concise"
  
  expertise_areas:
    add:
      # Added to base expertise
      - "New domain"
    emphasize:
      # Prioritized in responses
      - "Existing area to focus on"
  
  custom_instructions: |
    # Appended to base instructions
    Additional instructions here.
```

### Command Overrides

```yaml
command_overrides:
  add:
    # New commands added
    - name: "custom-command"
      description: "Does something"
      handler: "task-name"
  
  modify:
    # Existing commands modified
    - name: "help"
      description: "Custom help text"
```

### Dependency Overrides

```yaml
dependency_overrides:
  tasks:
    add:
      # Additional tasks loaded
      - "custom-task.md"
  
  templates:
    add:
      # Additional templates available
      - "custom-template.yaml"
  
  data:
    add:
      # Additional data files
      - "custom-data.md"
```

### Project Context

```yaml
project_context:
  always_load:
    # Files always loaded for this agent
    - "docs/project-specific.md"
  
  preferences:
    # Project-specific preferences
    coding_style: "Pythonic"
    technology_preferences: ["FastAPI", "React"]
```

## Implementation in Agent Files

Agents should check for customizations in their activation instructions:

```yaml
activation-instructions:
  - STEP 1: Read THIS ENTIRE FILE
  - STEP 2: Check for customization file at `.bmad-core/customizations/{agent-id}-custom.yaml`
  - STEP 3: If customization exists, load and merge with base configuration
  - STEP 4: Apply customization overrides
  - STEP 5: Continue with normal activation
```

## Example: Loading Customization

```python
# Pseudo-code for customization loading
def load_agent_with_customizations(agent_id):
    # Load base agent
    base_config = load_agent_file(f".bmad-core/agents/{agent_id}.md")
    
    # Check for customization
    custom_path = f".bmad-core/customizations/{agent_id}-custom.yaml"
    if file_exists(custom_path):
        custom_config = load_yaml(custom_path)
        
        # Merge configurations
        merged_config = merge_configs(base_config, custom_config)
        return merged_config
    
    return base_config
```

## Validation

Before applying customizations:

1. **Validate YAML syntax**
2. **Check agent_id matches filename**
3. **Verify referenced files exist** (tasks, templates, data)
4. **Warn on unknown override keys**

## Error Handling

- **Missing customization file**: Use base agent (no error)
- **Invalid YAML**: Log error, use base agent
- **Missing referenced files**: Warn user, continue with available files
- **Invalid agent_id**: Log error, ignore customization

## Notes

- Customizations are **additive and overriding**, not replacing
- Base agent structure is preserved
- Customizations take precedence where specified
- Unknown customization keys are ignored (with warning)

