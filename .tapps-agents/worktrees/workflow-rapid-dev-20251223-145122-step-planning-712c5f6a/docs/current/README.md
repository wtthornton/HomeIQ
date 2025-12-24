# Current Documentation

**Status:** ✅ Active Reference Documentation  
**Last Updated:** October 20, 2025

## Purpose

This directory contains **CURRENT, ACTIVE** documentation that agents and developers should reference. All historical, completed, or superseded documentation has been moved to `docs/archive/`.

## Structure

### API Documentation
- **[api/](../api/)** - Complete API reference (all services, all endpoints)

### Architecture Documentation  
- **[architecture/](../architecture/)** - System architecture, tech stack, coding standards

### Product Requirements
- **[prd/](../prd/)** - Product requirements, epics, features (sharded)

### User Stories
- **[stories/](../stories/)** - Development stories (active and completed)

### Quality Assurance
- **[qa/](../qa/)** - QA assessments and quality gates

### Knowledge Base
- **[kb/](../kb/)** - Context7 cache and knowledge base

### Research
- **[research/](../research/)** - Technical research and evaluations

## What's NOT Here

The following types of documents are **archived** (not current reference):
- ❌ Status reports (DEPLOYMENT_COMPLETE.md, *_STATUS.md)
- ❌ Completion summaries (*_SUMMARY.md)
- ❌ Fix reports (*_FIX_*.md)
- ❌ Historical planning documents
- ❌ Superseded documentation

**These belong in:** `docs/archive/` or `implementation/`

## For Agents

**IMPORTANT:** Focus your attention on this directory structure:
- `docs/current/` - **REFERENCE THIS** for current documentation
- `docs/archive/` - **IGNORE THIS** for active development  
- `implementation/` - **REFERENCE ONLY** for active work, ignore completed items

## For Developers

### Finding Documentation

**Need API docs?** → `docs/api/API_REFERENCE.md`  
**Need architecture info?** → `docs/architecture/`  
**Need deployment info?** → `docs/DEPLOYMENT_GUIDE.md` (root)  
**Need user story?** → `docs/stories/`  

### Operations Quick Links

- Manual suggestion refresh: `POST /api/suggestions/refresh` (UI button on Conversational Dashboard, 24h cooldown enforced in `manual_refresh_triggers`)
- Refresh availability: `GET /api/suggestions/refresh/status`
- Latest nightly run metrics: `GET /api/analysis/status` → `analysis_run`
- Context7 MCP quick start: [`docs/current/context7-setup.md`](context7-setup.md)

### Adding New Documentation

**Reference documentation** (guides, manuals, API docs):
- Add to appropriate subdirectory in `docs/`
- Never add status reports or completion summaries here

**Implementation notes** (status, summaries, plans):
- Add to `implementation/` directory
- Will be archived quarterly

## Directory Summary

| Directory | Purpose | Files | Status |
|-----------|---------|-------|--------|
| `api/` | API reference | 2 | ✅ Current |
| `architecture/` | Architecture docs | 27 | ✅ Current |
| `prd/` | Product requirements | 52 | ✅ Current |
| `stories/` | User stories | 222 | ✅ Current |
| `qa/` | Quality assurance | 51 | ✅ Current |
| `kb/` | Knowledge base cache | 101 | ✅ Current |
| `research/` | Technical research | 5 | ✅ Current |
| **Total Active** | | **~460 files** | **Manageable** |

## Archive Summary

| Archive Location | Purpose | Status |
|-----------------|---------|--------|
| `docs/archive/2024/` | 2024 artifacts | Archived |
| `docs/archive/2025-q1/` | Q1 2025 (Jan-Mar) | Archived |
| `docs/archive/2025-q2/` | Q2 2025 (Apr-Jun) | Archived |
| `docs/archive/2025-q3/` | Q3 2025 (Jul-Sep) | Archived |
| `docs/archive/2025-q4/` | Q4 2025 (Oct-Dec) | Current archive |

## Quarterly Maintenance

Every quarter (Jan, Apr, Jul, Oct):
1. Review docs/current/ for outdated content
2. Move completed/historical docs to appropriate archive quarter
3. Update this README with current file counts
4. Update agent rules if needed

---

**Last Maintenance:** October 20, 2025 (Q4 2025)  
**Next Review:** January 2026 (Q1 2026)  
**Maintained By:** Documentation Cleanup Project


