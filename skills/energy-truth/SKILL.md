---
name: energy-truth
description: Authoritative energy metric definitions, source authority rules, and expected discrepancy handling. Smart meter is authoritative for whole-home watts and kWh; Powercalc estimates are never authoritative vs meter; carbon only from carbon service; HA entity states authoritative for device on/off.
version: 1.0.0
allowed_tools: ""
---
# Energy Truth — Metric Definitions and Authority Rules

When the `hiq-correlate` gene joins energy data from multiple sources (smart meter, Home Assistant entity states, Powercalc estimates, weather API), it consults this skill to decide which source is authoritative for each field and whether a discrepancy is expected or anomalous.

## Authoritative Sources by Field

| Field | Authoritative Source | Never Authoritative | Why |
|-------|----------------------|---------------------|-----|
| **Whole-home power (watts)** | Smart meter (current_power_w) | Powercalc sum, HA sensor.total_power (unless manually calibrated) | Meter is a direct measurement; Powercalc is estimation for unmetered loads only |
| **Daily energy (kWh)** | Smart meter (daily_kwh) | Powercalc, HA helper sum | Meter is the utility's ground truth for billing; Powercalc estimates |
| **Peak power in 24h** | Smart meter (peak_power_w) | Powercalc, HA logs | Meter records the actual peak; Powercalc may smooth peaks |
| **Device on/off state** | Home Assistant entity state | Powercalc (which infers from on/off) | HA is the source for device logic; Powercalc depends on it |
| **Device power draw when on** | Powercalc (average_power_on_w) for unmetered devices; smart meter for whole-home | Estimated sum of Powercalc values | Powercalc is purpose-built for estimation; meter for metered loads only |
| **Estimated daily energy per device** | Powercalc (estimated_daily_kwh) | — | Powercalc projects from observed duty cycle; not a measurement |
| **Carbon intensity (gCO2/kWh)** | Carbon Intensity API (grid_operator + intensity) | Any local estimate, HA sensor guess | API is real-time grid data; local estimates are stale |
| **Presence / occupancy** | Home Assistant presence group and individual sensors | Inferred from power spike timing or anomalies | HA is the authoritative source for logical state |

## Metric Definitions

**`current_power_w`** — Latest whole-home smart-meter reading in watts.
- Source: data-api `/api/v1/energy/statistics` → `current_power_w`
- Freshness: Updated ≥ once per minute (meter dependent; typically 1–30 sec)
- Null handling: Omitted if meter is offline or reading failed

**`daily_kwh`** — Energy consumed since local midnight, in kilowatt-hours.
- Calculation: Watt-hours / 1000
- Source: Smart meter via data-api `/api/v1/energy/statistics`
- Boundary: Resets at 00:00 local timezone
- Null handling: Omitted if meter is offline

**`peak_power_w` / `peak_time`** — Highest reading in the 24-hour statistics window and when it occurred.
- Source: Smart meter via data-api (computed from meter's own rolling window)
- Freshness: Calculated over 24 hours; may lag by up to 1 hour depending on meter
- Null handling: Omitted if meter offline

**`average_power_w`** — Mean power draw over the 24-hour statistics window, in watts.
- Calculation: Sum of meter readings / number of readings over 24h
- Source: Smart meter via data-api
- Null handling: Omitted if meter offline or insufficient readings

**`top_consumers[].average_power_on_w`** — Mean power draw while the device is in the "on" state, in watts.
- Source: Powercalc (powerid calculator)
- Interpretation: Powercalc's estimate of mean draw when the device is not standby
- Note: Not a measurement; calibration required for accuracy

**`top_consumers[].estimated_daily_kwh`** — Powercalc's projection of the device's daily consumption based on observed duty cycle.
- Calculation: Powercalc projects from `average_power_on_w` × observed on-time
- Interpretation: Estimate only; used for comparison with meter totals to spot anomalies
- Note: Sum of device estimates ≠ smart meter total due to unmetered loads

**`carbon.grams_per_kwh`** — Grid carbon intensity from the carbon service.
- Source: Carbon Intensity API (data-api `/api/v1/energy/carbon-intensity/current`)
- Field: `intensity` (gCO2 per kilowatt-hour)
- Grid operator: Included in `source` field if available
- Null handling: Field is omitted (never set to 0 or estimated) if the carbon service returns 404 or no reading

## Expected Discrepancies — Do Not Raise as Anomalies

### 1. Smart-Meter Total vs. Powercalc Device Sum

**Expected variance:** 5–30% difference.

**Why:** Powercalc estimates only controllable loads; it misses:
- Standby power draw (always-on, small)
- Conversion losses (AC/DC supplies, inverters)
- Wiring losses and transformers
- Loads Powercalc hasn't been trained on (e.g., specialized medical equipment)
- Integration overhead and helper automations

**Handling:** If `(powercalc_sum / meter_total) < 0.9` or `> 1.1`, mark it as `expected: true` in the conflict entry. Preserve both figures with attribution. Do NOT flag as power_spike or anomaly.

**Example:**
```json
{
  "field": "daily_energy_reconciliation",
  "smart_meter_kwh": 12.5,
  "powercalc_estimate_kwh": 10.2,
  "discrepancy_pct": 18.4,
  "expected": true,
  "reason": "Unmetered loads and standby draw account for variance",
  "recommendation": "no action"
}
```

### 2. Peak Power Timestamp Mismatch

**Expected variance:** ±5 minutes.

**Why:** Meter and Powercalc's statistics window boundaries may not align; meter may report peak at a different granularity than HA polling.

**Handling:** If peak occurs within ±5 minutes, do not raise as anomaly. Report both timestamps; mark `expected: true`.

### 3. No Carbon Intensity Available

**Expected condition:** Carbon service offline or region has no data.

**Handling:** Omit the `carbon` field entirely. Do NOT infer zero, estimate from historical data, or use a placeholder. Absent ≠ zero.

## Non-Expected Discrepancies — Investigate

### 1. Smart Meter Reports 0 W, But Devices Are On

Meter offline, not reporting, or wired incorrectly.

### 2. Powercalc Sum >> Smart Meter (>150%)

Calibration error or Powercalc overestimating a dominant load.

### 3. Daily Energy Goes Backward

Meter reset, billing boundary crossed, or clock skew.

## Conflict Entry Structure

When reporting a discrepancy, use this shape:

```json
{
  "source_a": "smart_meter",
  "field_a": "current_power_w",
  "value_a": 5200,
  "source_b": "powercalc",
  "field_b": "estimated_current_power_w",
  "value_b": 4100,
  "delta_pct": 21.0,
  "expected": true,
  "reason": "Unmetered standby loads account for difference",
  "recommendation": "monitor for increase; normal variance"
}
```

## Integration with Genes

- **hiq-correlate**: Receives this skill as input. Uses authority rules to decide which source to trust for each field. Never blends authorities.
- **hiq-explain-anomaly**: References expected-discrepancy rules when interpreting why power did not match expectations.
- **hiq-memory-curator**: Learns seasonal patterns for peak/average power so anomaly detection improves over time.

## Versioning

- **Version:** 1.0.0
- **Last Updated:** 2026-02-03
- **Aligned with:** data-api `/api/v1/energy/*` contract (v2.0) and Powercalc 2026.01+
