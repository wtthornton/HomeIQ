# Code Review Guide 2025

**Last Updated:** December 2025  
**Purpose:** Comprehensive code review standards and practices for AI agents and developers  
**Target Audience:** AI agents performing code reviews, QA team, developers  
**Integration:** BMAD QA workflows, Progressive Reviews, Quality Gates

## Table of Contents

1. [Overview](#overview)
2. [2025 Best Practices](#2025-best-practices)
3. [Review Scope and Timing](#review-scope-and-timing)
4. [Review Dimensions](#review-dimensions)
5. [Project-Specific Standards](#project-specific-standards)
6. [Agent Guidelines](#agent-guidelines)
7. [Checklists](#checklists)
8. [Review Workflows](#review-workflows)
9. [Quality Gate Integration](#quality-gate-integration)

---

## Overview

This guide provides comprehensive standards for conducting code reviews in 2025, specifically designed for AI agents and integrated with the HomeIQ project's BMAD workflows. It combines industry best practices with project-specific patterns and standards.

### Core Principles

1. **Context-Aware Reviews** - Understand the full picture before reviewing
2. **Actionable Feedback** - Provide specific, fixable recommendations
3. **Risk-Based Prioritization** - Focus on critical issues first
4. **Active Refactoring** - Improve code directly when safe
5. **Continuous Learning** - Document patterns for team knowledge
6. **Time-Boxed Efficiency** - Complete reviews within 60-90 minutes
7. **AI-Assisted Analysis** - Leverage automation for routine checks
8. **Positive Collaboration** - Reviews are opportunities for growth

### Review Types

This guide supports three review types:

1. **Progressive Task Reviews** - After each task completion (5-10 min)
2. **Story Reviews** - When story marked "Ready for Review" (60-90 min)
3. **Comprehensive Reviews** - High-risk or complex changes (90+ min)

---

## 2025 Best Practices

### 1. Manageable Review Scope

**2025 Standard:** Limit reviews to 200-400 lines of code (LoC) per session.

**Application:**
- For changes >400 LoC, split into multiple review sessions
- Focus on logical units (feature, service, component)
- If diff >500 lines, escalate to deep review automatically
- Progressive reviews handle smaller increments (task-level)

**Agent Action:**
```yaml
if lines_changed > 400:
    recommendation: "Consider splitting this into multiple reviews"
    focus: "Review in logical chunks (e.g., service layer, then API layer)"
```

### 2. Automated Routine Checks

**2025 Standard:** Automate formatting, style, basic security, and dependency checks.

**Current Automation:**
- **Python:** Ruff (linting, formatting), mypy (type checking), Radon (complexity)
- **TypeScript:** ESLint (linting, complexity), TypeScript (type checking)
- **Security:** Static analysis patterns, dependency scanning
- **Performance:** Pattern detection (blocking async, N+1 queries, unbatched writes)

**Agent Action:**
- Run automated checks FIRST before manual review
- Only review manually after automated checks pass
- Reference automated output in review comments

### 3. Time-Boxed Review Sessions

**2025 Standard:** Complete reviews within 60-90 minute sessions.

**Application:**
- Set explicit time limits per review
- Focus on highest-risk areas first
- Defer non-critical improvements to follow-up
- Use progressive reviews to prevent overwhelming sessions

**Agent Action:**
```yaml
review_priority:
  first_30_min: [security, critical_bugs, architecture]
  next_30_min: [performance, testing, standards]
  final_30_min: [code_quality, documentation, optimization]
```

### 4. Constructive and Specific Feedback

**2025 Standard:** Provide clear, actionable feedback with reasoning.

**Feedback Format:**
```markdown
**Issue:** [What's wrong]

**Location:** `file:line`

**Current Code:**
```python
# Show actual code
```

**Recommendation:**
```python
# Show improved code
```

**Reasoning:** [Why this change matters]

**Priority:** [HIGH/MEDIUM/LOW]
```

**Agent Action:**
- Always include code examples in feedback
- Explain the "why" behind recommendations
- Link to relevant documentation or standards
- Provide concrete fix suggestions

### 5. Descriptive Context

**2025 Standard:** Require clear commit messages and change descriptions.

**Agent Action:**
- Verify commit messages explain "what" and "why"
- Check that PR/story descriptions include context
- Request clarification if intent is unclear
- Document context in review notes

### 6. Knowledge Sharing

**2025 Standard:** Rotate reviewers and document patterns.

**Application:**
- Document review patterns for team learning
- Share knowledge through review comments
- Create reusable checklists and guides
- Build institutional knowledge

**Agent Action:**
- Document common patterns found
- Create reusable review templates
- Share learnings in review summaries

### 7. AI-Assisted Analysis

**2025 Standard:** Use AI tools for real-time, context-aware analysis.

**Current Tools:**
- Context7 KB for library best practices
- Pattern detection for anti-patterns
- Automated complexity analysis
- Performance pattern recognition

**Agent Action:**
- Use Context7 KB for technology decisions (MANDATORY)
- Leverage pattern detection for common issues
- Cross-reference with project documentation
- Provide contextual recommendations

### 8. Security-First Approach

**2025 Standard:** Security checks are mandatory and non-negotiable.

**Agent Action:**
- Security issues are always HIGH priority
- Always check: auth, input validation, secrets, injection risks
- Reference security standards in feedback
- Block merge on critical security issues

### 9. Positive Review Culture

**2025 Standard:** Reviews are learning opportunities, not criticism.

**Agent Action:**
- Recognize good code patterns
- Provide educational context
- Focus on improvement, not blame
- Celebrate best practices

---

## Review Scope and Timing

### When to Review

#### Progressive Task Reviews (NEW 2025 Pattern)
- **When:** After completing each task within a story
- **Duration:** 5-10 minutes
- **Scope:** Task-specific changes only
- **Focus:** Critical issues that block progress
- **Cost:** $0.30-0.45 per story
- **ROI:** 20x faster fixes (fix while context fresh)

**Trigger Conditions:**
- Task marked complete
- Auto-trigger enabled in config
- Not skipped for documentation/config tasks

#### Story Reviews (Standard)
- **When:** Story marked "Ready for Review"
- **Duration:** 60-90 minutes
- **Scope:** Complete story implementation
- **Focus:** Comprehensive quality assessment
- **Output:** QA Results section + Quality Gate file

**Prerequisites:**
- All tasks completed
- File List updated
- All automated tests passing
- Story status = "Review"

#### Comprehensive Reviews (High-Risk)
- **When:** Auto-escalated for high-risk changes
- **Duration:** 90+ minutes
- **Scope:** Deep architecture and security analysis

**Auto-Escalation Triggers:**
- Auth/payment/security files touched
- No tests added to story
- Diff > 500 lines
- Previous gate was FAIL/CONCERNS
- Story has > 5 acceptance criteria

### What Gets Reviewed

**Priority Order:**

1. **Security** (CRITICAL - Always first)
   - Authentication/authorization bypasses
   - SQL injection, XSS, CSRF risks
   - Exposed secrets or credentials
   - Cryptographic vulnerabilities
   - Input validation failures

2. **Performance** (HIGH - HomeIQ Specific)
   - Blocking async operations (violates "Async Everything")
   - N+1 database queries
   - Unbatched writes (<100 points)
   - Missing caching on expensive operations
   - Unbounded queries (no LIMIT)
   - Synchronous HTTP in async (requests vs aiohttp)

3. **Testing** (MEDIUM)
   - Missing critical path tests
   - Poor edge case coverage
   - Weak error scenario tests
   - Flaky or unreliable tests
   - Inappropriate test levels (unit vs integration vs E2E)

4. **Code Quality** (LOW)
   - High complexity (Radon/ESLint violations)
   - Code duplication (>3%)
   - Poor naming conventions
   - Missing type hints/TypeScript types
   - Inadequate documentation

---

## Review Dimensions

### 1. Security Review

**2025 Security Standards:**

#### Authentication & Authorization
- ✅ Strong password policies (min 12 chars, complexity)
- ✅ Multi-factor authentication support
- ✅ Secure session management (HttpOnly, Secure, SameSite)
- ✅ Proper logout (invalidate tokens/sessions)
- ✅ OAuth 2.0/OIDC for third-party auth
- ✅ Rate limiting on auth endpoints
- ✅ Secure password hashing (bcrypt, argon2, scrypt)
- ✅ Account lockout after failed attempts
- ✅ Secure password reset flows

#### Data Protection
- ✅ No plaintext passwords
- ✅ Strong encryption for sensitive data
- ✅ Proper key management
- ✅ Environment variables for secrets
- ✅ No secrets in version control
- ✅ Parameterized queries (no SQL injection)
- ✅ Input validation on client and server
- ✅ Output encoding (prevent XSS)

#### API Security
- ✅ Token validation (JWT signature, expiry, issuer, audience)
- ✅ Role-based access control (RBAC)
- ✅ Principle of least privilege
- ✅ Request rate limiting
- ✅ CORS configuration
- ✅ Error message sanitization

**Agent Checklist:**
```yaml
security_checks:
  - Check for hardcoded secrets
  - Verify input validation on all endpoints
  - Check for SQL injection risks (parameterized queries)
  - Verify authentication/authorization on protected routes
  - Check for XSS vulnerabilities (output encoding)
  - Verify error messages don't leak sensitive info
  - Check for CSRF protection (if applicable)
  - Verify rate limiting on sensitive endpoints
```

### 2. Performance Review

**HomeIQ-Specific Performance Standards:**

#### Async Everything Pattern
**Violation Detection:**
```python
# ❌ WRONG - Blocking in async
async def fetch_data(url: str):
    response = requests.get(url)  # Blocking!
    return response.json()

# ✅ CORRECT - Async HTTP
async def fetch_data(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

**Agent Check:**
- No `requests` library in async functions
- Use `aiohttp` for async HTTP
- Use `aiosqlite` for async database
- No blocking I/O in async code

#### Database Performance Patterns

**N+1 Query Detection:**
```python
# ❌ WRONG - N+1 queries
for device_id in device_ids:
    device = await db.query(Device).filter(Device.id == device_id).first()
    # Creates N queries

# ✅ CORRECT - Eager loading
devices = await db.query(Device).filter(Device.id.in_(device_ids)).all()
# Single query
```

**Batch Write Detection:**
```python
# ❌ WRONG - Individual writes
for event in events:
    await influxdb.write(event)  # N writes

# ✅ CORRECT - Batched writes
await influxdb.write_batch(events)  # 1 write
```

**Unbounded Query Detection:**
```python
# ❌ WRONG - No LIMIT
results = await db.query(Event).all()

# ✅ CORRECT - Bounded query
results = await db.query(Event).limit(1000).all()
```

#### Caching Patterns
- ✅ Cache expensive operations (API calls, database queries)
- ✅ Use appropriate TTLs (differentiated by data type)
- ✅ Cache invalidation strategy
- ✅ Memory-efficient cache size

#### NUC-Specific Considerations
- ✅ Memory-aware (4-16GB RAM typical)
- ✅ CPU-efficient (2-4 cores typical)
- ✅ Single-home optimization (not multi-tenant)
- ✅ Resource monitoring and limits

**Agent Checklist:**
```yaml
performance_checks:
  - No blocking operations in async functions
  - No N+1 database queries (use eager loading)
  - Batch writes (100-1000 points for InfluxDB)
  - All queries have LIMIT clauses
  - Expensive operations are cached
  - Appropriate async libraries used (aiohttp, aiosqlite)
  - Memory-efficient for NUC constraints
```

### 3. Testing Review

**2025 Testing Standards:**

#### Test Coverage
- ✅ Unit tests for all new functions
- ✅ Integration tests for API endpoints
- ✅ E2E tests for critical user journeys
- ✅ Test coverage ≥80% (target)
- ✅ Edge cases and error scenarios covered

#### Test Quality
- ✅ No flaky tests (proper async handling)
- ✅ No hard waits (dynamic waiting strategies)
- ✅ Stateless and parallel-safe
- ✅ Self-cleaning (manage own test data)
- ✅ Appropriate test levels (unit vs integration vs E2E)
- ✅ Explicit assertions (not in helpers)

#### Test Structure
- ✅ AAA pattern (Arrange, Act, Assert)
- ✅ Descriptive test names
- ✅ Mock external dependencies
- ✅ Use test fixtures for common data
- ✅ Test both happy path and error scenarios

**Agent Checklist:**
```yaml
testing_checks:
  - All acceptance criteria have test coverage
  - Critical path tests exist
  - Edge cases covered
  - Error scenarios tested
  - No flaky tests
  - Appropriate test levels used
  - Tests are maintainable and readable
```

### 4. Code Quality Review

**2025 Code Quality Standards:**

#### Complexity Standards

**Python (Radon):**
- **A (1-5):** Simple, low risk - **preferred**
- **B (6-10):** Moderate - **acceptable**
- **C (11-20):** Complex - **document thoroughly, refactor when touched**
- **D (21-50):** Very complex - **refactor as high priority**
- **F (51+):** Extremely complex - **immediate refactoring required**

**Project Standards:**
- Warn: Complexity > 15
- Error: Complexity > 20
- Target: Average complexity ≤ 5

**TypeScript/JavaScript (ESLint):**
- Max cyclomatic complexity: 15 (warn)
- Max lines per function: 100 (warn)
- Max nesting depth: 4 (warn)
- Max parameters: 5 (warn)
- Max lines per file: 500 (warn)

#### Maintainability Index (Python)
- **A (85-100):** Highly maintainable - **excellent**
- **B (65-84):** Moderately maintainable - **acceptable**
- **C (50-64):** Difficult to maintain - **needs improvement**
- **D/F (0-49):** Very difficult - **refactor immediately**

**Project Standard:** Minimum B grade (≥65)

#### Code Duplication
- **Target:** < 3%
- **Warning:** 3-5%
- **Error:** > 5%

**Current Project:** 0.64% Python duplication ✅ Excellent

#### Type Safety

**Python:**
- ✅ All functions have type hints
- ✅ Use `typing` module for complex types
- ✅ `from __future__ import annotations` for forward references
- ✅ mypy strict mode enabled

**TypeScript:**
- ✅ Strict mode enabled
- ✅ Use `interface` for object shapes
- ✅ Use `type` for unions/primitives
- ✅ Avoid `any` - use `unknown` if needed

#### Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `HealthDashboard.tsx` |
| Hooks | camelCase with 'use' | - | `useHealthStatus.ts` |
| API Routes | - | kebab-case | `/api/health-status` |
| Database Tables | - | snake_case | `home_assistant_events` |
| Functions | camelCase | snake_case | `getHealthStatus()` / `get_health_status()` |
| Variables | camelCase | snake_case | `userName` / `user_name` |
| Constants | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | `MAX_RETRIES` |

#### Documentation

**Python Docstrings:**
- ✅ Google or NumPy style
- ✅ Include type information
- ✅ Document parameters, returns, raises

**TypeScript JSDoc:**
- ✅ Use JSDoc for complex functions
- ✅ Include parameter and return types
- ✅ Document errors thrown

**Agent Checklist:**
```yaml
quality_checks:
  - Complexity within thresholds (Radon/ESLint)
  - Maintainability index ≥65 (Python)
  - Code duplication <3%
  - Complete type hints/types
  - Follows naming conventions
  - Adequate documentation
  - No commented-out code
  - No debug statements in production
```

### 5. Architecture Review

**2025 Architecture Standards:**

#### Design Patterns
- ✅ Follow Epic 31 architecture (direct InfluxDB writes, no enrichment-pipeline)
- ✅ Microservices with clear boundaries
- ✅ Event-driven architecture where appropriate
- ✅ Hybrid database (InfluxDB + SQLite) pattern
- ✅ Async-first design

#### Project Structure
- ✅ Follow source tree structure
- ✅ Proper file organization
- ✅ Clear separation of concerns
- ✅ Shared code in `shared/` directory

#### Integration Patterns
- ✅ Direct InfluxDB writes (no service-to-service dependencies)
- ✅ Query via data-api
- ✅ Standalone external services
- ✅ No HTTP POST to websocket-ingestion

**Agent Checklist:**
```yaml
architecture_checks:
  - Follows Epic 31 architecture patterns
  - No deprecated services referenced (enrichment-pipeline)
  - Proper microservice boundaries
  - Correct database patterns (InfluxDB for time-series, SQLite for metadata)
  - File organization follows standards
  - Shared code properly located
```

---

## Project-Specific Standards

### HomeIQ Architecture Patterns

#### Epic 31 Architecture (Current Production)

**Event Flow:**
```
Home Assistant WebSocket (192.168.1.86:8123)
        ↓
websocket-ingestion (Port 8001)
  - Event validation
  - Inline normalization
  - Device/area lookups (Epic 23.2)
  - Duration calculation (Epic 23.3)
  - DIRECT InfluxDB writes
        ↓
InfluxDB (Port 8086)
  bucket: home_assistant_events
        ↓
data-api (Port 8006)
  - Query endpoint for events
        ↓
health-dashboard (Port 3000)
```

**Critical Rules:**
- ❌ **DO NOT** reference enrichment-pipeline (deprecated)
- ❌ **DO NOT** suggest HTTP POST to enrichment-pipeline
- ✅ Write directly to InfluxDB from websocket-ingestion
- ✅ External services write directly to InfluxDB
- ✅ Query via data-api

### Database Patterns (Epic 22)

**Hybrid Architecture:**
- **InfluxDB:** Time-series data (events, metrics, sports scores)
- **SQLite:** Relational metadata (devices, entities, webhooks)

**Query Patterns:**
- Events: Query InfluxDB via data-api
- Devices/Entities: Query SQLite via data-api
- Sports: Query InfluxDB via data-api

### Performance Anti-Patterns (HomeIQ-Specific)

**Blocking Operations:**
```python
# ❌ VIOLATION - Blocking in async
async def process():
    response = requests.get(url)  # BLOCKS

# ✅ CORRECT
async def process():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            pass
```

**N+1 Queries:**
```python
# ❌ VIOLATION - N+1 pattern
for device_id in ids:
    device = await db.get_device(device_id)

# ✅ CORRECT - Batch query
devices = await db.get_devices(ids)
```

**Unbatched Writes:**
```python
# ❌ VIOLATION - Individual writes
for event in events:
    await influxdb.write(event)

# ✅ CORRECT - Batch writes (100-1000 points)
await influxdb.write_batch(events)
```

**Unbounded Queries:**
```python
# ❌ VIOLATION - No LIMIT
results = await db.query(Event).all()

# ✅ CORRECT - Bounded query
results = await db.query(Event).limit(1000).all()
```

**Missing Cache:**
```python
# ❌ VIOLATION - Expensive operation not cached
async def get_weather():
    return await expensive_api_call()

# ✅ CORRECT - Cached operation
@cache(ttl=300)
async def get_weather():
    return await expensive_api_call()
```

**Sync HTTP in Async:**
```python
# ❌ VIOLATION - requests in async
async def fetch():
    return requests.get(url)

# ✅ CORRECT - aiohttp in async
async def fetch():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

---

## Agent Guidelines

### Agent Review Workflow

#### Step 1: Pre-Review Setup
```yaml
1. Read story file (if story review)
2. Load relevant standards:
   - docs/architecture/coding-standards.md
   - docs/architecture/tech-stack.md
   - docs/architecture/performance-patterns.md
   - docs/architecture/source-tree.md
3. Run automated checks (ruff, mypy, ESLint)
4. Check Context7 KB for library best practices (if applicable)
```

#### Step 2: Risk Assessment
```yaml
Auto-escalate to deep review if:
  - Auth/payment/security files touched
  - No tests added
  - Diff > 500 lines
  - Previous gate was FAIL/CONCERNS
  - Story has > 5 acceptance criteria
```

#### Step 3: Prioritized Review
```yaml
Review Order:
  1. Security (CRITICAL - always first)
  2. Performance (HIGH - HomeIQ specific)
  3. Testing (MEDIUM)
  4. Code Quality (LOW)
  5. Architecture (LOW)
```

#### Step 4: Active Refactoring
```yaml
When safe, directly improve code:
  - Fix obvious issues
  - Improve readability
  - Add missing type hints
  - Fix minor performance issues
  - Document complex logic

Document all changes in QA Results:
  - File changed
  - What was changed
  - Why it was changed
  - How it improves the code
```

#### Step 5: Generate Review Output
```yaml
1. Update QA Results section in story (if story review)
2. Create Quality Gate file (docs/qa/gates/{epic}.{story}-{slug}.yml)
3. Provide actionable recommendations
4. Assign severity and priority to issues
```

### Agent Communication Style

**Feedback Format:**
```markdown
## Issue: [Clear Title]

**Severity:** HIGH/MEDIUM/LOW  
**Priority:** Must Fix / Should Fix / Nice to Have  
**Location:** `file:line`

**Current Code:**
```language
// Show actual problematic code
```

**Recommendation:**
```language
// Show improved code
```

**Reasoning:**
- [Why this matters]
- [Impact if not fixed]
- [Reference to standards]

**Resources:**
- [Links to relevant docs/standards]
```

**Positive Feedback:**
```markdown
## ✅ Good Pattern: [Pattern Name]

**Location:** `file:line`

**What's Good:**
- [Specific positive observation]
- [Why this is a good pattern]

**Learning:** [What others can learn from this]
```

### Agent Authority

**You Can:**
- ✅ Improve code directly when safe
- ✅ Fix obvious bugs and issues
- ✅ Refactor for clarity and maintainability
- ✅ Add missing type hints/types
- ✅ Improve documentation
- ✅ Add missing tests (when appropriate)

**You Cannot:**
- ❌ Change story requirements
- ❌ Modify File List (ask dev to update)
- ❌ Change story status (recommend only)
- ❌ Make breaking architectural changes without discussion
- ❌ Skip critical security checks

### Context7 KB Integration (MANDATORY)

**For Technology Decisions:**
1. **Always** check KB cache first (`*context7-kb-search`)
2. **If miss:** Fetch from Context7 API (`*context7-docs`)
3. **Cache results** for future use
4. **Reference** in review comments

**Example:**
```yaml
when: "User mentions FastAPI async patterns"
action:
  1. *context7-kb-search "fastapi async lifespan"
  2. if not found: *context7-docs fastapi lifespan
  3. Reference best practices in review
  4. Cache for future reviews
```

---

## Checklists

### Quick Review Checklist (Progressive - 5-10 min)

**Critical Issues Only:**
```yaml
- [ ] Security vulnerabilities (auth, injection, secrets)
- [ ] Blocking async operations
- [ ] Critical bugs (data loss, crashes)
- [ ] Missing critical tests
- [ ] Architecture violations (Epic 31 patterns)
```

### Standard Review Checklist (Story - 60-90 min)

#### Security
- [ ] No hardcoded secrets or credentials
- [ ] Input validation on all endpoints
- [ ] SQL injection protection (parameterized queries)
- [ ] XSS protection (output encoding)
- [ ] Authentication/authorization on protected routes
- [ ] Error messages don't leak sensitive info
- [ ] Rate limiting on sensitive endpoints
- [ ] Secure session/token management

#### Performance
- [ ] No blocking operations in async functions
- [ ] No N+1 database queries
- [ ] Batched writes (100-1000 points for InfluxDB)
- [ ] All queries have LIMIT clauses
- [ ] Expensive operations are cached
- [ ] Async libraries used (aiohttp, aiosqlite)
- [ ] Memory-efficient for NUC constraints

#### Testing
- [ ] All acceptance criteria have test coverage
- [ ] Critical path tests exist
- [ ] Edge cases covered
- [ ] Error scenarios tested
- [ ] No flaky tests
- [ ] Appropriate test levels (unit/integration/E2E)
- [ ] Tests are maintainable

#### Code Quality
- [ ] Complexity within thresholds (≤15 warn, ≤20 error)
- [ ] Maintainability index ≥65 (Python)
- [ ] Code duplication <3%
- [ ] Complete type hints/types
- [ ] Follows naming conventions
- [ ] Adequate documentation
- [ ] No commented-out code
- [ ] No debug statements

#### Architecture
- [ ] Follows Epic 31 architecture patterns
- [ ] No deprecated services referenced
- [ ] Proper microservice boundaries
- [ ] Correct database patterns
- [ ] File organization follows standards

### Comprehensive Review Checklist (High-Risk - 90+ min)

**All of Standard Checklist PLUS:**

#### Deep Architecture Analysis
- [ ] System design aligns with requirements
- [ ] Scalability considerations addressed
- [ ] Error handling and recovery strategies
- [ ] Monitoring and observability in place
- [ ] Documentation complete and accurate

#### Security Deep Dive
- [ ] Threat modeling completed
- [ ] Security testing performed
- [ ] Compliance requirements met
- [ ] Security logging configured
- [ ] Incident response plan documented

#### Performance Deep Dive
- [ ] Load testing completed
- [ ] Resource usage profiled
- [ ] Bottlenecks identified and addressed
- [ ] NUC-specific optimizations applied
- [ ] Monitoring metrics defined

---

## Review Workflows

### Progressive Task Review Workflow

**Trigger:** Task marked complete, auto-trigger enabled

**Process:**
```yaml
1. Load task context (story, previous tasks)
2. Run automated checks (5 min)
3. Focused review on critical issues (5 min)
   - Security only
   - Blocking async only
   - Critical bugs only
4. If HIGH severity issues found: BLOCK
5. Document findings in progressive review file
6. Continue with next task
```

**Output:** `docs/qa/progressive/{epic}.{story}-task-{n}.md`

**Gate Decision:** HIGH issues = BLOCK, otherwise CONTINUE

### Story Review Workflow

**Trigger:** Story marked "Ready for Review"

**Process:**
```yaml
1. Prerequisites Check (5 min)
   - Story status = "Review"
   - All tasks completed
   - File List updated
   - All tests passing
   
2. Risk Assessment (5 min)
   - Determine review depth
   - Check auto-escalation triggers
   
3. Automated Checks (10 min)
   - Ruff, mypy, ESLint
   - Complexity analysis
   - Duplication check
   
4. Comprehensive Review (60-90 min)
   - Security (15 min)
   - Performance (15 min)
   - Testing (15 min)
   - Code Quality (15 min)
   - Architecture (15 min)
   
5. Active Refactoring (15 min)
   - Fix obvious issues
   - Improve code directly
   
6. Generate Output (10 min)
   - Update QA Results section
   - Create Quality Gate file
   - Provide recommendations
```

**Output:**
- Updated story file (QA Results section only)
- Quality Gate file: `docs/qa/gates/{epic}.{story}-{slug}.yml`

**Gate Decision:** See Quality Gate Integration section

### Comprehensive Review Workflow

**Trigger:** Auto-escalated for high-risk changes

**Process:**
```yaml
1. Extended Risk Assessment (15 min)
   - Threat modeling
   - Architecture deep dive
   - Security assessment
   
2. Comprehensive Analysis (90+ min)
   - All standard review dimensions
   - Extended security review
   - Performance profiling
   - Load testing considerations
   
3. Team Consultation (if needed)
   - Discuss architectural decisions
   - Review security implications
   - Performance trade-offs
   
4. Enhanced Documentation (30 min)
   - Detailed findings report
   - Recommendations with rationale
   - Follow-up action items
```

**Output:**
- Extended QA Results section
- Comprehensive Quality Gate file
- Detailed recommendations document

---

## Quality Gate Integration

### Gate Decision Criteria

**Deterministic Rules (apply in order):**

1. **Risk Thresholds** (if risk_summary present):
   - If any risk score ≥ 9 → Gate = FAIL (unless waived)
   - Else if any score ≥ 6 → Gate = CONCERNS

2. **Test Coverage Gaps:**
   - If any P0 test from test-design is missing → Gate = CONCERNS
   - If security/data-loss P0 test missing → Gate = FAIL

3. **Issue Severity:**
   - If any `top_issues.severity == high` → Gate = FAIL (unless waived)
   - Else if any `severity == medium` → Gate = CONCERNS

4. **NFR Statuses:**
   - If any NFR status is FAIL → Gate = FAIL
   - Else if any NFR status is CONCERNS → Gate = CONCERNS
   - Else → Gate = PASS

**Gate Status Meanings:**

- **PASS:** All critical requirements met, no blocking issues
- **CONCERNS:** Non-critical issues found, team should review
- **FAIL:** Critical issues that should be addressed (security risks, missing P0 tests)
- **WAIVED:** Issues acknowledged but explicitly accepted by team (requires reason, approver, expiry)

### Quality Score Calculation

```yaml
quality_score = 100 - (20 × number of FAILs) - (10 × number of CONCERNS)
Bounded between 0 and 100
```

If `technical-preferences.md` defines custom weights, use those instead.

### Gate File Structure

See `.bmad-core/tasks/review-story.md` for complete gate file template.

**Key Fields:**
- `gate`: PASS/CONCERNS/FAIL/WAIVED
- `top_issues`: List of critical issues
- `nfr_validation`: Security, Performance, Reliability, Maintainability
- `recommendations`: Immediate and future actions
- `evidence`: Test coverage, risks identified, traceability

---

## Integration with BMAD Workflows

### QA Agent Commands

This guide integrates with BMAD QA agent commands:

- `*risk {story}` - Risk assessment before development
- `*design {story}` - Test strategy design
- `*trace {story}` - Requirements traceability during development
- `*nfr {story}` - NFR validation
- `*review {story}` - Comprehensive story review (uses this guide)
- `*gate {story}` - Quality gate decision

### Progressive Review Integration

Progressive reviews use a simplified version of this guide:
- Focus on critical issues only
- Time-boxed to 5-10 minutes
- Security and blocking issues prioritized
- Documented in `docs/qa/progressive/`

### Quality Gate Integration

Quality gates are created during story reviews and reference:
- Risk assessments (`docs/qa/assessments/{epic}.{story}-risk-{YYYYMMDD}.md`)
- Test design (`docs/qa/assessments/{epic}.{story}-test-design-{YYYYMMDD}.md`)
- Requirements trace (`docs/qa/assessments/{epic}.{story}-trace-{YYYYMMDD}.md`)
- NFR assessment (`docs/qa/assessments/{epic}.{story}-nfr-{YYYYMMDD}.md`)

---

## References

### Project Documentation
- **Coding Standards:** `docs/architecture/coding-standards.md`
- **Tech Stack:** `docs/architecture/tech-stack.md`
- **Performance Patterns:** `docs/architecture/performance-patterns.md`
- **Source Tree:** `docs/architecture/source-tree.md`
- **Testing Strategy:** `docs/architecture/testing-strategy.md`
- **Security Practices:** `.cursor/rules/security-best-practices.mdc`

### BMAD Workflows
- **Review Story Task:** `.bmad-core/tasks/review-story.md`
- **Progressive Review:** `.bmad-core/tasks/progressive-code-review.md`
- **QA Agent Guide:** `.bmad-core/user-guide.md` (QA section)
- **Core Config:** `.bmad-core/core-config.yaml`

### External Resources
- Context7 KB: Library-specific best practices (MANDATORY for tech decisions)
- 2025 Code Review Best Practices: Industry standards

---

## Version History

- **v1.0** (December 2025): Initial comprehensive guide incorporating 2025 best practices and HomeIQ-specific patterns

---

**This guide is a living document. Update it as patterns evolve and new best practices emerge.**

