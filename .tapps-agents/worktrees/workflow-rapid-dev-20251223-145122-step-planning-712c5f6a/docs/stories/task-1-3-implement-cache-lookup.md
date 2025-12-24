# Task 1.3: Implement Basic Cache Lookup in context7-simple.md

## Task Information
- **Story**: Context7 Knowledge Base Cache Implementation
- **Task ID**: 1.3
- **Priority**: High
- **Estimate**: 45 minutes
- **Status**: Pending

## Task Description
Enhance the existing context7-simple.md task to implement KB-first lookup functionality, checking local cache before making Context7 API calls.

## Acceptance Criteria
- [ ] KB-first lookup workflow implemented in context7-simple.md
- [ ] Cache hit logic implemented (check if library/topic exists in KB)
- [ ] Cache miss logic implemented (fallback to Context7 API)
- [ ] Cache storage logic implemented (store Context7 results in KB)
- [ ] Metadata tracking implemented (timestamp, file size, library, topic)
- [ ] Index update functionality implemented
- [ ] Error handling for KB operations
- [ ] Backward compatibility maintained

## Implementation Steps

### Step 1: Enhance Workflow Structure
```yaml
# Enhanced context7-simple.md workflow
workflow:
  - name: "check_local_cache"
    action: "lookup_in_kb"
    parameters:
      library: "{library}"
      topic: "{topic}"
    success_action: "return_cached_docs"
    failure_action: "fetch_from_context7"
  
  - name: "fetch_from_context7"
    action: "call_context7_get_docs"
    tool: "mcp_Context7_get-library-docs"
    parameters:
      context7CompatibleLibraryID: "{library_id}"
      topic: "{topic}"
      tokens: "{token_limit}"
  
  - name: "cache_results"
    action: "store_in_kb"
    parameters:
      library: "{library}"
      topic: "{topic}"
      content: "{docs_content}"
      metadata: "{docs_metadata}"
  
  - name: "update_index"
    action: "update_kb_index"
    parameters:
      library: "{library}"
      topic: "{topic}"
      cache_hit: false
      file_size: "{content_size}"
```

### Step 2: Implement Cache Lookup Logic
```yaml
# Cache lookup implementation
cache_lookup:
  steps:
    - name: "check_library_exists"
      action: "check_file_exists"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/meta.yaml"
    
    - name: "check_topic_exists"
      action: "check_file_exists"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/{topic}.md"
    
    - name: "check_cache_freshness"
      action: "check_file_age"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/{topic}.md"
      max_age: 3600  # 1 hour
    
    - name: "return_cached_content"
      action: "read_file"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/{topic}.md"
      success_action: "display_cached_docs"
```

### Step 3: Implement Cache Storage Logic
```yaml
# Cache storage implementation
cache_storage:
  steps:
    - name: "create_library_directory"
      action: "create_directory"
      path: ".bmad-core/kb/context7-cache/libraries/{library}"
    
    - name: "store_documentation"
      action: "write_file"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/{topic}.md"
      content: "{docs_content}"
      format: "markdown"
    
    - name: "update_metadata"
      action: "update_meta_yaml"
      path: ".bmad-core/kb/context7-cache/libraries/{library}/meta.yaml"
      updates:
        topics:
          "{topic}":
            file: "{topic}.md"
            size: "{content_size}"
            last_updated: "{current_timestamp}"
            cache_hits: 0
            token_count: "{token_count}"
    
    - name: "update_master_index"
      action: "update_index_yaml"
      path: ".bmad-core/kb/context7-cache/index.yaml"
      updates:
        libraries:
          "{library}":
            topics: ["{topic}"]
            last_fetched: "{current_timestamp}"
            cache_hits: 0
```

### Step 4: Add Error Handling
```yaml
# Error handling implementation
error_handling:
  kb_read_error:
    action: "log_error"
    message: "KB cache read failed, falling back to Context7"
    fallback: "fetch_from_context7"
  
  kb_write_error:
    action: "log_warning"
    message: "KB cache write failed, continuing without cache"
    continue: true
  
  context7_error:
    action: "log_error"
    message: "Context7 API call failed"
    fallback: "return_error_message"
```

## Files to Modify
- `.bmad-core/tasks/context7-simple.md` - Enhanced with KB-first workflow

## Testing
- [ ] Cache hit returns cached documentation
- [ ] Cache miss falls back to Context7 API
- [ ] Context7 results are stored in KB cache
- [ ] Metadata is updated correctly
- [ ] Index is updated after cache operations
- [ ] Error handling works for KB operations
- [ ] Backward compatibility maintained

## Success Criteria
- KB-first lookup workflow implemented
- Cache hit/miss logic working correctly
- Cache storage functionality implemented
- Metadata tracking working
- Index update functionality working
- Error handling implemented
- Ready for Phase 2 implementation
