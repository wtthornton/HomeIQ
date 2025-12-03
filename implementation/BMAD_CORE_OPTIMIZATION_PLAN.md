# BMAD Core Files Optimization Plan

**Date:** December 2025  
**Goal:** Reduce context window usage by 40-60% while maintaining quality and exactness  
**Strategy:** Apply Context7 best practices, remove redundancy, consolidate content

## Analysis Summary

### Files Loaded by Agents

#### Always Loaded (All Agents)
- `.bmad-core/core-config.yaml` - Project configuration (226 lines)
- Agent-specific `.mdc` files in `.cursor/rules/bmad/` - Agent activation rules
- Agent-specific `.md` files in `.bmad-core/agents/` - Full agent definitions

#### Agent-Specific Always Files (from core-config.yaml)
- **architect**: tech-stack.md, source-tree.md, coding-standards.md, performance-patterns.md
- **dev**: tech-stack.md, source-tree.md, coding-standards.md, performance-patterns.md, performance-checklist.md
- **qa**: tech-stack.md, coding-standards.md, testing-strategy.md, performance-patterns.md, performance-anti-patterns.md
- **bmad-master**: tech-stack.md, source-tree.md, coding-standards.md
- **pm**: tech-stack.md, source-tree.md

### Optimization Opportunities

#### 1. Agent File Duplication (HIGH PRIORITY)
**Issue:** `.mdc` files duplicate most content from `.md` files  
**Impact:** ~50% redundancy in agent definitions  
**Solution:** 
- Make `.mdc` files minimal wrappers (reference `.md` files)
- Consolidate YAML blocks to single source
- **Estimated Savings:** 30-40% reduction in agent file size

#### 2. Architecture Documentation Size (HIGH PRIORITY)
**Issue:** Large docs loaded by multiple agents
- `source-tree.md`: 526 lines
- `performance-patterns.md`: 412 lines
- `performance-anti-patterns.md`: 634 lines
- `coding-standards.md`: 387 lines
- `tech-stack.md`: 291 lines

**Solution:**
- Extract verbose examples to separate reference files
- Consolidate performance-patterns and performance-anti-patterns
- Use concise summaries with references
- **Estimated Savings:** 40-50% reduction per file

#### 3. Redundant Context7 Instructions (MEDIUM PRIORITY)
**Issue:** Context7 rules repeated in every agent file  
**Solution:** Extract to shared reference, reference from agents  
**Estimated Savings:** 10-15% per agent file

#### 4. Verbose Examples (MEDIUM PRIORITY)
**Issue:** Long code examples in documentation  
**Solution:** Extract to examples directory, reference from docs  
**Estimated Savings:** 20-30% in affected files

## Implementation Plan

### Phase 1: Agent Files Optimization
1. ✅ Analyze duplication between .mdc and .md files
2. ⏳ Optimize .mdc files to minimal wrappers
3. ⏳ Consolidate YAML blocks
4. ⏳ Extract Context7 rules to shared reference

### Phase 2: Architecture Docs Optimization
1. ⏳ Optimize source-tree.md (remove verbose structure details)
2. ⏳ Consolidate performance-patterns.md and performance-anti-patterns.md
3. ⏳ Optimize coding-standards.md (extract examples)
4. ⏳ Optimize tech-stack.md (consolidate tables)

### Phase 3: Context7 Best Practices
1. ⏳ Apply topic-focused documentation
2. ⏳ Add token budget guidance
3. ⏳ Implement progressive loading patterns
4. ⏳ Add caching strategies documentation

### Phase 4: Validation
1. ⏳ Verify all agents still function correctly
2. ⏳ Measure token savings
3. ⏳ Document optimization results

## Context7 Best Practices Applied

1. **Topic Focus**: Documentation organized by specific topics
2. **Token Limits**: Clear guidance on token budgets per agent
3. **Progressive Loading**: Load only what's needed
4. **Caching**: Reference patterns instead of duplicating
5. **Concise Examples**: Minimal examples with references to full docs

## Expected Results

- **Agent Files**: 30-40% reduction
- **Architecture Docs**: 40-50% reduction
- **Total Context Window**: 40-60% reduction
- **Quality**: Maintained (references to full docs preserved)
- **Exactness**: Maintained (all critical information preserved)

