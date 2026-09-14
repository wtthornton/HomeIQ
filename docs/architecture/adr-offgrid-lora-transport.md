# ADR: ESPHome LoRa `packet_transport` carries presence out of Wi-Fi-unreachable zones

**Status:** Provisional — see [Why this is provisional](#why-this-is-provisional-not-accepted)
**Date:** 2026-09-14
**Origin:** [TAP-7629](https://linear.app/tappscodingagents/issue/TAP-7629) — filed under
[TAP-7628](https://linear.app/tappscodingagents/issue/TAP-7628) (HomeIQ S5: mmWave radar
over LoRa for zones Wi-Fi cannot reach)
**Deciders:** HomeIQ owner + operating agent

---

## Context

TAP-7628 needs a way to carry presence data (an RD-03D mmWave sensor's output) from a zone
with no Wi-Fi — an outbuilding, a gate, a detached garage — into HomeIQ. HomeIQ already
enforces two hard constraints that most radio transports violate before they get to the
merits:

- `infrastructure/container-budget.json` ratchets the production service count at 31
  (`scripts/check-container-budget.py`) — no new container.
- The stack ships no MQTT broker today (verified: `infrastructure/container-budget.json`'s
  `measured.services` list has no `mosquitto`, no `mqtt`, no broker of any kind). A
  transport whose only Home Assistant path runs through MQTT would require standing one up
  — a new container by another name.

Four candidates exist. This ADR verifies each against current upstream sources (not
training-data memory) and records which specific constraint eliminates three of them.

### How a candidate would actually reach HomeIQ

`domains/core-platform/websocket-ingestion/src/discovery_service.py:74-171` pulls Home
Assistant's device registry over the websocket (`config/device_registry/list`) and builds
a `device_id → area_id` cache; `entity_filter.py:103-132` (`EntityFilter.should_include`)
filters every event by `domain`, `device_class`, `entity_id`, and `area_id` before it
reaches InfluxDB. Both operate on Home Assistant's registry identifiers, never on a
friendly name (`.claude/rules/friendly-names.md`) — a remote node's area comes from
whatever HA's device registry assigns it, and its entities need a `domain` (`sensor`,
`binary_sensor`) and pass through the same filter every other HA entity does. Concretely,
the candidate has to land as normal HA entities through HA's existing device/entity
registry — not as an opaque byte stream this codebase would have to parse itself.

## Decision

**ESPHome's `sx126x`/`sx127x` LoRa components, using the `packet_transport` platform, in
point-to-point mode — no LoRaWAN gateway, no network server.**

Verified via [esphome.io](https://esphome.io), fetched 2026-09-14:

- [ESPHome 2025.7.0 release notes](https://esphome.io/blog/2025/07/16/esphome-2025-7/)
  (2025-07-16): SX126x and SX127x LoRa modules shipped as new hardware support in this
  release, described as "long-range, low-power communication for remote sensors and IoT
  applications."
- [`packet_transport` platform docs](https://esphome.io/components/packet_transport/):
  "allows ESPHome nodes to directly communicate with each other over a communication
  channel" — no central server or broker in the data path. It exposes **Packet Transport
  Binary Sensor** and **Packet Transport Sensor** entities, i.e. `binary_sensor` and
  `sensor` domains — not a raw packet stream. The remote node's RD-03D presence reading
  becomes a normal `binary_sensor.*` entity through HA's existing **core** `esphome`
  integration (local push, already in this stack for other ESPHome devices) — zero new
  integration component, zero decoder service.
- [`sx127x` component docs](https://esphome.io/components/sx127x/): frequency 137–1020 MHz,
  covering the 915 MHz ISM band; bandwidth is configurable (`7_8kHz` … `500_0kHz` in LoRa
  mode); modulation is `OOK`, `FSK`, or `LORA`.

This satisfies the acceptance box that a transport must deliver typed `sensor` /
`binary_sensor` state, not raw packets needing a bespoke decoder — and it adds no new
container or broker, since it rides the `esphome` core integration already in this stack.

### Corrected claim from the issue body

TAP-7629 (and its sibling TAP-7595) states "ESPHome is already referenced in 9 product
files here." Re-run 2026-09-14, scoped the way TAP-7595 describes its own grep
(`domains/`, `libs/`, `custom_components/`, word-boundary): **7 files**, not 9
(`custom_components/` does not exist in this repo; the 9 figure could not be reproduced).
This does not change the decision — ESPHome is still an existing, referenced dependency —
but the number is corrected here rather than carried forward unverified.

TAP-7629 also states "S3 has already committed to [ESPHome] as the CSI transport." Checked
against TAP-7595 directly: it is Backlog, its own first acceptance box ("the firmware and
library choice is recorded as a decision...") is unchecked, and no CSI-related ADR exists
under `docs/architecture/` (checked: zero files mention CSI). ESPHome is stated as S3's
transport *constraint* in TAP-7595's issue body, but no S3 ADR has been recorded yet — this
is not an independently verifiable "already committed" decision, it is a same-author
restatement. Flagged here as unverified-as-written rather than repeated as fact.

## Options rejected — the specific constraint each one failed

**Meshtastic.** Has a maintained Home Assistant integration
([`meshtastic/home-assistant`](https://github.com/meshtastic/home-assistant)) reachable
over TCP, serial, or Bluetooth without a broker for the direct-connection path — so it
does not fail on the no-broker constraint the way TTN and ChirpStack do. It fails the
**typed-entity-without-a-decoder** constraint instead: the integration is installed via
HACS as a third-party `custom_component`, not part of Home Assistant core, and it decodes
Meshtastic's own mesh-node telemetry (battery, SNR, GPS, hop count) into entities — it has
no equivalent of ESPHome's `packet_transport` for exposing an arbitrary third-party
sensor's reading (an RD-03D's presence output) as a typed HA entity without first encoding
it into Meshtastic's protobuf telemetry schema and extending the decoder side to unpack it.
That decoder component is exactly the "bespoke decoder service" trap TAP-7629 names,
running inside Home Assistant instead of as a new container, but the same shape of
problem.

**The Things Network (TTN).** *Is* a Home Assistant **core** integration
([home-assistant.io/integrations/thethingsnetwork](https://www.home-assistant.io/integrations/thethingsnetwork)),
confirmed via the integration's own page: **IoT class: Cloud Polling**, introduced in Home
Assistant 0.55, requiring TTN's console/application layer in the cloud. Fails the
constraint that a Wi-Fi-unreachable zone's transport must not depend on an internet path
that a detached outbuilding may not have (and that HomeIQ, as a local-first appliance,
does not want as a dependency for presence sensing).

**ChirpStack.** Has no Home Assistant core integration. Every documented path to HA goes
through MQTT: ChirpStack's own
[MQTT integration](https://www.chirpstack.io/docs/chirpstack/integrations/mqtt.html)
publishes device data as JSON to broker topics; the community `chirpstack-ha-addon`
packages ChirpStack itself as an HA add-on but still requires bridging into HA's MQTT
broker; the third-party "chirp" custom component explicitly "glues together HA MQTT and
ChirpStack." Fails the no-MQTT-broker constraint directly — HomeIQ ships no broker today
(verified above), and every ChirpStack path requires one.

## Regional band and the regulatory limit on transmit scheduling

HomeIQ's default deployment timezone is `America/Los_Angeles`
(`domains/core-platform/compose.yml:716,768`) — a US deployment, so the applicable band is
**US915** (902–928 MHz ISM), not EU868.

Checked against 47 CFR §15.247 and §15.249 (law.cornell.edu, fetched 2026-09-14) rather
than carried over from memory:

- §15.247(a)(1)(i): a **frequency-hopping** system in this band with 20 dB hopping-channel
  bandwidth under 250 kHz must use at least 50 hopping frequencies, and "the average time
  of occupancy on any frequency shall not be greater than 0.4 seconds within a 20 second
  period." This is the rule that governs transmit scheduling **if** HomeIQ operates in
  hopping mode for extra range/power.
- §15.247(a)(2): a **digitally-modulated, non-hopping** system in the same band needs a
  minimum 6 dB bandwidth of 500 kHz (available as ESPHome's `500_0kHz` LoRa bandwidth
  option) to use this section's higher power allowance. No dwell-time or duty-cycle text
  applies to this path either.
- §15.249(a): a fixed-frequency, narrowband system that qualifies under neither of the
  above is limited to a 50 mV/m field strength at 3 m — no duty-cycle or periodic-
  transmission restriction at all, at the cost of much lower transmit power and range.

**HomeIQ's default is the §15.249(a) fixed-frequency, narrowband path** — RD-03D presence
events are small, infrequent payloads (a binary occupied/clear state, not a stream), so the
lower power ceiling is an acceptable trade for regulatory simplicity: no hopping to
implement, no dwell-time budget to track. The FHSS path (§15.247(a)(1)(i)) remains
available later if range proves insufficient on the bench.

**What the transport does not provide.** Verified against the `packet_transport` and
`sx127x`/`sx126x` component docs directly: neither implements frequency hopping, dwell-time
limiting, or any duty-cycle scheduling. If HomeIQ ever moves to the FHSS path above, the
50-channel hop sequence and the 0.4s/20s occupancy budget must be built at the application
layer — ESPHome does not provide it. This is deliberate and not a gap in this decision: the
fixed-frequency §15.249(a) default needs none of that, and the choice to add hopping later
is a separate, explicit decision this ADR does not make.

## Why this is provisional, not Accepted

This ADR is a paper decision. The one measurement that could overturn it —
**a bench link test between two nodes, with measured payload size, spreading factor, and
observed packet loss, over a stated distance and through stated obstructions** — is
blocked on hardware that does not exist yet: an RD-03D and two LoRa32 boards, not yet
ordered as of 2026-09-14 (recorded verbatim in TAP-7629's `## Deferred` section). Until
that test runs, this decision rests entirely on vendor documentation and FCC text, not on
a working link. **DEFERRED — not attempted here, per TAP-7629's explicit instruction not
to simulate or estimate it from datasheets.** Reopen it as a live acceptance box the moment
the boards arrive.

## `scripts/check-container-budget.py` — no new container, no MQTT broker

```
$ python3 scripts/check-container-budget.py
OK: 31 production services (ceiling 31, target 12); 7406 MiB recorded (ceiling 7406, target 4096), measured 2026-09-09.
     19 services above the TAP-5283 target of 12.
```

Exit 0. This decision adds no compose service, so the ratchet is untouched by design — the
transport rides the existing `esphome` and `websocket-ingestion` services.

**Negative control — proving the gate can fail.** Ran the same script against a throwaway
copy of the baseline with the service ceiling lowered by one (simulating a container added
without updating the baseline), compose files unchanged:

```
$ CONTAINER_BUDGET_FILE=<scratch>/container-budget-negctrl.json CONTAINER_BUDGET_ROOT=$(pwd) \
  python3 scripts/check-container-budget.py
FAIL: production container count 31 exceeds the ceiling of 30. Services added since the baseline:

  Consolidate, or raise the ceiling deliberately with --update-baseline and say why in the commit message.
```

Exit 1. The gate is capable of going red.

## Consequences

- No change to `infrastructure/container-budget.json`, `domains/core-platform/compose.yml`,
  or any running service — this ADR adds no code yet, it records the transport choice for
  the story that will ship the ESPHome node definition ([TAP-7630](https://linear.app/tappscodingagents/issue/TAP-7630)).
- `entity_filter.py` and `discovery_service.py` need no change: the remote node's entities
  arrive through the existing `esphome` core integration exactly like any other ESPHome
  device, with area assigned by HA's device registry the same way every other device gets
  one.
- The §15.249(a) power ceiling may prove too low on the bench for the actual outbuilding
  distances HomeIQ needs to cover. That is precisely what the deferred bench test exists to
  find out, and precisely why this ADR cannot be marked Accepted yet.
- If the bench test forces a move to FHSS (§15.247(a)(1)(i)), the 50-channel hop sequence
  and 0.4s/20s dwell budget are new application-layer work, not something ESPHome ships.

## See also

- [TAP-7629](https://linear.app/tappscodingagents/issue/TAP-7629) — this decision's issue
- [TAP-7628](https://linear.app/tappscodingagents/issue/TAP-7628) — parent epic (S5)
- [TAP-7630](https://linear.app/tappscodingagents/issue/TAP-7630) — ships the ESPHome
  radar+LoRa node definition and entity contract this ADR unblocks
- `docs/architecture/adr-appliance-secret-store.md` — the ADR format this one follows
- `.claude/rules/friendly-names.md` — why area comes from the device registry, never a name
