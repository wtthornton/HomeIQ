# Context7 Shared Rules (Reference)

**Purpose:** Shared Context7 KB integration rules referenced by all agents to reduce duplication.

## Mandatory Rules (All Agents)

### KB-First Approach
- **MANDATORY**: Check KB cache BEFORE Context7 API calls - FORBIDDEN to bypass
- **MANDATORY**: Use `*context7-kb-search` before fetching from Context7
- **MANDATORY**: Cache all Context7 results for future use

### Technology Decisions
- **MANDATORY**: Use Context7 KB for ANY technology/library decisions - NO EXCEPTIONS
- **MANDATORY**: Use `*context7-docs` commands when researching libraries/frameworks
- **FORBIDDEN**: Using generic knowledge instead of Context7 KB

### Auto-Triggers (When to Use Context7)
- User mentions library/framework name (React, FastAPI, etc.)
- Discussing implementation patterns or best practices
- Troubleshooting library-specific errors
- Explaining how technology works
- Making technology recommendations
- **ALWAYS offer**: "Would you like me to check Context7 KB for current best practices?"

### Workflow Pattern
1. **BEFORE**: Check KB with `*context7-kb-search {library}`
2. **IF KB miss**: Proactively say "Let me fetch current docs from Context7"
3. **AFTER fetching**: Mention cache hit rate and suggest related topics
4. **REMIND**: "This is cached for future use - run *context7-kb-status to see stats"

## Agent-Specific Token Limits

- **Architect**: 4000 tokens, topics: architecture, design-patterns, scalability
- **Dev**: 3000 tokens, topics: hooks, routing, authentication, testing
- **QA**: 2500 tokens, topics: testing, security, performance
- **BMad Master**: 3000 tokens (default)

## Performance Targets

- **Cache Hit Rate**: 87%+ target
- **Response Time**: 0.15s target
- **KB-First**: Always check cache before API calls

