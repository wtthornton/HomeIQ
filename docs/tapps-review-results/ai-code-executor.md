# TAPPS Quality Review: ai-code-executor

**Service Tier**: 7 (Specialized)
**Review Date**: 2026-02-22
**Preset**: standard (gate threshold: 70.0)
**Reviewer**: tapps-mcp via Claude Opus 4.6

## Summary

| Metric | Value |
|--------|-------|
| Total Python files | 11 |
| Files passing (pre-fix) | 7 / 11 |
| Files passing (post-fix) | **11 / 11** |
| Total lint issues fixed | 22 |
| Security issues (informational) | 4 (all acceptable) |

## Pre-Fix Results

| File | Score | Pass | Lint | Sec | Issues |
|------|-------|------|------|-----|--------|
| `src/__init__.py` | 100 | PASS | 0 | 0 | - |
| `src/config.py` | 90 | PASS | 2 | 1 | W293 trailing whitespace, B028 missing stacklevel, B108 temp dir |
| `src/executor/__init__.py` | 100 | PASS | 0 | 0 | - |
| `src/executor/mcp_sandbox.py` | 100 | PASS | 0 | 1 | B108 temp dir (expected for sandbox) |
| `src/executor/sandbox.backup_20251229_102558.py` | **60** | **FAIL** | 8 | 1 | UP035 deprecated import, ARG001 unused args, W293, B102 exec |
| `src/executor/sandbox.py` | **60** | **FAIL** | 8 | 1 | UP035 deprecated import, ARG001 unused args, W293, B102 exec |
| `src/main.py` | 90 | PASS | 2 | 1 | ARG001 unused `app`, W293, B104 bind all interfaces |
| `src/mcp/__init__.py` | 100 | PASS | 0 | 0 | - |
| `src/mcp/homeiq_tools.py` | 100 | PASS | 0 | 0 | - |
| `src/middleware.py` | 70 | PASS | 6 | 0 | UP035 deprecated `Callable`, W293 x5 |
| `src/security/code_validator.py` | 100 | PASS | 0 | 0 | CC~11 moderate complexity |

## Post-Fix Results

| File | Score | Pass | Lint | Sec |
|------|-------|------|------|-----|
| `src/__init__.py` | 100 | PASS | 0 | 0 |
| `src/config.py` | 100 | PASS | 0 | 1 |
| `src/executor/__init__.py` | 100 | PASS | 0 | 0 |
| `src/executor/mcp_sandbox.py` | 100 | PASS | 0 | 1 |
| `src/executor/sandbox.backup_20251229_102558.py` | 95 | PASS | 1 | 1 |
| `src/executor/sandbox.py` | 90 | PASS | 2 | 1 |
| `src/main.py` | 100 | PASS | 0 | 1 |
| `src/mcp/__init__.py` | 100 | PASS | 0 | 0 |
| `src/mcp/homeiq_tools.py` | 100 | PASS | 0 | 0 |
| `src/middleware.py` | 100 | PASS | 0 | 0 |
| `src/security/code_validator.py` | 100 | PASS | 0 | 0 |

## Fixes Applied

### sandbox.py and sandbox.backup_20251229_102558.py
- **UP035**: Changed `from typing import Callable` to `from collections.abc import Callable`
- **ARG001**: Added `# noqa: ARG001` for `globals`/`locals` params in `_safe_import()` (required by `__import__` signature)
- **W293**: Removed trailing whitespace from 5 blank lines

### middleware.py
- **UP035**: Changed `from typing import Callable` to `from collections.abc import Callable`
- **W293**: Removed trailing whitespace from 5 blank lines

### config.py
- **W293**: Removed trailing whitespace from 1 blank line
- **B028**: Added `stacklevel=2` to `warnings.warn()` call

### main.py
- **W293**: Removed trailing whitespace from 1 blank line
- **ARG001**: Added `# noqa: ARG001` for `app` param in `lifespan()` (standard FastAPI pattern)

## Accepted Security Findings

| File | Code | Finding | Rationale |
|------|------|---------|-----------|
| `config.py` | B108 | Temp file usage (`/tmp/mcp_workspace`) | Expected -- configurable workspace directory for MCP sandbox |
| `mcp_sandbox.py` | B108 | Temp file usage | Same as above, sandbox workspace |
| `sandbox.py` | B102 | `exec()` detected | Expected -- this IS the code execution sandbox, using RestrictedPython's compiled bytecode |
| `main.py` | B104 | Binding to `0.0.0.0` | Expected for Docker container deployment |

## Complexity Notes

- `sandbox.py`: Max CC ~17 (high) in `_run_in_subprocess()` -- complex process lifecycle management with timeout/kill logic. Acceptable given the safety requirements.
- `code_validator.py`: Max CC ~11 (moderate) -- validation logic with multiple security checks.
