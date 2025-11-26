<!-- Powered by BMAD™ Core -->

# Document Sharding Task

## Purpose

- Split a large document into multiple smaller documents based on level 2 sections
- Create a folder structure to organize the sharded documents
- Maintain all content integrity including code blocks, diagrams, and markdown formatting

## Primary Method: Automatic with markdown-tree

[[LLM: First, check if markdownExploder is set to true in .bmad-core/core-config.yaml. If it is, attempt to run the command: `md-tree explode {input file} {output path}`.

If the command succeeds, inform the user that the document has been sharded successfully and STOP - do not proceed further.

If the command fails (especially with an error indicating the command is not found or not available), inform the user: "The markdownExploder setting is enabled but the md-tree command is not available. Please either:

1. Install @kayvan/markdown-tree-parser globally with: `npm install -g @kayvan/markdown-tree-parser`
2. Or set markdownExploder to false in .bmad-core/core-config.yaml

**IMPORTANT: STOP HERE - do not proceed with manual sharding until one of the above actions is taken.**"

If markdownExploder is set to false, inform the user: "The markdownExploder setting is currently false. For better performance and reliability, you should:

1. Set markdownExploder to true in .bmad-core/core-config.yaml
2. Install @kayvan/markdown-tree-parser globally with: `npm install -g @kayvan/markdown-tree-parser`

I will now proceed with the manual sharding process."

Then proceed with the manual method below ONLY if markdownExploder is false.]]

### Installation and Usage

1. **Install globally**:

   ```bash
   npm install -g @kayvan/markdown-tree-parser
   ```

2. **Use the explode command**:

   ```bash
   # For PRD
   md-tree explode docs/prd.md docs/prd

   # For Architecture
   md-tree explode docs/architecture.md docs/architecture

   # For any document
   md-tree explode [source-document] [destination-folder]
   ```

3. **What it does**:
   - Automatically splits the document by level 2 sections
   - Creates properly named files
   - Adjusts heading levels appropriately
   - Handles all edge cases with code blocks and special markdown

If the user has @kayvan/markdown-tree-parser installed, use it and skip the manual process below.

---

## Manual Method (if @kayvan/markdown-tree-parser is not available or user indicated manual method)

### Task Instructions

1. Identify Document and Target Location

- Determine which document to shard (user-provided path)
- Create a new folder under `docs/` with the same name as the document (without extension)
- Example: `docs/prd.md` → create folder `docs/prd/`

2. Parse and Extract Sections

CRITICAL AEGNT SHARDING RULES:

