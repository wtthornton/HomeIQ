# BMAD Epic and Story Creation Best Practices

**Source**: Context7 Research - BMAD Method Library  
**Library**: `/bmadcode/bmad-method`  
**Topic**: Epic and Story Creation  
**Last Updated**: December 19, 2024  
**Trust Score**: 5.1  
**Code Snippets**: 2735  

---

## 🎯 **Executive Summary**

BMAD methodology has specific requirements for epic and story creation that differ from standard agile practices. Key principles include **2-4 hour story scope**, **vertical slicing**, **BMAD-specific acceptance criteria structure**, and **AI agent execution optimization**.

---

## 📋 **Critical BMAD Requirements**

### **1. Story Sizing Guidelines**

**BMAD Requirement**: "Think 'junior developer working for 2-4 hours' - stories must be small, focused, and self-contained"

**Story Types and Scope**:
- **Foundation Stories**: 1-2 points (2-4 hours) - Individual systems with TDD
- **Feature Stories**: 2-3 points (2-4 hours) - Complete functionality with validation
- **Polish Stories**: 1-2 points (2-4 hours) - Testing, documentation, optimization

**Sizing Rules**:
- ✅ **Maximum 3 points per story**
- ✅ **Completable by single AI agent in one focused session**
- ✅ **No context overflow**
- ❌ **No 5+ point stories**
- ❌ **No multi-day stories**

### **2. Vertical Slicing Requirements**

**BMAD Requirement**: "Each story should be a 'vertical slice' delivering complete functionality"

**Vertical Slice Definition**:
- **Complete functionality** from user perspective
- **End-to-end value delivery**
- **Testable and demonstrable**
- **No horizontal layers** (avoid "add X to Y" stories)

**Examples**:
- ✅ **Good**: "User gets weather-aware suggestions when querying climate devices"
- ❌ **Bad**: "Add weather context to unified service" (horizontal layer)

### **3. Story Sequencing Requirements**

**BMAD Requirements**:
- Stories within each epic MUST be logically sequential
- No story should depend on work from a later story or epic
- Identify and note direct prerequisite stories
- Focus on "what" and "why" not "how"

**Sequencing Rules**:
- ✅ **Sequential dependencies only**
- ✅ **Clear prerequisite identification**
- ✅ **Logical order of operations**
- ❌ **No circular dependencies**
- ❌ **No future story dependencies**

---

## 📝 **BMAD Story Template Structure**

### **Required Story Headers**

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

### **BMAD-Specific Acceptance Criteria Structure**

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

## 🔧 **Implementation Guidelines**

### **1. Story Creation Process**

**Step 1: Identify Vertical Slice**
- What complete functionality does this deliver?
- What user value does this provide?
- Can this be tested end-to-end?

**Step 2: Validate 2-4 Hour Scope**
- Can a junior developer complete this in 2-4 hours?
- Is this a single focused task?
- Will this cause context overflow?

**Step 3: Check Dependencies**
- What stories must be completed first?
- Are dependencies sequential?
- No circular or future dependencies?

**Step 4: Structure Acceptance Criteria**
- Separate functional and technical requirements
- Make criteria testable and specific
- Include performance and quality requirements

### **2. Epic Structure Requirements**

**Epic Headers**:
```markdown
**Epic ID**: [ID]  
**Title**: [Title]  
**Status**: [Planning/In Progress/Done]  
**Priority**: [High/Medium/Low]  
**Estimated Duration**: [X weeks]  
**Value**: [Score/10]  
**Complexity**: [Score/10]  
**Created**: [Date]  
**Last Updated**: [Date]  
```

**Epic Content**:
- **Epic Description**: 2-3 sentences describing objective and value
- **Business Value**: Clear value proposition
- **Success Criteria**: Measurable outcomes
- **Stories**: List with story type and points
- **Timeline**: Phase-based delivery
- **Risk Mitigation**: Identified risks and mitigation strategies

### **3. Story Type Guidelines**

#### **Foundation Stories**
- **Purpose**: Create foundational systems and infrastructure
- **Scope**: Individual systems with TDD
- **Points**: 1-2 points
- **Examples**: Create service class, add configuration system, implement basic testing

#### **Feature Stories**
- **Purpose**: Deliver complete user-facing functionality
- **Scope**: Complete features with validation
- **Points**: 2-3 points
- **Examples**: Add weather context to user queries, implement energy-aware suggestions

#### **Polish Stories**
- **Purpose**: Testing, documentation, optimization
- **Scope**: Quality improvements and documentation
- **Points**: 1-2 points
- **Examples**: Comprehensive testing suite, performance optimization, documentation

---

## ⚠️ **Common Anti-Patterns to Avoid**

### **1. Story Sizing Anti-Patterns**

❌ **Too Large**: 5+ point stories
- "Create unified suggestion engine with all contextual patterns" (8 points)
- **Fix**: Break into multiple 2-3 point stories

❌ **Horizontal Layers**: Adding features to existing systems
- "Add energy context to unified service" (horizontal)
- **Fix**: "User gets energy-aware suggestions for high-power devices" (vertical)

### **2. Dependency Anti-Patterns**

❌ **Circular Dependencies**: Story A depends on B, B depends on A
❌ **Future Dependencies**: Story depends on work from later stories
❌ **Missing Dependencies**: Stories without clear prerequisites

### **3. Acceptance Criteria Anti-Patterns**

❌ **Combined Requirements**: Mixing functional and technical requirements
❌ **Vague Criteria**: "Code should be good" instead of "Code follows Python best practices"
❌ **Non-Testable**: "System should be fast" instead of "Response time < 100ms"

---

## 📊 **Quality Checklist**

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

## 🎯 **Context7 Integration Commands**

### **Research Commands**
```yaml
- context7-docs bmad-method epic story creation
- context7-docs bmad-method story sizing guidelines
- context7-docs bmad-method vertical slicing
- context7-docs bmad-method acceptance criteria structure
```

### **Validation Commands**
```yaml
- context7-kb-search "BMAD story sizing"
- context7-kb-search "vertical slicing requirements"
- context7-kb-search "acceptance criteria structure"
```

---

## 📚 **Related Documentation**

- [BMAD Method Library](https://context7.com/bmadcode/bmad-method)
- [Story Creation Workflow](https://github.com/bmadcode/bmad-method/blob/main/dist/expansion-packs/bmad-2d-unity-game-dev/teams/unity-2d-game-team.txt)
- [Epic Details Structure](https://github.com/bmadcode/bmad-method/blob/main/dist/expansion-packs/bmad-2d-unity-game-dev/teams/unity-2d-game-team.txt)

---

## 🔄 **Update History**

- **2024-12-19**: Initial creation from Context7 research
- **2024-12-19**: Added story sizing guidelines and vertical slicing requirements
- **2024-12-19**: Added BMAD-specific acceptance criteria structure
- **2024-12-19**: Added anti-patterns and quality checklist
