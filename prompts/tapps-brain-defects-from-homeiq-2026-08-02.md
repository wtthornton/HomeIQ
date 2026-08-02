# tapps-brain: writes acknowledged but not stored (2026-08-02)

Paste this into a session in the **tapps-brain** repo.

---

## The headline

**`architectural` and `pattern` tier writes return success and do not persist.
`context` tier writes do.** Every failing save returned `success: true`. Nothing
in the response distinguishes a write that survived from one that vanished.

This is worse than a normal data-loss bug because of what sits on top of it: the
TappsMCP pipeline instructs every agent, in `.claude/rules/tapps-pipeline.md`
stage 5, to record architectural decisions and patterns at the end of every task.
Those are exactly the two tiers that do not persist. So the memory system has
been reporting success while accumulating nothing in its two longest-lived tiers
— 180-day and 60-day half-lives, the ones meant to carry knowledge across
sessions.

I lost four real session learnings to this before noticing, and only noticed
because I went looking for an entry I had written hours earlier.

## Reproduction

Save, then immediately `get` the same key, in one session. Observed via the
`tapps_memory` bridge in `http_bridge` mode:

| # | key | tier | save returned | `get` |
|---|---|---|---|---|
| 1 | `probe-write-readback-20260802` | `context` | `status: "saved"` | **found: true** |
| 2 | `homeiq-session-learnings-2026-08-02` | `context` | `event_id`, `memory_key: null` | **found: true** |
| 3 | `probe-architectural-short-20260802` | `architectural` | `event_id`, `memory_key: null` | found: false |
| 4 | `homeiq-concurrent-writer-same-worktree-hazard` | `architectural` | `status: "saved"` | found: false |
| 5 | `homeiq-ha-websockets-13-floor-blocks-tap-5424` | `architectural` | `status: "saved"` | found: false |
| 6 | `homeiq-registry-migration-completed-lessons` | `architectural` | `status: "saved"` | found: false |

**Entry size is not the variable.** #3 is a deliberately short architectural
probe — one sentence — and it vanished exactly like #5, which was ~1500
characters. Tier is the only thing that separates the two groups.

## Three things that make this hard to detect

**1. The response shape varies and does not predict persistence.** Some saves
return `{status: "saved", key: "..."}`, others `{event_id: "...",
memory_key: null, entity_ids: [], edge_ids: []}`. It is tempting to read
`memory_key: null` as the failure signal — it is not. Row 2 returned
`memory_key: null` and **persisted**; rows 4-6 returned `status: "saved"` and
**did not**. A caller cannot tell from the response whether the write survived.

That second shape looks like an event/knowledge-graph record rather than a
`memory_save`. If there are genuinely two write paths and requests are being
routed between them, that routing is worth auditing first — it is the most likely
home for this bug.

**2. `health` reports zero entries while entries exist:**

```
tapps_memory(action="health")
  -> status: "ok"
     postgres: "connected"
     entry_count: 0
     tier_distribution: {}
     relation_count: 0
     integrity_status: "clean"
```

At that moment two `context` entries were retrievable by key. So `entry_count`
cannot be used to sanity-check the store either, and a "healthy, connected,
clean" report is actively misleading here.

**3. `search` returns nothing for entries that `get` can retrieve.** Semantic
search for terms drawn verbatim from a stored entry's text returned
`result_count: 0`, while `get` on that key returned the entry with a populated
`embedding_model_id` (`BAAI/bge-small-en-v1.5@5c38ec7c...`). So either the
embedding is not being indexed, or the search path queries a different store than
the read path. Worth checking whether these are the same bug.

## Latency

Same-session `tapps_memory` calls ranged from **12 ms to 31 seconds**, with no
obvious correlation to action or payload — `get` calls returned in 18 ms and
30,546 ms for the same key shape. The ~30 s clustering is suspiciously close to a
round timeout, which usually means a downstream call being waited out rather than
real work. Worth tracing before optimising.

## What to fix

1. `architectural`, `pattern` and `procedural` tier saves must be retrievable by
   `get` immediately after a save that reported success. This is the bug.
2. A save that does not persist must return an error, not `success: true`. Even
   once #1 is fixed, the silent-success contract is what allowed it to go
   unnoticed for a whole session.
3. Make the save response shape consistent, or document precisely what each shape
   means and which one indicates a durable write.
4. `health.entry_count` should reflect retrievable entries.
5. `search` should find entries that `get` can retrieve.
6. Investigate the ~30 s latency spikes.

## Context

- Bridge mode: `http_bridge`. Profile negotiated `full`, memory profile
  `repo-brain` v1.1, layers architectural/pattern/procedural/context with
  power-law decay.
- Consuming project: HomeIQ. Tracked there as **TAP-5442**.
- Stopgap in place: the lost learnings were re-saved under `context` as
  `homeiq-session-learnings-2026-08-02`, verified retrievable, with a header
  noting they belong in `architectural`. `context` has a 14-day half-life, so
  they expire around 2026-08-16 unless this is fixed and they are promoted.

## Also: the 4096-char cap makes handoff mirroring fail in practice

`tapps_handoff_save` mirrors the handoff markdown to the brain by default
(`mirror_brain: true`). Every realistic handoff exceeds the limit:

```
tapps_handoff_save(markdown=<8 KB handoff>)
  -> success: true
     file_path: ".tapps-mcp/session-handoff.md"
     lint: { ok: true }
     brain_mirror: {
       error: "bad_request",
       detail: "Value error, Value exceeds max length (7998 > 4096)."
     }
```

The file write succeeded and the overall call reported `success: true`, so
nothing surfaces unless you read the nested `brain_mirror` key. The practical
result is that **brain-side handoff recall is empty across sessions** while the
tool reports success — the same silent-failure shape as the tier bug above.

4096 characters is well under a normal handoff. A session handoff carrying
environment quirks, blockers and next steps runs 6-10 KB. Either raise the cap
for this field, chunk the mirror, or make the partial failure a top-level
`success: false` so the caller knows the mirror did not happen.

## Related, may or may not be yours

The deployed slim profile exposes only `get, health, related, save, search` — no
`delete`. Combined with the above, an agent that writes a bad entry can neither
remove it nor trust that it was written. Whether `delete` belongs in the profile
is a tapps-mcp packaging decision, but the write-without-delete contract is worth
a view from this side too.
