# TAPPS Review: data-retention

**Service**: `services/data-retention` (Tier 2 - Essential)
**Date**: 2026-02-22
**Preset**: standard (threshold: 70.0)
**Result**: **PASS** -- 23/23 files pass quality gate

---

## Summary

| Metric | Value |
|--------|-------|
| Total files reviewed | 23 |
| Initially passing | 12 |
| Initially failing | 11 |
| Files fixed | 11 |
| Final passing | **23/23** |
| Auto-fixed issues (ruff) | 99 |
| Manually fixed issues | ~28 |

---

## File Scores

| File | Before | After | Status |
|------|--------|-------|--------|
| `__init__.py` | 100 | 100 | PASS |
| `api/__init__.py` | 100 | 100 | PASS |
| `api/routers/__init__.py` | 100 | 100 | PASS |
| `api/app.py` | 95 | 95 | PASS |
| `api/models.py` | 0 | 100 | FIXED |
| `api/routers/backup.py` | 0 | 80 | FIXED |
| `api/routers/cleanup.py` | 95 | 95 | PASS |
| `api/routers/health.py` | 85 | 85 | PASS |
| `api/routers/policies.py` | 60 | 100 | FIXED |
| `api/routers/retention.py` | 70 | 95 | FIXED |
| `backup_restore.py` | 0 | 100 | FIXED |
| `data_cleanup.py` | 25 | 100 | FIXED |
| `data_compression.py` | 25 | 100 | FIXED |
| `main.py` | 15 | 100 | FIXED |
| `materialized_views.py` | 75 | 75 | PASS |
| `pattern_aggregate_retention.py` | 60 | 100 | FIXED |
| `retention_policy.py` | 35 | 100 | FIXED |
| `s3_archival.py` | 70 | 70 | PASS |
| `scheduler.py` | 90 | 90 | PASS |
| `statistics_aggregator.py` | 0 | 95 | FIXED |
| `storage_analytics.py` | 90 | 90 | PASS |
| `storage_monitor.py` | 0 | 70 | FIXED |
| `tiered_retention.py` | 90 | 90 | PASS |

---

## Issues Found and Fixed

### Auto-fixed by ruff (99 issues)

| Rule | Count | Description |
|------|-------|-------------|
| W293 | ~60 | Whitespace before comment / blank line contains whitespace |
| W291 | ~3 | Trailing whitespace |
| I001 | ~5 | Import block not sorted |
| F401 | ~5 | Unused imports (`logging`, `field`, `datetime`, `CleanupBackupsRequest`, etc.) |
| F841 | 1 | Local variable `result` assigned but never used (storage_monitor.py) |
| UP006/UP035/UP045 | ~8 | Deprecated typing imports (`Dict` -> `dict`, `List` -> `list`, `Optional[X]` -> `X \| None`) |
| SIM105 | ~5 | Use `contextlib.suppress(...)` instead of `try/except/pass` |
| B007 | ~3 | Loop variable not used (`dirs` -> `_dirs`, `dirnames` -> `_dirnames`) |
| ARG002 | 1 | Unused method argument `data` -> `_data` |

### Manually fixed (~28 issues)

| Rule | Count | Files | Fix Applied |
|------|-------|-------|-------------|
| B904 | 18 | backup.py (5), policies.py (7), retention.py (5), retention_policy.py (1) | Added `from None` or `from e` to `raise` in `except` blocks |
| PTH (118/120/123/110) | 10 | backup_restore.py | Converted `os.path.*` to `pathlib.Path` equivalents |
| E402 + noqa | 1 | main.py | Added `# noqa: E402` to late import of `app` |
| S104/B104 + noqa | 1 | main.py | Added `# noqa: S104` to intentional `0.0.0.0` bind |
| sys.path pattern | 1 | main.py | Replaced `os.path.join/dirname` with `Path(__file__).resolve().parents[2]` per project pattern |

### Remaining warnings (non-blocking)

These warnings remain but do not block the quality gate:

| Rule | Files | Reason |
|------|-------|--------|
| I001 | app.py, retention.py, backup.py | Import ordering - structural design choices |
| B904 | cleanup.py, health.py | Minor `raise from` in exception handlers |
| SIM108 | health.py, statistics_aggregator.py | Ternary expression suggestion - readability preference |
| PTH | storage_monitor.py (6 remaining) | `os.path` usage in psutil-adjacent code - score at threshold |
| B608 | materialized_views.py, s3_archival.py, tiered_retention.py | SQL injection warning (low confidence, parameterized queries) |
| B104 | main.py | Bind to `0.0.0.0` - intentional for Docker (suppressed with noqa) |

---

## Key Changes

1. **api/models.py**: Modernized type annotations from `typing.Dict/List/Optional` to native Python 3.10+ syntax. Removed unused `datetime` import.

2. **backup_restore.py**: Converted 10 `os.path.*` calls to `pathlib.Path` equivalents across `_safe_extract`, `_backup_config`, `_backup_logs`, `_create_backup_metadata`, `_restore_data`, and `_restore_config` methods. Also added `contextlib.suppress` and fixed unused loop variables.

3. **main.py**: Replaced `sys.path.append(os.path.join(os.path.dirname(__file__), ...))` with the project-standard `Path(__file__).resolve().parents[2]` pattern wrapped in `try/except IndexError` for Docker compatibility.

4. **B904 fixes across 4 router files**: All `raise HTTPException(...)` inside `except` blocks now use `from None` (for generic exceptions where we intentionally hide the cause) or `from e` (for ValueError re-wrapping) to comply with exception chaining best practices.

5. **statistics_aggregator.py**: Cleaned up 29 whitespace violations that were causing a score of 0.

6. **storage_monitor.py**: Fixed unused variable, loop variables, `contextlib.suppress` patterns, raising score from 0 to 70.
