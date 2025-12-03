# Agent Customizations

This directory contains user-specific customizations for BMAD agents. Files in this directory are **gitignored** and persist through BMAD updates.

## How It Works

1. **Create customization file**: `{agent-id}-custom.yaml`
   - Example: `bmad-master-custom.yaml`
   - Example: `dev-custom.yaml`

2. **Agent loads customizations**: Agents automatically load customizations if present
   - Customizations override default agent behavior
   - Update-safe: Your customizations persist through BMAD updates

3. **Customization structure**: See template below

## Customization Template

```yaml
# Agent Customization File
# File: .bmad-core/customizations/{agent-id}-custom.yaml

agent_id: bmad-master  # Must match filename

# Override agent persona
persona_overrides:
  # Add or modify core principles
  additional_principles:
    - "Your custom principle here"
    - "Another custom principle"
  
  # Modify communication style
  communication_style:
    tone: "professional" | "casual" | "friendly" | "technical"
    formality: "formal" | "informal"
    verbosity: "concise" | "detailed" | "balanced"
  
  # Custom expertise areas
  expertise_areas:
    add:
      - "Your domain expertise"
      - "Another area"
    emphasize:
      - "Focus more on this area"
  
  # Custom instructions
  custom_instructions: |
    Additional instructions specific to your needs.
    These are appended to the agent's base instructions.

# Override commands
command_overrides:
  # Add custom commands
  add:
    - name: "custom-command"
      description: "Description of custom command"
      handler: "task-name"  # References a task file
  
  # Modify existing commands
  modify:
    - name: "help"
      description: "Custom help description"

# Override dependencies
dependency_overrides:
  # Add custom tasks
  tasks:
    add:
      - "custom-task.md"
  
  # Add custom templates
  templates:
    add:
      - "custom-template.yaml"
  
  # Add custom data files
  data:
    add:
      - "custom-data.md"

# Project-specific context
project_context:
  # Always load these files for this agent
  always_load:
    - "docs/project-specific.md"
    - "docs/team-guidelines.md"
  
  # Project-specific preferences
  preferences:
    coding_style: "Your team's style"
    architecture_patterns: ["Pattern 1", "Pattern 2"]
    technology_preferences: ["Tech 1", "Tech 2"]
```

## Examples

### Example 1: Customize Dev Agent for Python Focus

File: `.bmad-core/customizations/dev-custom.yaml`

```yaml
agent_id: dev

persona_overrides:
  additional_principles:
    - "Always use type hints in Python"
    - "Follow PEP 8 strictly"
    - "Use async/await for I/O operations"
  
  communication_style:
    tone: "technical"
    verbosity: "detailed"
  
  expertise_areas:
    emphasize:
      - "Python"
      - "FastAPI"
      - "Async programming"
  
  custom_instructions: |
    This project uses Python 3.11+ with FastAPI.
    Always use async/await for database operations.
    Follow the project's performance patterns document.

project_context:
  always_load:
    - "docs/architecture/performance-patterns.md"
  preferences:
    coding_style: "Pythonic with type hints"
    technology_preferences: ["FastAPI", "SQLAlchemy", "Pydantic"]
```

### Example 2: Customize PM Agent for Agile Focus

File: `.bmad-core/customizations/pm-custom.yaml`

```yaml
agent_id: pm

persona_overrides:
  additional_principles:
    - "Always break stories into 1-3 day tasks"
    - "Include acceptance criteria for every story"
    - "Consider technical debt in story estimation"
  
  communication_style:
    tone: "professional"
    formality: "balanced"
  
  custom_instructions: |
    This team follows 2-week sprints.
    Stories should be small enough to complete in 1-3 days.
    Always include risk assessment for complex stories.

project_context:
  preferences:
    sprint_length: "2 weeks"
    story_size: "1-3 days"
    estimation_method: "story points"
```

## Loading Customizations

Agents automatically load customizations on activation:

1. Agent checks for `{agent-id}-custom.yaml` in `.bmad-core/customizations/`
2. If found, loads and merges with base agent configuration
3. Customizations take precedence over defaults
4. Base agent behavior is preserved where not overridden

## Best Practices

1. **Start Small**: Begin with minor customizations, expand as needed
2. **Document Why**: Add comments explaining customizations
3. **Version Control**: Keep customizations in your project repo (not BMAD repo)
4. **Team Alignment**: Share customization files with team
5. **Test Changes**: Verify customizations work as expected

## Troubleshooting

**Customization not loading?**
- Check filename matches `{agent-id}-custom.yaml`
- Verify YAML syntax is valid
- Check agent ID matches exactly

**Conflicting customizations?**
- Customizations override defaults
- Last loaded customization wins
- Check for duplicate keys

**Want to reset?**
- Delete the customization file
- Agent returns to default behavior

## Notes

- Customizations are **project-specific**
- They persist through BMAD updates
- They are **gitignored** by default (add to `.gitignore`)
- Share with team via your project repository

