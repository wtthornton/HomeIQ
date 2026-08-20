---
name: home-atlas
description: Home structural ground truth for Home — 17 areas, 93 devices, 768 entities, each claim carrying how it was established. Rendered from dna-core/intake/homeiq.yaml; do not hand-edit.
version: 2.0.0
allowed_tools: ""
---
# Home Atlas — Structural Ground Truth

Genes that resolve entities, explain anomalies, or draft automations read this
pack to understand the home's physical structure.

**This file is rendered.** It is generated from `dna-core/intake/homeiq.yaml` by
`scripts/render_dna_core.py --write-packs`, and `scripts/validate.py` fails if it
drifts from that intake. Edit the intake, not this file. The intake in turn is
generated from the live instance by `scripts/generate_home_intake.py --write`.

## How to read a claim

Every claim below says how it was established. The classes are ordered:

    measured > upstream_source > attestation > unverified

- **`measured`** — read from the thing itself: a protocol-native identifier, or a
  physical observation.
- **`upstream_source`** — an integration's own model asserts it (a Hue bridge
  knows which room it commissioned a bulb into). Real corroboration, but it is
  the integration's belief, not a measurement.
- **`attestation`** — a person stated it, dated.
- **`unverified`** — nothing independent supports it.

There is no `name_match` class, and its absence is the point. A friendly name
that happens to contain an area name is not a way of knowing where a device is.
Two identically-modelled dimmers on this instance carried **swapped** names, so
every "office" row derived from names pointed at the bar switch; acting on one
would have written to the wrong physical device. Where a name echo is the only
signal, the row is typed `unverified` and says so in its method.

**A row with `actionable: false` must not be acted on.** Abstain and say why, or
run its `next_verification_step` first. Abstaining on a low-confidence row is a
correct outcome, not a failure.

## Instance

| Fact | Value |
|---|---|
| Instance | Home |
| Home Assistant | 2026.8.2 |
| Areas | 17 |
| Devices | 93 |
| Entities | 768 |
| Devices with no area | 33 |
| Verified at | 2026-08-19T22:28:51Z |
| Verified by | config/{area,device,entity}_registry/list over the HA websocket API, plus /api/states and /api/config over REST |

Every fact in this pack is as of `2026-08-19T22:28:51Z`. A home changes; a claim older
than the thing it describes is how the predecessor atlas came to name entities
that no longer existed.

## Areas

| Area id | Name | Devices | Evidence | How established |
| --- | --- | --- | --- | --- |
| `backyard` | `Backyard` | `2` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `bar` | `Bar` | `3` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `dining_room` | `Dining Room` | `1` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `driveway` | `Driveway` | `1` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `family_room` | `Family Room` | `1` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `garage` | `Garage` | `5` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `garage_hallway` | `Garage Hallway` | `2` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `guest_room` | `Guest Room` | `2` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `hallway` | `Hallway` | `3` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `kitchen` | `Kitchen` | `4` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `living_room` | `Living Room` | `9` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `master_bedroom` | `Master Bedroom` | `6` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `masters_closet` | `Masters Closet` | `1` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `office` | `Office` | `12` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `patio` | `Patio` | `3` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `porch` | `Porch` | `3` | `measured` | config/area_registry/list; device count from device_registry.area_id |
| `stairs` | `Stairs` | `2` | `measured` | config/area_registry/list; device count from device_registry.area_id |

## Device placement

One row per device that claims an area. `identity_evidence` and `area_evidence`
are separate columns because they fail independently: a device can be identified
perfectly by its ieee address and still be in an unknown room.

