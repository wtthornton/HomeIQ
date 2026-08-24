# Session handoff

**Updated:** 2026-08-23T21:08:51Z

## Why the next session exists

Owner wants to **change something in the plan and discuss architecture**. The
backlog below is filed but unstarted, so nothing is expensive to revisit. Treat
every decision here as open for challenge.

## Where things stand

- Branch `feat/unclaimed-device-discovery`, PR #125, **6 commits, unmerged**.
- Deployed and verified live: `homeiq-setup-service`, `homeiq-zeek-network-service`.
- **20 Linear issues filed, TAP-6460 to TAP-6481** (5 epics, 15 stories), all
  validated 98-100, assigned to Claude Agent, `blockedBy` wired. None started.

## What shipped and works

`integrations.unclaimed_devices` recipe: finds LAN devices no HA integration
owns. Reads HA's own dhcp matchers via `integration/descriptions` +
`manifest/get`, so no vendor table in HomeIQ to rot. Blocker catalogue (12
entries) in `homeiq_ha.agent.blockers`, served at `GET /api/v1/init/blockers`,
persisted to `devices.integration_blockers`.

Fixed 4 upstream bugs that had kept `devices.network_device_fingerprints` empty
since first deploy while `/health` said healthy: alembic never invoked; raw
asyncpg given a SQLAlchemy DSN; DHCP parser read the wrong field (92% of records
dropped); alembic's `fileConfig` silenced all logging. Store now: 54 devices,
45 vendors resolved.

## Decisions to re-examine

1. **B2C, runtime config.** Customers configure in-app via a wizard. `.env` is
   for deployment values only. This invalidated the env-var credential path I
   shipped; TAP-6460 rips it out.
2. **Store nothing.** Customer credentials drive the HA config flow immediately;
   HA owns them after. No encryption key, no secrets at rest. Exception:
   TAP-6481 (OPENAI/WEATHER keys) has no downstream owner and must persist.
3. **REVERSED 2026-08-23 — HomeIQ owns a headless HA.** Guided paste is dead;
   so is the add-on/OAuth question. The appliance ships its own pre-provisioned
   HA that the customer never opens, and the shared credential is minted on
   first boot. (The "63 services" figure was also wrong: the measured count is
   **48 production services / 7,406 MiB**, per `infrastructure/container-budget.json`.)
   Recorded in `docs/architecture/adr-appliance-packaging.md`.
4. **AF-first shape:** gene proposes, `kind: gate` asks the human, dumb relay
   executes — mirrors `device-onboard.yaml` ("the chokepoint is the TOOL
   GRANT"). Credentials never enter a node payload, prompt, or ledger.

## Constraints any redesign must respect

- `iot_class` does NOT indicate credential need. Roborock is `local_polling`
  and still needs a cloud account. Only probing the flow answers it.
- A config-flow form with no input is a **human gate, not an error**. Wrong
  exception type halts the whole converge (`engine.py`: `if not outcome.ok:
  return report`).
- Evidence bar splits by flow kind: address flows need STRICT (writes the match
  itself); account flows accept MAC (integration enumerates from cloud);
  HOSTNAME never authorises a write.
- Repo is **public**. MACs in tests/docs keep the real IEEE OUI with synthetic
  last-3-octets.

## Known gaps, not mine

7 HA discovery flows awaiting a click (apple_tv x3, androidtv_remote x2,
denonavr, homekit_controller). `heos` entry is `state=not_loaded`. A third Ring
(`b0:09:da`) is in ARP but sent no address-bearing DHCP record.

## Open question I raised last — RESOLVED 2026-08-23

Whether to tell the customer to click into HA's Security page or deep-link
`/profile/security`. **Neither.** The question lost its subject: there is no
customer-facing HA, so there is no credential for a customer to fetch.

## Open questions that remain

1. **Zeek retention.** Opt-in answers *whether* traffic is captured, not what is
   kept, for how long, or whether the customer can see and erase it. Blocks the
   wizard step, not the packaging.
2. **Where the appliance secret store lives**, and whether support can read it.
   A store nobody can read is also a store nobody can recover.
3. **Whether tapps-brain ships at all** — per-appliance it is an empty brain with
   no federation.
