# BMAD Core v6 Improvements Proposal

**Date:** January 2025  
**Current Version:** 4.44.1  
**Target:** BMAD-METHOD v6 Alpha Features  
**Status:** For Review and Approval

## Executive Summary

This document outlines proposed improvements to the `.bmad-core` implementation based on BMAD-METHOD v6 features. The current implementation is at v4.44.1 and includes solid foundations (Context7 KB, progressive code review, document sharding). This proposal identifies 25+ enhancements organized into 8 categories.

---

## 1. Scale-Adaptive Intelligence ⚡

### 1.1 Automatic Workflow Track Selection
**Priority:** High  
**Effort:** Medium (2-3 days)

**Current State:**
- Manual workflow selection (greenfield vs brownfield, fullstack vs service vs UI)
- No automatic complexity assessment

**Proposed Enhancement:**
- Add `*workflow-init` command to analyze project and recommend workflow track
- Three intelligent tracks:
  - **⚡ Quick Flow**: Bug fixes, small features (tech spec only, < 5 min setup)
  - **📋 BMad Method**: Products, platforms (PRD + Architecture + UX, < 15 min setup)
  - **🏢 Enterprise**: Compliance, scale (Full governance suite, < 30 min setup)

**Implementation:**
- New task: `workflow-init.md` in `.bmad-core/tasks/`
- Analyzes project size, complexity, existing docs, codebase structure
- Recommends appropriate workflow track with reasoning
- Updates `core-config.yaml` with selected track

**Files to Create/Modify:**
- `.bmad-core/tasks/workflow-init.md` (new)
- `.bmad-core/core-config.yaml` (add `workflow_track` field)
- `.bmad-core/user-guide.md` (document new command)

---

### 1.2 Dynamic Planning Depth
**Priority:** Medium  
**Effort:** Medium (2-3 days)

**Current State:**
- Fixed planning depth regardless of project complexity
- All projects follow same PRD → Architecture → Stories flow

**Proposed Enhancement:**
- Scale-adaptive planning that adjusts depth based on:
  - Project size (LOC, files, services)
  - Risk profile (new vs existing, criticality)
  - Team size and timeline
- Quick Flow: Tech spec only, minimal documentation
- Standard: Full PRD + Architecture
- Enterprise: Full governance with compliance checks

**Implementation:**
- Enhance existing workflow YAML files with `planning_depth` field
- Add complexity assessment logic to `workflow-init.md`
- Modify templates to support optional sections based on depth

**Files to Modify:**
- `.bmad-core/workflows/*.yaml` (add planning_depth)
- `.bmad-core/tasks/workflow-init.md` (complexity assessment)
- `.bmad-core/templates/*-tmpl.yaml` (optional sections)

---

## 2. Visual Workflows & Diagrams 🎨

### 2.1 SVG Workflow Diagrams
**Priority:** High  
**Effort:** High (1 week)

**Current State:**
- Mermaid diagrams in workflows (text-based, requires plugins)
- No visual workflow representation in documentation

**Proposed Enhancement:**
- Generate SVG workflow diagrams for each workflow
- Beautiful visual representations showing:
  - Complete methodology flow
  - Agent handoffs
  - Decision points
  - Phase transitions
- Embed in user guide and workflow documentation

**Implementation:**
- Create SVG generator script/tool
- Generate diagrams for all 6 existing workflows
- Add to `.bmad-core/workflows/*.yaml` as `svg_diagram` field
- Include in user guide with rendering instructions

**Files to Create/Modify:**
- `.bmad-core/utils/svg-workflow-generator.md` (new - instructions for generating SVGs)
- `.bmad-core/workflows/*.yaml` (add `svg_diagram` field)
- `.bmad-core/user-guide.md` (add visual workflow section)

**Note:** Could use existing Mermaid → SVG conversion tools or create custom SVG templates

---

### 2.2 Interactive Workflow Visualizer
**Priority:** Low  
**Effort:** High (2 weeks)

**Proposed Enhancement:**
- Web-based interactive workflow visualizer
- Click through workflow steps
- Show current position in workflow
- Agent recommendations at each step

**Implementation:**
- HTML/JS tool (optional, nice-to-have)
- Could be separate tool or integrated into docs

---

## 3. Enhanced Agent System 🤖

### 3.1 Additional Specialized Agents
**Priority:** Medium  
**Effort:** Medium (1 week per agent)

