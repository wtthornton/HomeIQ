<!-- Powered by BMAD™ Core -->

# Context7 Documentation Retrieval Task

## Purpose
MANDATORY: Retrieve focused documentation for a library using KB-FIRST lookup with Context7 MCP tools. FAILURE to use KB-first approach is FORBIDDEN. This task implements the KB-first workflow from context7-kb-lookup.md.

## CRITICAL: KB-First Workflow (MANDATORY)
You MUST follow this exact workflow - checking KB cache BEFORE calling Context7 API:

1. **KB Cache Check**: Check `docs/kb/context7-cache/libraries/{library}/{topic}.md` first
2. **Fuzzy Match**: If exact match not found, try fuzzy matching via `docs/kb/context7-cache/index.yaml`
3. **Library Resolution**: Resolve library name to Context7 ID using `mcp_Context7_resolve-library-id` (only if needed)
4. **Context7 API Call**: Call `mcp_Context7_get-library-docs` ONLY if KB cache miss
5. **KB Storage**: Store Context7 results in KB cache structure
6. **Metadata Update**: Update KB index and metadata files

## MANDATORY Implementation Steps

### Step 0: KB-First Lookup (MUST DO FIRST)
```yaml
kb_first_lookup:
  action: "execute_kb_first_workflow"
  reference: ".bmad-core/tasks/context7-kb-lookup.md"
  
  step_1_check_cache:
    file_path: "docs/kb/context7-cache/libraries/{library}/{topic}.md"
    on_hit:
      - extract_metadata_from_file
      - update_hit_count_in_meta_yaml
      - update_last_accessed_timestamp
      - return_cached_content
      - log_performance: "< 0.15s response time"
    on_miss:
      - proceed_to_fuzzy_match
  
  step_2_fuzzy_match:
    search_index: "docs/kb/context7-cache/index.yaml"
    search_cross_refs: "docs/kb/context7-cache/cross-references.yaml"
    threshold: 0.7
    on_match:
      - return_fuzzy_match_with_confidence
      - update_hit_count
    on_no_match:
      - proceed_to_context7_api
```

### Step 1: Library Resolution (if needed)
```yaml
resolve_library:
  action: "check_kb_for_library_id"
  check_path: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
  
  on_found:
    - use_cached_context7_id
  
  on_not_found:
    - call_mcp_tool: "mcp_Context7_resolve-library-id"
    - parameter: "libraryName: {library}"
    - store_result_in_kb: "libraries/{library}/meta.yaml"
```

### Step 2: Context7 API Call (ONLY if KB miss)
```yaml
context7_api_call:
  condition: "kb_cache_miss AND fuzzy_match_failed"
  action: "call_mcp_tool"
  tool: "mcp_Context7_get-library-docs"
  parameters:
    context7CompatibleLibraryID: "{resolved_library_id}"
    topic: "{topic}"
    mode: "code"
    tokens: "{token_limit (default: 3000)}"
  
  on_success:
    - proceed_to_kb_storage
  
  on_error:
    - return_error_with_suggestion
```

### Step 3: KB Storage (MANDATORY)
```yaml
kb_storage:
  action: "store_in_kb_cache"
  steps:
    - create_directory: "docs/kb/context7-cache/libraries/{library}"
    - write_content: "docs/kb/context7-cache/libraries/{library}/{topic}.md"
      format: "markdown_with_metadata_comments"
    - update_metadata: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
    - update_index: "docs/kb/context7-cache/index.yaml"
    - update_cross_refs: "docs/kb/context7-cache/cross-references.yaml"
  
  metadata_includes:
    - library_name
    - topic
    - context7_id
    - trust_score
    - snippet_count
    - last_updated
    - cache_hits (initial: 0)
    - token_count
```

### Step 4: Output Formatting
```yaml
format_output:
  format: "structured_markdown"
  include:
    - source_indicator: "KB Cache" or "Context7 API"
    - metadata_header
    - documentation_content
    - performance_metrics
    - cache_statistics
```

## KB File Structure Reference

### KB Cache Location
- **Base Path**: `docs/kb/context7-cache/`
- **Library Docs**: `libraries/{library}/{topic}.md`
- **Library Metadata**: `libraries/{library}/meta.yaml`
- **Master Index**: `index.yaml`
- **Cross-References**: `cross-references.yaml`

### Reading KB Cache Files
When checking KB cache:
1. Read `docs/kb/context7-cache/libraries/{library}/{topic}.md`
2. Extract metadata from HTML comments at end of file
3. If file exists and metadata valid, return cached content
4. Update hit count in `meta.yaml` and `index.yaml`

### Writing KB Cache Files
When storing Context7 results:
1. Create directory if needed: `docs/kb/context7-cache/libraries/{library}/`
2. Write markdown file with content + metadata comments
3. Update or create `meta.yaml` with library metadata
4. Update `index.yaml` with entry metadata
5. Update `cross-references.yaml` if needed

## Token Management
- Default token limit: 3000 (configurable per agent)
- Topic-focused retrieval
- Progressive loading (start small, expand if needed)
- KB cache avoids repeated API calls (87%+ reduction)

## MCP Tool Usage

### Library Resolution
```yaml
mcp_tool: "mcp_Context7_resolve-library-id"
parameters:
  libraryName: "{library_name}"
returns:
  context7CompatibleLibraryID: "/org/project" or "/org/project/version"
```

### Documentation Retrieval
```yaml
mcp_tool: "mcp_Context7_get-library-docs"
parameters:
  context7CompatibleLibraryID: "{resolved_library_id}"
  topic: "{topic}"
  mode: "code" (default) or "info"
  page: 1 (optional, 1-10)
returns:
  documentation_content: "markdown formatted documentation"
```

## Error Handling
- **KB file not found**: Try fuzzy match, then Context7 API
- **Library not found**: Use `mcp_Context7_resolve-library-id` to find alternatives
- **Context7 service unavailable**: Return cached content if available, or error message
- **Token limit exceeded**: Suggest breaking into smaller topics
- **Invalid topic parameter**: Suggest valid topics from KB index

## Success Criteria
- KB-first lookup executed (check cache before API)
- Documentation retrieved successfully
- KB cache updated with new content
- Metadata properly tracked
- Token usage within limits
- Clear, structured output provided
- Performance metrics logged
