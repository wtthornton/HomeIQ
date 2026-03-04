# Data API — AI Agent Guide

## Quality Pipeline
Run `tapps_quick_check("domains/core-platform/data-api/src/main.py")` after edits.

## Key Files
- `src/main.py` — Service class, FastAPI app, public endpoints
- `src/_app_setup.py` — Middleware and router registration
- `tests/test_main.py` — Unit tests for main module

## Rules
- All sensitive routes require auth via `_auth_dependency`
- Health and root endpoints are public (no auth)
- CORS credentials disabled when wildcard origins