1. Read the entire document content
2. Identify all level 2 sections (## headings)
3. For each level 2 section:
   - Extract the section heading and ALL content until the next level 2 section
   - Include all subsections, code blocks, diagrams, lists, tables, etc.
   - Be extremely careful with:
     - Fenced code blocks (```) - ensure you capture the full block including closing backticks and account for potential misleading level 2's that are actually part of a fenced section example
     - Mermaid diagrams - preserve the complete diagram syntax
     - Nested markdown elements
     - Multi-line content that might contain ## inside code blocks

CRITICAL: Use proper parsing that understands markdown context. A ## inside a code block is NOT a section header.]]

### 3. Create Individual Files

For each extracted section:

1. **Generate filename**: Convert the section heading to lowercase-dash-case
   - Remove special characters
   - Replace spaces with dashes
   - Example: "## Tech Stack" → `tech-stack.md`

2. **Adjust heading levels**:
   - The level 2 heading becomes level 1 (# instead of ##) in the sharded new document
   - All subsection levels decrease by 1:

   ```txt
     - ### → ##
     - #### → ###
     - ##### → ####
     - etc.
   ```

3. **Write content**: Save the adjusted content to the new file

### 4. Create Index File with Cross-References

Create an `index.md` file in the sharded folder that:

1. Contains the original level 1 heading and any content before the first level 2 section
2. Lists all the sharded files with links and brief descriptions
3. Includes cross-reference map for related sections

```markdown
# Original Document Title

[Original introduction content if any]

## Sections

- [Section Name 1](./section-name-1.md) - Brief description
- [Section Name 2](./section-name-2.md) - Brief description
- [Section Name 3](./section-name-3.md) - Brief description
  ...

## Cross-References

### Related Sections
- Section Name 1 ↔ Section Name 2 (related concepts)
- Section Name 3 → Section Name 1 (dependency)
```

### 4b. Create Cross-Reference Metadata

For each sharded file, create a metadata section at the top:

```markdown
---
title: "Section Name"
parent: "Original Document Title"
related:
  - section-name-2.md: "Related concept"
  - section-name-3.md: "Dependency"
see_also:
  - ../other-doc/section.md: "External reference"
---
```

This enables:
- **90% token savings**: Only load needed sections
- **Intelligent navigation**: Know related sections
- **Dependency tracking**: Understand section relationships
- **Auto-update capability**: Track which sections reference others
```

### 5. Preserve Special Content

1. **Code blocks**: Must capture complete blocks including:

   ```language
   content
   ```

2. **Mermaid diagrams**: Preserve complete syntax:

   ```mermaid
   graph TD
   ...
   ```

3. **Tables**: Maintain proper markdown table formatting

4. **Lists**: Preserve indentation and nesting

5. **Inline code**: Preserve backticks

6. **Links and references**: Keep all markdown links intact

7. **Template markup**: If documents contain {{placeholders}} ,preserve exactly

### 6. Validation

After sharding:

1. Verify all sections were extracted
2. Check that no content was lost
3. Ensure heading levels were properly adjusted
4. Confirm all files were created successfully

### 7. Create Cross-Reference Map

After sharding, create a `.cross-refs.json` file in the sharded folder:

```json
{
  "document": "original-doc.md",
  "sharded_at": "2025-01-XX",
  "sections": {
    "section-name-1.md": {
      "title": "Section Title 1",
      "references": ["section-name-2.md", "section-name-3.md"],
      "referenced_by": ["section-name-4.md"]
    }
  },
  "token_savings": {
    "original_size": 50000,
    "average_shard_size": 5000,
    "estimated_savings": "90%"
  }
}
```

### 8. Report Results

Provide a summary:

```text
Document sharded successfully:
- Source: [original document path]
- Destination: docs/[folder-name]/
- Files created: [count]
- Token savings: ~90% (load only needed sections)
- Sections:
  - section-name-1.md: "Section Title 1" (references: 2, referenced by: 1)
  - section-name-2.md: "Section Name 2" (references: 0, referenced by: 2)
  ...

Cross-reference map created: docs/[folder-name]/.cross-refs.json
Index file created: docs/[folder-name]/index.md

Usage:
- Load individual sections as needed (90% token savings)
- Use index.md for navigation
- Check .cross-refs.json for related sections
```

## Enhanced Features (v6)

### Cross-Reference Detection

When sharding, automatically detect:
- **Internal references**: Links to other sections in the same document
- **External references**: Links to other documents
- **Dependencies**: Sections that reference each other
- **Related concepts**: Sections with similar keywords

### Token Savings Optimization

- **90% token savings**: Only load sections actually needed
- **Intelligent loading**: Load related sections together when needed
- **Metadata tracking**: Track section sizes and relationships
- **Usage analytics**: Track which sections are loaded most often

### Auto-Update Capability

When source document changes:
- Track which shards need updates
- Preserve customizations in shards
- Update cross-references automatically
- Notify when related sections change

## Important Notes

- Never modify the actual content, only adjust heading levels
- Preserve ALL formatting, including whitespace where significant
- Handle edge cases like sections with code blocks containing ## symbols
- Ensure the sharding is reversible (could reconstruct the original from shards)
- **Cross-references enable 90% token savings** by loading only needed sections
- **Metadata files** (.cross-refs.json) enable intelligent section loading
