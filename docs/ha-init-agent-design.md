# HA Init/Setup Agent — Design & Priority Plan

> **SUPERSEDED for the appliance, 2026-08-23.** This document describes converging
> an **external, Supervised** Home Assistant that the customer owns. HomeIQ now
> ships and owns a **headless HA Container** instance with no Supervisor, so every
> add-on claim below is false for the shipped product: there is no Supervisor API,
> no add-on store, no `core_ssh`, no `core_configurator`, and HACS is a build-time
> tool that is not present at runtime. Powercalc, Team Tracker and the Aqara FP1E
> quirk are vendored into `/config/custom_components/` at image build. The
> long-lived token is minted automatically on first boot, not created by a person.
>
> Read [`docs/architecture/adr-appliance-packaging.md`](architecture/adr-appliance-packaging.md)
> first. It records the decision, what it deletes, and what it costs.
>
> What in here is **still accurate**: the phase model and its ordering, the backup
> gate, the check/plan/apply/verify recipe contract, the human-gate semantics, and
> the reasoning about why nothing is auto-applied. Those survived the reversal
> unchanged. The add-on and HACS mechanics did not.

**Status:** Executed and live against the original external instance. The engine has converged the real instance repeatedly
since 2026-08-11 through the init gateway (`:8024`, PR #82); the recipe set has grown
past this document (20 audit outcomes as of 2026-08-13, including report-only Zigbee
diagnostics and a coordinator watchdog). Treat the sections below as the founding
design, not a current inventory — the code (`libs/homeiq-ha/src/homeiq_ha/agent/`)
and `docs/operations/init-gateway.md` are current.
**Target instance:** HA 2026.7.4 at design time (2026.8.1 as of 2026-08-13), HAOS/Supervised, Raspberry Pi (aarch64), `192.168.1.80:8123`
**Date:** 2026-08-01 (currency note updated 2026-08-13)

---

## 1. Current state (measured, not assumed)

Everything below was read live from the instance via read-only API calls.

| Dimension | Reality |
|---|---|
| Devices | **19** — 5× WLED strips (Bar, Dishes, Kitchen Strip, Living Room, Office), 2× Chromecast TV, plus Pi/system entries |
| Entities | 164 in registry, 123 in state API (41 disabled/hidden) |
| Config entries | 19, of which **14 are HA defaults** (sun, bluetooth, analytics, radio_browser, go2rtc, shopping_list, thread, met, google_translate, cast, hassio, backup, raspberry_pi, rpi_power) |
| Real integrations | **WLED ×5 + Cast.** That is the entire smart home today. |
| Add-ons ("Apps") | **0 installed** (79 available in store) |
| Areas / Floors / Labels | 3 areas (Living Room, Kitchen, Bedroom) / **0 floors** / **0 labels** |
| **Backups** | 🔴 **NONE. Zero backups exist. `automatic_backups_configured: false`, schedule `never`, no storage agent, no retention, no encryption key.** |
| Location | Set correctly — 35.9561663, -115.1833246 (Henderson NV), `America/Los_Angeles` |
| Remote access | Nabu Casa Cloud loaded |
| Token identity | `Tapps House` — **admin + owner** |
| Energy dashboard | Loaded but **inert** — no energy/power sensors exist |

**Reading of this:** the instance is essentially factory-fresh with a handful of lights. That is *good news* — the expensive organizational decisions (floors, areas, labels, naming) are cheap now and get more expensive with every device added.

---

## 2. The automation ceiling (this drives the whole design)

The single most important discovery, verified two independent ways — a live probe against this instance, and a source read of `home-assistant/core` at the pinned `2026.7.4` tag:

> **The REST path `/api/hassio/*` is a hard deny-by-default allowlist and returns 401 even for an admin+owner token.
> The WebSocket command `supervisor/api` is an *unrestricted Supervisor passthrough* for admin users.**

```jsonc
// This works. It is how the HA frontend itself drives the Supervisor panel.
{"id": 1, "type": "supervisor/api",
 "endpoint": "/store/addons/core_ssh/install", "method": "post", "timeout": 900}
```

Without this, the agent could only write documentation. With it, add-on installation, custom repositories, network mounts, and the full Supervisor surface are all reachable from outside the host using the token we already hold.

### What is automatable

| Capability | Mechanism |
|---|---|
| Areas, Floors, Labels, Categories, Zones — full CRUD | WS `config/{registry}/*` |
| Entity rename / entity_id change / icon / hide / disable / area / labels | WS `config/entity_registry/update` |
| Device → area assignment, rename, labels | WS `config/device_registry/update` |
| **Backup schedule, retention, encryption, off-site fan-out** | WS `backup/config/update` |
| Create / restore / delete backups | WS `backup/*` + REST |
| **Install, configure, start, set boot policy for any add-on** | WS `supervisor/api` |
| Add custom add-on repositories | WS `supervisor/api` → `POST /store/repositories` |
| Network storage mounts (off-site backup target) | WS `supervisor/api` → `/mounts` |
| Non-OAuth integration setup, end to end | REST `POST /api/config/config_entries/flow` |
| All 27 helper types (9 storage-collection + 18 config-flow) | WS `{domain}/create` / REST flow |
| Automations, scripts, scenes | REST `/api/config/{domain}/config/{key}` |
| Restart / reload_all / check_config | REST services |
| Idempotency detection for every one of the above | list/get probes + `require_restart` flags |

### What genuinely requires a human

| Blocker | Why | Mitigation |
|---|---|---|
| **OAuth integrations** (Google Drive backup agent, Spotify, etc.) | Flow returns `type: "external"`; core **refuses** client-side advancement | Agent surfaces the URL, human clicks, agent detects the new config entry and resumes |
| **HACS GitHub device authorization** | No PAT bypass exists in HACS 2.x | ✅ **Device code + URL are machine-readable** in `description_placeholders`. Agent displays them and polls. Human effort: open a URL, type 6 characters. |
| **Physical pairing** (Hue button, Z-Wave inclusion) | Real-world action | Agent surfaces prompt, polls |
| Creating the long-lived token | Bootstrap chicken-and-egg | Already done |

---

## 3. Correcting the existing `ha-setup-service`

HomeIQ already ships `ha-setup-service` (host port 8024). An audit found it is **substantially non-functional** and must be fixed rather than extended blindly:

- `MQTTSetupWizard` is a **pure stub** — defines 5 steps, never overrides `_execute_step_logic`, so every step returns "success" while doing nothing.
- **Rollback is a no-op.** `_rollback_step()` is an empty method body, no subclass overrides it, and it is not exposed on any route.
- **Two competing Zigbee wizards** (`setup_wizard.py` and `zigbee_setup_wizard.py`) with different step models and no shared state.
- Calls **two HA services that do not exist**: `mqtt.discover` and `zigbee2mqtt.permit_join`.
- Uses `POST /api/hassio/addon/...` — **which returns 401**, as proven above.

### The platform-wide bug worth fixing first

**Six+ services call HA's entity/device/area registries over REST. Those endpoints do not exist — they are WebSocket-only commands.** Affected: `ha-setup-service`, `data-api`, `device-health-monitor`, `device-context-classifier`, `device-recommender`, `device-setup-assistant`, `ha-ai-agent-service`, `device-intelligence-service`. Most degrade silently; but **every "apply a fix to Home Assistant" path in HomeIQ is currently dead because of this.**

→ **A shared WebSocket HA client in `libs/homeiq-ha` is the highest-leverage single change in this entire plan.** The setup agent needs it; eight other services are silently broken without it.

---

## 4. Agent design

### 4.1 Shape

A **declarative, idempotent, plan/apply engine** — Terraform-shaped, not wizard-shaped. The existing wizard model (in-memory sessions, step numbers, no rollback) is the wrong abstraction for something that must be safely re-runnable.

```
HAInitAgent
├── HAClient (libs/homeiq-ha)        ← shared; fixes the platform-wide REST/WS bug
│   ├── rest       (config flows, automations, services)
│   ├── ws         (registries, helpers, backup, entity updates)
│   └── supervisor (via ws `supervisor/api`)  ← the unlock
├── Recipe registry                  ← each unit of setup work
└── Engine: check() → plan() → apply() → verify() → report()
```

Every recipe implements four methods:

| Method | Contract |
|---|---|
| `check()` | Read-only. Returns `SATISFIED` / `NEEDS_APPLY` / `BLOCKED_ON_HUMAN` / `NOT_APPLICABLE` |
| `plan()` | Returns a human-readable diff. **No writes.** |
| `apply()` | Performs the change. Must be safe to re-run. |
| `verify()` | Independently re-reads state to confirm the change landed |

### 4.2 Operating modes

1. **`audit`** — run every `check()`, write a report. Zero writes. *This is the default and the only mode that should run unattended initially.*
2. **`plan`** — show the exact diff that `apply` would produce.
3. **`apply --phase N`** — execute one phase, with verification.
4. **`apply --all`** — full run, halting at each human gate.

### 4.3 Non-negotiable safety rules

1. **Phase 1 (backup) must succeed before any other phase runs.** A setup agent that mutates an unbacked-up instance is a liability.
2. **Take a backup immediately before each subsequent phase.** Every phase is then individually revertible.
3. **`homeassistant.check_config` before any restart**; read the `require_restart` flag from API responses rather than guessing.
4. **Never write secrets to the repo.** Note: `backup/config/info` returns the backup encryption key **in plaintext** — any admin token is therefore a secret-bearing credential and the agent's logs must redact it.
5. **Human gates are hard stops**, not timeouts. The agent surfaces the URL/code and waits.

---

## 5. Priority list — for review

Legend: 🤖 fully automatable · 🔶 automatable with one human step · 👤 manual · ⏸️ deferred (prerequisite missing)

### P0 — Do first. Nothing else matters until these are done.

| # | Action | Why | Mode |
|---|---|---|---|
| 0.1 | **Configure automatic backups**: daily, keep 7, pre-update backup ON, contents `config`+`ssl`+`apps` (exclude `media`/`share`), encryption ON | 🔴 **Zero backups exist today.** The entire instance is one SD-card failure from total loss. | 🤖 WS `backup/config/update` |
| 0.2 | **Add a second off-site backup target** (Google Drive / OneDrive / Dropbox — all now *official core integrations*, not add-ons) | Nabu Casa Cloud stores **exactly one** backup file (5 GB, latest only). It is not sufficient alone. | 🔶 OAuth = human click |
| 0.3 | **Download the Backup Emergency Kit** and store it in a password manager, off the HA host | Without the encryption key, backups are unrecoverable. Nabu Casa cannot recover it for you. | 👤 |
| 0.4 | **Take and verify a first full backup** | An untested backup is a hope, not a backup. | 🤖 |
| 0.5 | **Backup-staleness alert automation** — notify if last successful backup >48 h old | Silent backup failure is the #1 real-world failure mode. | 🤖 |

### P1 — Security & correctness. Cheap, high consequence.

| # | Action | Why | Mode |
|---|---|---|---|
| 1.1 | Set `login_attempts_threshold: 5` in `http:` | `ip_ban_enabled` defaults **true** but the threshold defaults to **`-1` = disabled**, so IP banning does nothing out of the box. | 🤖 (YAML — needs file access) |
| 1.2 | **Enable TOTP MFA on the admin account** | With Nabu Casa, all remote traffic arrives as `127.0.0.1`, so IP banning cannot see remote clients. **MFA is the actual remote-auth control.** | 👤 |
| 1.3 | **Set currency to USD** | Defaults to **EUR** — all Energy dashboard costs would be wrong. | 🤖 |
| 1.4 | Create a **dedicated non-admin service user + token for HomeIQ** | HomeIQ currently uses the owner's admin token. One token per consumer, least privilege. ⚠️ *Note: some HomeIQ writes need admin — scope must be tested before switching.* | 👤 + 🤖 |
| 1.5 | Set add-on update policy: Supervisor auto-update **ON**, apps auto-update **OFF**, Core manual +1 week | Out-of-date Supervisor → unsupported state. Auto-updating third-party apps is how instances break at 3am. | 🤖 |

### P2 — Organization. Cheap now (19 devices), expensive later.

| # | Action | Why | Mode |
|---|---|---|---|
| 2.1 | **Create Floors, expand Areas, assign all 19 devices** | **2026.7 graduated area-targeted triggers/conditions out of Labs.** Automations now target *areas*, so they adapt as devices change. Area hygiene is load-bearing, not cosmetic. Also: the new Maintenance dashboard groups batteries by area, and Assist reasons over areas. | 🤖 |
| 2.2 | Create Labels (e.g. `downstairs`, `exterior`, `critical`) | Cross-cutting grouping; automation-targetable. Zero exist today. | 🤖 |
| 2.3 | Rename **devices** (not entities) where names are poor | `has_entity_name` cascades device renames to entity_ids and friendly names — 19 renames vs 164. | 🤖 |
| 2.4 | Apply `recorder:` tuning — `purge_keep_days: 3`, exclude `update` domain + `*_rssi`/`*_linkquality`/`*_uptime` globs, `commit_interval: 10` | **HomeIQ/InfluxDB already owns long-term history.** Long-term statistics are *never* purged, so the Energy dashboard is unaffected. Stay on **SQLite** — official docs now actively favor it over MariaDB at this scale. | 🤖 (YAML) |

### P3 — Capability. This is where HomeIQ starts earning its keep.

| # | Action | Why | Mode |
|---|---|---|---|
| 3.1 | **Install HACS** via the official **"Get HACS" add-on** (the `wget \| bash` method in every online guide is Container/Core-only and stale) | Gateway for everything below. | 🔶 GitHub device code |
| 3.2 | **Install Team Tracker** + `ha-teamtracker-card` | ⚠️ **Explicitly requested — and `sports-api` is 100 % dead weight without it.** See the naming trap in §6. | 🤖 after HACS |
| 3.3 | **Install Powercalc** | **Highest-value install after Team Tracker.** 7 lights + 27 switches with zero energy metering is exactly its use case — derives live wattage from brightness/color using 190+ device profiles. Populates the Energy dashboard *and* feeds HomeIQ's energy-correlation chain with **no hardware purchase**. | 🤖 |
| 3.4 | Install **OpenThread Border Router** add-on | You have a Thread radio doing nothing. This activates it. | 🤖 |
| 3.5 | Install **Terminal & SSH** + **Studio Code Server** add-ons | Gives the agent (and you) file access to `/config` for the YAML-only items above (recorder, http). | 🤖 |
| 3.6 | Enable the **automation editor** (`automation: !include automations.yaml`) | **Required for HomeIQ's headline feature.** `ai-automation-service-new`, `ha-ai-agent-service` and `ai-pattern-service` all deploy automations via `POST /api/config/automation/config/{id}`, which hard-fails without it. | 🤖 (YAML) |
| 3.7 | Add core integrations: **NWS** (better than Met.no for a US address), **AirNow** (free EPA AQI — you are in wildfire-smoke season) | Free, core, no HACS. Feeds HomeIQ's weather/air-quality services. | 🤖 |
| 3.8 | Create a **Local Calendar** + set `CALENDAR_ENTITIES` | `calendar-service` logs a warning and collects nothing for a calendar it cannot find (`main.py:119-120`). It does *not* hard-fail — the `ConnectionError` at `main.py:105` fires only when Home Assistant itself is unreachable. So this is "the service is inert", not "the service is down". Local Calendar is the zero-dependency option. | 🤖 |

### P4 — HomeIQ-specific enablement (quirks worth knowing)

| # | Action | Why | Mode |
|---|---|---|---|
| 4.1 | Create **template sensor aliases** named exactly `sensor.total_power` / `sensor.daily_energy` once a power source exists | `smart-meter-service` matches on **literal entity_id strings**, not `device_class`. This one alias unlocks the entire `energy-correlator` chain. | 🤖 |
| 4.2 | Set `DEFAULT_NOTIFY_SERVICE` to a real `notify.*` (companion app) | `ha-device-control` notifications are silently unroutable otherwise. | 🔶 (app install is manual) |
| 4.3 | Ensure motion/door sensors have `motion`/`door` **in the entity_id** | `activity-writer` classifies by substring, not `device_class`. A `device_class: motion` sensor named `binary_sensor.hallway_pir` is classified `other` and its data becomes noise. | 🤖 (when such sensors exist) |
| 4.4 | Set `device_class` on all binary_sensors | Gates automation planning in `intent_planner`; drives InfluxDB event categorization. | 🤖 |

### P5 — Recommended but optional

| Item | Note | Mode |
|---|---|---|
| Waste Collection Schedule | First-class Henderson/Clark County support via `republicservices_com` | 🤖 |
| weatheralerts | **Core NWS gives forecasts but no alerts.** This is your Red Flag / Excessive Heat / Flash Flood / Dust Storm channel — genuinely relevant in Nevada. | 🤖 |
| Adaptive Lighting | Natural fit for 5 WLED strips | 🤖 |
| Spook | Toolbox; v5.0.0 shipped 2026-06 (the "abandoned" rumor is false) | 🤖 |
| Battery Notes | Trivial effort; pairs with the new 2026.5 Maintenance dashboard | 🤖 |
| Bubble Card | Healthiest frontend project in the ecosystem; pop-ups genuinely not in core | 🤖 |
| Browser Mod | **Only** if a wall tablet/kiosk is coming | 🤖 |
| Music Assistant add-on | Reasonable fit for 2 Chromecast TVs | 🤖 |

### ⛔ Explicitly do NOT install — and why

| Item | Reason |
|---|---|
| **Google Drive Backup add-on** | **Superseded.** Google Drive/OneDrive/Dropbox are now official *core* integrations acting as native backup agents (13 agents total). The add-on's store build is from 2023. |
| **Auto-Backup (HACS)** | Superseded by core Backup — scheduling, retention, off-site agents all absorbed. |
| **MariaDB add-on** | Official docs now favor SQLite; 164 entities is nowhere near the threshold. Adds a second failure domain. |
| **InfluxDB / Grafana add-ons** | **Redundant — HomeIQ already runs both externally.** |
| **Mosquitto / Zigbee2MQTT / ZHA / Z-Wave JS** | Zero devices at design time; install when hardware arrives. (2026 guidance: prefer **ZHA** unless you already run MQTT.) *Superseded 2026-08-11: ZHA is live on an SMLIGHT SLZB-06p7 (`socket://192.168.1.121:6638`) with mesh-health and coordinator-watchdog audit recipes.* |
| **Frigate** | Requires MQTT *and* cameras. Two blockers. |
| **Alexa Media Player** | Core shipped `alexa_devices` in 2025.6. |
| **Average (HACS)** | ☠️ Abandoned — last commit 2025-01, open crash bug. Use core Min/Max or Statistics helpers. |
| **Node-RED** | Core automations handle 19 devices comfortably. |
| **Bermuda BLE / Better Thermostat / Alarmo / Watchman** | Prerequisites absent (BT proxies / TRVs / contact sensors / YAML config respectively). |
| **ApexCharts, layout-card, mini-media-player, Swipe Card, Stack-In-Card** | Superseded by core (sections, `grid_options`, tile features) or outright abandoned. |

---

## 6. Traps that will silently break things

1. **🚨 Team Tracker entity naming — this will break `sports-api` if missed.**
   The README says the sensor will be `sensor.team_tracker`. **That is only true for the YAML path.** The UI config flow prefills the name as `"{league} - {team}"` → `sensor.nfl_las_vegas_raiders`. HomeIQ's `sports-api` filters for entity_ids **containing `team_tracker`** and will match nothing.
   → **Type a name containing `team_tracker` at the finalize step of every Team Tracker config flow** (e.g. `team_tracker_raiders`). Verify the resulting entity_id before wiring the poller.
   *(Source-read inference from v0.17.8 `config_flow.py:430` + `sensor.py:209`; confirm on first sensor creation.)*

2. **Team Tracker card version pinning** — integration and card must match on MAJOR.MINOR (`0.17.x` ↔ `0.17.y`). Upgrade together.

3. **Custom add-on slugs are `<sha1(url)[:8]>_<folder>`** — read them from `GET /store/addons` at runtime; never compute or guess. Also, ESPHome and Music Assistant are built-in but *not* `core_`-prefixed, so logic keying on `core_` to mean "official" gets them wrong.

4. **Config-write POSTs return before the reload completes** — `200 {"result":"ok"}` means *written*, not *loaded*. Poll for the entity.

5. **`POST` to an existing automation/scene id is a full replace, not a merge.** Never put `id` in the body.

6. **Storage-helper `update` is a full replace** and the id cannot be chosen or changed — read it back from the create response.

7. **Backup API renames**: `schedule.state` → **`schedule.recurrence`** (`never`/`daily`/`custom_days`). The encryption key is `create_backup.password`.

8. **"Advanced Mode" was retired in 2026.6** and "Add-ons" were renamed **"Apps"** in 2026.2. Any guide referencing either is stale.

9. **HACS's latest *tagged* release is 2.0.5 from 2025-01** — this looks abandoned and is not (`main` was committed 2026-07-31, pinning HA 2026.7.4). Long cadence, not neglect.

10. **HA 2026.11 will require `mean_type` + `unit_class`** in the recorder statistics WebSocket API. → **Action item for HomeIQ** if it reads or imports HA long-term statistics.

---

## 7. Proposed phase order

```
Phase 0  Preflight ......... verify token, admin, WS, supervisor/api reachable       🤖
Phase 1  SAFETY ............ backups configured + first backup verified + kit saved  🔶  ← gate
Phase 2  Correctness ....... currency, recorder, http hardening, update policy       🤖
Phase 3  Organization ...... floors, areas, labels, device assignment,
                             report-only diagnostics (scenes, zigbee mesh, watchdog)  🤖
Phase 4  Add-ons ........... OTBR, SSH, Studio Code Server                           🤖
Phase 5  HACS bootstrap .... Get HACS add-on → GitHub device code → onboard          🔶  ← gate
Phase 6  Integrations ...... Team Tracker, Powercalc, + selected P5                  🤖
Phase 7  HomeIQ enablement . automation editor, calendar, template aliases, NWS/AirNow 🤖
Phase 8  Verify & report ... re-run all check()s, diff against intent, report        🤖
```

Human gates: **Phase 1** (OAuth for the off-site backup agent) and **Phase 5** (GitHub device code). Everything else runs unattended.

---

## 8. Open questions for you

1. **Off-site backup target** — Google Drive, OneDrive, or Dropbox? (All official core integrations now; all need one OAuth click.) Or a NAS via network storage, if you have one?
2. **Which teams** for Team Tracker? (League + team, e.g. NFL/Las Vegas Raiders.)
3. **Service account** — split HomeIQ onto its own non-admin user/token, or keep the owner token for now? (Some HomeIQ write paths need admin; needs testing.)
4. **Wall tablet / kiosk** planned? Decides Browser Mod.
5. **Energy monitoring** — worth noting NV Energy introduced a residential **demand charge in April 2026** (billed on your highest 15-min window per day), which makes whole-home power monitoring directly monetizable. Interested in CT-clamp hardware later? Powercalc is the zero-hardware interim.
6. **Rebuild vs. extend** `ha-setup-service` — recommendation is rebuild its core around the new `HAClient`, keeping the health-check code, discarding the two broken wizards.

---

## 9. Sources

Live source reads at `home-assistant/core@2026.7.4`; HA release notes 2026.1–2026.7; `developers.home-assistant.io` REST/WebSocket/Supervisor API docs; `hacs/documentation`; `vasqued2/ha-teamtracker` v0.17.8 source; live GitHub repo health via API (2026-08-01). Reddit was unreachable during research — community sentiment is from `community.home-assistant.io` only.
