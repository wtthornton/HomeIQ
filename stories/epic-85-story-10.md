# Story 85.10 -- Coverage Measurement & Gap Closure

<!-- docsmcp:start:user-story -->

> **As a** platform engineer, **I want** a measured coverage report and targeted tests closing the remaining gaps, **so that** data-api reaches 40%+ line coverage with proof

<!-- docsmcp:end:user-story -->

<!-- docsmcp:start:sizing -->
**Points:** 5 | **Size:** L

<!-- docsmcp:end:sizing -->

<!-- docsmcp:start:purpose-intent -->
## Purpose & Intent

This story exists so that after Stories 85.1-85.9, we measure actual pytest-cov line coverage, identify the remaining highest-value uncovered branches, write targeted tests to close gaps, and produce a committed coverage report proving 40%+ achievement.

<!-- docsmcp:end:purpose-intent -->

<!-- docsmcp:start:description -->
## Description

This is the capstone story. After all Phase 1-3 stories are complete:

1. Run `pytest --cov=src --cov-report=html --cov-report=term-missing` to measure actual line coverage
2. Analyze the coverage report to find remaining uncovered branches in high-value modules
3. Write targeted tests for the most impactful uncovered code paths
4. Re-run coverage to verify 40%+ achieved
5. Commit the coverage report to `docs/`

This story also validates that all prior stories' tests integrate correctly and run together without conflicts.

See [Epic 85](epic-85-data-api-line-coverage.md) for project context.

<!-- docsmcp:end:description -->

<!-- docsmcp:start:files -->
## Files

- `domains/core-platform/data-api/tests/` (all test files)
- `domains/core-platform/data-api/tests/test_coverage_gaps.py` (new — targeted gap tests)
- `docs/data-api-coverage-report.md` (new — coverage summary)

<!-- docsmcp:end:files -->

<!-- docsmcp:start:tasks -->
## Tasks

- [ ] Run `pytest --cov=src --cov-report=term-missing` in data-api directory
- [ ] Record baseline coverage after Stories 85.1-85.9
- [ ] Identify top 10 uncovered code sections by line count
- [ ] Write targeted tests for the 5 highest-value uncovered branches
- [ ] Re-run coverage measurement
- [ ] If below 40%, write additional tests targeting the largest uncovered modules
- [ ] Generate HTML coverage report
- [ ] Create `docs/data-api-coverage-report.md` with summary table (per-file coverage)
- [ ] Verify all tests pass together: `pytest tests/ -v --tb=short`
- [ ] Document any modules that remain low-coverage with justification (e.g., dead code, I/O-heavy)

<!-- docsmcp:end:tasks -->

<!-- docsmcp:start:acceptance-criteria -->
## Acceptance Criteria

- [ ] Measured line coverage reaches **40%+** (from ~8.8%)
- [ ] Coverage report committed to `docs/data-api-coverage-report.md`
- [ ] All tests pass in a single pytest run (no conflicts between test files)
- [ ] Low-coverage modules documented with justification
- [ ] Total test count documented (prior + new from Epic 85)

<!-- docsmcp:end:acceptance-criteria -->

<!-- docsmcp:start:definition-of-done -->
## Definition of Done

Definition of Done per [Epic 85](epic-85-data-api-line-coverage.md).

<!-- docsmcp:end:definition-of-done -->

<!-- docsmcp:start:test-cases -->
## Test Cases

Test cases are dynamic — determined by coverage analysis. Expected patterns:

1. `test_gap_*` -- Targeted tests for uncovered branches identified by pytest-cov
2. Estimated 15+ additional tests to close remaining gaps

<!-- docsmcp:end:test-cases -->

<!-- docsmcp:start:technical-notes -->
## Technical Notes

- Use `pytest-cov` with `--cov-report=term-missing` to identify exact uncovered lines
- HTML report useful for visual analysis: `--cov-report=html:htmlcov`
- Some modules may be inherently hard to unit test (heavy I/O, complex setup) — document these
- Dead code modules (docker_endpoints, config_endpoints) should be excluded from coverage target
- Coverage measurement should exclude test files themselves

<!-- docsmcp:end:technical-notes -->

<!-- docsmcp:start:dependencies -->
## Dependencies

- Stories 85.1 through 85.9 (all must be complete before measurement)

<!-- docsmcp:end:dependencies -->

<!-- docsmcp:start:invest -->
## INVEST Checklist

- [ ] **I**ndependent -- Depends on all prior stories
- [x] **N**egotiable -- Gap targets adjustable based on measurement
- [x] **V**aluable -- Provides proof of coverage achievement
- [x] **E**stimable -- Known effort pattern: measure → analyze → test → remeasure
- [x] **S**mall -- 5 points, focused on gaps only
- [x] **T**estable -- Coverage percentage is the metric

<!-- docsmcp:end:invest -->
