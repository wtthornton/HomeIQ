# BMAD Story Creation Process

**Source**: Context7 Research - BMAD Method Library  
**Library**: `/bmadcode/bmad-method`  
**Topic**: Story Creation Workflow  
**Last Updated**: December 19, 2024  
**Trust Score**: 5.1  
**Code Snippets**: 2735  

---

## 🎯 **Executive Summary**

BMAD methodology has a specific 4-step process for creating stories that ensures proper sizing, vertical slicing, and AI agent execution optimization. This process must be followed to create BMAD-compliant stories.

---

## 📋 **BMAD Story Creation Process**

### **Step 1: Identify Vertical Slice**

**Purpose**: Ensure story delivers complete functionality from user perspective

**Questions to Ask**:
- What complete functionality does this deliver?
- What user value does this provide?
- Can this be tested end-to-end?
- Is this a vertical slice or horizontal layer?

**Examples**:
- ✅ **Good**: "User gets weather-aware suggestions when querying climate devices"
- ❌ **Bad**: "Add weather context to unified service" (horizontal layer)

### **Step 2: Validate 2-4 Hour Scope**

**Purpose**: Ensure story is completable by single AI agent in one focused session

**Questions to Ask**:
- Can a junior developer complete this in 2-4 hours?
- Is this a single focused task?
- Will this cause context overflow?
- Can this be broken down further while maintaining vertical slice?

**Sizing Guidelines**:
- **Foundation Stories**: 1-2 points (2-4 hours)
- **Feature Stories**: 2-3 points (2-4 hours)
- **Polish Stories**: 1-2 points (2-4 hours)

### **Step 3: Check Dependencies**

**Purpose**: Ensure proper story sequencing and avoid circular dependencies

**Questions to Ask**:
- What stories must be completed first?
- Are dependencies sequential?
- No circular or future dependencies?
- Are prerequisites clearly identified?

**Dependency Rules**:
- ✅ **Sequential dependencies only**
- ✅ **Clear prerequisite identification**
- ✅ **Logical order of operations**
- ❌ **No circular dependencies**
- ❌ **No future story dependencies**

### **Step 4: Structure Acceptance Criteria**

**Purpose**: Create testable, specific criteria following BMAD format

**BMAD Format**:
```markdown
## Acceptance Criteria

### Functional Requirements
- [ ] [Specific user-facing functionality]
- [ ] [Testable user behavior]
- [ ] [Complete feature delivery]

### Technical Requirements  
- [ ] Code follows [language] best practices
- [ ] Performance requirements met
- [ ] Error handling implemented
- [ ] Unit tests written with >90% coverage
- [ ] Integration tests cover [specific scenarios]
```

---

## 🔧 **Story Template Structure**

### **Required Headers**

```markdown
# Story [ID]: [Title]

**Story ID**: [ID]  
**Title**: [Title]  
**Epic**: [Epic ID]  
**Phase**: [1/2]  
**Priority**: [High/Medium/Low]  
**Estimated Points**: [1-3]  
**Story Type**: [Foundation/Feature/Polish]  
**Dependencies**: [List]  
**Vertical Slice**: [What complete functionality this delivers]  
**AI Agent Scope**: [Confirmation this is 2-4 hour work]  
**Created**: [Date]  
**Last Updated**: [Date]  
```

### **Content Sections**

1. **User Story**: "As a [user type], I want [functionality] so that [benefit]"
2. **Acceptance Criteria**: Separate functional and technical requirements
3. **Implementation Details**: Files to modify, key implementation points
4. **Definition of Done**: Specific deliverables
5. **Testing**: Unit, integration, and user acceptance testing
6. **Risks**: Identified risks and mitigation strategies

---

## ⚠️ **Common Mistakes to Avoid**

### **1. Story Sizing Mistakes**

❌ **Too Large**: 5+ point stories
- **Example**: "Create unified suggestion engine with all contextual patterns" (8 points)
- **Fix**: Break into multiple 2-3 point stories

❌ **Not Focused**: Multiple unrelated tasks
- **Example**: "Create service class and add weather context and write tests"
- **Fix**: Separate into individual stories

### **2. Vertical Slicing Mistakes**

❌ **Horizontal Layers**: Adding features to existing systems
- **Example**: "Add energy context to unified service"
- **Fix**: "User gets energy-aware suggestions for high-power devices"

❌ **Incomplete Functionality**: Stories that don't deliver complete value
- **Example**: "Create weather detector class" (no integration)
- **Fix**: "User gets weather-aware suggestions when querying climate devices"

### **3. Dependency Mistakes**

❌ **Circular Dependencies**: Story A depends on B, B depends on A
❌ **Future Dependencies**: Story depends on work from later stories
❌ **Missing Dependencies**: Stories without clear prerequisites

### **4. Acceptance Criteria Mistakes**

❌ **Combined Requirements**: Mixing functional and technical requirements
- **Example**: "Code should be good and user should see weather suggestions"
- **Fix**: Separate into functional and technical sections

❌ **Vague Criteria**: Non-specific, non-testable criteria
- **Example**: "System should be fast"
- **Fix**: "Response time < 100ms"

---

## 📊 **Quality Validation Checklist**

### **Story Quality Checklist**

- [ ] **Sizing**: 1-3 points (2-4 hours)
- [ ] **Vertical Slice**: Delivers complete functionality
- [ ] **Dependencies**: Sequential, no circular dependencies
- [ ] **Acceptance Criteria**: Separate functional and technical
- [ ] **Testable**: All criteria are verifiable
- [ ] **AI Agent Scope**: Confirmed 2-4 hour work
- [ ] **User Value**: Clear user or business value

### **Epic Quality Checklist**

- [ ] **Epic Description**: 2-3 sentences, clear objective
- [ ] **Business Value**: Clear value proposition
- [ ] **Success Criteria**: Measurable outcomes
- [ ] **Story Sequence**: Logical, sequential order
- [ ] **Timeline**: Realistic phase-based delivery
- [ ] **Risk Mitigation**: Identified risks and solutions

---

## 🎯 **Context7 Integration**

### **Research Commands**
```yaml
- context7-docs bmad-method story creation workflow
- context7-docs bmad-method story sizing guidelines
- context7-docs bmad-method vertical slicing
- context7-docs bmad-method acceptance criteria structure
```

### **Validation Commands**
```yaml
- context7-kb-search "BMAD story creation process"
- context7-kb-search "story sizing validation"
- context7-kb-search "vertical slicing requirements"
```

---

## 📚 **Related Documentation**

- [BMAD Epic and Story Best Practices](bmad-epic-story-best-practices.md)
- [BMAD Story Template Structure](bmad-story-template-structure.md)
- [BMAD Quality Checklist](bmad-quality-checklist.md)

---

## 🔄 **Update History**

- **2024-12-19**: Initial creation from Context7 research
- **2024-12-19**: Added 4-step process validation
- **2024-12-19**: Added common mistakes and anti-patterns
- **2024-12-19**: Added quality validation checklist
