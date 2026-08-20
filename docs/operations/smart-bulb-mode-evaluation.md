# Smart-bulb-mode evaluation — Inovelli Blue dimmer circuits (TAP-5988)

Evaluated 2026-08-13 (evidence read 2026-08-13T01:0x–01:2xZ; adversarially
re-verified same hour) against the live instance (HA 2026.8.1), read-only via the
init gateway container. Rule: smart-bulb-mode changes only ever follow a
recorded, evidence-based recommendation — this document is that record. No
setting was changed as part of this evaluation.

## Evidence (read live 2026-08-12T23:06Z states, fetched 2026-08-13T01:2xZ)

> **⚠️ IDENTITY CORRECTION — 2026-08-19. The Office/Bar columns below are
> INVERTED.** The mapping under them was "verified by friendly-name mapping",
> and those two friendly names were swapped on the instance. Re-read against
> ieee ground truth (`config/device_registry/list`, 2026-08-19):
>
> | ieee | area | slug | role |
> |---|---|---|---|
> | `90:35:ea:ff:fe:c9:0e:8f` | Office | **unsuffixed** `inovelli_vzm31_sn` | **Office Light Dimmer** |
> | `90:35:ea:ff:fe:c9:11:ef` | Bar | **`_2`-suffixed** | **Bar Light Dimmer** |
>
> So every "Office id" cell below names the **Bar** device and vice versa. The
> observations are real; their attribution is not. Do not act on a row without
> re-attaching it by ieee. See
> [`docs/architecture/adr-device-knowledge-provenance.md`](../architecture/adr-device-knowledge-provenance.md)
> — a name-string match is `inferred` evidence and must never outrank a
> `measured` identity.

Entity-id convention as originally recorded (**inverted — see the correction
above**): the `_2`-suffixed entities were taken to belong to the Office Light
Dimmer, and the unsuffixed `inovelli_vzm31_sn` entities to the Bar Light Dimmer.
Full ids per row:

| Observable (Office id / Bar id) | Office Light Dimmer (VZM31-SN) | Bar Light Dimmer (VZM31-SN) |
|---|---|---|
| `switch.inovelli_vzm31_sn_smart_bulb_mode_2` / `switch.inovelli_vzm31_sn_smart_bulb_mode` | `off` | `off` |
| `select.inovelli_vzm31_sn_output_mode_2` / `select.inovelli_vzm31_sn_output_mode` | **`Dimmer`** (load-bearing fact: the 13% inference below is only valid in this mode — contrast the Office Fan Switch, which runs `OnOff`) | `Dimmer` |
| `select.inovelli_vzm31_sn_dimming_mode_2` / `select.inovelli_vzm31_sn_dimming_mode` | `LeadingEdge` | `LeadingEdge` |
| `select.inovelli_vzm31_sn_switch_type_2` / `select.inovelli_vzm31_sn_switch_type` | **`Three Way AUX`** | **`Three Way AUX`** (read during panel verification — BOTH dimmers are 3-way installs, so this setting alone does not differentiate the circuits; it still argues each load terminal has real wiring behind it) |
| Dimmer output (`light.inovelli_vzm31_sn_2` / `light.inovelli_vzm31_sn`) | `on`, brightness 33/255 (13%) | `on`, brightness 203/255 (80%) |
| Load power (`sensor.inovelli_vzm31_sn_power_2` / `sensor.inovelli_vzm31_sn_power`) | 0.0 W | 0.0 W |
| Smart bulbs in area | 4× **Hue color downlight** (ceiling cans) + 1× Hue Go (portable) + WLED strip | none (WLED strip only, separate DC PSU) |
| Smart-bulb health under current dimmer level | 3 downlights ON at full brightness (255), reachable, fresh states | n/a |

## Reasoning

**Office:** a dimmer in `Dimmer` output mode (leading-edge) passing 13%
output cannot coexist with healthy, full-brightness, reachable smart bulbs
on its load — yet all three lit downlights are stable at 255 while the
dimmer sits at 13%, sustained over 2h14m with no availability blip (adversarial
verification cross-checked this over recorder history, not a snapshot). The
downlights therefore receive full, un-dimmed power today — always-hot wiring
or a different circuit. A concrete "different circuit" candidate exists in
the same room: `light.inovelli_vzm35_sn_light` (the Office Fan Switch's
mains light channel, `OnOff` mode, on at 254). What the dimmer's own load
terminal feeds is NOT established: 0.0 W says "nothing", but that sensor may
be a never-bound attribute, and `switch_type = Three Way AUX` is live
evidence someone deliberately wired this as a 3-way — pointing at a real
conventional load.

(The unavailable `light.office_office_go` is the portable USB-powered Hue Go
— its unavailability is not circuit evidence.)

**Bar:** the only other light in the area is `light.bar` (WLED, its own DC
power supply — 0.0 W on the dimmer while the strip is on confirms it is not
the dimmer's load). No smart bulbs on or near this circuit.

Caveat recorded honestly: the 0.0 W power readings are three history points
(`0.0` → `unavailable` → `0.0` across a ZHA restart) while the same device's
temperature sensor reported ~every 90 s — the electrical-measurement channel
either genuinely never changes or was never bound. Treat 0.0 W as weak
evidence. The brightness-vs-bulb-health observation does not depend on it
and stands alone.

## Recommendations

1. **Office Light Dimmer — ENABLE smart-bulb-mode, conditional on one
   owner-confirmable fact:** what does this dimmer's load terminal feed?
   - If it feeds the Hue downlights (power telemetry stale): enabling
     protects them from paddle brown-outs — clearly better.
   - If it feeds nothing: enabling is electrically a no-op — harmless.
   - **Third world, not ruled out:** if it feeds a conventional (non-smart)
     load — which `Three Way AUX` wiring hints at — enabling would pin that
     load at full mains and strip local dimming, the exact harm that keeps
     the Bar dimmer as-is. Confirm by paddle-testing what physically changes
     (10 seconds at the wall) or by owner knowledge of the circuit.
   Enable is better in the two established worlds and recommended; the
   third world needs the 10-second check first. It also turns the paddle
   into the pure scene controller the TAP-5987 gesture catalogue assumes.
2. **Bar Light Dimmer — LEAVE AS-IS (off).** No smart bulbs on the circuit;
   the WLED strip is separately powered. Enabling would only remove local
   dimming from whatever conventional load the dimmer feeds.

## Applying (not done here)

Enabling is one HA write on the **Office** dimmer, which by ieee `90:35:ea:ff:fe:c9:0e:8f` is the **unsuffixed** entity:
`switch.inovelli_vzm31_sn_smart_bulb_mode` → on (**not** the `_2` slug this
document originally named — that is the Bar dimmer, which recommendation 2
says to leave alone),
routed through the gateway converge path per standing rules, after owner
acknowledgment of recommendation 1. Record the before/after in the applying
change, not here.
