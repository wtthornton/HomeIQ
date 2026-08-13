# Smart-bulb-mode evaluation — Inovelli Blue dimmer circuits (TAP-5988)

Evaluated 2026-08-13 (evidence read 2026-08-13T01:0x–01:2xZ; adversarially
re-verified same hour) against the live instance (HA 2026.8.1), read-only via the
init gateway container. Rule: smart-bulb-mode changes only ever follow a
recorded, evidence-based recommendation — this document is that record. No
setting was changed as part of this evaluation.

## Evidence (read live 2026-08-12T23:06Z states, fetched 2026-08-13T01:2xZ)

| Observable | Office Light Dimmer (VZM31-SN) | Bar Light Dimmer (VZM31-SN) |
|---|---|---|
| `switch.…_smart_bulb_mode` | `off` | `off` |
| `select.…_output_mode` | **`Dimmer`** (load-bearing fact: the 13% inference below is only valid in this mode — contrast the Office Fan Switch, which runs `OnOff`) | `Dimmer` |
| `select.…_dimming_mode` | `LeadingEdge` | `LeadingEdge` |
| `select.…_switch_type` | **`Three Way AUX`** — a deliberate 3-way install; someone wired an aux companion, which argues the load terminal is NOT unloaded | n/a checked |
| Dimmer output | `on`, brightness 33/255 (13%) | `on`, brightness 203/255 (80%) |
| Load power (`sensor.…_power`) | 0.0 W | 0.0 W |
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

Enabling is one HA write: `switch.inovelli_vzm31_sn_smart_bulb_mode_2` → on,
routed through the gateway converge path per standing rules, after owner
acknowledgment of recommendation 1. Record the before/after in the applying
change, not here.
