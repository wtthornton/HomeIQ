<!-- Powered by BMAD™ Core -->

# Workflow Initialization Task

## Purpose

Automatically analyze the project and recommend the appropriate workflow track based on project characteristics. This implements scale-adaptive intelligence to help users select the right workflow without manual decision-making.

## Command

```
*workflow-init
```

## Task Instructions

### Step 1: Project Analysis

Analyze the current project to determine its characteristics:

1. **Check for existing documentation:**
   - Look for `docs/prd.md` or `docs/prd/` directory
   - Look for `docs/architecture.md` or `docs/architecture/` directory
   - Look for `docs/stories/` directory
   - Check for existing `.bmad-core/` configuration

2. **Assess project size:**
   - Count source files (approximate)
   - Check for monorepo structure
   - Identify number of services/modules
   - Check for existing test infrastructure

3. **Determine project type:**
   - Greenfield (new project) vs Brownfield (existing project)
   - Full-stack vs Service-only vs UI-only
   - Web app vs Mobile vs API vs Data pipeline

4. **Assess complexity:**
   - Number of dependencies
   - Technology stack complexity
   - Integration requirements
   - Team size indicators (if available)

5. **Check project state:**
   - Is this a bug fix or small feature?
   - Is this a major new feature?
   - Is this enterprise/compliance-focused?

### Step 2: Workflow Track Recommendation

Based on analysis, recommend one of three tracks:

#### ⚡ Quick Flow Track
**Recommended when:**
- Bug fixes or small features (< 5 files changed)
- Single service/module changes
- No architectural impact
- Minimal documentation needed
- Estimated time: < 1 hour

**Workflow characteristics:**
- Tech spec only (no PRD)
- Minimal planning overhead
- Direct to implementation
- Quick QA review

**Setup time:** < 5 minutes

#### 📋 BMad Method Track (Standard)
**Recommended when:**
- New features or enhancements
- Multiple files/services affected
- Requires planning and architecture
- Standard product/platform development
- Team collaboration needed

**Workflow characteristics:**
- Full PRD + Architecture + UX (if needed)
- Story-driven development
- Comprehensive QA
- Standard BMad workflow

**Setup time:** < 15 minutes

#### 🏢 Enterprise Track
**Recommended when:**
- Enterprise applications
- Compliance requirements (HIPAA, SOC2, etc.)
- Multi-team coordination
- Complex integrations
- High-risk systems
- Extensive documentation required

**Workflow characteristics:**
- Full governance suite
- Enhanced documentation
- Compliance checkpoints
- Risk assessment mandatory
- Extended QA gates

**Setup time:** < 30 minutes

### Step 3: Generate Recommendation Report

Create a recommendation report with:

```yaml
workflow_recommendation:
  track: "quick-flow" | "bmad-method" | "enterprise"
  confidence: "high" | "medium" | "low"
  reasoning:
    - "Reason 1"
    - "Reason 2"
    - "Reason 3"
  
project_analysis:
  type: "greenfield" | "brownfield"
  scope: "fullstack" | "service" | "ui"
  size: "small" | "medium" | "large"
  complexity: "low" | "medium" | "high"
  existing_docs: true | false
  
recommended_workflow:
  id: "workflow-id"
  name: "Workflow Name"
  file: ".bmad-core/workflows/{workflow-id}.yaml"
  
alternative_workflows:
  - id: "alternative-id"
    name: "Alternative Name"
    when_to_use: "Use when..."
```

### Step 4: Update Configuration

If user approves recommendation:

1. Update `.bmad-core/core-config.yaml`:
   ```yaml
   workflow:
     track: "quick-flow" | "bmad-method" | "enterprise"
     selected_workflow: "workflow-id"
     initialized_at: "YYYY-MM-DD"
     initialized_by: "workflow-init"
   ```

2. Provide next steps:
   - How to start the recommended workflow
   - Key commands for the track
   - Expected timeline

### Step 5: Interactive Selection (if needed)

If confidence is low or user wants to override:

1. Present all three tracks with descriptions
2. Show project analysis summary
3. Ask user to confirm or select alternative
4. Update configuration based on selection

## Output Format

```
=== BMAD Workflow Initialization ===

Project Analysis:
- Type: [greenfield/brownfield]
- Scope: [fullstack/service/ui]
- Size: [small/medium/large]
- Complexity: [low/medium/high]
- Existing Documentation: [yes/no]

Recommended Track: ⚡ Quick Flow / 📋 BMad Method / 🏢 Enterprise

Reasoning:
1. [Reason based on analysis]
2. [Reason based on analysis]
3. [Reason based on analysis]

Recommended Workflow: [workflow-id]
- File: .bmad-core/workflows/[workflow-id].yaml
- Setup Time: [X minutes]
- Expected Duration: [estimate]

Next Steps:
1. [First step]
2. [Second step]
3. [Third step]

Would you like to:
- [A] Accept this recommendation
- [B] See alternative workflows
- [C] Manually select a workflow
```

## Decision Logic

### Quick Flow Criteria (ALL must be true):
- ✅ Small change (< 5 files typically affected)
- ✅ Single service/module
- ✅ No architectural changes
- ✅ No new dependencies
- ✅ Bug fix or minor enhancement
- ✅ No compliance requirements

### BMad Method Criteria (Standard):
- ✅ New feature or significant enhancement
- ✅ Multiple files/services affected
- ✅ Requires planning
- ✅ Standard development workflow
- ✅ Team collaboration

### Enterprise Criteria (ANY of these):
- ✅ Compliance requirements mentioned
- ✅ Enterprise/critical system
- ✅ Multi-team coordination needed
- ✅ High-risk or regulated industry
- ✅ Extensive documentation required
- ✅ Complex integration requirements

## Integration with Workflows

After recommendation:

1. **Quick Flow:**
   - Use `quick-fix.yaml` workflow (to be created)
   - Minimal planning phase
   - Direct to implementation

2. **BMad Method:**
   - Use appropriate greenfield/brownfield workflow
   - Full planning → development cycle
   - Standard BMad process

3. **Enterprise:**
   - Use appropriate workflow with enhanced gates
   - Additional compliance checkpoints
   - Extended documentation requirements

## Notes

- This task should be run at project start or when workflow is unclear
- Can be re-run if project characteristics change
- Recommendations are advisory - user can override
- Analysis is based on heuristics and may need refinement

## Error Handling

- If project structure unclear: Ask user clarifying questions
- If no clear recommendation: Present all options with guidance
- If configuration update fails: Provide manual instructions

