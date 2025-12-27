# Dependency Maintenance Cadence

## Automated Updates
- Renovate runs weekly before 09:00 America/Chicago to open grouped PRs for Python and Node manifests.
- Each PR must pass `python scripts/simple-unit-tests.py`, relevant `pytest` suites, and frontend `npm run lint && npm run test`.
- Reviewers merge only after verifying changelog notes and ensuring no breaking changes land without migration tasks.

## Quarterly Audit
- First Monday of each quarter, product ops schedules a dependency review session with service owners.
- Owners validate pinned versions against security advisories, update long-lived model artifacts, and document results in `implementation/analysis/`.
- Any deferred upgrades require a tracking issue with mitigation notes and a target resolution date.

