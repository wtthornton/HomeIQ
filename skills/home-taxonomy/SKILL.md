---
name: home-taxonomy
description: Device event types, anomaly labels, maintenance events, and integration identity labels that hiq-classify uses to triage ingest items.
version: 1.0.0
allowed_tools: ""
---
# Home Taxonomy — Label Sets for Classification

The `hiq-classify` gene receives a taxonomy as an input and assigns labels from it to ingest envelope items. This skill defines the four label sets: device events, anomalies, maintenance, and integrations.

## Device Event Types

Labels for the originating source/type of a home event.

- `state_changed` — Entity state transitioned (e.g., light on→off, sensor reading updated)
- `automation_triggered` — An automation executed
- `service_call` — A service was called (not through automation)
- `device_action` — Physical button press or device-originated action
- `integration_event` — Integration webhook or upstream event
- `user_input` — User or customer request received
- `system_event` — HA system event (startup, shutdown, core restart)
- `unknown_event` — Event type could not be determined

**Fallback (when input does not match any above):** `unknown_event`

## Anomaly Labels

Labels for detected problems or unexpected conditions.

- `power_spike` — Sudden increase in power draw
- `power_dip` — Sudden decrease in power draw
- `sensor_stall` — Sensor reading unchanged for longer than expected
- `unavailable_flap` — Entity repeatedly cycling between available↔unavailable
- `battery_low` — Battery state below critical threshold
- `battery_dead` — Battery at 0% or entity unavailable due to dead battery
- `presence_conflict` — Multiple presence signals contradicting each other
- `temperature_extreme` — Temperature outside expected range for the area
- `humidity_extreme` — Humidity outside expected range
- `connectivity_loss` — Device lost network/zigbee/wifi connectivity
- `automation_failure` — Automation did not execute or execution failed
- `integration_offline` — Integration bridge/hub offline or unreachable

**Fallback (when anomaly does not match above):** `integration_offline`

## Maintenance Labels

Labels for predicted or observed maintenance needs.

- `device_age_warning` — Device approaching end-of-life based on purchase date
- `filter_replacement_due` — Filter (HVAC, air purifier) due for replacement
- `scheduled_maintenance` — Planned maintenance window approaching
- `calibration_needed` — Sensor calibration drifting (typical for analog sensors)
- `firmware_update_available` — Device firmware update ready to apply
- `integration_update_available` — Integration or add-on update available

**Fallback (when maintenance type does not match above):** `firmware_update_available`

## Integration Labels

Labels identifying the system/integration the entity belongs to.

- `zha` — Zigbee Home Automation (native HA integration)
- `hue` — Philips Hue Bridge
- `powercalc` — Powercalc power estimation
- `smart_meter` — Utility smart meter / energy monitor
- `mqtt` — MQTT-connected devices
- `zwave` — Z-Wave devices
- `matter` — Matter protocol devices
- `local_calendar` — Home Assistant local calendar
- `rest` — REST/HTTP integration
- `template` — HA template entities
- `helper` — HA helper (automation, script, template sensor)
- `modbus` — Modbus RTU/TCP devices
- `weather` — Weather integration
- `system` — Home Assistant system/core
- `unknown` — Integration could not be determined

**Fallback (when integration does not match above):** `unknown`

## Classification Rules

1. **One label per set.** Each classified item receives exactly one label from each set (one device event type, one anomaly if applicable, etc.).
2. **Always use fallback when unsure.** Never invent a label. If the input does not clearly match any label, use the designated fallback for that set and explain in the `rationale`.
3. **Ambiguous cases pick the costlier misclassification.** When torn between two labels, prefer the one that will get the item re-routed more quickly to a human if wrong (false negative is worse than false positive).
4. **Urgency ladder:** device events and anomalies carry urgency (`low`, `medium`, `high`, `critical`); other labels are informational.

## Refresh Policy

This taxonomy is versioned in git and committed when HA 2026.x reaches a new stable release, when new integrations are added to the home, or when anomaly patterns change. Use the latest version in `skills/home-taxonomy/SKILL.md`. Stale copies are silently overwritten on next ingest.
