<!-- Powered by BMAD™ Core -->

# Context7 MCP Integration Guide

## Overview

This guide explains how to properly integrate Context7 MCP (Model Context Protocol) tools with the BMAD KB (Knowledge Base) caching system. This ensures KB-first lookup, automatic caching, and optimal performance.

## MCP Tools Available

### 1. Library Resolution Tool
**Tool Name**: `mcp_Context7_resolve-library-id`

**Purpose**: Resolve a library/package name to a Context7-compatible library ID.

**Parameters**:
- `libraryName` (string, required): The library name to resolve (e.g., "react", "fastapi", "pytest")

**Returns**: A list of matching libraries with Context7-compatible IDs in the format `/org/project` or `/org/project/version`.

**Usage Example**:
```yaml
tool_call:
  name: "mcp_Context7_resolve-library-id"
  parameters:
    libraryName: "react"
  
expected_result:
  - library_id: "/reactjs/react.dev"
  - description: "React documentation"
  - benchmark_score: 100
```

### 2. Documentation Retrieval Tool
**Tool Name**: `mcp_Context7_get-library-docs`

**Purpose**: Fetch up-to-date documentation for a library from Context7.

**Parameters**:
- `context7CompatibleLibraryID` (string, required): The Context7 library ID (e.g., "/reactjs/react.dev")
- `topic` (string, optional): Focus documentation on a specific topic (e.g., "hooks", "routing", "authentication")
- `mode` (string, optional): "code" (default) for API references and code examples, or "info" for conceptual guides
- `page` (integer, optional): Page number for pagination (1-10, default: 1)

**Returns**: Documentation content in markdown format, including code snippets, examples, and API references.

**Usage Example**:
```yaml
tool_call:
  name: "mcp_Context7_get-library-docs"
  parameters:
    context7CompatibleLibraryID: "/reactjs/react.dev"
    topic: "hooks"
    mode: "code"
    page: 1
  
expected_result:
  documentation: "# React Hooks\n\n..."
  snippets: [...]
  trust_score: 10
```

## KB-First Workflow (MANDATORY)

### Workflow Overview

```
User Request (*context7-docs {library} {topic})
    ↓
Step 1: Check KB Cache
    ├─ Hit? → Return cached content (0.12s avg)
    └─ Miss? → Step 2
    ↓
Step 2: Fuzzy Match Lookup
    ├─ Match Found? → Return fuzzy match
    └─ No Match? → Step 3
    ↓
Step 3: Resolve Library ID (if needed)
    └─ Use mcp_Context7_resolve-library-id
    ↓
Step 4: Call Context7 API
    └─ Use mcp_Context7_get-library-docs
    ↓
Step 5: Store in KB Cache
    └─ Save to docs/kb/context7-cache/
    ↓
Return Documentation
```

### Step-by-Step Implementation

#### Step 1: Check KB Cache

**Action**: Read KB cache file first
**Path**: `docs/kb/context7-cache/libraries/{library}/{topic}.md`

```yaml
kb_cache_check:
  action: "read_file"
  path: "docs/kb/context7-cache/libraries/{library}/{topic}.md"
  
  on_success:
    - extract_metadata_from_comments
    - update_hit_count_in_meta_yaml
    - update_last_accessed_timestamp
    - return_cached_content
    - log_performance: "cache_hit"
  
  on_failure:
    - proceed_to_fuzzy_match
```

**Example KB Cache File Structure**:
```markdown
# React - hooks

**Source**: /reactjs/react.dev (Trust Score: 10)
**Snippets**: 2378 | **Tokens**: 3000
**Last Updated**: 2025-10-07T16:40:00Z | **Cache Hits**: 5

---

# React Hooks

React Hooks are functions that let you use state and other React features...

[Documentation content here]

---

<!-- KB Metadata -->
<!-- Library: react -->
<!-- Topic: hooks -->
<!-- Context7 ID: /reactjs/react.dev -->
<!-- Trust Score: 10 -->
<!-- Snippet Count: 2378 -->
<!-- Last Updated: 2025-10-07T16:40:00Z -->
<!-- Cache Hits: 5 -->
<!-- Token Count: 3000 -->
```

#### Step 2: Fuzzy Match Lookup

**Action**: Search KB index for similar topics
**Path**: `docs/kb/context7-cache/index.yaml`

