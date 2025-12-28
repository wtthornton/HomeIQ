# 📚 Documentation Index

**Last Updated:** December 28, 2025
**Status:** ✅ Recently Cleaned & Organized + Phase 1 AI Containerization Complete

> **🎉 Documentation Cleanup Complete!** (October 20, 2025)  
> - API docs consolidated (5 files → 1)
> - Historical docs archived (~51 files)
> - Agent rules updated for clarity
> - See [Cleanup Report](../implementation/DOCUMENTATION_CLEANUP_EXECUTIVE_SUMMARY.md)

---

## 🚀 Quick Start

### For Developers
- **API Reference** → [api/API_REFERENCE.md](api/API_REFERENCE.md)
- **Architecture** → [architecture/](architecture/)
- **Deployment** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Quick Start** → [QUICK_START.md](QUICK_START.md)

### For AI Agents
- **Priority:** Focus on docs/, ignore archive/
- **API Docs:** Use [api/API_REFERENCE.md](api/API_REFERENCE.md) only
- **Archive:** IGNORE docs/archive/ unless researching history

---

## 📖 Documentation Structure

### Active Reference Documentation

#### 1. API Documentation
**Location:** `docs/api/`  
**Status:** ✅ Consolidated (October 2025)

- **[API_REFERENCE.md](api/API_REFERENCE.md)** - **SINGLE SOURCE OF TRUTH**
  - All 65 API endpoints documented
  - Admin API, Data API, Sports, AI Automation, Statistics
  - Request/response examples
  - Integration patterns

**Superseded Files:** (marked with ⛔ redirect notices)
- API_DOCUMENTATION.md → Use API_REFERENCE.md
- API_COMPREHENSIVE_REFERENCE.md → Use API_REFERENCE.md
- API_ENDPOINTS_REFERENCE.md → Use API_REFERENCE.md
- API_DOCUMENTATION_AI_AUTOMATION.md → Use API_REFERENCE.md
- API_STATISTICS_ENDPOINTS.md → Use API_REFERENCE.md

---

#### 2. Phase 1 AI Services (NEW)
**Location:** `docs/`  
**Status:** ✅ Complete (October 24, 2025)

- **[PHASE1_AI_CONTAINERIZATION_COMPLETE.md](PHASE1_AI_CONTAINERIZATION_COMPLETE.md)** - **COMPLETE SUMMARY**
  - 5 containerized AI services operational
  - OpenVINO, ML, NER, OpenAI, AI Core services
  - Microservices architecture with health monitoring
  - Comprehensive testing and documentation

**Updated Architecture:**
- **[architecture.md](architecture.md)** - Updated with Phase 1 AI Services section
- **[SERVICES_OVERVIEW.md](SERVICES_OVERVIEW.md)** - Added AI services documentation
- **[README.md](../README.md)** - Updated with containerized AI services

#### 2b. Home Type Categorization System (NEW - November 2025)
**Location:** `docs/architecture/`  
**Status:** ✅ Complete (November 25, 2025)

- **[home-type-categorization.md](architecture/home-type-categorization.md)** - **NEW ARCHITECTURE DOCUMENT**
  - ML-based home classification using RandomForest
  - API endpoints for profiling and classification
  - Integration with suggestion ranking and pattern detection
  - Event categorization system

**Updated Documentation:**
- **[architecture.md](architecture.md)** - Added Home Type Categorization section
- **[architecture/index.md](architecture/index.md)** - Added to architecture index
- **[API_REFERENCE.md](api/API_REFERENCE.md)** - Added Home Type API endpoints

---

#### 3. Architecture Documentation
**Location:** `docs/architecture/`  
**Status:** ✅ Current (sharded structure)

- **[index.md](architecture/index.md)** - Architecture overview
- **[tech-stack.md](architecture/tech-stack.md)** - Technology stack
- **[source-tree.md](architecture/source-tree.md)** - Source tree structure
- **[coding-standards.md](architecture/coding-standards.md)** - Code quality standards
- **[data-models.md](architecture/data-models.md)** - Data model definitions
- **[database-schema.md](architecture/database-schema.md)** - Database schemas
- **[deployment-architecture.md](architecture/deployment-architecture.md)** - Deployment patterns
- **[testing-strategy.md](architecture/testing-strategy.md)** - Testing approach
- **[monitoring-and-observability.md](architecture/monitoring-and-observability.md)** - Monitoring
- **[security-and-performance.md](architecture/security-and-performance.md)** - Security
- **[core-workflows.md](architecture/core-workflows.md)** - Core workflows
- [+ 16 more architecture docs]

