# Wayfind ticket types

Every ticket is **HITL** (human in the loop) or **AFK** (agent alone). HITL only
resolves through live human exchange — never stand in for the human's side.

| Type | Mode | When | Resolution |
|------|------|------|------------|
| **research** | AFK | Facts outside the working tree (docs, APIs, KB) | Research subagent; findings + context pointer on the ticket |
| **prototype** | HITL | "How should it look/behave?" needs a cheap artifact to react to | Link the prototype as an asset; decision recorded on close |
| **grilling** | HITL | Default — conversation to lock a preference or tradeoff | Human answers; agent records the decision |
| **task** | HITL or AFK | Manual work that *unblocks a decision* (access, signup, data move) — not the destination deliverable | Done when the blocking work is done; answer records resulting facts |

Label convention (Linear labels or title prefix): `wayfinder:research`,
`wayfinder:prototype`, `wayfinder:grilling`, `wayfinder:task`. Map parent:
`wayfinder:map`.

**Research exception:** multiple research tickets may run in parallel in one
charting or work session. All other types: **one ticket per session**.
