# ADR: Device Knowledge with First-Class Provenance

**Status:** Proposed
**Date:** 2026-08-19
**Origin:** The Inovelli smart-bulb-mode episode — a confident, heavily-cited
device recommendation that was wrong, and whose refutation already existed in
the project before the work started.
**Deciders:** HomeIQ owner + operating agent

---

## Context

On 2026-08-19 an agent audited three Inovelli Zigbee switches and produced a
detailed recommendation: enable Smart Bulb Mode (P52) on the Office Light
Dimmer to stop the office Hue downlights losing power. The report cited the
vendor parameter tables, the firmware changelog, and the `zha-quirks` source.
It was wrong.

Live cluster reads taken hours earlier — and already written to project
memory — showed that both VZM31-SN dimmers are **non-neutral** installs where
Smart Bulb Mode does not hold. The report had also leaned on
`sensor.inovelli_vzm31_sn_power_2` reading `0.0 W`; that sensor never reports at
all.

A second inference then failed the same way, which is why this ADR exists in the
form it does. The refutation above was extended to "**neither** HA-visible office
switch feeds those downlights", on the grounds that both were held on at full
while all four bulbs stayed `unavailable`. The owner then operated the paddle and
the downlights came on. Entity availability is a Hue-**bridge** reachability
signal, not a circuit measurement — so that was an `inferred` claim dressed as a
refutation, and it displaced an observation.

Compounding both: the device identity itself rested on a friendly-name match, and
those two dimmers' names were swapped on the instance. The `_2` slug the report
named is the **Bar** dimmer (ieee `90:35:ea:ff:fe:c9:11:ef`); the Office dimmer is
the unsuffixed one (`90:35:ea:ff:fe:c9:0e:8f`). Three failures, one shape: an
`inferred` claim outranking a `measured` one.

This is not a one-off. It is the predictable output of three structural gaps:

1. **No model-keyed store.** Facts like "P52 forces full-wave output on
   firmware ≥ 3.00" or "P21 is read-only, not Output Mode" are properties of a
   *model*, not of a device instance. HomeIQ has `devices`,
   `device_capabilities` and `zigbee_device_metadata`, all keyed to instances
   discovered from Home Assistant. Vendor facts have nowhere to live, so every
   agent re-derives them from the web and re-makes the same mistakes.

2. **No home for measurements.** The cluster reads that refuted the report were
   captured, but only into agent memory prose. Nothing in HomeIQ could be
   queried for "what did we actually measure on this device?"

3. **No provenance ordering — the one that caused the failure.** The wrong claim
   was an *inference* from a state snapshot. The right claim was a *measurement*.
   Nothing in the system recorded that difference, so the inference read as
   truth. A knowledge layer without epistemic status reproduces this bug
   faithfully: the first agent to write a confident guess makes it fact for
   everyone after.

`rag-service` (`:8027`) exists and is healthy, but is empty with no producers or
consumers, has no vector index, and no chunking. `libs/homeiq-memory` has a real
pgvector store, but its `MemoryType` CHECK constraint scopes it to user-behaviour
memory and it uses a different embedding model. Neither is a device knowledge
layer, and neither becomes one by being pointed at.

## Decision

Add a **device knowledge layer whose primary key on every claim is its
epistemic status**, not its confidence score.

### 1. Every fact carries an evidence class, and the classes are ordered

    measured  >  upstream_source  >  vendor_doc  >  community  >  inferred

- `measured` — read off the actual hardware or instance ("live wire evidence"),
  with the method and timestamp recorded.
- `upstream_source` — the source code that defines the behaviour, cited as
  `file:line` **with the pinned version** that makes the citation valid.
- `vendor_doc` — manufacturer documentation, cited by URL.
- `community` — forum or community report. Corroborating, never authoritative.
- `inferred` — derived by reasoning from other facts.

The ordering is enforced **server-side**. An `inferred` write never silently
overwrites a `measured` fact for the same key; it is stored, ranked below it,
and returned with both visible. Clients do not re-derive this ranking — they
read the outcome. (See `.claude/rules/integration-hygiene.md`: do not mirror
server-enforced state into the client.)

This vocabulary is not invented here. It is the one the repo already uses in
`libs/homeiq-ha/src/homeiq_ha/agent/quirks/aqara_fp1e.py`, whose docstring
separates "Upstream source" from "Live wire evidence" and pins the version of
each. That file is the content model; this ADR makes it queryable.

### 2. Model knowledge and instance knowledge are separate subjects

A claim is about either a **model** (`inovelli/vzm31-sn`) or an **instance**
(a specific device in this home). Conflating them is precisely what produced
the failure: "P21 is read-only" is a model fact; "P21 reads false on the Office
dimmer" is an instance measurement. Both are stored; retrieval for a device
returns instance facts layered over its model facts, with instance winning on
key collision.

### 3. Not-claiming is a first-class record

The strongest thing in `aqara_fp1e.py` is its refusal: attribute `0x014D`
"is left unmapped: it also updates live but no source defines it for this model,
and guessing it would be exactly the invention this quirk exists to avoid."

A store that can only record knowledge invites the next agent to invent the
gaps. So "we deliberately do not know X, and here is why" is a storable claim.

### 4. Supersession, not deletion

A refuted claim is marked superseded by the claim that replaced it and stays
readable. The Inovelli episode is the argument: the withdrawn recommendation is
more useful retained-and-marked than deleted, because the next agent reaching
for P52 needs to find the refutation, not silence.

### 5. Deliberately NOT built

- **No vector search, no document ingestion, no RAG.** Every fact that failed
  here was structured and exact-lookup-shaped. Adding embeddings would add a
  dormant dependency and a second retrieval path without addressing the defect.
  `rag-service` is left untouched. If unstructured vendor prose later needs
  semantic retrieval, that is a separate decision with its own evidence.
- **No automatic vendor-doc scraping.** Ingesting manuals automatically trades a
  known gap for silent, unattributable claims — the opposite of this ADR.
- **No new embedding model or second vector store.**

## Consequences

**Good.** An agent about to make a device recommendation can ask what is already
known and see how it is known. Measurements outrank guesses by construction
rather than by an agent remembering to check. Refutations are discoverable.
The `aqara_fp1e.py` content model stops being one exceptional docstring.

**Cost.** Every write must carry provenance, which makes casual capture slightly
more expensive — deliberately. Facts with firmware predicates need those
predicates recorded or they will mislead across firmware versions, exactly as
"P52 forces full-wave" would if applied to a pre-3.00 switch.

**Risk.** The store is only as good as what is written to it, and nothing forces
an agent to consult it. Adoption is the open question, not the schema.

**Explicitly unresolved.** The office Hue dropouts remain unexplained. Those
downlights sit on a circuit Home Assistant cannot see. This ADR makes the dead
end recorded rather than repeated; it does not diagnose it.

## References

- `docs/operations/smart-bulb-mode-evaluation.md` — TAP-5988, and its
  2026-08-19 correction section.
- `libs/homeiq-ha/src/homeiq_ha/agent/quirks/aqara_fp1e.py` — the content model.
- `.claude/rules/integration-hygiene.md` — server-enforced decisions are not
  mirrored into clients.
- Survey of 2026 agent-memory practice: epistemic status as a primary field
  (`fact | verified_inference | hypothesis | speculation`) rather than
  confidence alone, and supersession that records the relationship between
  claims instead of overwriting —
  <https://arxiv.org/html/2606.04990>,
  <https://arxiv.org/pdf/2604.11364>.
