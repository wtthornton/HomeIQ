# Step 4: Design Specification - Recommendations Document Format

**Date:** 2025-12-31  
**Workflow:** Simple Mode *build

## Document Design Specification

### Format Standards

**Markdown Format:**
- Use standard markdown syntax
- Headers: # for main title, ## for sections, ### for subsections
- Tables: Use markdown table syntax
- Lists: Use numbered lists for ordered items, bullets for unordered
- Code blocks: Use triple backticks with language tags
- Emphasis: Use **bold** for important terms, *italic* for emphasis

### Typography

**Headers:**
- H1: Document title (single use)
- H2: Major sections (Executive Summary, Critical Issues, etc.)
- H3: Subsections within major sections
- H4: Sub-subsections (if needed)

**Text Formatting:**
- Status indicators: ✅ (fixed/verified), ⚠️ (needs attention), ❌ (blocked)
- Priority indicators: 🔴 (Critical), 🟡 (High), 🟢 (Medium), 🔵 (Low)
- Code references: Use backticks for file paths, commands, code snippets

### Color Palette (Status Indicators)

- ✅ Green: Fixed, Verified, Complete
- ⚠️ Yellow: Needs Attention, Partially Fixed, Pending
- ❌ Red: Blocked, Critical Issue, Failed
- 🔴 Red Circle: Critical Priority
- 🟡 Yellow Circle: High Priority
- 🟢 Green Circle: Medium Priority
- 🔵 Blue Circle: Low Priority

### Spacing System

**Section Spacing:**
- Between major sections: 2 blank lines
- Between subsections: 1 blank line
- Within subsections: No extra spacing

**List Spacing:**
- Between list items: No extra spacing
- After lists: 1 blank line

### Table Design

**Quick Status Summary Table:**
```
| Issue | Status | Action Required |
|-------|--------|-----------------|
```

**Implementation Priority Matrix:**
```
| Priority | Recommendation | Effort | Impact | Timeline |
|----------|---------------|--------|--------|----------|
```

### Code Block Formatting

**Command Examples:**
```bash
python -m tapps_agents.cli reviewer review {file}
```

**File Paths:**
```markdown
`implementation/FINAL_RECOMMENDATIONS_PATTERN_SYNERGY_VALIDATION.md`
```

**Verification Commands:**
```bash
# Check synergy types
python scripts/diagnose_synergy_types.py --use-docker-db
```

### Cross-Reference Format

**Internal References:**
```markdown
See `EXTERNAL_DATA_AUTOMATION_VALIDATION_RECOMMENDATIONS.md` for details.
```

**Cursor Rules References:**
```markdown
See `.cursor/rules/simple-mode.mdc` for Simple Mode usage.
```

### Status Badge Format

**In Text:**
- ✅ **Fixed** - Issue resolved
- ⚠️ **Needs Re-run** - Fix applied, verification needed
- ❌ **Blocked** - Cannot proceed

**In Tables:**
- Use emoji indicators in Status column
- Use text in Action Required column

### Section Templates

**Critical Issue Template:**
```markdown
### N. Issue Name ⚠️ STATUS

**Problem:**
- Bullet point description

**Root Cause:**
- Analysis

**Fix Applied:**
- ✅ What was fixed

**Status:** Current status

**Next Steps:**
- Action items
```

**Recommendation Template:**
```markdown
#### N. Recommendation Name

**Action:** What to do

**Why:**
- Reason

**Expected Results:**
- Outcome

**Verification:**
\`\`\`bash
# Commands
\`\`\`

**Current Status:**
- Latest results
```

### Document Metadata

**Header Format:**
```markdown
**Date:** YYYY-MM-DD  
**Last Updated:** YYYY-MM-DD (Description)  
**Status:** Current Status  
**Author:** AI Assistant (via tapps-agents)

**Validation Status:** ✅ Description
```

### Accessibility

- Use descriptive link text (not "click here")
- Alt text for any images (if added)
- Clear heading hierarchy
- Tables have headers

### Consistency Rules

- Always use same status indicators throughout
- Always use same priority indicators
- Always format commands the same way
- Always use same date format (YYYY-MM-DD)
- Always use same file path format (relative paths)
