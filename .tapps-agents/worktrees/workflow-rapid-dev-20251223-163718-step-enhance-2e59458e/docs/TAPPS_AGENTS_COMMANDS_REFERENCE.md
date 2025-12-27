# TappsCodingAgents Commands and Prompts Reference

**Complete reference guide for all TappsCodingAgents commands, prompts, and when to use each.**

---

## Table of Contents

1. [Simple Mode Commands](#simple-mode-commands)
2. [Workflow Presets](#workflow-presets)
3. [Top-Level Commands](#top-level-commands)
4. [Agent Commands](#agent-commands)
   - [Analyst](#analyst-agent)
   - [Architect](#architect-agent)
   - [Debugger](#debugger-agent)
   - [Designer](#designer-agent)
   - [Documenter](#documenter-agent)
   - [Enhancer](#enhancer-agent)
   - [Implementer](#implementer-agent)
   - [Improver](#improver-agent)
   - [Ops](#ops-agent)
   - [Orchestrator](#orchestrator-agent)
   - [Planner](#planner-agent)
   - [Reviewer](#reviewer-agent)
   - [Tester](#tester-agent)
5. [Command Entry Points](#command-entry-points)
6. [Quick Decision Guide](#quick-decision-guide)

---

## Simple Mode Commands

Simple Mode provides natural language commands that automatically orchestrate multiple agents.

### `@simple-mode *build "{description}"`

**Purpose:** Create new features with full workflow orchestration

**When to Use:**
- Building new features from scratch
- Implementing well-defined requirements
- Standard feature development
- Sprint work

**What It Does:**
- Orchestrates: enhancer → planner → architect → designer → implementer → reviewer → tester
- Automatically ensures quality gates are met
- Generates tests and documentation

**Example:**
```bash
@simple-mode *build "Create user authentication with JWT tokens"
@simple-mode *build "Add REST API endpoint for user profile management"
```

---

### `@simple-mode *review {file}`

**Purpose:** Review code quality with comprehensive analysis

**When to Use:**
- Before committing code
- After code changes
- During pull request reviews
- Quality audits

**What It Does:**
- Orchestrates: reviewer → improver (if issues found)
- Provides comprehensive feedback
- Identifies bugs, security issues, performance problems

**Example:**
```bash
@simple-mode *review services/websocket-ingestion/src/main.py
@simple-mode *review src/api/auth.py
```

---

### `@simple-mode *test {file}`

**Purpose:** Generate and run tests automatically

**When to Use:**
- After implementing code
- Before commits
- When adding new tests
- Ensuring test coverage

**What It Does:**
- Generates comprehensive tests (unit + integration)
- Automatically runs tests
- Reports results and coverage

**Example:**
```bash
@simple-mode *test services/data-api/src/main.py
@simple-mode *test src/models/user.py
```

---

### `@simple-mode *fix {file} "{description}"`

**Purpose:** Fix bugs and errors with structured debugging

**When to Use:**
- Encountering errors
- Fixing bugs
- Addressing issues
- Debugging problems

**What It Does:**
- Orchestrates: debugger → implementer → tester
- Structured debugging and fixing
- Ensures fixes don't break existing functionality

**Example:**
```bash
@simple-mode *fix services/data-api/src/main.py "Fix connection timeout error"
@simple-mode *fix src/utils.py "Fix KeyError when user_id is missing"
```

---

### `@simple-mode *full "{description}"`

**Purpose:** Full SDLC workflow with testing and development loopbacks

**When to Use:**
- Enterprise projects
- Complex features requiring complete lifecycle
- Compliance-heavy systems
- New applications

**What It Does:**
- Complete SDLC pipeline: requirements → architecture → implementation → testing → documentation
- Automatic loopbacks if quality scores aren't met
- Test execution with retry logic
- Security validation with remediation

**Example:**
```bash
@simple-mode *full "Build complete REST API for inventory management"
@simple-mode *full "Create microservices architecture for e-commerce"
```

---

## Workflow Presets

Workflow presets orchestrate multiple agents in sequence for common development scenarios.

### `workflow full` / `workflow enterprise`

**Command:**
```bash
python -m tapps_agents.cli workflow full --prompt "{description}" --auto
python -m tapps_agents.cli workflow enterprise --prompt "{description}" --auto
```

**When to Use:**
- Enterprise projects
- New applications
- Complex features
- Compliance-heavy systems
- Mission-critical projects

**Quality Gates:**
- Overall score: ≥70
- Security: ≥7.0
- Maintainability: ≥7.0

**Agents:** Analyst → Planner → Architect → Designer → Implementer → Reviewer → Tester → Ops → Documenter

**Example:**
```bash
python -m tapps_agents.cli workflow full --prompt "Build a microservices e-commerce platform" --auto
```

---

### `workflow rapid` / `workflow feature`

**Command:**
```bash
python -m tapps_agents.cli workflow rapid --prompt "{description}" --auto
python -m tapps_agents.cli workflow feature --prompt "{description}" --auto
```

**When to Use:**
- Feature development
- Sprint work
- Well-understood features
- Iterative development
- Tight deadlines

**Quality Gates:**
- Overall score: ≥65
- Security: ≥6.5

**Agents:** Enhancer → Planner → Implementer → Reviewer → Tester

**Example:**
```bash
python -m tapps_agents.cli workflow rapid --prompt "Add user profile editing" --auto
```

---

### `workflow fix` / `workflow refactor`

**Command:**
```bash
python -m tapps_agents.cli workflow fix --file {file} --auto
python -m tapps_agents.cli workflow refactor --file {file} --auto
```

**When to Use:**
- Bug fixes
- Technical debt reduction
- Code refactoring
- Maintenance work
- Existing codebases

**Quality Gates:**
- Overall score: ≥70
- Maintainability: ≥7.5

**Agents:** Debugger → Improver → Reviewer → Tester → Documenter

**Example:**
```bash
python -m tapps_agents.cli workflow fix --file src/buggy_module.py --auto
```

---

### `workflow quality` / `workflow improve`

**Command:**
```bash
python -m tapps_agents.cli workflow quality --file {file} --auto
python -m tapps_agents.cli workflow improve --file {file} --auto
```

**When to Use:**
- Code quality improvement initiatives
- Refactoring sprints
- Quality gates
- Improving existing code

**Quality Gates:**
- Overall score: ≥75
- Maintainability: ≥8.0

**Agents:** Reviewer → Improver → Reviewer → Tester

**Example:**
```bash
python -m tapps_agents.cli workflow quality --file src/legacy_code.py --auto
```

---

### `workflow hotfix` / `workflow urgent`

**Command:**
```bash
python -m tapps_agents.cli workflow hotfix --file {file} --auto
python -m tapps_agents.cli workflow urgent --file {file} --auto
```

**When to Use:**
- Critical production bugs (URGENT ONLY)
- Immediate fixes required
- Production incidents

**Quality Gates:**
- Essential tests only

**Agents:** Debugger → Implementer → Tester (minimal)

**Example:**
```bash
python -m tapps_agents.cli workflow hotfix --file example_bug.py --auto
```

---

### `workflow new-feature`

**Command:**
```bash
python -m tapps_agents.cli workflow new-feature --prompt "{description}" --auto
```

**When to Use:**
- Building new features quickly
- Standard feature development
- Well-understood requirements

**Quality Gates:**
- Overall ≥65
- Security ≥6.5

**Agents:** Enhancer → Planner → Implementer → Reviewer → Tester

**Example:**
```bash
python -m tapps_agents.cli workflow new-feature --prompt "Add user authentication" --auto
```

---

### `workflow list`

**Command:**
```bash
python -m tapps_agents.cli workflow list
```

**When to Use:**
- Discovering available workflows
- Understanding workflow differences
- Finding the right workflow for your task

**What It Does:**
- Lists all available workflow presets
- Shows descriptions and use cases
- Displays quality gates and agent sequences

---

### `workflow recommend`

**Command:**
```bash
python -m tapps_agents.cli workflow recommend
python -m tapps_agents.cli workflow recommend --non-interactive --format json
```

**When to Use:**
- Unsure which workflow to use
- Starting a new task
- Getting AI-powered recommendations

**What It Does:**
- Analyzes project context
- Examines codebase state
- Recommends appropriate workflow
- Optionally auto-starts recommended workflow

---

### `workflow state {command}`

**Command:**
```bash
python -m tapps_agents.cli workflow state list
python -m tapps_agents.cli workflow state show {workflow_id}
python -m tapps_agents.cli workflow state cleanup --retention-days 30
python -m tapps_agents.cli workflow resume --workflow-id {id}
```

**When to Use:**
- Managing workflow state persistence
- Resuming interrupted workflows
- Inspecting workflow progress
- Cleaning up old states

---

## Top-Level Commands

### `create "{description}"`

**Command:**
```bash
python -m tapps_agents.cli create "Build a task management web app with React and FastAPI"
python -m tapps_agents.cli create "{description}" --workflow rapid
```

**When to Use:**
- Creating new projects from scratch (PRIMARY USE CASE)
- Building complete applications
- Starting greenfield projects

**What It Does:**
- Shortcut for `workflow full --auto --prompt`
- Executes fully automated SDLC pipeline
- Creates complete, tested application

**Options:**
- `--workflow {full|rapid|enterprise|feature}` - Choose workflow preset (default: full)
- `--cursor-mode` - Run in Cursor mode (uses Background Agents)

---

### `score {file}`

**Command:**
```bash
python -m tapps_agents.cli score src/main.py
python -m tapps_agents.cli score src/main.py --format json
```

**When to Use:**
- Quick quality checks
- CI/CD pipelines
- Fast objective metrics
- Pre-commit checks

**What It Does:**
- Quick shortcut for `reviewer score`
- Fast objective metrics (no LLM calls)
- Returns scores: Overall, Complexity, Security, Maintainability, Test Coverage

---

### `init`

**Command:**
```bash
python -m tapps_agents.cli init
python -m tapps_agents.cli init --no-rules --no-presets
```

**When to Use:**
- Initializing new projects
- Setting up TappsCodingAgents configuration
- First-time project setup

**What It Does:**
- Sets up Cursor Rules (.cursor/rules/)
- Creates workflow presets (workflows/presets/)
- Creates configuration (.tapps-agents/config.yaml)
- Installs Cursor Skills (.claude/skills/)
- Sets up Background Agents (.cursor/background-agents.yaml)

**Options:**
- `--no-rules` - Skip Cursor Rules
- `--no-presets` - Skip workflow presets
- `--no-config` - Skip configuration
- `--no-skills` - Skip Cursor Skills
- `--no-background-agents` - Skip Background Agents
- `--no-cache` - Skip Context7 cache
- `--no-cursorignore` - Skip .cursorignore

---

### `doctor`

**Command:**
```bash
python -m tapps_agents.cli doctor
python -m tapps_agents.cli doctor --format json
```

**When to Use:**
- Validating local environment
- Diagnosing setup issues
- Checking tool availability
- Troubleshooting

**What It Does:**
- Checks Python version and dependencies
- Validates required tools (ruff, mypy, pytest, etc.)
- Checks configuration files
- Verifies Cursor integration components
- Validates file permissions

---

### `health {command}`

**Command:**
```bash
python -m tapps_agents.cli health check
python -m tapps_agents.cli health dashboard
python -m tapps_agents.cli health metrics --check-name environment
python -m tapps_agents.cli health trends --check-name execution --days 7
```

**When to Use:**
- Comprehensive health checks
- Monitoring system status
- Tracking health trends
- Diagnosing issues

**Subcommands:**
- `check` - Run health checks (environment, automation, execution, context7_cache, knowledge_base, governance, outcomes)
- `dashboard` - Display health dashboard
- `metrics` - Show stored health metrics
- `trends` - Show health trends over time

---

### `setup-experts {command}`

**Command:**
```bash
python -m tapps_agents.cli setup-experts init
python -m tapps_agents.cli setup-experts add
python -m tapps_agents.cli setup-experts remove
python -m tapps_agents.cli setup-experts list
```

**When to Use:**
- Configuring Industry Experts
- Adding domain-specific knowledge
- Setting up expert consultation

**What It Does:**
- Interactive wizard for expert configuration
- Manages .tapps-agents/experts.yaml
- Adds/removes domain experts

---

### `analytics {command}`

**Command:**
```bash
python -m tapps_agents.cli analytics dashboard
python -m tapps_agents.cli analytics agents --agent-id reviewer
python -m tapps_agents.cli analytics workflows --workflow-id {id}
python -m tapps_agents.cli analytics trends --metric-type agent_duration --days 30
python -m tapps_agents.cli analytics system
```

**When to Use:**
- Monitoring agent performance
- Tracking workflow metrics
- Analyzing historical trends
- System status monitoring

**Subcommands:**
- `dashboard` - Comprehensive analytics dashboard
- `agents` - Agent performance metrics
- `workflows` - Workflow performance metrics
- `trends` - Historical trends and patterns
- `system` - System status and resource usage

---

### `hardware-profile` / `hardware`

**Command:**
```bash
python -m tapps_agents.cli hardware-profile
python -m tapps_agents.cli hardware --set workstation
```

**When to Use:**
- Checking hardware configuration
- Optimizing performance
- Setting hardware profile

**What It Does:**
- Displays current hardware metrics
- Detects hardware profile (NUC, Development, Workstation, Server)
- Optimizes resource usage based on profile

---

## Agent Commands

### Analyst Agent

**Purpose:** Requirements gathering, stakeholder analysis, technology research

#### `analyst gather-requirements "{description}"`

**When to Use:**
- Starting new projects
- Gathering requirements
- Project initiation
- Requirements documentation

**Example:**
```bash
python -m tapps_agents.cli analyst gather-requirements "Build a REST API for inventory management"
python -m tapps_agents.cli analyst gather-requirements "E-commerce platform" --context "Must support 10k users"
```

**Options:**
- `--context` - Additional context or constraints
- `--output-file` - Save requirements to file

---

#### `analyst stakeholder-analysis "{description}"`

**When to Use:**
- Beginning of projects
- Understanding stakeholders
- Managing expectations
- Identifying conflicts

**Example:**
```bash
python -m tapps_agents.cli analyst stakeholder-analysis "Payment processing feature"
python -m tapps_agents.cli analyst stakeholder-analysis "User authentication system" --stakeholders product-owner end-users devops-team
```

**Options:**
- `--stakeholders` - List of known stakeholders

---

#### `analyst tech-research "{requirement}"`

**When to Use:**
- Technology selection
- Evaluating options
- Making technology decisions
- Researching solutions

**Example:**
```bash
python -m tapps_agents.cli analyst tech-research "Database for high-traffic web app"
python -m tapps_agents.cli analyst tech-research "Authentication solution" --criteria security scalability
```

**Options:**
- `--context` - Project context
- `--criteria` - Evaluation criteria (performance, security, scalability, etc.)

---

#### `analyst estimate-effort "{description}"`

**When to Use:**
- Planning features
- Sprint planning
- Effort estimation
- Complexity assessment

**Example:**
```bash
python -m tapps_agents.cli analyst estimate-effort "Add payment processing"
```

---

### Architect Agent

**Purpose:** System architecture design, technology selection, diagrams

#### `architect design-system "{requirements}"`

**When to Use:**
- Designing new systems
- Creating architecture
- System design
- Architecture documentation

**Example:**
```bash
python -m tapps_agents.cli architect design-system "Microservices e-commerce platform"
python -m tapps_agents.cli architect design-system "Real-time chat application" --output-file architecture.md
```

**Options:**
- `--context` - Additional context
- `--output-file` - Save architecture to file

---

#### `architect architecture-diagram "{description}"`

**When to Use:**
- Creating visual diagrams
- Documentation
- System visualization
- Architecture communication

**Example:**
```bash
python -m tapps_agents.cli architect architecture-diagram "E-commerce system with microservices" --diagram-type component
python -m tapps_agents.cli architect architecture-diagram "User login flow" --diagram-type sequence
```

**Options:**
- `--diagram-type` - component, sequence, or deployment (default: component)
- `--output-file` - Save diagram to file

---

#### `architect tech-selection "{component_description}"`

**When to Use:**
- Technology decisions
- Selecting components
- Evaluating options
- Making architectural choices

**Example:**
```bash
python -m tapps_agents.cli architect tech-selection "Message queue for event processing"
python -m tapps_agents.cli architect tech-selection "API gateway" --requirements horizontal-scaling --constraints budget-limited
```

**Options:**
- `--requirements` - Specific requirements
- `--constraints` - Constraints (budget-limited, compliance-required, etc.)

---

#### `architect design-security "{system_description}"`

**When to Use:**
- Security architecture design
- Security planning
- Compliance requirements
- Security controls

**Example:**
```bash
python -m tapps_agents.cli architect design-security "Payment processing system"
```

---

### Debugger Agent

**Purpose:** Error debugging, stack trace analysis, code tracing

#### `debugger debug "{error_message}"`

**When to Use:**
- Debugging errors
- Understanding exceptions
- Finding root causes
- Error analysis

**Example:**
```bash
python -m tapps_agents.cli debugger debug "KeyError: 'user_id'" --file src/api.py --line 42
python -m tapps_agents.cli debugger debug "Connection timeout" --stack-trace "traceback.txt"
```

**Options:**
- `--file` - Source file where error occurred
- `--line` - Line number
- `--stack-trace` - Stack trace file or text

---

#### `debugger analyze-error "{error_message}"`

**When to Use:**
- Detailed error analysis
- Complex errors
- Root cause analysis
- In-depth debugging

**Example:**
```bash
python -m tapps_agents.cli debugger analyze-error "ValueError: invalid literal" --stack-trace "traceback.txt"
```

**Options:**
- `--stack-trace` - Stack trace file or text
- `--code-context` - Code context around error

---

#### `debugger trace {file}`

**When to Use:**
- Understanding execution paths
- Finding logic errors
- Code flow analysis
- Control flow tracing

**Example:**
```bash
python -m tapps_agents.cli debugger trace src/main.py --function process_data
```

**Options:**
- `--function` - Function to start tracing from
- `--line` - Line number to start from

---

### Designer Agent

**Purpose:** API design, data models, UI/UX design, wireframes

#### `designer api-design "{description}"`

**When to Use:**
- Designing REST APIs
- Creating API specifications
- API documentation
- Interface design

**Example:**
```bash
python -m tapps_agents.cli designer api-design "User management API"
python -m tapps_agents.cli designer api-design "Payment processing API" --api-type REST
```

**Options:**
- `--api-type` - REST, GraphQL, etc.

---

#### `designer design-model "{description}"`

**When to Use:**
- Data model design
- Database schema design
- Entity design
- Model specifications

**Example:**
```bash
python -m tapps_agents.cli designer design-model "Product catalog data model"
```

---

### Documenter Agent

**Purpose:** Documentation generation, API docs, README creation

#### `documenter document-api {file}`

**When to Use:**
- Generating API documentation
- Creating API docs
- Documenting endpoints
- API reference

**Example:**
```bash
python -m tapps_agents.cli documenter document-api src/api.py
```

---

#### `documenter generate-readme {path}`

**When to Use:**
- Creating README files
- Project documentation
- Setup instructions
- Usage guides

**Example:**
```bash
python -m tapps_agents.cli documenter generate-readme .
```

---

#### `documenter document-code {file}`

**When to Use:**
- Code documentation
- Docstring generation
- Function documentation
- Code comments

**Example:**
```bash
python -m tapps_agents.cli documenter document-code src/service.py
```

---

### Enhancer Agent

**Purpose:** Prompt enhancement, specification generation

#### `enhancer enhance "{prompt}"`

**When to Use:**
- Enhancing simple prompts
- Creating detailed specifications
- Enriching requirements
- Before implementation

**Example:**
```bash
python -m tapps_agents.cli enhancer enhance "Add user authentication"
python -m tapps_agents.cli enhancer enhance "Build a todo app" --format json --output spec.json
```

**Options:**
- `--format` - markdown, json, yaml (default: markdown)
- `--output` - Output file path
- `--config` - Custom enhancement configuration

---

#### `enhancer enhance-quick "{prompt}"`

**When to Use:**
- Quick prompt enhancement
- Fast specification
- Initial planning
- Quick iteration

**Example:**
```bash
python -m tapps_agents.cli enhancer enhance-quick "Add user authentication"
```

**Options:**
- `--format` - markdown, json, yaml
- `--output` - Output file path

---

#### `enhancer enhance-stage {stage} --prompt "{prompt}"`

**When to Use:**
- Running specific enhancement stages
- Stage-by-stage enhancement
- Custom enhancement flow

**Example:**
```bash
python -m tapps_agents.cli enhancer enhance-stage analysis "Create payment system"
python -m tapps_agents.cli enhancer enhance-stage requirements "Create payment system"
```

**Stages:** analysis, requirements, architecture, implementation, testing, documentation

---

#### `enhancer enhance-resume {session_id}`

**When to Use:**
- Resuming interrupted enhancements
- Continuing from saved session
- Re-running stages

**Example:**
```bash
python -m tapps_agents.cli enhancer enhance-resume {session_id}
```

---

### Implementer Agent

**Purpose:** Code generation, implementation, refactoring

#### `implementer implement "{specification}" {file_path}`

**When to Use:**
- Implementing new features
- Generating code
- Creating new files
- Writing production code

**Example:**
```bash
python -m tapps_agents.cli implementer implement "Create a User model with email and name fields" src/models/user.py
python -m tapps_agents.cli implementer implement "Add authentication endpoint" src/api/auth.py --context "Use JWT tokens"
```

**Options:**
- `--context` - Additional context
- `--language` - Programming language (default: python)
- `--format` - json, text (default: json)

---

#### `implementer generate-code "{specification}"`

**When to Use:**
- Previewing code before writing
- Generating code snippets
- Testing specifications
- Getting code suggestions

**Example:**
```bash
python -m tapps_agents.cli implementer generate-code "Create a function to validate email addresses"
python -m tapps_agents.cli implementer generate-code "Add error handling" --file src/api.py
```

**Options:**
- `--file` - Existing file for context
- `--context` - Additional context
- `--language` - Programming language
- `--format` - json, text

---

#### `implementer refactor {file_path} "{instruction}"`

**When to Use:**
- Refactoring code
- Improving code structure
- Applying design patterns
- Fixing code smells

**Example:**
```bash
python -m tapps_agents.cli implementer refactor src/utils.py "Extract common logic into helper functions"
python -m tapps_agents.cli implementer refactor src/api.py "Apply dependency injection pattern"
```

**Options:**
- `--format` - json, text (default: json)

---

### Improver Agent

**Purpose:** Code refactoring, optimization, quality improvement

#### `improver improve-quality {file}`

**When to Use:**
- General code improvements
- Quality enhancement
- Addressing multiple quality aspects
- Code modernization

**Example:**
```bash
python -m tapps_agents.cli improver improve-quality src/service.py
```

---

#### `improver refactor {file} "{instruction}"`

**When to Use:**
- Specific refactoring goals
- Targeted improvements
- Pattern application
- Structure improvements

**Example:**
```bash
python -m tapps_agents.cli improver refactor src/utils.py "Extract common logic into helper functions"
```

---

#### `improver optimize {file}`

**When to Use:**
- Performance optimization
- Memory optimization
- Performance-critical code
- Optimization initiatives

**Example:**
```bash
python -m tapps_agents.cli improver optimize src/processor.py --type both
```

**Options:**
- `--type` - performance, memory, or both

---

### Ops Agent

**Purpose:** Security scanning, compliance checks, deployment

#### `ops security-scan --target {path}`

**When to Use:**
- Security audits
- Pre-deployment checks
- Vulnerability detection
- Security reviews

**Example:**
```bash
python -m tapps_agents.cli ops security-scan --target src/ --type all
```

**Options:**
- `--type` - all, sql-injection, xss, secrets, etc.

---

#### `ops compliance-check --type {standard}`

**When to Use:**
- Compliance audits
- Regulatory requirements
- Compliance validation
- Standards compliance

**Example:**
```bash
python -m tapps_agents.cli ops compliance-check --type GDPR
python -m tapps_agents.cli ops compliance-check --type HIPAA
```

---

#### `ops audit-dependencies`

**When to Use:**
- Dependency security audits
- Vulnerability scanning
- Dependency reviews
- Security checks

**Example:**
```bash
python -m tapps_agents.cli ops audit-dependencies --severity-threshold high
```

**Options:**
- `--severity-threshold` - low, medium, high, critical

---

### Orchestrator Agent

**Purpose:** Workflow management, step coordination, gate decisions

#### `orchestrator workflow-list`

**When to Use:**
- Discovering available workflows
- Understanding workflow options
- Workflow selection

**Example:**
```bash
python -m tapps_agents.cli orchestrator workflow-list
```

---

#### `orchestrator workflow-start {workflow_id}`

**When to Use:**
- Starting workflow execution
- Manual workflow launch
- Workflow coordination

**Example:**
```bash
python -m tapps_agents.cli orchestrator workflow-start {workflow_id}
```

---

#### `orchestrator workflow-status`

**When to Use:**
- Checking workflow progress
- Monitoring execution
- Status updates

**Example:**
```bash
python -m tapps_agents.cli orchestrator workflow-status
```

---

#### `orchestrator gate --condition "{condition}"`

**When to Use:**
- Making gate decisions
- Workflow control flow
- Conditional execution
- Quality gates

**Example:**
```bash
python -m tapps_agents.cli orchestrator gate --condition "score > 80"
```

**Options:**
- `--condition` - Gate condition expression
- `--scoring-data` - JSON string with scoring data

---

### Planner Agent

**Purpose:** Create plans, user stories, task breakdowns

#### `planner plan "{description}"`

**When to Use:**
- Creating feature plans
- Planning implementations
- Task breakdown
- Sprint planning

**Example:**
```bash
python -m tapps_agents.cli planner plan "Add user authentication with OAuth"
python -m tapps_agents.cli planner plan "Implement shopping cart" --format text
```

**Options:**
- `--format` - json, text (default: json)

---

#### `planner create-story "{description}"`

**When to Use:**
- Generating user stories
- Story creation
- Feature documentation
- Agile planning

**Example:**
```bash
python -m tapps_agents.cli planner create-story "User login functionality"
python -m tapps_agents.cli planner create-story "Export data to CSV" --epic "Data Management" --priority high
```

**Options:**
- `--epic` - Epic name
- `--priority` - high, medium, low (default: medium)
- `--format` - json, text

---

#### `planner list-stories`

**When to Use:**
- Viewing user stories
- Story management
- Filtering stories
- Story tracking

**Example:**
```bash
python -m tapps_agents.cli planner list-stories
python -m tapps_agents.cli planner list-stories --epic "Authentication" --status todo
```

**Options:**
- `--epic` - Filter by epic
- `--status` - Filter by status (todo, in-progress, done)
- `--format` - json, text

---

### Reviewer Agent

**Purpose:** Code review, quality analysis, scoring

#### `reviewer review {file}`

**When to Use:**
- Comprehensive code review
- Pre-commit reviews
- PR reviews
- Quality audits

**Example:**
```bash
python -m tapps_agents.cli reviewer review src/app.py
python -m tapps_agents.cli reviewer review src/app.py --format json
python -m tapps_agents.cli reviewer review file1.py file2.py file3.py
python -m tapps_agents.cli reviewer review --pattern "**/*.py" --max-workers 8
```

**Options:**
- `--pattern` - Glob pattern for multiple files
- `--max-workers` - Concurrent operations (default: 4)
- `--format` - json, text, markdown, html (default: json)
- `--output` - Output file path

---

#### `reviewer score {file}`

**When to Use:**
- Quick quality checks
- CI/CD pipelines
- Fast objective metrics
- Quality scoring

**Example:**
```bash
python -m tapps_agents.cli reviewer score src/utils.py
python -m tapps_agents.cli reviewer score src/utils.py --format text
python -m tapps_agents.cli reviewer score file1.py file2.py file3.py
python -m tapps_agents.cli reviewer score --pattern "**/*.py" --max-workers 8
```

**Options:**
- `--pattern` - Glob pattern
- `--max-workers` - Concurrent operations
- `--format` - json, text, markdown, html
- `--output` - Output file path

---

#### `reviewer lint {file}`

**When to Use:**
- Style checks
- Code smell detection
- PEP 8 validation
- Linting

**Example:**
```bash
python -m tapps_agents.cli reviewer lint src/main.py
python -m tapps_agents.cli reviewer lint src/main.py --format text
python -m tapps_agents.cli reviewer lint --pattern "**/*.py" --max-workers 8
```

**Options:**
- `--pattern` - Glob pattern
- `--max-workers` - Concurrent operations
- `--format` - json, text
- `--output` - Output file path

---

#### `reviewer type-check {file}`

**When to Use:**
- Type safety validation
- Type annotation checks
- Type error detection
- mypy validation

**Example:**
```bash
python -m tapps_agents.cli reviewer type-check src/models.py
python -m tapps_agents.cli reviewer type-check src/models.py --format text
```

**Options:**
- `--pattern` - Glob pattern
- `--max-workers` - Concurrent operations
- `--format` - json, text
- `--output` - Output file path

---

#### `reviewer report {target} {formats}`

**When to Use:**
- Project-wide quality assessment
- Comprehensive reports
- Quality documentation
- Multiple format reports

**Example:**
```bash
python -m tapps_agents.cli reviewer report src/ json markdown
python -m tapps_agents.cli reviewer report src/ --formats all --output-dir reports/
```

**Options:**
- `formats` - json, markdown, html, all
- `--output-dir` - Output directory (default: reports/quality/)

---

#### `reviewer duplication {target}`

**When to Use:**
- Detecting code duplication
- Refactoring opportunities
- Maintainability analysis
- Duplication detection

**Example:**
```bash
python -m tapps_agents.cli reviewer duplication src/
python -m tapps_agents.cli reviewer duplication src/utils.py --format text
```

**Options:**
- `--format` - json, text (default: json)

---

#### `reviewer analyze-project`

**When to Use:**
- Comprehensive project analysis
- Quality initiatives
- Technical debt assessment
- Project-wide metrics

**Example:**
```bash
python -m tapps_agents.cli reviewer analyze-project
python -m tapps_agents.cli reviewer analyze-project --project-root /path/to/project --format json
```

**Options:**
- `--project-root` - Project root directory
- `--no-comparison` - Skip comparison with previous analysis
- `--format` - json, text

---

#### `reviewer analyze-services {services}`

**When to Use:**
- Targeted service analysis
- Large project analysis
- Service-specific metrics
- Module analysis

**Example:**
```bash
python -m tapps_agents.cli reviewer analyze-services api auth
python -m tapps_agents.cli reviewer analyze-services --project-root /path/to/project
```

**Options:**
- `services` - Space-separated list of service names
- `--project-root` - Project root directory
- `--no-comparison` - Skip comparison
- `--format` - json, text

---

### Tester Agent

**Purpose:** Test generation, execution, coverage

#### `tester test {file}`

**When to Use:**
- Generating and running tests
- New code testing
- Test coverage
- Comprehensive testing

**Example:**
```bash
python -m tapps_agents.cli tester test src/utils.py
python -m tapps_agents.cli tester test src/api.py --test-file tests/test_api.py --integration
```

**Options:**
- `--test-file` - Path for generated test file
- `--integration` - Generate integration tests too

---

#### `tester generate-tests {file}`

**When to Use:**
- Generating tests without running
- Reviewing tests before execution
- Batch test generation
- CI/CD integration

**Example:**
```bash
python -m tapps_agents.cli tester generate-tests src/models.py
python -m tapps_agents.cli tester generate-tests src/api.py --test-file tests/test_api.py
```

**Options:**
- `--test-file` - Path for generated test file
- `--integration` - Generate integration tests

---

#### `tester run-tests {test_path}`

**When to Use:**
- Running existing tests
- Continuous testing
- Coverage validation
- Test execution

**Example:**
```bash
python -m tapps_agents.cli tester run-tests
python -m tapps_agents.cli tester run-tests tests/unit/
python -m tapps_agents.cli tester run-tests --no-coverage
```

**Options:**
- `test_path` - Test file, directory, or pattern (default: tests/)
- `--no-coverage` - Skip coverage analysis

---

## Command Entry Points

Both entry points are supported:

```bash
# Installed console script
tapps-agents {command}

# Module invocation
python -m tapps_agents.cli {command}
```

**Examples:**
```bash
tapps-agents reviewer review src/app.py
python -m tapps_agents.cli reviewer review src/app.py
```

---

## Quick Decision Guide

### When to Use Simple Mode

✅ **Use Simple Mode for:**
- Standard development tasks (build, review, test, fix)
- Automatic orchestration
- Quality gates enforcement
- Working in Cursor AI

**Commands:**
- `@simple-mode *build "{description}"` - New features
- `@simple-mode *review {file}` - Code reviews
- `@simple-mode *test {file}` - Test generation
- `@simple-mode *fix {file} "{description}"` - Bug fixes
- `@simple-mode *full "{description}"` - Full SDLC

---

### When to Use Workflow Presets

✅ **Use Workflow Presets for:**
- Complete development workflows
- Multi-agent orchestration
- Automated quality gates
- Standard development patterns

**Commands:**
- `workflow full` - Enterprise projects
- `workflow rapid` - Feature development
- `workflow fix` - Bug fixes
- `workflow quality` - Quality improvement
- `workflow hotfix` - Urgent fixes

---

### When to Use Direct Agent Commands

✅ **Use Direct Agent Commands for:**
- Specific agent capabilities
- Fine-grained control
- CI/CD pipelines
- Batch processing
- Single-step operations

**Examples:**
- `reviewer score {file}` - Quick quality check
- `enhancer enhance-quick "{prompt}"` - Fast enhancement
- `debugger analyze-error "{error}"` - Error analysis
- `tester generate-tests {file}` - Test generation only

---

## Quality Thresholds

**All code MUST meet these thresholds:**

- **Overall Quality Score:** ≥ 70 (≥ 80 for critical services)
- **Security Score:** ≥ 7.0/10
- **Maintainability Score:** ≥ 7.0/10
- **Test Coverage:** ≥ 80% (target)
- **Complexity Score:** ≤ 7.0/10 (lower is better)

**If thresholds not met:**
1. Run `improver improve-quality {file}` to address issues
2. Re-run `reviewer review {file}` to verify
3. Loop until thresholds are met

---

## Related Documentation

- [TappsCodingAgents Command Guide](.cursor/rules/tapps-agents-command-guide.mdc) - Complete command guide
- [Simple Mode Guide](.cursor/rules/simple-mode.mdc) - Simple Mode usage
- [Agent Capabilities](.cursor/rules/agent-capabilities.mdc) - Detailed agent capabilities
- [Workflow Selection Guide](.cursor/rules/tapps-agents-workflow-selection.mdc) - When to use which workflow
- [Quick Reference](docs/TAPPS_AGENTS_QUICK_REFERENCE.md) - Quick decision guide

---

**Last Updated:** January 2025

