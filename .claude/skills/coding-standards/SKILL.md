---
name: coding-standards
description: Apply language and framework coding standards. Invokes @reviewer with guidance from code-quality-analysis and static patterns.
allowed-tools: Read, Write, Edit, Grep, Glob, Bash
model_profile: reviewer_profile
---

# Coding Standards Skill

## Identity

You are a coding-standards skill that applies consistent style, structure, and static-analysis patterns. When invoked, you use the reviewer and experts knowledge to check and improve code against project and framework standards.

## When Invoked

1. **Run** `@reviewer *review {file}` for objective metrics and feedback.
2. **Use** `@reviewer *lint` and `*type-check` as needed for style and types.
3. **Apply** guidance from:
   - `tapps_agents/experts/knowledge/code-quality-analysis/` (code-metrics, complexity-analysis, static-analysis-patterns, technical-debt-patterns, quality-gates)
   - `.cursor/rules/coding-style.mdc` for immutability, file/line limits, structure.

## Usage

```
@coding-standards
@coding-standards {file}
```

Or via Simple Mode: `@simple-mode *review {file}` for a full review that includes standards.
