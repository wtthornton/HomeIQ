<!-- BEGIN: tapps-skill tapps-wayfind v3.12.65 -->
---
name: tapps-wayfind
user-invocable: true
disable-model-invocation: true
description: >-
  Chart foggy multi-session work as a Linear decision map, then resolve one
  decision ticket per session until the route to the destination is clear. Use
  when the path is still foggy, the user invokes /tapps-wayfind, or
  orchestration-prompt refuses to invent a Goal because decisions are missing.
argument-hint: "[chart <idea> | work <map-id> [ticket-id]]"
---

# tapps-wayfind

A loose idea arrived — too big for one agent session, and wrapped in **fog**: the
way from here to the **destination** isn't visible yet. Wayfinding finds that way
as a **shared decision map** on Linear, then resolves **decision tickets**
(questions whose answer is a decision, not build slices) one at a time until the
route is clear.

You produce **decisions and map updates**, not the destination deliverable.
When the route is clear, hand off to `/orchestration-prompt` (or implementable
stories via `linear-issue`). Do **not** invent a harness Goal while fog remains.

## Plan, don't do

Default: each ticket resolves a decision; the map is done when nothing is left to
decide before someone builds. The pull to just ship code usually means you've
reached the edge of the map — hand off. An effort may override this in **Notes**
(carry limited execution into the map); absent that, produce decisions, not
deliverables.

## Refer by name

Every map and ticket is a Linear issue with a **title**. In narration and in the
map's Decisions-so-far, refer by **name** (title wrapping its URL) — never bare
ids alone. Ids ride inside the name.

## Linear is SoT; brain is resume/rationale

| Concern | Where |
|---------|--------|
| Map, tickets, status, assignee, blocking, frontier | **Linear** (always) |
| Cross-session resume notes, decision rationale extras | **brain** (`tapps-mcp memory`) optional |

Never store ticket status or frontier in brain. See `references/linear-ops.md`.

## The map

One Linear parent issue (label or title convention `wayfinder:map`) — the
canonical artifact. Tickets are **children** of that map. The map is an
**index**, not a store: it gists closed decisions and links the ticket that holds
detail. Open tickets are **not** listed in the body — query children.

Map body shape: `assets/map-template.md`. Ticket types: `references/ticket-types.md`.

## Fog of war

Don't chart what you can't yet see. **Not yet specified** holds in-scope fog too
dim to ticket. **Out of scope** is past the destination — never graduates.

- **Ticket when** the question is already sharp (even if blocked).
- **Not yet specified when** you can't phrase it that sharply yet.

## Invocation

Two modes. **Never resolve more than one non-research ticket per session.**

### Chart the map

User invokes with a loose idea (`/tapps-wayfind chart …`).

1. **Name the destination** — what reaching the end looks like (spec, locked
   decision, or in-place change). Settles scope first.
2. **Map the frontier breadth-first** — surface open decisions and first
   takeable steps. **If no fog** (journey fits one session, route already clear):
   stop; ask how to proceed — no map needed; prefer `/orchestration-prompt` or a
   normal story.
3. **Create the map** on Linear (parent): Destination + Notes filled,
   Decisions-so-far empty, fog in Not yet specified. Use `linear-issue` (never
   raw `save_issue`).
4. **Create tickets you can specify now** as children (Question body; type from
   `references/ticket-types.md`), then **wire blocking** in a second pass.
5. **Research only:** for each `research` ticket, spawn research subagents in
   parallel; capture findings with a context pointer on the ticket.
6. Stop — charting hand-resolves nothing.

### Work through the map

User invokes with a map id (`/tapps-wayfind work TAP-#### [ticket]`).

1. Load the **map** body (low-res), not every ticket.
2. Choose the ticket (user-named, else first frontier: open + unblocked +
   unclaimed). **Claim** by assigning yourself before work.
3. Resolve — zoom related/closed tickets on demand; follow Notes skills.
4. Record: resolution comment + close ticket + append one gist line to map
   Decisions-so-far. Optionally save rationale to brain keyed to the ticket id.
5. Graduate newly sharp fog into tickets (create-then-wire); clear graduated
   patches from Not yet specified. Rule mis-scoped tickets **out of scope**
   (close + one Out-of-scope line) rather than resolving them on the route.

When no open children remain and Not yet specified is empty, the map is done —
point the user at `/orchestration-prompt` or implementable stories.

## Guardrails

- One non-research ticket per session.
- Linear writes only via `linear-issue`; multi-issue reads via `linear-read`.
- Decision tickets use a **Question** body — do not invent fake Acceptance
  Criteria or file anchors to pass validators (until `issue_kind=decision`
  lands, keep bodies honest and note the kind in the title/labels).
- Do not start `/orchestration-prompt` while fog remains on this map.
- Refer by name; keep Decisions-so-far as an index, not a paste dump.
<!-- END: tapps-skill -->
