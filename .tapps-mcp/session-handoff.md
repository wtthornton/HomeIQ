# Session handoff
**Updated:** 2026-08-20T14:25:00Z
**Git:** a9cb9fb8 on master
**Repo root:** /home/wtthornton/code/HomeIQ (paths below absolute)
**Linear P0:** none open

## Done
- TAP-6310 CLOSED: PR #118. electricity-pricing InfluxDB tests: payloads lacked `provider`/`peak_period` so store_in_influxdb fail-closed and never wrote; the local fixture wrote raw os.environ (leaking INFLUXDB_ORG into test_main) and called startup() after assigning the mock, replacing it with a real client. 137 passed.
- PR #119: deleted 302 lines of unrunnable CI (agentic-pr-review.yml, tapps-quality*.yml, the quality-gate JOB). Kept the passing regression-checks job in that file.
- PR #120: two defects the never-green CI hid — /home/wtthornton/code/HomeIQ/.github/workflows/integration-tests.yml imported `AutomationLintEngine`, which never existed (real: `LintEngine` in `homeiq_ha.ha_automation_lint`); and /home/wtthornton/code/HomeIQ/tests/integration/cross_group/test_agent_chains.py passed a `context_type=` kwarg score_action() rejects. Fixed the TEST — prod caller .../proactive-agent-service/src/services/agent_loop.py:306 omits it.
- PR #121: tapps-mcp upgrade 3.12.65 -> 3.12.72. Doctor 83 passed / 0 failed.
- Housekeeping: 4 stashes dropped, 8 merged branches deleted, 34 stale refs pruned; removed the empty root-owned /home/wtthornton/code/HomeIQ/domains/ml-engine/ai-training-service tree (owner ran sudo rmdir) that was breaking `git rebase`.

## Open
- 3 red checks, all /home/wtthornton/code/HomeIQ/.github/workflows/test.yml, pre-existing on master: E2E (compose .env heredoc omits INFLUXDB_PASSWORD/POSTGRES_PASSWORD), Integration Tests (29 tests hit live HTTP in a job starting no services; 2 need influxdb_client_3), Test Summary (aggregates).
- Doctor WARN: alwaysApply rules 26491 bytes vs 16384 ceiling. Worst /home/wtthornton/code/HomeIQ/.cursor/rules/tapps-pipeline.md=7196; af-integration.mdc duplicated at 3441 in .claude/rules/ and .cursor/rules/.
- tapps upgrade shortened CLAUDE.md's generated Memory System block, dropping tapps_memory action/tier/scope detail. Upstream wording, managed region.
- CI backlog, all under /home/wtthornton/code/HomeIQ/.github/workflows/: docker-security-scan.yml duplicates 11 of docker-build.yml's 21 Trivy legs; Trivy `fs scan-ref: .` runs 21x in one matrix; scripts/validate-dockerfile-libs.py up to 78x; no top-level concurrency on test/docker-build/docker-test/docker-security-scan; deploy-production.yml.example is 225 dead lines.

## Next (P0)
- Remove the `|| true` masking in /home/wtthornton/code/HomeIQ/.github/workflows/integration-tests.yml: 7 of 9 jobs structurally cannot fail, so it reports success while proving nothing. Strip it from the 7 pytest calls (:105,190,235,276,323,364,405) and 4 installs (:88,166,173,311), then triage what surfaces. Do this BEFORE the test.yml compose-var fix.

## Blockers
- none

## Verify
- USER RULE: no full local suites; targeted files only, CI runs the suite.
- `gh pr checks --json` unsupported here; `gh run view --log` empty. Use `gh api repos/wtthornton/HomeIQ/actions/jobs/<id>/logs`.
- Diff PR reds against master head first: `gh api repos/wtthornton/HomeIQ/commits/$(git -C /home/wtthornton/code/HomeIQ rev-parse origin/master)/check-runs?per_page=100 --jq '.check_runs[]|select(.conclusion=="failure")|.name'`
- TappsMCP is a LOCAL GLOBAL install, never PyPI: /home/wtthornton/code/tapps-mcp -> ~/.tapps-mcp/releases/<ver>-<sha>; agents via the nlt-* fleet on 127.0.0.1:8760-8765. Cannot run on a hosted runner. See /home/wtthornton/code/HomeIQ/docs/TAPPSMCP_INSTALL_MODEL.md.
- /home/wtthornton/code/HomeIQ/.github/workflows/README.md is load-bearing: /home/wtthornton/code/HomeIQ/scripts/check-workflow-enablement.sh derives its set from it (floor 15).

## Success criterion
- CI carries only checks that can actually pass; every remaining red is a real defect with an owner.
