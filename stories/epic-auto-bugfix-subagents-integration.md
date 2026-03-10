---
epic: auto-bugfix-subagents-integration
priority: high
status: open
estimated_duration: 1-2 weeks
risk_level: low
source: research on Claude Code 2026 subagents/agent-teams (2026-03-10)
type: quality
---

# Epic 48: Auto-Bugfix Pipeline — Claude Code Subagents Integration

**Status:** Open
**Priority:** P1 High
**Duration:** 1–2 weeks
**Risk Level:** Low
**Source:** Research on Claude Code 2026 features (subagents, agent teams); recommendation to integrate subagents for faster, cheaper scan phase.
**Affects:** `scripts/auto-bugfix.ps1`, `scripts/auto-bugfix-stream.ps1`, `.claude/agents/`, docs

## Context

The auto-bugfix pipeline runs Claude Code in headless mode via `claude --print --output-format stream-json`. The scan phase (step 2) uses a single Sonnet session to find bugs via TappsMCP tools + code review. Research into Claude Code 2026 features found:

- **Subagents** run in isolated context with custom prompts, tools, and models (e.g., Haiku). They integrate via `--agents` and work with headless mode.
- **Agent teams** enable parallel teammates but add cost and complexity; defer unless subagents prove insufficient.

The recommendation: add a **bug-scanner subagent** (Haiku, read-only) for the scan phase so the main session delegates discovery. Benefits: faster scan (Haiku), lower cost, cleaner separation of concerns. Implementation is low-effort (add `--agents` to `Invoke-ClaudeStream` + project subagent definition).

---

## Goals

1. Integrate Claude Code subagents into the auto-bugfix pipeline.
2. Reduce scan-phase latency and cost by delegating discovery to a Haiku-based subagent.
3. Preserve existing behavior: BUGS markers, retry logic, dashboard updates, and fix phase.
4. Document the subagent architecture and provide a path to agent teams if needed later.

---

## Stories

### Story 48.1: Define Bug-Scanner Subagent

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** No project-level subagent exists for bug discovery. The scan phase runs entirely in the main Sonnet session.

**Acceptance Criteria:**
- [ ] Create `.claude/agents/bug-scanner.md` with:
  - `name: bug-scanner`
  - `description`: Clear trigger for bug-finding (e.g., "Finds real bugs in Python codebases for the auto-bugfix pipeline. Use proactively when asked to audit, scan, or find bugs.")
  - `model: haiku` (fast, low-cost)
  - `tools`: Read, Grep, Glob, and optionally `mcp__tapps-mcp__tapps_security_scan`, `mcp__tapps-mcp__tapps_quick_check` (allowlist only what is needed)
  - System prompt instructing: focus on real bugs (crashes, data loss, logic errors), emit <<<BUGS>>>...<<<END_BUGS>>> JSON, no style issues or test files
- [ ] Subagent inherits project context (MCP config, CLAUDE.md). Do not grant Edit/Write.
- [ ] Document in epic or `docs/workflows/` how the subagent is used and when the main session delegates.

---

### Story 48.2: Wire Subagent into Scan Invocation

**Priority:** P1 High | **Estimate:** 3h | **Risk:** Low

**Problem:** `Invoke-ClaudeStream` in `auto-bugfix-stream.ps1` does not pass `--agents`. The scan prompt is sent to the main session, which may or may not delegate.

**Acceptance Criteria:**
- [ ] Add optional parameter `-ScanAgents` (or `-UseBugScanner`) to `Invoke-ClaudeStream` or to the scan-phase call site in `auto-bugfix.ps1`.
- [ ] When enabled, append `--agents` to the `claude` invocation for the **scan step only** (step 2). Use project subagent `bug-scanner` (by name) or pass JSON if needed.
- [ ] Add script parameter e.g. `-UseSubagents` (default: `$true` for new behavior) so users can disable for A/B testing or fallback.
- [ ] Scan output (stream-json, BUGS extraction) remains unchanged; no changes to retry logic or fix phase.
- [ ] Update script header / usage comment to document `-UseSubagents`.

---

### Story 48.3: Update Scan Prompt for Subagent Delegation

**Priority:** P1 High | **Estimate:** 2h | **Risk:** Low

**Problem:** The main session must delegate to the bug-scanner subagent. If the prompt does not encourage delegation, the main session may do the work itself.

**Acceptance Criteria:**
- [ ] Update `$findPrompt` (and `$retryPrompt` if applicable) to explicitly ask: "Delegate bug discovery to the bug-scanner subagent when available; synthesize its findings and emit the final <<<BUGS>>> block."
- [ ] Ensure prompt remains compatible with non-subagent mode (retry path, `-UseSubagents:$false`).
- [ ] Add or update `FIND_PROMPT_OVERRIDES.md` if delegation rules should persist across runs.
- [ ] Verify scan completes successfully with `-Bugs 3` and `-UseSubagents` enabled; compare latency/cost vs baseline.

---

### Story 48.4: Validate Scan Output and Dashboard

**Priority:** P2 Medium | **Estimate:** 2h | **Risk:** Low

**Problem:** Subagent delegation may change token flow, turn count, or stream events. The dashboard and JSON extraction must still work.

**Acceptance Criteria:**
- [ ] Run full pipeline with `-Bugs 3 -UseSubagents`; confirm BUGS markers are extracted and fix phase runs.
- [ ] Confirm dashboard updates correctly (step 2 progress, tool calls if visible, final bug count).
- [ ] Compare scan cost (from `result` event or logs) before/after; document expected savings (e.g., "~20–30% scan cost reduction with Haiku subagent").
- [ ] If stream event shape differs (e.g., subagent tool calls), ensure `auto-bugfix-stream.ps1` handles it without regression.

---

### Story 48.5: Documentation and Rollout

**Priority:** P2 Medium | **Estimate:** 1.5h | **Risk:** Low

**Problem:** Operators and future maintainers need to understand the subagent integration and how to disable or extend it.

**Acceptance Criteria:**
- [ ] Add `docs/workflows/auto-bugfix-subagents.md` (or extend `auto-bugfix-scan-format.md`) describing:
  - Subagent architecture (bug-scanner, when it is used)
  - `-UseSubagents` flag and `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` (if relevant)
  - How to add a fix-phase subagent (optional follow-up) or agent teams (future epic)
- [ ] Update `scripts/auto-bugfix.ps1` header with subagent usage and `-UseSubagents`.
- [ ] Add epic summary to `stories/OPEN-EPICS-INDEX.md` (Sprint 13 or Backlog).

---

## Summary

| Story | Focus | Priority | Est. |
|-------|--------|----------|------|
| 48.1 | Define bug-scanner subagent | P1 | 2h |
| 48.2 | Wire subagent into scan invocation | P1 | 3h |
| 48.3 | Update scan prompt for delegation | P1 | 2h |
| 48.4 | Validate output and dashboard | P2 | 2h |
| 48.5 | Documentation and rollout | P2 | 1.5h |
| **Total** | | | **~10.5h** |

## Dependencies

- Claude Code CLI with subagent support (`--agents`). Verify with `claude agents` or docs.
- Project uses `claude --print --output-format stream-json` (already in place).
- Epic 46 (scan robustness, BUGS format) is complete — structured output contract remains.

## Future Work (Out of Scope)

- **Agent teams**: Parallel scan (2–3 teammates) for larger units; higher cost, experimental. Consider Epic 49 if subagents prove insufficient.
- **Fix-phase subagent**: Delegate fixes to a dedicated subagent; higher complexity, evaluate after 48.1–48.5.