```yaml
fuzzy_match_lookup:
  action: "search_kb_index"
  index_file: "docs/kb/context7-cache/index.yaml"
  cross_refs_file: "docs/kb/context7-cache/cross-references.yaml"
  
  search_strategy:
    - exact_library_match: true
    - topic_similarity: true
    - confidence_threshold: 0.7
    - cross_reference_lookup: true
  
  on_match:
    - return_fuzzy_match_with_confidence
    - update_hit_count
  
  on_no_match:
    - proceed_to_context7_resolution
```

#### Step 3: Resolve Library ID (if needed)

**Action**: Check KB metadata first, then use MCP tool if needed
**Path**: `docs/kb/context7-cache/libraries/{library}/meta.yaml`

```yaml
resolve_library:
  check_kb_first:
    path: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
    field: "context7_id"
  
  on_found_in_kb:
    - use_cached_context7_id
  
  on_not_found:
    - call_mcp_tool: "mcp_Context7_resolve-library-id"
    - parameter: "libraryName: {library}"
    - select_best_match: "highest_benchmark_score"
    - store_in_kb: "libraries/{library}/meta.yaml"
```

**MCP Tool Call Example**:
```python
# Agent should call:
mcp_Context7_resolve-library-id(libraryName="react")

# Returns:
[
  {
    "library_id": "/reactjs/react.dev",
    "description": "React documentation",
    "benchmark_score": 100
  }
]

# Select best match (highest benchmark_score)
# Store in KB: libraries/react/meta.yaml
```

#### Step 4: Call Context7 API

**Action**: Fetch documentation using MCP tool
**Only if**: KB cache miss AND fuzzy match failed

```yaml
context7_api_call:
  condition: "kb_cache_miss AND fuzzy_match_failed"
  tool: "mcp_Context7_get-library-docs"
  
  parameters:
    context7CompatibleLibraryID: "{resolved_library_id}"
    topic: "{topic}"
    mode: "code"
    page: 1
  
  on_success:
    - extract_documentation_content
    - extract_metadata: "trust_score, snippet_count"
    - proceed_to_kb_storage
  
  on_error:
    - return_error_with_suggestion
    - check_if_cached_version_available
```

**MCP Tool Call Example**:
```python
# Agent should call:
mcp_Context7_get-library-docs(
  context7CompatibleLibraryID="/reactjs/react.dev",
  topic="hooks",
  mode="code",
  page=1
)

# Returns documentation content + metadata
```

#### Step 5: Store in KB Cache

**Action**: Save Context7 results to KB cache structure

```yaml
kb_storage:
  steps:
    - create_directory: "docs/kb/context7-cache/libraries/{library}"
    
    - write_content:
        file: "docs/kb/context7-cache/libraries/{library}/{topic}.md"
        format: "markdown_with_metadata_comments"
    
    - update_metadata:
        file: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
        fields:
          - context7_id
          - trust_score
          - snippet_count
          - last_fetched
          - topics: ["{topic}"]
    
    - update_index:
        file: "docs/kb/context7-cache/index.yaml"
        entry:
          library: "{library}"
          topic: "{topic}"
          cache_hits: 0
          last_updated: "{current_timestamp}"
    
    - update_cross_refs:
        file: "docs/kb/context7-cache/cross-references.yaml"
        if_needed: true
```

## KB Cache Directory Structure

```
docs/kb/context7-cache/
├── index.yaml                    # Master index of all cached docs
├── cross-references.yaml         # Topic cross-references
├── fuzzy-matching.yaml           # Fuzzy matching configuration
├── README.md                     # KB documentation
│
├── libraries/                    # Library-based sharding
│   ├── react/
│   │   ├── meta.yaml            # React library metadata
│   │   ├── hooks.md             # React hooks docs
│   │   ├── components.md        # React components docs
│   │   └── state-management.md  # React state docs
│   │
│   ├── fastapi/
│   │   ├── meta.yaml            # FastAPI metadata
│   │   ├── authentication.md    # FastAPI auth docs
│   │   └── routing.md           # FastAPI routing docs
│   │
│   └── [other libraries...]
│
└── topics/                       # Topic-based cross-referencing
    ├── hooks/
    │   └── index.yaml           # Hooks topic index
    └── routing/
        └── index.yaml           # Routing topic index
```

## Configuration

### Core Config (`.bmad-core/core-config.yaml`)

