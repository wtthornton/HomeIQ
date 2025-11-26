# BMAD Developer Guide

**Your Complete Guide to Becoming a BMAD Developer**

## What is BMAD?

**BMAD (Business Model and Architecture Design)** is a structured methodology for AI-driven planning and development. It provides:

- **Structured Workflows**: Clear processes for planning and development
- **Specialized AI Agents**: Role-based agents (PM, Architect, Dev, QA, etc.) that understand your project
- **Quality Gates**: Built-in quality assurance and testing strategies
- **Documentation Standards**: Consistent documentation patterns
- **Context Management**: Intelligent document sharding for efficient AI context usage

## Why BMAD?

BMAD helps you:
- ✅ Build better software with structured planning
- ✅ Maintain quality through automated QA processes
- ✅ Work efficiently with AI agents that understand your project
- ✅ Scale from small fixes to enterprise projects
- ✅ Reduce context bloat with intelligent document management

---

## Core Concepts

### 1. Workflow Tracks

BMAD offers three workflow tracks based on project complexity:

#### ⚡ Quick Flow Track (< 5 min)
**Use for:** Bug fixes, small features, hotfixes
- Minimal planning overhead
- Direct to implementation
- Quick QA review
- **Workflow:** `quick-fix.yaml`

#### 📋 BMad Method Track (< 15 min) - **Standard**
**Use for:** New features, standard development
- Full PRD + Architecture + UX (if needed)
- Story-driven development
- Comprehensive QA
- **Workflows:** `greenfield-*.yaml` or `brownfield-*.yaml`

#### 🏢 Enterprise Track (< 30 min)
**Use for:** Enterprise apps, compliance, complex projects
- Full governance suite
- Enhanced documentation
- Compliance checkpoints
- Risk assessment mandatory

### 2. BMAD Agents

BMAD provides specialized AI agents for different roles:

| Agent | Role | When to Use |
|-------|------|-------------|
| **@bmad-master** | Universal executor | Any task, don't want to switch agents |
| **@pm** | Product Manager | Create PRDs, define requirements |
| **@architect** | System Architect | Design architecture, technical decisions |
| **@dev** | Developer | Implement features, write code |
| **@qa** | Test Architect | Quality assurance, testing, reviews |
| **@po** | Product Owner | Story validation, backlog management |
| **@sm** | Scrum Master | Story creation, workflow management |
| **@ux-expert** | UX Designer | UI/UX design, frontend specs |
| **@analyst** | Business Analyst | Research, market analysis |

### 3. Document Structure

BMAD organizes documentation in a specific structure:

```
docs/
├── prd.md                    # Product Requirements Document
├── architecture.md            # System Architecture
├── prd/                      # Sharded PRD sections
├── architecture/              # Sharded architecture sections
├── stories/                   # User stories
│   └── story-{epic}-{number}-{slug}.md
└── qa/                       # Quality assurance
    ├── assessments/           # QA assessments
    └── gates/                # Quality gates
```

### 4. Quality Gates

BMAD uses quality gates to ensure code quality:

- **PASS**: All critical requirements met
- **CONCERNS**: Non-critical issues found
- **FAIL**: Critical issues that must be addressed
- **WAIVED**: Issues acknowledged but accepted

---

## Getting Started

### Step 1: Initialize Your Project

If you're starting fresh or want to configure BMAD for your project:

```bash
@bmad-master *workflow-init
```

This will:
- Analyze your project automatically
- Recommend a workflow track (Quick Flow / BMad Method / Enterprise)
- Update `.bmad-core/core-config.yaml` with your selection

### Step 2: Understand Your Project Type

#### Greenfield (New Project)
- Starting from scratch
- Use `greenfield-*.yaml` workflows
- Full planning phase recommended

#### Brownfield (Existing Project)
- Adding to existing codebase
- Use `brownfield-*.yaml` workflows
- Document existing system first

**For HomeIQ:** You're working in a **brownfield** project. The workflow is already configured as `brownfield-fullstack.yaml`.

### Step 3: Learn the Development Cycle

The standard BMAD development cycle:

