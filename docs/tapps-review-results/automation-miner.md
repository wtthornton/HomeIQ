# TAPPS Code Quality Review: automation-miner

**Service Tier**: 5 (AI Automation Features)
**Review Date**: 2026-02-22
**Preset**: standard (gate threshold: 70.0)
**Reviewer**: tapps-mcp via Claude Code

## Summary

| Metric | Value |
|--------|-------|
| Total files reviewed | 21 |
| Files passing (pre-fix) | 12 |
| Files failing (pre-fix) | 9 |
| Files passing (post-fix) | 21 |
| Files failing (post-fix) | 0 |

## Pre-Fix Results

### Passing Files (12/21)

| File | Score | Lint | Security |
|------|-------|------|----------|
| `src/__init__.py` | 100.0 | 0 | 0 |
| `src/api/__init__.py` | 100.0 | 0 | 0 |
| `src/api/admin_routes.py` | 85.0 | 3 | 0 |
| `src/api/schemas.py` | 100.0 | 0 | 0 |
| `src/config.py` | 100.0 | 0 | 0 |
| `src/jobs/__init__.py` | 100.0 | 0 | 0 |
| `src/jobs/weekly_refresh.py` | 75.0 | 5 | 0 |
| `src/miner/__init__.py` | 100.0 | 0 | 0 |
| `src/miner/database.py` | 70.0 | 6 | 0 |
| `src/miner/discourse_client.py` | 70.0 | 6 | 0 |
| `src/miner/models.py` | 85.0 | 3 | 0 |
| `src/recommendations/__init__.py` | 100.0 | 0 | 0 |

### Failing Files (9/21)

| File | Score | Lint | Security | Issues |
|------|-------|------|----------|--------|
| `src/api/device_routes.py` | 60.0 | 8 | 0 | W293 (6), B904 (2) |
| `src/api/main.py` | 50.0 | 10 | 2 | I001 (3), W293 (7), B110, B104 |
| `src/api/routes.py` | 55.0 | 9 | 0 | B904 (4), W293 (5) |
| `src/cli.py` | 30.0 | 14 | 0 | W293 (12), SIM117 (2), CC~23 |
| `src/miner/deduplicator.py` | 40.0 | 12 | 0 | W293 (12) |
| `src/miner/github_client.py` | 0.0 | 27 | 0 | W293 (20+), CC~12 |
| `src/miner/parser.py` | 15.0 | 17 | 0 | C414 (3), SIM102 (2), W293 (12), CC~15 |
| `src/miner/repository.py` | 15.0 | 17 | 0 | W293 (15), C414 (2) |
| `src/recommendations/device_recommender.py` | 45.0 | 11 | 0 | W293 (6), PTH123, ARG002, C414 (3) |

## Fixes Applied

### Ruff Auto-Fix (bulk)
- **W293**: Removed whitespace from blank lines (all files)
- **W291**: Removed trailing whitespace
- **I001**: Sorted/formatted import blocks (`api/main.py`)
- **C414**: Removed unnecessary `list()` calls within `sorted()` (`parser.py`, `repository.py`, `device_recommender.py`)
- **SIM102**: Combined nested `if` statements into single conditions (`parser.py`)

### Manual Fixes
- **B904**: Added `from e` to `raise` statements in `except` clauses (`admin_routes.py`, `device_routes.py`, `routes.py`, `database.py`)
- **SIM117**: Combined nested `async with` statements into single multi-context `with` (`cli.py` x2, `weekly_refresh.py`)
- **PTH123**: Replaced `open()` with `Path.open()` (`device_recommender.py`)
- **ARG002**: Added `# noqa: ARG002` for `user_integrations` parameter reserved for future use (`device_recommender.py`)

## Post-Fix Results

| File | Score | Lint | Security |
|------|-------|------|----------|
| `src/__init__.py` | 100.0 | 0 | 0 |
| `src/api/__init__.py` | 100.0 | 0 | 0 |
| `src/api/admin_routes.py` | 100.0 | 0 | 0 |
| `src/api/device_routes.py` | 100.0 | 0 | 0 |
| `src/api/main.py` | 100.0 | 0 | 2 |
| `src/api/routes.py` | 100.0 | 0 | 0 |
| `src/api/schemas.py` | 100.0 | 0 | 0 |
| `src/cli.py` | 100.0 | 0 | 0 |
| `src/config.py` | 100.0 | 0 | 0 |
| `src/jobs/__init__.py` | 100.0 | 0 | 0 |
| `src/jobs/weekly_refresh.py` | 100.0 | 0 | 0 |
| `src/miner/__init__.py` | 100.0 | 0 | 0 |
| `src/miner/database.py` | 100.0 | 0 | 0 |
| `src/miner/deduplicator.py` | 100.0 | 0 | 0 |
| `src/miner/discourse_client.py` | 100.0 | 0 | 0 |
| `src/miner/github_client.py` | 100.0 | 0 | 0 |
| `src/miner/models.py` | 100.0 | 0 | 0 |
| `src/miner/parser.py` | 100.0 | 0 | 0 |
| `src/miner/repository.py` | 100.0 | 0 | 0 |
| `src/recommendations/__init__.py` | 100.0 | 0 | 0 |
| `src/recommendations/device_recommender.py` | 100.0 | 0 | 0 |

## Remaining Observations

- **B110** (`api/main.py` line 142): `try/except/pass` pattern detected (security low). This is an intentional silent exception for optional import and is acceptable.
- **B104** (`api/main.py` line 304): Binding to `0.0.0.0` is expected for Docker container deployment.
- **Complexity**: `cli.py` had CC~23, `parser.py` had CC~15, `github_client.py` had CC~12. These are noted but acceptable for their orchestration/parsing roles.

## Gate Status: ALL 21 FILES PASS