---

#### 3. Product Requirements (PRD)
**Location:** `docs/prd/`  
**Status:** ✅ Current (sharded structure)

- **[index.md](prd/index.md)** - PRD overview
- **[requirements.md](prd/requirements.md)** - Functional & non-functional requirements
- **[epic-list.md](prd/epic-list.md)** - All epics
- **[epic-1-foundation-core-infrastructure.md](prd/epic-1-foundation-core-infrastructure.md)**
- **[epic-2-data-capture-normalization.md](prd/epic-2-data-capture-normalization.md)**
- [+ 50 more PRD shards including epic-34]

---

#### 4. User Stories
**Location:** `docs/stories/`  
**Status:** ✅ Current (222 stories)

- **Epic 1-34 Stories** - All development stories
- **Format:** `{epic}.{story}-{slug}.md`
- **Example:** `31.1-weather-api-service-foundation.md`

---

#### 5. Quality Assurance
**Location:** `docs/qa/`  
**Status:** ✅ Current

- **assessments/** - Risk assessments and test designs (19 files)
- **gates/** - Quality gates (32 files)
- **Format:** `{epic}.{story}-{type}-{YYYYMMDD}.md`

---

#### 6. Knowledge Base
**Location:** `docs/kb/`  
**Status:** ✅ Current (Context7 cache)

- **context7-cache/** - Cached library documentation (101 files)
- **index.json** - Knowledge base index
- **Purpose:** Fast lookup for library docs (87% hit rate)

---

#### 7. Research
**Location:** `docs/research/`  
**Status:** ✅ Current (5 files)

- Technical research documents
- Technology evaluations
- Decision rationale

---

### Guides & Manuals (Root docs/)

#### Deployment & Operations
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment guide
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Deployment checklist
- **[QUICK_START.md](QUICK_START.md)** - Quick start guide

#### User Guides
- **[USER_MANUAL.md](USER_MANUAL.md)** - User manual
- **[TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md)** - Troubleshooting

#### Technical Guides
- **[DOCKER_STRUCTURE_GUIDE.md](DOCKER_STRUCTURE_GUIDE.md)** - Docker organization
- **[SECURITY_CONFIGURATION.md](SECURITY_CONFIGURATION.md)** - Security setup
- **[CLI_REFERENCE.md](CLI_REFERENCE.md)** - CLI tools

#### Specific Features
- **[EPIC_23_USER_GUIDE.md](EPIC_23_USER_GUIDE.md)** - Epic 23 features
- **[CONVERSATIONAL_UI_USER_GUIDE.md](CONVERSATIONAL_UI_USER_GUIDE.md)** - AI UI
- **[AI_AUTOMATION_COMPREHENSIVE_GUIDE.md](AI_AUTOMATION_COMPREHENSIVE_GUIDE.md)** - AI automation
- **[CALENDAR_SERVICE_DOCUMENTATION_INDEX.md](CALENDAR_SERVICE_DOCUMENTATION_INDEX.md)** - Calendar service

---

### Historical Documentation (Archive)

#### Archive Structure
**Location:** `docs/archive/`  
**Agent Rule:** **IGNORE THIS DIRECTORY**

```
docs/archive/
├── README.md             # Archive guide
├── 2024/                 # 2024 artifacts (~11 files)
│   └── planning/         # Early project planning
├── 2025-q1/              # Jan-Mar 2025 (~3 files)
│   ├── DEPLOYMENT_STATUS_JANUARY_2025.md
│   ├── FUTURE_ENHANCEMENTS.md
│   └── RECENT_FIXES_JANUARY_2025.md
├── 2025-q2/              # Apr-Jun 2025 (empty)
├── 2025-q3/              # Jul-Sep 2025 (~21 files)
│   ├── summaries/        # Epic completion summaries (20 files)
│   └── CHANGELOG_EPIC_23.md
└── 2025-q4/              # Oct-Dec 2025 (~15 files)
    ├── DEPLOYMENT_READY.md
    ├── DEPLOYMENT_SUCCESS_REPORT.md
    ├── E2E_TEST_RESULTS.md
    └── [12 more status/completion files]
```

**Purpose:**
- Preserve historical context
- Document project evolution
- Support historical research

**Usage:**
- Rarely referenced (agents ignore)
- Only for historical investigation
- Organized by quarter for easy cleanup

---

## 🔍 Finding Documentation

### By Topic

| Topic | Location | Files |
|-------|----------|-------|
| **APIs** | [api/API_REFERENCE.md](api/API_REFERENCE.md) | 1 |
| **Architecture** | [architecture/](architecture/) | 27 |
| **Deployment** | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) | 1 |
| **Quick Start** | [QUICK_START.md](QUICK_START.md) | 1 |
| **User Manual** | [USER_MANUAL.md](USER_MANUAL.md) | 1 |
| **Troubleshooting** | [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) | 1 |
| **PRD** | [prd/](prd/) | 52 |
| **Stories** | [stories/](stories/) | 222 |
| **QA** | [qa/](qa/) | 51 |

### By Use Case

| Use Case | Start Here |
|----------|------------|
| **Integrating with APIs** | [api/API_REFERENCE.md](api/API_REFERENCE.md) |
| **Deploying the system** | [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) |
| **Understanding architecture** | [architecture/index.md](architecture/index.md) |
| **Building new features** | [prd/](prd/) + [stories/](stories/) |
| **Setting up development** | [development-environment-setup.md](development-environment-setup.md) |
| **Troubleshooting issues** | [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md) |
| **Historical research** | [archive/](archive/) |

---

## 🎯 Documentation Standards

### Creating New Documentation

**Reference Documentation:**
- Add to appropriate docs/ subdirectory
- Use clear, descriptive filenames
- Include table of contents for long docs
- Add to this index

**Implementation Notes:**
- Add to implementation/ directory
- Will be archived quarterly
- Follow BMAD project-structure rules

**Never Create:**
- Duplicate API documentation (update API_REFERENCE.md instead)
- Status reports in docs/ (use implementation/)
- Files in docs/ root without clear purpose

---

## 📊 Documentation Statistics

### Current Active Documentation
- **Total Files:** ~560 markdown files
- **API Docs:** 2 files (1 reference + 1 navigation)
- **Architecture:** 27 files
- **PRD:** 52 files (sharded)
- **Stories:** 222 files
- **QA:** 51 files
- **KB Cache:** 101 files
- **Research:** 5 files
- **Guides:** ~60 files

### Archived Documentation
- **Total Files:** ~51 markdown files
- **2024:** ~11 files (planning)
- **2025-Q1:** ~3 files (Jan status)
- **2025-Q2:** 0 files
- **2025-Q3:** ~21 files (summaries)
- **2025-Q4:** ~15 files (recent status)

### Quality Metrics
- **API Duplication:** 0% (was 60%)
- **Status Reports in docs/:** 0 (was 15+)
- **Navigation Clarity:** High (READMEs in key dirs)
- **Agent Confusion Risk:** Low (was High)

---

## 🔄 Maintenance Schedule

### Monthly
- Review new documentation for proper placement
- Ensure no duplicate API docs created

### Quarterly (Jan, Apr, Jul, Oct)
- Move completed status reports to archive/{quarter}/
- Update this index with file counts
- Review archive retention policy

### Annually (January)
- Evaluate 2-year-old content for deletion
- Consolidate very old quarterly folders
- Update documentation standards

---

## ❓ Need Help?

### Documentation Questions
- **Can't find a doc?** Check this index or docs/current/README.md
- **Found duplicate docs?** Report for cleanup
- **Need to archive?** See docs/archive/README.md for guidelines

### Technical Questions
- **API integration?** See [api/API_REFERENCE.md](api/API_REFERENCE.md)
- **Deployment issues?** See [TROUBLESHOOTING_GUIDE.md](TROUBLESHOOTING_GUIDE.md)
- **Architecture questions?** See [architecture/](architecture/)

---

**Last Major Update:** October 20, 2025 (Documentation Cleanup Project)  
**Next Review:** January 2026 (Q1 Quarterly Maintenance)  
**Maintained By:** HA Ingestor Team