```
1. SM: Draft Story from Epic
   ↓
2. QA: Risk Assessment (optional, recommended)
   ↓
3. QA: Test Design (optional, recommended)
   ↓
4. PO: Validate Story (optional)
   ↓
5. Dev: Implement Tasks
   ↓
6. QA: Requirements Tracing (mid-dev, optional)
   ↓
7. Dev: Mark Ready for Review
   ↓
8. QA: Comprehensive Review
   ↓
9. QA: Quality Gate Decision
   ↓
10. Mark Story as Done
```

---

## Essential Commands

### BMad Master Commands

```bash
@bmad-master *help                    # Show all available commands
@bmad-master *workflow-init           # Initialize/analyze project workflow
@bmad-master *shard-doc {doc} {dest}  # Shard large documents
@bmad-master *task {task-name}        # Execute a specific task
```

### QA Agent Commands (Test Architect)

```bash
@qa *risk {story}      # Assess risks before development
@qa *design {story}    # Create test strategy
@qa *trace {story}     # Verify test coverage during dev
@qa *nfr {story}       # Check quality attributes
@qa *review {story}    # Full assessment → writes gate
@qa *gate {story}      # Update quality gate status
```

### Dev Agent Commands

```bash
@dev Implement {feature}     # Implement a feature
@dev Fix {bug}              # Fix a bug
@dev Add tests for {module}  # Write tests
```

### PM Agent Commands

```bash
@pm Create PRD for {feature}           # Create product requirements
@pm Create epic for {feature}           # Create an epic
@pm Create story for {feature}          # Create a user story
```

### Architect Commands

```bash
@architect Design architecture for {system}  # Design system architecture
@architect Document project                   # Document existing project
```

---

## Best Practices

### 1. Use the Right Agent for the Task

- **Planning**: Use `@pm` or `@architect`
- **Development**: Use `@dev`
- **Quality**: Use `@qa`
- **General**: Use `@bmad-master`

### 2. Run Risk Assessment Early

For brownfield projects, **always** run risk assessment before development:

```bash
@qa *risk {story}
```

This identifies:
- Regression risks
- Integration points
- Breaking change potential
- Data migration complexity

### 3. Shard Large Documents

Large documents consume too much AI context. Shard them:

```bash
@bmad-master *shard-doc docs/prd.md docs/prd
@bmad-master *shard-doc docs/architecture.md docs/architecture
```

### 4. Use Quality Gates

Don't skip QA reviews. They catch issues early:

```bash
# Before development
@qa *risk {story}
@qa *design {story}

# During development
@qa *trace {story}
@qa *nfr {story}

# After development
@qa *review {story}
```

### 5. Commit Frequently

BMAD workflow emphasizes committing after each story completion. Don't wait!

### 6. Use Context7 KB for Technology Decisions

BMAD integrates with Context7 for up-to-date library documentation:

```bash
@bmad-master *context7-docs {library} {topic}
```

**MANDATORY**: Always use Context7 KB for technology decisions - don't rely on generic knowledge.

---

## Common Workflows

### Adding a New Feature (Brownfield)

```bash
# 1. Create story
@sm Create story for {feature}

# 2. Assess risks
@qa *risk {story}

# 3. Design tests
@qa *design {story}

# 4. Validate story
@po Validate {story}

# 5. Implement
@dev Implement {story}

# 6. Review
@qa *review {story}

# 7. Update gate
@qa *gate {story}
```

### Fixing a Bug (Quick Flow)

```bash
# 1. Create quick fix story
@sm Create story for bug fix: {description}

# 2. Implement fix
@dev Fix {bug}

# 3. Quick QA review
@qa *review {story}

# 4. Commit and done
```

### Documenting Existing System

```bash
# 1. Document project
@architect *document-project

# 2. Shard architecture
@bmad-master *shard-doc docs/architecture.md docs/architecture
```

---

## HomeIQ-Specific Notes

### Current Configuration

Your project is configured as:
- **Type**: Brownfield full-stack
- **Workflow**: `brownfield-fullstack.yaml`
- **Track**: BMad Method (standard)

### Architecture Pattern (Epic 31)

**CRITICAL**: Understand the current architecture:

