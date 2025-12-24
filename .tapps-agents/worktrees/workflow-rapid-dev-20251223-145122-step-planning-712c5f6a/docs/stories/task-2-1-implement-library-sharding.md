# Task 2.1: Implement Library-Based Sharding System

## Task Information
- **Story**: Context7 Knowledge Base Cache Implementation
- **Task ID**: 2.1
- **Priority**: High
- **Estimate**: 60 minutes
- **Status**: Pending

## Task Description
Implement the library-based sharding system that organizes Context7 documentation by library and topic, creating structured markdown files with proper metadata tracking.

## Acceptance Criteria
- [ ] Library-based sharding system implemented
- [ ] Sharded documentation files created with proper markdown formatting
- [ ] Library metadata files (meta.yaml) created with comprehensive tracking
- [ ] Cross-reference system implemented between libraries
- [ ] File naming conventions established and documented
- [ ] Sharding logic integrated into cache storage workflow
- [ ] Index update functionality for sharded content
- [ ] Error handling for sharding operations

## Implementation Steps

### Step 1: Implement Sharding Logic
```yaml
# Library-based sharding implementation
sharding_system:
  library_structure:
    path: ".bmad-core/kb/context7-cache/libraries/{library}/"
    files:
      - "{topic}.md"  # Documentation content
      - "meta.yaml"   # Library metadata
    
  sharding_rules:
    - name: "library_normalization"
      action: "normalize_library_name"
      rules:
        - "react" → "react"
        - "reactjs" → "react"
        - "react.js" → "react"
        - "express" → "express"
        - "expressjs" → "express"
    
    - name: "topic_normalization"
      action: "normalize_topic_name"
      rules:
        - "hooks" → "hooks"
        - "react-hooks" → "hooks"
        - "routing" → "routing"
        - "express-routing" → "routing"
```

### Step 2: Create Sharded Documentation Format
```markdown
# Context7 Documentation Cache - {Library} {Topic}
# Generated: {timestamp}
# Source: Context7 MCP Tool
# Library: {library}
# Topic: {topic}
# Context7 ID: {context7_id}

## {Topic} Documentation

### Overview
{context7_documentation_content}

### Code Examples
{code_snippets_from_context7}

### Best Practices
{best_practices_from_context7}

### Common Patterns
{common_patterns_from_context7}

## Cross-References
- **Related Topics**: {related_topics}
- **Related Libraries**: {related_libraries}
- **BMad Integration**: Use in {agent} agent for {scenarios}
```

### Step 3: Implement Metadata Tracking
```yaml
# Library metadata structure
library_metadata:
  library:
    name: "{library}"
    context7_id: "{context7_id}"
    version: "{version}"
    trust_score: "{trust_score}"
    code_snippets: "{code_snippets_count}"
    topics:
      "{topic}":
        file: "{topic}.md"
        size: "{file_size}"
        last_updated: "{timestamp}"
        cache_hits: "{hit_count}"
        token_count: "{token_count}"
        context7_source: "{context7_url}"
    cross_references:
      - library: "{related_library}"
        topic: "{related_topic}"
        relevance: "{relevance_score}"
    bmad_integration:
      - agent: "{agent_name}"
        scenarios: ["{scenario1}", "{scenario2}"]
        usage_frequency: "{frequency}"
```

### Step 4: Implement Cross-Reference System
```yaml
# Cross-reference implementation
cross_references:
  library_relationships:
    react:
      related_libraries:
        - name: "react-router"
          topics: ["routing", "navigation"]
          relevance: 0.9
        - name: "redux"
          topics: ["state-management", "hooks"]
          relevance: 0.8
        - name: "react-query"
          topics: ["data-fetching", "hooks"]
          relevance: 0.7
    
    express:
      related_libraries:
        - name: "mongoose"
          topics: ["database", "orm"]
          relevance: 0.9
        - name: "passport"
          topics: ["authentication", "security"]
          relevance: 0.8
        - name: "helmet"
          topics: ["security", "middleware"]
          relevance: 0.7
```

## Files to Create/Modify
- `.bmad-core/kb/context7-cache/libraries/react/meta.yaml`
- `.bmad-core/kb/context7-cache/libraries/react/hooks.md`
- `.bmad-core/kb/context7-cache/libraries/react/components.md`
- `.bmad-core/kb/context7-cache/libraries/express/meta.yaml`
- `.bmad-core/kb/context7-cache/libraries/express/routing.md`
- `.bmad-core/kb/context7-cache/libraries/express/middleware.md`
- `.bmad-core/tasks/context7-simple.md` (enhanced with sharding logic)

## Testing
- [ ] Library sharding creates proper directory structure
- [ ] Sharded documentation files have correct markdown format
- [ ] Library metadata files track all required information
- [ ] Cross-reference system links related libraries and topics
- [ ] File naming conventions are consistent
- [ ] Sharding logic integrates with cache storage workflow
- [ ] Index updates correctly after sharding operations
- [ ] Error handling works for sharding failures

## Success Criteria
- Library-based sharding system fully implemented
- Sharded documentation files properly formatted
- Metadata tracking comprehensive and accurate
- Cross-reference system functional
- Ready for Phase 3 implementation
