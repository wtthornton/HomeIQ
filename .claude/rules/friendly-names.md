# Friendly Names Are For Customers, Never For The System

**A friendly name is a presentation artifact.** It is what the system shows a
person. It is never an identifier, never a join key, and never an input to a
decision the system makes on its own.

This is a hard rule in this project because it has already been broken and it
cost real correctness. Two identically-modelled Inovelli VZM31-SN dimmers on the
live instance carried **swapped** friendly names. Every claim derived from those
names pointed at the wrong physical device: the "office" row named the bar
switch, and an evaluation document's apply instruction would have enabled
smart-bulb mode on the wrong circuit. Nothing detected it, because a name match
looks exactly like knowledge.

## The two directions

**Allowed — customer to system, resolved immediately to a stable id.**
A person says "turn on the office lights". Matching that against friendly names
is the *only* way to know what they meant, so entity resolution from a user
utterance is legitimate. It must resolve to a stable id at the boundary, and
everything downstream operates on the id.

**Allowed — system to customer.**
Rendering a name in a dashboard, a notification, a chat reply, or a report.
Scoring a name's *quality* is also fine: the naming rubric evaluates the name as
a customer-facing artifact, which is exactly what it is.

**Forbidden — name as identity or as a decision input.**
- Joining two datasets on a name.
- Inferring a device's area, room, or function from its name.
- Matching a device to a group, scene, or automation by name.
- Letting a name confer confidence, an evidence class, or an authorization.
- Any comparison whose result changes what the system *does*, keyed on a name.

## Durable identifiers to use instead

In descending order of durability:

1. **Protocol-native identity** — Zigbee `ieee` address, MAC, Matter VID/PID.
   Survives renames, re-pairing, and integration changes.
2. **HA's registry key** — `(domain, platform, unique_id)`. This is what HA
   itself keys the entity registry on (`EntityRegistryItems`). Note `unique_id`
   alone is **not** unique: 21 pairs on this instance share one.
3. **HA's registry UUID** — `RegistryEntry.id`, stable across renames.
4. **`entity_id`** — an ADDRESS, not an identity. It moves on rename and
   re-pair. Usable as a current address; never as a durable key. `device_entities`
   keys on the tuple above and treats `entity_id` as a mutable column for exactly
   this reason.

## Watch for the one-hop launder

The dangerous version is not a direct name comparison — it is a name match one
hop removed, wearing the label of something better. Hue room-group membership
looked like independent upstream corroboration of which room a bulb is in; the
group entity lists member **names**, not ids, so renaming the device silently
erases the "evidence". It was a name match with a better job title.

Before trusting any corroborating signal, ask: **would a rename break this?** If
yes, it is the name, and it confers nothing.

## Evidence vocabulary

Where the system records how a claim was established, the ordered classes are:

    measured > upstream_source > attestation > unverified

There is deliberately **no `name_match` class**. Giving the absence of evidence a
name of its own would let it sort above `unverified` and read as established. A
name echo is recorded in a free-text `method` field on a row that is already
`unverified` — visible to a human, inert to the system.

## How to apply

When writing or reviewing code that touches names:

1. Does this comparison change what the system does? If yes, it may not be keyed
   on a name.
2. Would a rename break this? If yes, it is a name match regardless of what the
   variable is called.
3. Is there a durable id available at this point? Use it. If there is not, that
   is a finding to surface, not a reason to fall back to the name.
4. Rendering to a person, or resolving what a person said? Carry on — that is
   the name's job.

## See also

- [docs/architecture/adr-device-knowledge-provenance.md](../../docs/architecture/adr-device-knowledge-provenance.md)
  — the evidence-class ordering and why provenance is ranked by *how a thing is
  known*.
- `skills/home-atlas/SKILL.md` — the structural pack; every claim states how it
  was established, and name-derived rows are `unverified` and non-actionable.
- `scripts/correlate_colocation.py` — the name-blind correlation engine. Its
  `FORBIDDEN_TAGS` are dropped in the query *and* rejected on ingest, so the
  clustering step is structurally unable to read a room label.