**Current State:**
- 9 agents: analyst, architect, bmad-master, bmad-orchestrator, dev, pm, po, qa, sm, ux-expert

**Proposed New Agents (from v6):**
1. **Test Architect** (enhancement of QA) - Already partially implemented
2. **Game Architect** - For game development projects
3. **Game Designer** - Game design and mechanics
4. **Game Developer** - Game-specific development
5. **Tech Writer** - Technical documentation specialist

**Implementation:**
- Create new agent files in `.bmad-core/agents/`
- Add to agent teams YAML files
- Update user guide with new agent descriptions

**Files to Create:**
- `.bmad-core/agents/game-architect.md` (new)
- `.bmad-core/agents/game-designer.md` (new)
- `.bmad-core/agents/game-developer.md` (new)
- `.bmad-core/agents/tech-writer.md` (new)

---

### 3.2 Agent Customization System
**Priority:** High  
**Effort:** Medium (3-4 days)

**Current State:**
- Basic agent personas in YAML
- No user customization mechanism

**Proposed Enhancement:**
- Update-safe customization system
- Allow users to customize:
  - Agent personalities
  - Expertise areas
  - Communication styles
  - Custom instructions
- Customizations persist through updates (separate from core files)

**Implementation:**
- Create `.bmad-core/customizations/` directory (gitignored)
- Customization files: `{agent-id}-custom.yaml`
- Agent files load customizations if present
- Installer preserves customizations during updates

**Files to Create/Modify:**
- `.bmad-core/customizations/` (new directory)
- `.bmad-core/.gitignore` (add customizations/)
- `.bmad-core/agents/*.md` (add customization loading logic)
- `.bmad-core/user-guide.md` (document customization)

---

### 3.3 Multi-Language Support
**Priority:** Medium  
**Effort:** Medium (1 week)

**Proposed Enhancement:**
- Separate settings for communication language and code output language
- Agent responses in user's preferred language
- Code output in project's language (Python, TypeScript, etc.)
- Template translations for common languages

**Implementation:**
- Add `language` settings to `core-config.yaml`:
  ```yaml
  language:
    communication: en  # Agent responses
    code_output: auto  # Detect from project
  ```
- Update agent personas to respect language settings
- Create language-specific template variants (optional)

**Files to Modify:**
- `.bmad-core/core-config.yaml` (add language section)
- `.bmad-core/agents/*.md` (add language awareness)

---

## 4. Expanded Workflow Library 📋

### 4.1 Additional Workflow Types
**Priority:** Medium  
**Effort:** Medium (2-3 days per workflow)

**Current State:**
- 6 workflows (3 greenfield, 3 brownfield)
- Focused on fullstack/service/UI

**Proposed New Workflows:**
1. **Quick Fix Workflow** - Bug fixes, small changes (< 1 hour)
2. **API Development Workflow** - API-first development
3. **Mobile App Workflow** - Mobile-specific (React Native, Flutter)
4. **Data Pipeline Workflow** - ETL, data processing
5. **DevOps/Infrastructure Workflow** - Infrastructure as code
6. **Microservices Workflow** - Multi-service architecture
7. **Legacy Modernization Workflow** - Specific brownfield modernization

**Implementation:**
- Create new workflow YAML files
- Add workflow selection to `workflow-init.md`
- Document in user guide

**Files to Create:**
- `.bmad-core/workflows/quick-fix.yaml` (new)
- `.bmad-core/workflows/api-development.yaml` (new)
- `.bmad-core/workflows/mobile-app.yaml` (new)
- `.bmad-core/workflows/data-pipeline.yaml` (new)
- `.bmad-core/workflows/devops-infrastructure.yaml` (new)
- `.bmad-core/workflows/microservices.yaml` (new)
- `.bmad-core/workflows/legacy-modernization.yaml` (new)

---

### 4.2 Workflow Templates Library
**Priority:** Low  
**Effort:** Low (1-2 days)

**Proposed Enhancement:**
- Pre-built workflow templates for common scenarios
- Industry-specific workflows (healthcare, finance, etc.)
- Team size adaptations (solo, small team, enterprise)

**Files to Create:**
- `.bmad-core/workflows/templates/` (new directory)
- Industry-specific workflow variants

---

## 5. Enhanced Document Management 📄