| Device | Area | Identity | Identity evidence | Area evidence | Confidence | Actionable | How established | Next verification step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Backyard` | `Backyard` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Hue outdoor motion sensor 1` | `Backyard` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Aqara Presence Sensor FP1E` | `Bar` | `zha ieee` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Bar` | `Bar` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Bar Light Dimmer` | `Bar` | `zha ieee` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Dishes` | `Dining Room` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Driveway` | `Driveway` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Family Room TV` | `Family Room` | `cast id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Basketball` | `Garage` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.garage_garage lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Garage` | `Garage` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Garage ` | `Garage` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Hue lightstrip outdoor 1` | `Garage` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.garage_garage lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Hue outdoor motion sensor 2` | `Garage` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Garage Door` | `Garage Hallway` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.garage_hallway_garage_hallway lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Garage Hallway` | `Garage Hallway` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Guest Room  TV` | `Guest Room` | `cast id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Guest Room  TV` | `Guest Room` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| ` New front hall back` | `Hallway` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.hallway_hallway lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Hallway` | `Hallway` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `New hallway front` | `Hallway` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.hallway_hallway lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `50" The Frame` | `Kitchen` | `cast id` | `upstream_source` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `50" The Frame` | `Kitchen` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `50&quot; The Frame (QN50LS03FAFXZA)` | `Kitchen` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Kitchen Strip` | `Kitchen` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `LR Back Left Ceiling` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.living_room_living_room lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `LR Back Right Ceiling` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.living_room_living_room lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `LR Front Left Ceiling` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.living_room_living_room lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `LR Front Right Ceiling` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.living_room_living_room lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Living Room ` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Living Room Button` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Living Room Left Play` | `Living Room` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Living room` | `Living Room` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `TV` | `Living Room` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Hue Smart button 1` | `Master Bedroom` | `mac` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Master Back Left` | `Master Bedroom` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.master_bedroom_master_bedroom lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Master Back Right` | `Master Bedroom` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.master_bedroom_master_bedroom lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Master Bedroom` | `Master Bedroom` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Master Front Left` | `Master Bedroom` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.master_bedroom_master_bedroom lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Master Front Right` | `Master Bedroom` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.master_bedroom_master_bedroom lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Masters Closet` | `Masters Closet` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Aqara Presence Sensor FP1E` | `Office` | `zha ieee` | `measured` | `unverified` | `low` | `false` | `registry area_id only; HA records no provenance for it` | correlate actuation against a sensor in the area, or confirm with the owner and date it |
| `Office Light Dimmer` | `Office` | `zha ieee` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Office Fan Switch` | `Office` | `zha ieee` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Office` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Office` | `Office` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Office Back Left` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.office_office lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Office Back Right` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.office_office lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Office Front Left` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.office_office lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Office Front Right` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.office_office lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Office Go` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.office_office lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Office Samsung TV (UN65TU700DFXZA)` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `[TV] Office Samsung TV` | `Office` | `mac` | `measured` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Back Porch Left` | `Patio` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.patio_patio lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Back Porch Right` | `Patio` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.patio_patio lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Patio` | `Patio` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Back Front Hallway` | `Porch` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.porch_porch lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Front Front Hallway` | `Porch` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.porch_porch lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Porch` | `Porch` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |
| `Bottom Of Stairs ` | `Stairs` | `mac` | `measured` | `unverified` | `low` | `false` | `observation only: hue room group light.stairs_stairs lists this device, but that group matches members by NAME, so it is a name match one hop removed and confers no evidence` | establish by behavioural correlation against a sensor in the area |
| `Stairs` | `Stairs` | `hue id` | `upstream_source` | `unverified` | `low` | `false` | `area name echoes the device's friendly name; no independent signal` | correlate actuation against a sensor in the area, or read protocol identity |

## Verified group entities

Only groups confirmed present on the instance appear here. The predecessor atlas
listed seven; six did not exist.

| Entity id | Members | Evidence | How established |
| --- | --- | --- | --- |
| `binary_sensor.office_presence_group` | `2` | `measured` | present in /api/states at verification time |

## Integrations

| Integration | Devices | Evidence | How established |
| --- | --- | --- | --- |
| `hue` | `51` | `measured` | device_registry identifiers |
| `hassio` | `8` | `measured` | device_registry identifiers |
| `zha` | `6` | `measured` | device_registry identifiers |
| `wled` | `5` | `measured` | device_registry identifiers |
| `cast` | `3` | `measured` | device_registry identifiers |
| `hacs` | `3` | `measured` | device_registry identifiers |
| `samsungtv` | `2` | `measured` | device_registry identifiers |
| `sun` | `1` | `measured` | device_registry identifiers |
| `backup` | `1` | `measured` | device_registry identifiers |
| `google_translate` | `1` | `measured` | device_registry identifiers |
| `met` | `1` | `measured` | device_registry identifiers |
| `rpi_power` | `1` | `measured` | device_registry identifiers |
| `raspberry_pi` | `1` | `measured` | device_registry identifiers |
| `ipp` | `1` | `measured` | device_registry identifiers |
| `upnp` | `1` | `measured` | device_registry identifiers |
| `upnp_host` | `1` | `measured` | device_registry identifiers |
| `upnp_serial_number` | `1` | `measured` | device_registry identifiers |
| `mobile_app` | `1` | `measured` | device_registry identifiers |
| `homeiq` | `1` | `measured` | device_registry identifiers |

## Naming

Entity ids on this instance follow no single scheme — these are real ids read
from the instance, not a convention to generate from. Resolve an entity by
looking it up, never by constructing an id from an area and a device type.

| Entity id | Friendly name | Evidence | How established |
| --- | --- | --- | --- |
| `light.bar` | `Bar` | `measured` | present in /api/states at verification time |
| `light.dishes` | `Dishes` | `measured` | present in /api/states at verification time |
| `light.downstairs` | `Downstairs` | `measured` | present in /api/states at verification time |
| `binary_sensor.archer_be800_wan_status` | `Archer BE800 WAN status` | `measured` | present in /api/states at verification time |
| `binary_sensor.backyard_hue_outdoor_motion_sensor_1_motion` | `Hue outdoor motion sensor 1 Motion` | `measured` | present in /api/states at verification time |
