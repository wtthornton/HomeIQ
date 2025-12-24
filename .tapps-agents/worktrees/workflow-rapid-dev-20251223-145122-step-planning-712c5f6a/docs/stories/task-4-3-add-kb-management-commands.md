# Task 4.3: Add KB Management Commands to BMad Master

## Task Information
- **Story**: Context7 Knowledge Base Cache Implementation
- **Task ID**: 4.3
- **Priority**: High
- **Estimate**: 45 minutes
- **Status**: Pending

## Task Description
Add comprehensive KB management commands to BMad Master agent, providing users with tools to manage, analyze, and optimize the Context7 knowledge base cache.

## Acceptance Criteria
- [ ] KB status command implemented (`*context7-kb-status`)
- [ ] KB search command implemented (`*context7-kb-search`)
- [ ] KB cleanup command implemented (`*context7-kb-cleanup`)
- [ ] KB rebuild command implemented (`*context7-kb-rebuild`)
- [ ] KB analytics command implemented (`*context7-kb-analytics`)
- [ ] KB export command implemented (`*context7-kb-export`)
- [ ] KB import command implemented (`*context7-kb-import`)
- [ ] Command help and usage examples provided

## Implementation Steps

### Step 1: Add KB Management Commands
```yaml
# Enhanced BMad Master commands
commands:
  - context7-resolve {library}: Resolve library name to Context7-compatible library ID
  - context7-docs {library} {topic}: Get focused documentation (KB-first, then Context7)
  - context7-help: Show Context7 usage examples and best practices
  - context7-kb-status: Show knowledge base statistics and hit rates
  - context7-kb-search {query}: Search local knowledge base
  - context7-kb-cleanup: Clean up old/unused cached documentation
  - context7-kb-rebuild: Rebuild knowledge base index
  - context7-kb-analytics: Show detailed KB usage analytics
  - context7-kb-export {format}: Export KB data in specified format
  - context7-kb-import {file}: Import KB data from file
```

### Step 2: Implement KB Status Command
```yaml
# KB status command implementation
kb_status_command:
  purpose: "Show knowledge base statistics and hit rates"
  output_format: "markdown"
  information:
    - total_entries: "Number of cached documentation entries"
    - total_size: "Total KB size in MB"
    - hit_rate: "Cache hit rate percentage"
    - avg_response_time: "Average response time"
    - top_libraries: "Most frequently accessed libraries"
    - top_topics: "Most frequently accessed topics"
    - last_updated: "Last KB update timestamp"
    - cleanup_status: "Next cleanup scheduled time"
```

### Step 3: Implement KB Search Command
```yaml
# KB search command implementation
kb_search_command:
  purpose: "Search local knowledge base"
  parameters:
    query: "Search query (library, topic, or content)"
    type: "Search type (library, topic, content, all)"
    limit: "Maximum results to return"
  search_types:
    - library: "Search by library name"
    - topic: "Search by topic name"
    - content: "Search within documentation content"
    - all: "Search across all KB content"
  output_format: "markdown"
  results_format:
    - title: "Result title"
    - library: "Library name"
    - topic: "Topic name"
    - relevance: "Relevance score"
    - snippet: "Content snippet"
    - file_path: "KB file path"
```

### Step 4: Implement KB Cleanup Command
```yaml
# KB cleanup command implementation
kb_cleanup_command:
  purpose: "Clean up old/unused cached documentation"
  cleanup_rules:
    - max_age: "Remove entries older than 30 days"
    - low_hit_rate: "Remove entries with hit rate < 10%"
    - large_size: "Remove entries larger than 10MB"
    - duplicate_content: "Remove duplicate content"
  cleanup_options:
    - dry_run: "Show what would be cleaned without actually cleaning"
    - force: "Force cleanup without confirmation"
    - selective: "Clean only specific libraries/topics"
  output_format: "markdown"
  cleanup_report:
    - entries_removed: "Number of entries removed"
    - space_freed: "Space freed in MB"
    - hit_rate_improvement: "Hit rate improvement"
    - cleanup_time: "Time taken for cleanup"
```

### Step 5: Implement KB Rebuild Command
```yaml
# KB rebuild command implementation
kb_rebuild_command:
  purpose: "Rebuild knowledge base index"
  rebuild_process:
    - scan_files: "Scan all KB files"
    - update_metadata: "Update library and topic metadata"
    - rebuild_cross_references: "Rebuild cross-reference system"
    - update_master_index: "Update master index file"
    - validate_integrity: "Validate KB integrity"
  rebuild_options:
    - full: "Full rebuild of entire KB"
    - incremental: "Incremental rebuild of changed files"
    - library: "Rebuild specific library"
    - topic: "Rebuild specific topic"
  output_format: "markdown"
  rebuild_report:
    - files_processed: "Number of files processed"
    - index_entries: "Number of index entries"
    - cross_references: "Number of cross-references"
    - rebuild_time: "Time taken for rebuild"
    - errors_found: "Number of errors found and fixed"
```

## Files to Create/Modify
- `.bmad-core/agents/bmad-master.md` (add KB management commands)
- `.bmad-core/tasks/context7-kb-status.md`
- `.bmad-core/tasks/context7-kb-search.md`
- `.bmad-core/tasks/context7-kb-cleanup.md`
- `.bmad-core/tasks/context7-kb-rebuild.md`
- `.bmad-core/tasks/context7-kb-analytics.md`

## Testing
- [ ] KB status command shows accurate statistics
- [ ] KB search command finds relevant results
- [ ] KB cleanup command removes old/unused entries
- [ ] KB rebuild command rebuilds index correctly
- [ ] KB analytics command shows detailed usage data
- [ ] All commands provide helpful output
- [ ] Error handling works for all commands
- [ ] Commands integrate with existing BMad workflow

## Success Criteria
- All KB management commands implemented
- Commands provide comprehensive KB management capabilities
- User-friendly output and error handling
- Commands integrate with BMad workflow
- Ready for Phase 4 completion
