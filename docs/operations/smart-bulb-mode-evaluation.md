# Smart-bulb-mode evaluation — Inovelli Blue dimmer circuits (TAP-5988)

Evaluated 2026-08-13 against the live instance (HA 2026.8.1), read-only via the
init gateway container. Rule: smart-bulb-mode changes only ever follow a
recorded, evidence-based recommendation — this document is that record. No
setting was changed as part of this evaluation.

## Evidence (read live 2026-08-12T23:06Z states, fetched 2026-08-13T01:2xZ)

| Observable | Office Light Dimmer (VZM31-SN) | Bar Light Dimmer (VZM31-SN) |
|---|---|---|
| `switch.…_smart_bulb_mode` | `off` | `off` |
| Dimmer output | `on`, brightness 33/255 (13%) | `on`, brightness 203/255 (80%) |
| Load power (`sensor.…_power`) | 0.0 W | 0.0 W |
| Smart bulbs in area | 4× **Hue color downlight** (ceiling cans) + 1× Hue Go (portable) + WLED strip | none (WLED strip only, separate DC PSU) |
| Smart-bulb health under current dimmer level | 3 downlights ON at full brightness (255), reachable, fresh states | n/a |

## Reasoning

**Office:** a trailing-edge dimmer passing 13% output cannot coexist with
healthy, full-brightness, reachable smart bulbs on its load — yet all three
lit downlights are stable at 255 while the dimmer sits at 13% and reports
0.0 W. The downlights are therefore receiving full, un-dimmed power today
(always-hot wiring or a different circuit). The room's primary lighting is
entirely smart bulbs.

**Bar:** the only other light in the area is `light.bar` (WLED, its own DC
power supply — 0.0 W on the dimmer while the strip is on confirms it is not
the dimmer's load). No smart bulbs on or near this circuit.

Caveat recorded honestly: both power sensors last updated 2026-08-12T23:06Z
(same instant as a ZHA state refresh), so the 0.0 W readings may be
report-threshold-stale. The brightness-vs-bulb-health observation does not
depend on the power sensor and stands alone.

## Recommendations

1. **Office Light Dimmer — ENABLE smart-bulb-mode.** The circuit's room
   lighting is entirely smart (4 Hue downlights). If the downlights are truly
   always-hot, enabling is electrically a no-op on an unloaded terminal; if
   they are in fact on the load (power telemetry being stale), enabling
   guarantees they can never be browned-out or cut by a paddle press. Strictly
   better in both worlds, and it turns the paddle into the pure scene
   controller the TAP-5987 gesture catalogue assumes.
2. **Bar Light Dimmer — LEAVE AS-IS (off).** No smart bulbs on the circuit;
   the WLED strip is separately powered. Enabling would only remove local
   dimming from whatever conventional load the dimmer feeds.

## Applying (not done here)

Enabling is one HA write: `switch.inovelli_vzm31_sn_smart_bulb_mode_2` → on,
routed through the gateway converge path per standing rules, after owner
acknowledgment of recommendation 1. Record the before/after in the applying
change, not here.