### 5.1 Advanced Document Sharding
**Priority:** High  
**Effort:** Medium (3-4 days)

**Current State:**
- Basic document sharding exists
- Manual sharding process

**Proposed Enhancement:**
- Enhanced sharding with 90% token savings claim
- Intelligent section detection
- Cross-reference management
- Automatic shard updates when source changes
- Shard dependency tracking

**Implementation:**
- Enhance `shard-doc.md` task
- Add shard metadata tracking
- Cross-reference resolver
- Auto-update mechanism

**Files to Modify:**
- `.bmad-core/tasks/shard-doc.md` (enhance)
- `.bmad-core/core-config.yaml` (add sharding config)

---

### 5.2 Document Versioning & History
**Priority:** Low  
**Effort:** Medium (1 week)

**Proposed Enhancement:**
- Track document versions
- Change history
- Rollback capability
- Diff visualization

**Implementation:**
- Add version tracking to sharded documents
- Create version history files
- Add rollback commands

---

## 6. BMad Builder Module 🏗️

### 6.1 Custom Agent Builder
**Priority:** Low  
**Effort:** High (2-3 weeks)

**Proposed Enhancement:**
- Allow users to create custom agents
- Define custom workflows
- Build domain-specific modules (legal, medical, finance, education)
- Share in community marketplace (future)

**Implementation:**
- Create builder templates and guides
- Agent creation wizard
- Workflow builder tool
- Validation system

**Files to Create:**
- `.bmad-core/builder/` (new directory)
- `.bmad-core/builder/agent-builder-guide.md` (new)
- `.bmad-core/builder/workflow-builder-guide.md` (new)

**Note:** This is a major feature that may be better as separate module

---

## 7. Web Bundles & Integration 🌐

### 7.1 Web Bundle Generation
**Priority:** Medium  
**Effort:** Medium (1 week)

**Current State:**
- Manual web bundle creation (team-fullstack.txt)
- No automated bundle generation

**Proposed Enhancement:**
- Automated web bundle generation
- Support for:
  - ChatGPT Custom GPTs
  - Claude Projects
  - Gemini Gems
- Include all necessary files in bundle
- Bundle validation

**Implementation:**
- Create bundle generator script/task
- Bundle templates for each platform
- Validation checks

**Files to Create:**
- `.bmad-core/tasks/generate-web-bundle.md` (new)
- `.bmad-core/utils/bundle-templates/` (new directory)

---

### 7.2 Enhanced IDE Integration
**Priority:** High  
**Effort:** Medium (1 week)

**Current State:**
- Cursor integration exists
- OpenCode integration exists
- Codex integration exists

**Proposed Enhancement:**
- Enhanced installer with better detection
- Auto-refresh capabilities
- Integration health checks
- Better error messages

**Files to Modify:**
- Installer improvements (external tool)
- `.bmad-core/install-manifest.yaml` (enhance)

---

## 8. Quality & Performance Improvements 🔧

### 8.1 Enhanced Progressive Code Review
**Priority:** Medium  
**Effort:** Low (2-3 days)

**Current State:**
- Progressive code review implemented
- Background review (optional, disabled)

**Proposed Enhancement:**
- Improve review accuracy
- Better cost controls
- Review caching improvements
- Integration with more IDEs

**Files to Modify:**
- `.bmad-core/core-config.yaml` (review config)
- `.bmad-core/tasks/progressive-code-review.md` (enhance)

---

### 8.2 Performance Monitoring
**Priority:** Low  
**Effort:** Medium (1 week)

**Proposed Enhancement:**
- Track workflow execution times
- Agent performance metrics
- Token usage tracking
- Cost estimation

**Implementation:**
- Add metrics collection
- Performance dashboard (optional)
- Cost tracking

---

### 8.3 Update Safety Improvements
**Priority:** High  
**Effort:** Medium (1 week)

**Current State:**
- Install manifest tracks files
- No update safety mechanism

**Proposed Enhancement:**
- Ensure customizations persist
- Safe update process
- Backup before updates
- Rollback capability

**Implementation:**
- Enhance installer with update safety
- Customization preservation
- Backup system

---

## 9. Documentation & User Experience 📚

### 9.1 Enhanced User Guide
**Priority:** High  
**Effort:** Medium (3-4 days)

**Proposed Enhancement:**
- Add visual workflow diagrams
- Better getting started guide
- Video tutorial links
- Common scenarios section
- Troubleshooting guide

