# ADR: Goal-Loop Operator Pattern

**Status:** Accepted
**Date:** 2026-08-13
**Origin:** TAP-5990 — proven during the HA init-agent activation and physical-layer pairing sessions, 2026-08-11/12
**Deciders:** HomeIQ owner + operating agent

---

## Context

On 2026-08-11/12 a long-running agent session activated the HA init agent
against the live home (`prompts/ha-init-agent-activation.md`, a 20/20 goal
loop, PR #82) and drove the physical layer: ZHA on the SLZB coordinator,
three Inovelli switches paired, the Hue Bridge absorbed (296 entities), HACS
and Team Tracker installed, backups armed. The same conventions carried the
subsequent backlog burndown (waves of stories, each independently verified).

Those sessions repeatedly re-derived the same four operating conventions.
This ADR names them so future sessions reuse them instead of rediscovering
them mid-incident.

## Decision

Agent sessions that operate on live systems follow the **goal-loop operator
pattern**, whose four first-class concepts are:

### 1. Long-running goal loop

Work is a loop over a committed prompt (the goal spec), not a one-shot
conversation: **State → Decide → Execute → Verify → Record**, printing a
SCORE line per iteration, with explicit iteration/token caps. Progress is
checkpointed to persistent memory and a session-handoff file at every story
boundary, so any context loss (compaction, crash, cap) resumes from the last
checkpoint rather than restarting. Hitting a cap mid-wave is a normal stop.

### 2. Readiness gates

An action that depends on a precondition never assumes it — it reads the
precondition first and refuses loudly when unmet. The canonical mechanized
example is the engine's backup gate (`BackupGateNotSatisfied`,
`libs/homeiq-ha/src/homeiq_ha/agent/engine.py`): nothing past phase 1
applies without a fresh backup. Human gates are the same concept where the
precondition is a person (`BLOCKED_ON_HUMAN` + `human_action`): hard stops,
not timeouts, recorded in `.tapps-mcp/pending-human-actions.jsonl` when they
leave the session's scope. The 2026-08-12 pairing day ran on these gates:
pairing windows only after permit-join verified, converge only after
backups, HACS only after a human GitHub device-code step.

### 3. Background watchers

Long asynchronous processes get watchers instead of blocking waits or blind
sleeps: the self-renewing Zigbee pairing window with a join watcher
(2026-08-12), polls with deadlines for backup jobs and ZHA network formation
(`wait_for_backup`, `ZHARecipe._form_network`), and standing watchers for
things nobody will think to check — the 03:15 nightly audit cron and the
coordinator watchdog (TAP-5983), born from the outage where ZHA sat in
`setup_retry` silently. A watcher's output is a visible artifact or alert,
never just a log line.

### 4. Registry-verified claims

No claim advances the loop on an actor's say-so:

- Every recipe `verify()` **re-reads** live state instead of trusting
  `apply()`'s return — HA's config writes return 200 before reloads land.
- Deployments are verified **by identity** (in-container source hash vs
  repo), never by build exit code — "merged ≠ live, built ≠ loaded."
- A **zero-change second apply** is the success signature of convergence.
- Story-level proof is judged by an independent fresh-context verifier told
  to *refute* it against the live registries, and wave-level completion by a
  perspective-diverse verifier panel; the verifier's verdict, not the
  executor's claim, advances the loop.

## Consequences

- **Positive:** context loss is cheap (checkpoints), silent failure modes
  become alerts (watchers), plausible-but-wrong claims die before they
  compound (registry verification + refute-verifiers), and irreversible
  actions structurally cannot run before their preconditions (gates).
- **Negative:** every story pays a verification tax (a second agent, live
  re-reads, container rebuilds), and blocked human gates halt later phases
  by design — throughput is deliberately sacrificed for honesty on a live
  home.
- The pattern is encoded operationally in `prompts/homeiq-backlog-burndown.md`
  (loop, guardrails, hard-stop list) and mechanically in the init-agent
  engine (`docs/ha-init-agent-design.md`, `docs/operations/init-gateway.md`).

## References

- Proving sessions: 2026-08-11/12 — `prompts/ha-init-agent-activation.md`
  (completed 20/20 goal loop), PR #82, and the wave-based backlog burndown
  that followed (`prompts/homeiq-backlog-burndown.md`).
- Engine semantics: `libs/homeiq-ha/src/homeiq_ha/agent/engine.py` (gates,
  verify-by-re-read), `readonly.py` (audit that cannot write).
- Watcher artifacts: `scripts/init-agent-nightly-audit.sh`,
  `.tapps-mcp/init-audit-<date>.json`, `zigbee.coordinator_watchdog`.