- ✅ **Direct InfluxDB writes** from websocket-ingestion (Port 8001)
- ❌ **Enrichment-pipeline is DEPRECATED** (removed in Epic 31)
- ✅ **Standalone external services** write directly to InfluxDB
- ✅ **Query via data-api** (Port 8006)

**DO NOT:**
- ❌ Reference enrichment-pipeline in new code
- ❌ Suggest HTTP POST to enrichment-pipeline
- ❌ Create service-to-service dependencies

**DO:**
- ✅ Write directly to InfluxDB
- ✅ Query via data-api
- ✅ Follow Epic 31 architecture patterns

### Performance Patterns

HomeIQ follows specific performance patterns:

- **Async Everything**: All I/O operations must be async
- **Batch Writes**: InfluxDB writes in batches (100-1000 points)
- **Caching**: Expensive operations must be cached
- **No N+1 Queries**: Use eager loading
- **Bounded Queries**: Always use LIMIT clauses

See `docs/architecture/performance-patterns.md` for details.

---

## Troubleshooting

### "Agent doesn't understand my codebase"

**Solution**: Document your project first:
```bash
@architect *document-project
```

### "Too much context, agent is slow"

**Solution**: Shard your documents:
```bash
@bmad-master *shard-doc docs/prd.md docs/prd
```

### "Quality gate keeps failing"

**Solution**: Run risk assessment early:
```bash
@qa *risk {story}
```

Address high-risk items before development.

### "Don't know which agent to use"

**Solution**: Use `@bmad-master` - it can do everything.

---

## Learning Path

### Beginner (Week 1)
1. ✅ Read this guide
2. ✅ Run `@bmad-master *help` to see commands
3. ✅ Try creating a simple story with `@sm`
4. ✅ Implement a small feature with `@dev`
5. ✅ Run `@qa *review` on your work

### Intermediate (Week 2-3)
1. ✅ Learn all QA commands (`*risk`, `*design`, `*trace`, `*nfr`)
2. ✅ Understand document sharding
3. ✅ Practice brownfield workflows
4. ✅ Use Context7 KB for technology decisions

### Advanced (Week 4+)
1. ✅ Customize agents (`.bmad-core/customizations/`)
2. ✅ Create custom workflows
3. ✅ Optimize document structure
4. ✅ Master quality gate management

---

## Resources

### Documentation
- **User Guide**: `.bmad-core/user-guide.md`
- **Working in Brownfield**: `.bmad-core/working-in-the-brownfield.md`
- **Core Config**: `.bmad-core/core-config.yaml`

### Project Documentation
- **Architecture**: `docs/architecture.md` (sharded to `docs/architecture/`)
- **PRD**: `docs/prd.md` (sharded to `docs/prd/`)
- **Stories**: `docs/stories/`

### Help
- **Discord**: [BMadCode Community](https://discord.gg/gk8jAdXWmj)
- **GitHub**: [BMad Method Repository](https://github.com/bmadcode/bmad-method)
- **YouTube**: [BMadCode Channel](https://www.youtube.com/@BMadCode)

---

## Quick Reference Card

### Agent Activation
```
@agent-name {command}
```

### Essential Commands
```
@bmad-master *help
@qa *risk {story}
@qa *review {story}
@dev Implement {feature}
@sm Create story for {feature}
```

### File Locations
```
PRD:              docs/prd.md
Architecture:     docs/architecture.md
Stories:          docs/stories/
QA Assessments:   docs/qa/assessments/
QA Gates:         docs/qa/gates/
```

### Workflow Tracks
```
Quick Flow:    Bug fixes, small features
BMad Method:   Standard development (YOU ARE HERE)
Enterprise:    Complex/compliance projects
```

---

## Next Steps

1. **Try it out**: Run `@bmad-master *help` to see all commands
2. **Read the workflow**: Check `.bmad-core/workflows/brownfield-fullstack.yaml`
3. **Review existing stories**: Look at `docs/stories/` for examples
4. **Start small**: Create a simple story and implement it
5. **Learn QA**: Run `@qa *risk` on your next story

**Welcome to BMAD development! 🚀**