**Files to Modify:**
- `.bmad-core/user-guide.md` (major update)

---

### 9.2 Quick Reference Cards
**Priority:** Low  
**Effort:** Low (1-2 days)

**Proposed Enhancement:**
- One-page quick reference
- Command cheat sheet
- Agent selection guide
- Workflow decision tree

**Files to Create:**
- `.bmad-core/docs/quick-reference.md` (new)

---

## 10. Advanced Features (Future) 🚀

### 10.1 BMad Core Framework (COR)
**Priority:** Low (Research)  
**Effort:** High (4+ weeks)

**Proposed Enhancement:**
- Implement COR (Collaboration Optimized Reflection Engine)
- Universal framework for human-AI collaboration
- Foundation for custom modules

**Note:** This is a major architectural change - research first

---

### 10.2 Community Marketplace
**Priority:** Low (Future)  
**Effort:** Very High (months)

**Proposed Enhancement:**
- Share custom agents
- Share custom workflows
- Community templates
- Rating system

**Note:** Long-term vision, not immediate priority

---

## Implementation Priority Matrix

### Phase 1: High Priority, High Impact (Weeks 1-2)
1. ✅ Scale-Adaptive Intelligence (`*workflow-init`)
2. ✅ SVG Workflow Diagrams
3. ✅ Agent Customization System
4. ✅ Enhanced Document Sharding
5. ✅ Enhanced User Guide

### Phase 2: Medium Priority, High Impact (Weeks 3-4)
6. ✅ Additional Workflow Types (Quick Fix, API, Mobile)
7. ✅ Multi-Language Support
8. ✅ Web Bundle Generation
9. ✅ Additional Specialized Agents (Game Architect, Tech Writer)

### Phase 3: Medium Priority, Medium Impact (Weeks 5-6)
10. ✅ Dynamic Planning Depth
11. ✅ Update Safety Improvements
12. ✅ Enhanced IDE Integration
13. ✅ More Workflow Types (Data Pipeline, DevOps, Microservices)

### Phase 4: Low Priority, Nice-to-Have (Future)
14. ⏸️ Interactive Workflow Visualizer
15. ⏸️ Document Versioning
16. ⏸️ BMad Builder Module
17. ⏸️ Performance Monitoring
18. ⏸️ Quick Reference Cards

---

## Estimated Effort Summary

| Category | Effort | Priority |
|----------|--------|----------|
| Scale-Adaptive Intelligence | 1 week | High |
| Visual Workflows | 1 week | High |
| Enhanced Agents | 2 weeks | Medium |
| Expanded Workflows | 2 weeks | Medium |
| Document Management | 1 week | High |
| Web Bundles | 1 week | Medium |
| Quality Improvements | 1 week | Medium |
| Documentation | 1 week | High |
| **Total Phase 1-3** | **10 weeks** | - |

---

## Approval Checklist

Please review and approve each category:

- [ ] **1. Scale-Adaptive Intelligence** - Automatic workflow selection and dynamic planning
- [ ] **2. Visual Workflows** - SVG diagrams for better visualization
- [ ] **3. Enhanced Agent System** - Customization, new agents, multi-language
- [ ] **4. Expanded Workflow Library** - More workflow types for different scenarios
- [ ] **5. Enhanced Document Management** - Advanced sharding and versioning
- [ ] **6. BMad Builder Module** - Custom agent/workflow creation (future)
- [ ] **7. Web Bundles & Integration** - Better IDE integration and bundles
- [ ] **8. Quality & Performance** - Code review improvements, monitoring
- [ ] **9. Documentation & UX** - Enhanced guides and references
- [ ] **10. Advanced Features** - COR framework, marketplace (research/future)

---

## Next Steps

1. **Review this proposal** - Approve/reject/modify categories
2. **Prioritize features** - Select which features to implement first
3. **Create implementation plan** - Detailed tasks for approved features
4. **Begin Phase 1** - Start with high-priority, high-impact features

---

## Questions for Discussion

1. Which features are most valuable for your use case?
2. Should we prioritize quick wins or comprehensive overhaul?
3. Are there any BMAD-METHOD v6 features we missed?
4. Should BMad Builder be a separate module or integrated?
5. What's the target timeline for implementation?

---

**Document Status:** Ready for Review  
**Last Updated:** January 2025  
**Next Review:** After approval