```yaml
context7:
  enabled: true
  defaultTokenLimit: 3000
  cacheDuration: 3600
  integrationLevel: mandatory
  knowledge_base:
    enabled: true
    location: "docs/kb/context7-cache"
    sharding: true
    indexing: true
    cross_references: true
    max_cache_size: "100MB"
    hit_rate_threshold: 0.7
    fuzzy_match_threshold: 0.7
```

### Agent-Specific Token Limits

- **Architect**: 4000 tokens (topics: architecture, design-patterns, scalability)
- **Dev**: 3000 tokens (topics: hooks, routing, authentication, testing)
- **QA**: 2500 tokens (topics: testing, security, performance)

## Error Handling

### Common Errors and Solutions

1. **MCP Tool Not Available**
   - Check MCP server is enabled in Cursor settings
   - Verify Context7 MCP server is running
   - Fallback to KB cache if available

2. **Library Not Found**
   - Use `mcp_Context7_resolve-library-id` to find alternatives
   - Suggest similar libraries from KB index
   - Return helpful error message

3. **KB Cache Write Failed**
   - Check directory permissions
   - Verify disk space available
   - Return documentation without caching (graceful degradation)

4. **Invalid Context7 ID**
   - Re-resolve library ID using MCP tool
   - Update KB metadata with correct ID
   - Retry documentation fetch

## Performance Targets

- **KB Cache Hit Response Time**: < 0.15 seconds
- **Context7 API Call**: < 2.0 seconds
- **KB Storage Operation**: < 0.5 seconds
- **Cache Hit Rate**: > 70% (target: 87%+)
- **Token Savings**: 87%+ reduction in API calls

## Best Practices

1. **Always Check KB First**: Never skip KB cache check
2. **Use Fuzzy Matching**: Improve hit rates with intelligent matching
3. **Cache Everything**: Store all Context7 API results
4. **Update Metadata**: Keep KB index and metadata current
5. **Monitor Performance**: Track hit rates and response times
6. **Clean Up Regularly**: Run `*context7-kb-cleanup` monthly

## Integration with BMAD Agents

### BMad Master Commands

- `*context7-resolve {library}` - Resolve library to Context7 ID (KB-first)
- `*context7-docs {library} {topic}` - Get documentation (KB-first)
- `*context7-kb-status` - Show KB statistics
- `*context7-kb-search {query}` - Search KB cache
- `*context7-kb-test` - Test KB integration

### Agent Auto-Triggers

Agents automatically use Context7 KB when:
- User mentions a library/framework name
- Discussing implementation patterns
- Making technology recommendations
- Troubleshooting library-specific issues

## Testing KB Integration

Use `*context7-kb-test` to verify:
- KB cache read/write operations
- MCP tool integration
- Metadata updates
- Performance metrics
- Error handling

## Troubleshooting

### KB Cache Not Being Used

**Symptoms**: Always calling Context7 API, 0% hit rate

**Solutions**:
1. Verify KB cache directory exists: `docs/kb/context7-cache/`
2. Check KB index file is valid: `docs/kb/context7-cache/index.yaml`
3. Ensure agents follow KB-first workflow from `context7-kb-lookup.md`
4. Run `*context7-kb-test` to diagnose issues

### MCP Tools Not Working

**Symptoms**: Errors when calling MCP tools

**Solutions**:
1. Check Cursor Settings → MCP → Context7 is enabled
2. Verify MCP server shows "Enabled" status (not "Disabled" or "Logout")
3. Check MCP tools are listed: `resolve-library-id`, `get-library-docs`
4. Try resolving a simple library first: `*context7-resolve react`

### KB Cache Out of Date

**Symptoms**: Old documentation, missing new features

**Solutions**:
1. Run `*context7-kb-refresh` to check staleness
2. Refresh specific library: `*context7-kb-refresh {library}`
3. Check auto-refresh settings in `core-config.yaml`
4. Process refresh queue: `*context7-kb-process-queue`

## Reference Documents

- **KB Lookup Task**: `.bmad-core/tasks/context7-kb-lookup.md`
- **Docs Task**: `.bmad-core/tasks/context7-docs.md`
- **KB Integration Utils**: `.bmad-core/utils/context7-kb-integration.md`
- **Core Config**: `.bmad-core/core-config.yaml`
- **KB Cache Index**: `docs/kb/context7-cache/index.yaml`

## Support

For issues or questions:
1. Run `*context7-kb-status` to check KB health
2. Run `*context7-kb-test` to test integration
3. Check `.bmad-core/utils/context7-kb-integration.md` for implementation details
4. Review agent task files for workflow requirements

