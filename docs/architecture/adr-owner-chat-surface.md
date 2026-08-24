# ADR: An AI-first chat surface for HomeIQ owners

**Status:** Proposed
**Date:** 2026-08-23
**Origin:** The owner asked for "a very simple chat based AI UI to help owners of
HomeIQ work and run it — but must be simple and AI first", raised while the
unclaimed-device recipe was being built.
**Deciders:** HomeIQ owner + operating agent

---

## Context

HomeIQ's capability is real and almost entirely invisible. The init agent runs
~30 recipes nightly, classifies each as `satisfied` / `needs_apply` /
`blocked_on_human` / `not_applicable`, and writes an artifact to
`.tapps-mcp/init-audit-<date>.json`. The blocker survey knows which
integrations are one credential away from configuring themselves. None of that
reaches a person unless they `curl` an endpoint.

The gap is not analysis. It is that the analysis has no face.

Two things make a chat surface unusually cheap here, and they are the reason
this ADR exists rather than a "build a dashboard" one:

1. **The agenda already exists.** `GET /api/v1/init/audit` returns one row per
   recipe with `status`, `summary`, `details`, and `human_action`. "What needs
   my attention?" is a filter on `status == blocked_on_human`. Nothing needs
   inventing.
2. **The write path already exists and is gated.** `POST /api/v1/init/converge`
   is backup-gated. `POST /api/v1/init/answers` accepts owner decisions for
   blocked rows. `/api/v1/init/flow/{flow_id}` resumes a config flow parked at
   a human gate — which, since the 2FA fix, is where Ring and Roborock land.

So a chat surface is a renderer over endpoints that exist, not a new subsystem.

## Decision

Build a **thin conversational renderer inside `homeiq-dashboard`**, backed by
the existing `hiq-assistant` AgentForge gene, over four endpoints.

### Why inside the dashboard rather than its own surface

- No new container, no new port, no new auth boundary. `homeiq-dashboard`
  (`:13000`) is already deployed and the owner is already signed in.
- The chat and the data it discusses live in one place, so "show me" can
  navigate rather than describe.
- A separate surface would need its own session handling to talk to a
  backup-gated write endpoint, which is the one thing worth not duplicating.

### The four endpoints, and what each turns into

| Endpoint | Conversational role |
|---|---|
| `GET /api/v1/init/audit` | The agenda. Blocked rows are the message list. |
| `GET /api/v1/init/blockers` | "Why can't you just do it?" — answers from the stored table in ~20 ms, no probing. |
| `POST /api/v1/init/converge` | "Go ahead." Backup-gated; the gate is a feature to surface, not hide. |
| `POST /api/v1/init/flow/{flow_id}` | "Here's the code." Resumes a flow parked at a human gate. |

### What "AI-first" means here, concretely

Not a chatbot bolted onto a form. Three properties:

- **The agent opens the conversation.** The nightly audit produces the first
  message; the owner replies. A surface that waits to be asked is a search box.
- **Every claim carries its provenance.** A row says `blocked_on_human` because
  a named recipe read a named thing. The chat renders `summary` and
  `human_action` verbatim rather than paraphrasing them into confidence it did
  not earn.
- **One decision per turn.** The blocker catalogue already names exactly what a
  person must supply — a credential pair, a code, a yes. The chat asks for that
  and nothing else.

## Consequences

**Good.** Ships as a front-end change. The hard part — knowing what is wrong,
what is safe to fix, and what needs a person — is done and tested. The chat
inherits the honesty properties already enforced server-side: an uninspected
network reports `not_applicable`, never `satisfied`; a name match never
authorises a write.

**Costs and risks.**

- **Paraphrase drift.** The moment the chat rewrites `human_action` in its own
  words it can soften a blocker into a suggestion. Mitigation: render
  `human_action` verbatim; let the agent add context around it, never replace
  it.
- **Credential capture is out of scope for v1.** Accepting a password in a chat
  transcript means it lands in conversation history, which is a different and
  larger security decision than this ADR should make. Secrets travel a separate
  deterministic path and never enter a prompt, a node payload, or a ledger.
  (Corrected 2026-08-23: this bullet previously said secrets reach the agent
  through `HOMEIQ_INTEGRATION_*` in `.env`. TAP-6460 is removing that path, and
  [`adr-appliance-packaging.md`](adr-appliance-packaging.md) replaces it — the
  eleven deployment keys are generated on first boot, and customer-supplied
  integration credentials are collected in the running app and handed straight
  to a Home Assistant config flow without being stored.)
- **The audit is not instant.** A full run walks ~30 recipes and ~1200
  manifests. The chat must show progress rather than block, and should prefer
  the stored blocker table for anything conversational.

**Rejected alternative: a full dashboard page.** More surface, more state, and
it answers "what is the status" — a question the owner has not asked. The
question they did ask is "what do you need from me", which is a conversation.

## Open questions

1. Does the chat get read access to the device fingerprint store, or only to
   audit output? Fingerprints carry MAC addresses and IPs; the audit carries
   already-summarised rows.
2. Should the nightly audit push a notification, or only populate the surface
   for the next visit? Pushing makes it an assistant; not pushing makes it a
   tool.

## See also

- [docs/operations/init-gateway.md](../operations/init-gateway.md) — the
  endpoints, the blocker catalogue, and why the second factor is a human gate
  rather than a failure.
- `agentforge/projects/homeiq/agents/hiq-assistant.md` — the existing gene.
