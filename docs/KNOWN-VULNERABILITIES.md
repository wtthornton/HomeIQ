# Known Vulnerabilities Registry (Epic 88.4)

Centralized CVE tracking for HomeIQ dependencies.
Audit cadence: **monthly** (or on any requirements file change via pre-commit).

## Fixed CVEs

### aiohttp (8 CVEs — Fixed Mar 2026)

All 44 Python containers pinned to `aiohttp>=3.13.3,<4.0.0`.

| CVE | Severity | Fixed In | Pin |
|-----|----------|----------|-----|
| CVE-2025-69223 | HIGH | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69224 | HIGH | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69225 | HIGH | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69226 | MEDIUM | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69227 | MEDIUM | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69228 | MEDIUM | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69229 | LOW | 3.13.3 | `>=3.13.3,<4.0.0` |
| CVE-2025-69230 | LOW | 3.13.3 | `>=3.13.3,<4.0.0` |

### Version Spread Fixes (Epic 88.2 — Mar 2026)

| Package | Issue | Fix Applied |
|---------|-------|-------------|
| pydantic | Unbounded `>=2.8.2` in data-retention-prod | Pinned to `>=2.9.0,<3.0.0` |
| FastAPI | Unbounded `>=0.115.0` in 4 services | Added `<1.0.0` upper bound |
| pydantic-settings | `>=2.0.0` in 5 prod files | Upgraded to `>=2.6.0,<3.0.0` |
| pydantic-settings | `>=2.5.0` in 2 files | Upgraded to `>=2.6.0,<3.0.0` |

## Dev-Only CVEs (No Fix Available)

These affect development tools only and are NOT present in production containers.

| Package | CVE(s) | Severity | Status | Risk |
|---------|--------|----------|--------|------|
| black | Multiple | LOW | No fix — dev formatter only | None (not in containers) |
| pip | Multiple | LOW | Inherited from Python base | None (build-time only) |
| wheel | Multiple | LOW | Inherited from Python base | None (build-time only) |
| virtualenv | Multiple | LOW | Dev environments only | None (not in containers) |
| filelock | Multiple | LOW | Transitive via virtualenv | None (not in containers) |
| setuptools | Multiple | MEDIUM | Inherited from Python base | None (build-time only) |

**Risk acceptance rationale:** These packages run only during development and CI build steps.
They are never installed in production container images (multi-stage builds copy only app code + production deps).

## Remaining Version Spread (Accepted)

| Package | Spread | Rationale |
|---------|--------|-----------|
| FastAPI | 0.115.0 (dev) vs 0.129.0 (prod) | Prod files use stricter pin; dev files use wider range. Both within `<1.0.0`. |
| Pydantic | 2.9.0 (services) vs 2.12.5 (base) | All within `<3.0.0`. Services use minimum viable version. |
| Shared libs (pyproject.toml) | `>=2.0` (broad) | Intentional — libs should work with any 2.x. Service requirements.txt pins the actual version. |

## How to Audit

```bash
# Audit base requirements
pip-audit --requirement requirements-base.txt --desc

# Audit a specific service
pip-audit --requirement domains/core-platform/data-api/requirements.txt --desc

# Full project scan (slow — audits all 81 files)
find . -name "requirements*.txt" -not -path "*/node_modules/*" | while read f; do
  echo "=== $f ==="
  pip-audit --requirement "$f" --desc --skip-editable 2>/dev/null || true
done

# Pre-commit hook (runs on requirements-base.txt changes)
pre-commit run pip-audit-base
```

## Audit History

| Date | Auditor | Scope | Findings |
|------|---------|-------|----------|
| 2026-03-18 | Claude (Epic 88) | Full project (81 files) | 5 unbounded pins fixed, 7 pydantic-settings upgraded, 8 aiohttp CVEs already fixed |
| 2026-03-13 | Claude (Epic 81) | aiohttp across 40 files | 8 CVEs fixed via pin to >=3.13.3 |
