# Context7 MCP Quick Reference

## MCP Tools

### 1. Resolve Library ID
```
Tool: mcp_Context7_resolve-library-id
Parameter: libraryName (string)
Example: libraryName="react"
```

### 2. Get Library Docs
```
Tool: mcp_Context7_get-library-docs
Parameters:
  - context7CompatibleLibraryID (string, required)
  - topic (string, optional)
  - mode: "code" | "info" (optional, default: "code")
  - page: 1-10 (optional, default: 1)
Example:
  context7CompatibleLibraryID="/reactjs/react.dev"
  topic="hooks"
  mode="code"
```

## KB-First Workflow (MANDATORY)

```
1. Check KB Cache
   Path: docs/kb/context7-cache/libraries/{library}/{topic}.md
   ↓ Hit? Return cached content
   ↓ Miss? Continue

2. Fuzzy Match
   Search: docs/kb/context7-cache/index.yaml
   ↓ Match? Return fuzzy match
   ↓ No match? Continue

3. Resolve Library ID (if needed)
   Check: docs/kb/context7-cache/libraries/{library}/meta.yaml
   ↓ Found? Use cached ID
   ↓ Not found? Call mcp_Context7_resolve-library-id

4. Call Context7 API (only if KB miss)
   Tool: mcp_Context7_get-library-docs
   ↓ Success? Continue
   ↓ Error? Return error

5. Store in KB Cache
   Save: docs/kb/context7-cache/libraries/{library}/{topic}.md
   Update: meta.yaml, index.yaml
```

## KB Cache Locations

- **Library Docs**: `docs/kb/context7-cache/libraries/{library}/{topic}.md`
- **Library Metadata**: `docs/kb/context7-cache/libraries/{library}/meta.yaml`
- **Master Index**: `docs/kb/context7-cache/index.yaml`
- **Cross-References**: `docs/kb/context7-cache/cross-references.yaml`

## Commands

- `*context7-resolve {library}` - Resolve library ID (KB-first)
- `*context7-docs {library} {topic}` - Get docs (KB-first)
- `*context7-kb-status` - Show KB statistics
- `*context7-kb-search {query}` - Search KB cache
- `*context7-kb-test` - Test KB integration

## Key Rules

1. ✅ ALWAYS check KB cache FIRST
2. ✅ Use MCP tools ONLY if KB miss
3. ✅ Store ALL Context7 results in KB
4. ✅ Update metadata files after caching
5. ✅ NEVER skip KB-first workflow

