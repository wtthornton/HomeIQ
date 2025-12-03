<!-- Powered by BMAD™ Core -->

# Context7 Library Resolution Task

## Purpose
Resolve a library name to its Context7-compatible library ID for subsequent documentation retrieval.

## CRITICAL: KB-First Workflow (MANDATORY)
You MUST check KB cache BEFORE calling Context7 API. This ensures cached library IDs are reused.

## Workflow
1. **Input Validation**: Validate library name parameter
2. **KB Cache Check**: Check if library ID is cached in KB (`docs/kb/context7-cache/libraries/{library}/meta.yaml`)
3. **Context7 Resolution**: Call `mcp_Context7_resolve-library-id` ONLY if not in KB cache
4. **KB Storage**: Store resolved ID in KB cache metadata
5. **Output**: Return Context7-compatible library ID

## Implementation

### Step 1: Check KB Cache First
```yaml
kb_cache_check:
  action: "read_yaml_file"
  path: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
  
  on_success:
    - extract_context7_id: "from meta.yaml context7_id field"
    - return_cached_id
    - log_performance: "kb_cache_hit"
  
  on_failure:
    - proceed_to_context7_resolution
```

### Step 2: Context7 Resolution (if KB miss)
```yaml
resolve_library:
  condition: "kb_cache_miss"
  action: "call_mcp_tool"
  tool: "mcp_Context7_resolve-library-id"
  parameters:
    libraryName: "{library_name}"
  
  result_processing:
    - select_best_match: "highest_benchmark_score"
    - extract_library_id: "from selected match"
    - proceed_to_kb_storage
```

### Step 3: Store in KB Cache
```yaml
kb_storage:
  action: "store_in_kb_metadata"
  steps:
    - create_directory: "docs/kb/context7-cache/libraries/{library}"
    - create_or_update_meta:
        file: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
        fields:
          - context7_id: "{resolved_library_id}"
          - last_resolved: "{current_timestamp}"
          - library_name: "{library}"
    - update_index:
        file: "docs/kb/context7-cache/index.yaml"
        entry: "{library}: {context7_id}"
```

### Complete Workflow
```yaml
steps:
  - name: "validate_input"
    action: "check_library_name_format"
    error_handling: "return_error_if_invalid"
  
  - name: "check_kb_cache"
    action: "read_kb_metadata"
    path: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
    field: "context7_id"
    on_success: "return_cached_id"
    on_failure: "proceed_to_resolve"
  
  - name: "resolve_library"
    action: "call_mcp_tool"
    tool: "mcp_Context7_resolve-library-id"
    parameters:
      libraryName: "{library_name}"
    on_success: "proceed_to_storage"
  
  - name: "store_in_kb"
    action: "update_kb_metadata"
    file: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
    fields:
      context7_id: "{resolved_library_id}"
      last_resolved: "{current_timestamp}"
  
  - name: "return_result"
    action: "display_library_id"
    format: "Context7 ID: {library_id} (from KB cache)" or "Context7 ID: {library_id} (resolved via MCP)"
```

## KB File Operations

### Reading KB Metadata
```yaml
read_kb_metadata:
  file: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
  extract_field: "context7_id"
  
  on_file_exists:
    - parse_yaml_file
    - extract_context7_id
    - return_cached_id
  
  on_file_not_found:
    - proceed_to_resolution
```

### Writing KB Metadata
```yaml
write_kb_metadata:
  file: "docs/kb/context7-cache/libraries/{library}/meta.yaml"
  fields:
    - context7_id: "{resolved_id}"
    - library_name: "{library}"
    - last_resolved: "{current_timestamp}"
    - source: "mcp_resolve"
```

## MCP Tool Usage

### Library Resolution Tool
```yaml
mcp_tool: "mcp_Context7_resolve-library-id"
parameters:
  libraryName: "{library_name}"

expected_result:
  - array of matching libraries
  - each with: library_id, description, benchmark_score

selection_strategy:
  - choose_highest_benchmark_score
  - extract_library_id: "from selected match"
```

## Error Handling
- **Invalid library name format**: Return error with format requirements
- **KB file read error**: Proceed to Context7 resolution (graceful degradation)
- **Context7 service unavailable**: Return error, suggest checking MCP server status
- **Library not found in Context7**: Return error with suggestions from KB index
- **KB storage failures**: Return resolved ID but log storage error (graceful degradation)
- **Invalid YAML in KB metadata**: Recreate meta.yaml file

## Success Criteria
- KB cache checked first (if available)
- Library ID successfully resolved (from KB or Context7)
- ID stored in KB cache for future use
- Clear output format provided
- Performance metrics logged (KB hit vs MCP call)
