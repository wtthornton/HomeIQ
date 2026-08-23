# ADR: HomeIQ ships as an appliance that owns its Home Assistant

**Status:** Accepted
**Date:** 2026-08-23
**Origin:** The owner asked for "a single docker that contains a clean Home
Assistant, tapps-brain, clean AgentForge, postgres and anything else HomeIQ
might need to run", with an installer.
**Deciders:** HomeIQ owner + operating agent
**Supersedes:** the guided-paste HA access route that
[TAP-6465](https://linear.app/tappscodingagents/issue/TAP-6465) was filed to
record.

---

## Context

HomeIQ is a B2C product whose install story is currently a developer's: clone a
repo, hand-edit `.env`, run `scripts/start-stack.sh`, and point it at a Home
Assistant you already own and administer. Every consumer-facing feature is
blocked behind that.

Three measurements frame the decision. All are from this host on 2026-08-23.

| Fact | Value | Source |
|---|---|---|
| Production services | 48 | `infrastructure/container-budget.json` |
| Resident memory | 7,406 MiB | same, measured 2026-08-18 |
| Built image weight | 48.3 GB summed | `docker images` |
| Declared target | 12 services / 4,096 MiB | TAP-5283, not yet met |

The ceiling is a CI-enforced ratchet that fails in **both** directions, so the
count cannot silently regrow and cannot silently absorb a deletion.

This is not a new problem. [TAP-5283](https://linear.app/tappscodingagents/issue/TAP-5283)
has been In Progress since 2026-08-11 and says so directly: *"The container
count is what blocks distribution and drives the hardware requirement… Collapsing
the data plane cuts the memory footprint to roughly 3–4 GB and makes an
installable artifact possible."* The appliance is the downstream deliverable of
that epic, not a parallel effort.

One measurement was worth isolating because it was a defect rather than an
architecture problem, and it has since been fixed. `ner-service` measured
**16.3 GB**, a third of the total, because
`domains/ml-engine/ner-service/requirements-prod.txt` pinned `torch>=2.5.0` with
no CPU wheel index, so pip resolved the CUDA build on a machine with no GPU. Two
sibling services already did this correctly —
`domains/ml-engine/openvino-service/requirements.txt:16` and
`domains/ml-engine/model-prep/Dockerfile:27` both pass
`--extra-index-url https://download.pytorch.org/whl/cpu`. Adding the same line
took the image to **3.39 GB, measured by rebuild on 2026-08-23** — 12.9 GB off
the stack for one line, before any architectural work.

That rebuild surfaced a second defect: the service **could not be built at all**.
`homeiq-observability` declares `homeiq-data[auth]>=1.0.0` (TAP-6037), and the
Dockerfile installed observability alone, so pip searched PyPI for `homeiq-data`
and failed. The 16.3 GB image on disk predated that dependency. Fixed by
installing the closure — observability, data and resilience — in one pip
invocation, matching the sibling services.

## Decision

Four decisions, taken together.

### 1. HomeIQ owns the Home Assistant instance, headless

The appliance ships its own HA. The customer never opens it; HomeIQ is the only
surface. HA arrives **pre-provisioned at build time** rather than converged at
run time.

This resolves what was otherwise a hard blocker. `AddonRecipe`
(`libs/homeiq-ha/src/homeiq_ha/agent/recipes.py:140`) installs add-ons through
`ha.ws.supervisor_api("/addons")`, and `ghcr.io/home-assistant/home-assistant` is
HA **Container** — no Supervisor, no add-on store. Under the owned model no
add-on is needed, because every add-on in `default_recipes()` existed either to
*install software* or to *let a human edit files*:

- **HACS becomes a build-time tool and does not ship.** Its only role in these
  recipes is downloading Powercalc and Team Tracker —
  `libs/homeiq-ha/src/homeiq_ha/agent/powercalc.py:347` calls
  `hacs/repository/download`, and nothing outside installation touches HACS at
  all. Vendoring those components into `/config/custom_components/` at image
  build removes both HACS and the GitHub device-code prompt that made
  `HACSBootstrapRecipe` the only `requires_human = True` recipe in phase 5.
- **`core_configurator` is deleted.** It is a file editor for a human, on an
  instance no human opens.
- **`core_ssh` is replaced by a shared `/config` mount.** This needs a
  `LocalTarget` beside `SSHTarget` in
  `libs/homeiq-ha/src/homeiq_ha/agent/host_files.py`, which is SSH-only today
  (port 22222, hardcoded to the add-on).
- **The backup gate survives.** `engine.py:229` refuses any phase past the gate
  without a backup taker, but `libs/homeiq-ha/src/homeiq_ha/agent/backup.py`
  drives the **core** `backup/*`
  websocket API rather than the Supervisor. Container HA has a local backup
  agent, so `backup/agents/info` resolves.

### 2. One shared HA credential, generated per install

A single HA credential serving HomeIQ, AgentForge and the other components is
correct. **Baking a constant into the image is not.** Every appliance would carry
the same token, anyone who pulls the image can read it, and this repo is public.
"Shared" and "constant" are different properties and only the first was wanted.

The credential is minted on first boot, at no interaction cost:

1. Start HA.
2. `POST /api/onboarding/users` creates the owner and returns an auth code.
3. Exchange the code for tokens.
4. Mint the shared credential over websocket with `auth/long_lived_access_token`.
5. Store it in the appliance secret store, unique to that home.

The same rule governs the other ten keys `env.required` marks required —
`POSTGRES_PASSWORD`, `API_KEY`, `INFLUXDB_TOKEN`, `JWT_SECRET_KEY`, and the brain
and AgentForge bearers. **Generate on first boot; ship none of them.**

#### Where the secrets live, and who can read them

**Rotatable, not readable.** You never need to read a secret you can regenerate,
and that dissolves the tension between "support can recover it" and "nobody can
steal it". Support rotates and re-provisions; there is no read path. That is also
auditable in a way that an engineer reading a value is not.

- One generated secrets file on a dedicated volume, `0600`, owned by the service
  user. Never in an image layer, never in the compose bundle, injected at
  container start.
- **Excluded from backups by default.** A backup carrying the secret store
  re-creates precisely the problem that not baking the secret avoided.
- **No encryption at rest in v1.** The key would have to sit on the same machine
  as the data, owned by a customer who owns the machine. That is theatre, not
  defence. TPM-sealing is the honest upgrade once the hardware has a TPM, and it
  is a v2 concern.
- **One exception, and it is real.** `OPENAI_API_KEY`-class keys are supplied by
  the customer and cannot be regenerated by HomeIQ, so "rotate instead of read"
  does not apply. They are either re-entered by the customer or genuinely
  persisted encrypted, which is why TAP-6481 already carries key management as
  its own question.

### 3. Ship an installer plus a pinned compose bundle

Not one image running every process under a supervisor, and not a flashable disk
image.

The deciding constraint is privilege. `zeek` is the only service requiring
`network_mode: host` with `NET_RAW` and `NET_ADMIN`. In a single fused container
that privilege would extend to Home Assistant and to the model-provider
credential litellm holds. The compose bundle keeps it scoped to one container
that only reads packets.

Secondary reasons: per-service upgrades are resumable where a fused image is
all-or-nothing, and a disk image would additionally make HomeIQ the owner of
kernel CVEs, OS patching and update-signing infrastructure.

### 4. Zeek ships, opt-in at setup

Default off. The wizard offers network scanning as a named feature, which is also
the consent moment for passive capture of household traffic.

The off path already exists and is deliberate:
`libs/homeiq-ha/src/homeiq_ha/agent/netobserve.py:98` returns `None` when
`HOMEIQ_NETWORK_OBSERVER_URL` is unset, and `UnclaimedDevicesRecipe` then reports
`NOT_APPLICABLE` — the docstring states the reason, that *"an unconfigured sensor
never reads as a network with nothing on it."*

## Consequences

### What this deletes

The guided-paste-versus-add-on-versus-OAuth decision loses its subject entirely,
and with it the standing question of whether to instruct the customer to open
HA's Security page or deep-link `/profile/security`. There is no customer-facing
HA, so there is no HA credential for a customer to fetch.

Five recipes change: `hacs.bootstrap`, `hacs.powercalc` and the Team Tracker
recipe collapse into build steps plus a "confirm loaded" check; `addons.core_ssh`
and `addons.core_configurator` are deleted.

In the filed backlog, epic [TAP-6464](https://linear.app/tappscodingagents/issue/TAP-6464)
and its four stories are invalidated as written. The other four epics —
TAP-6460, TAP-6469, TAP-6474, TAP-6478 — survive, because they concern
*third-party integration* credentials (Ring, Roborock) rather than HA access.

### What this costs

**Owning HA means owning its update surface.** The HA image must be pinned;
`:stable` is currently the only unpinned tag in the repo, while
`custom_components/homeiq/manifest.json` declares `min_ha_version 2026.8.0`. HA's
breaking changes are real and already recorded here —
`libs/homeiq-ha/src/homeiq_ha/agent/backup.py:14-16` notes HA renaming
`schedule.state` to `create_backup.password` mid-stream. Today that breaks an
integration against a customer's instance; under this ADR it is the appliance
shipping a broken update, and HA's CVE cadence becomes the release cadence.

Dropping HACS sharpens this rather than softening it: vendored components no
longer self-update, so a Powercalc fix ships as a new appliance image. That is
correct appliance behaviour, but the build needs a **tracked, pinned manifest of
vendored component versions** or the drift becomes invisible.

**The build is multi-repo.** AgentForge and tapps-brain sources must be present.
`.mcp.json:48` hardcodes `/home/wtthornton/code/AgentForge/clients/agentforge-mcp`
and all twelve `.claude/skills/af-*` are absolute symlinks into that tree. Those
are developer-surface only and do not ship, but the appliance cannot be built
from a HomeIQ checkout alone.

**Two services still mount the Docker socket.** `admin-api` and `log-aggregator`
both drive it. The compose-bundle shape keeps a real container topology for them
to manage, so this is survivable — but under the appliance they are managing
containers the customer did not create, which is a different authorisation
question than the one they were written for.

### What still needs a human, and where

Config flows requiring input. The seven pending discovery flows (apple_tv ×3,
androidtv_remote ×2, denonavr, homekit_controller) and any cloud-account
integration still need a person. The difference is that the person is now in
**HomeIQ's** UI, and HomeIQ drives the flow through
`libs/homeiq-ha/src/homeiq_ha/client/rest.py::run_config_flow`. A config-flow
form with no input is a gate rather than a failure — that distinction is already
implemented and is the AF-first shape described in
[adr-owner-chat-surface.md](adr-owner-chat-surface.md).

## Rejected alternatives

**One image, all processes under s6-overlay.** The simplest possible UX — one
`docker run`. Rejected because Zeek's `NET_RAW` and host networking would apply
to every process in the image, including Home Assistant and the provider
credential, and because all-or-nothing upgrades on a 48-service stack are a
worse failure mode than a partial one.

**A flashable disk image, HA-OS style.** The best consumer experience by a wide
margin. Rejected for now on scope: it adds kernel patching, A/B slot updating and
update signing to a project that has not yet met its own container-count target.
Revisit once the count is near 12.

**HA Supervised inside the appliance.** Would preserve the add-on route and the
existing recipes unchanged. Rejected because Supervisor manages its own
containers, which conflicts directly with an installer that owns the compose
topology.

**Distributing the integration through HACS as a second channel.** `hacs.json`
declared HomeIQ as a HACS-installable custom repository, which would let someone
run `custom_components/homeiq` against their own Home Assistant without the
appliance. Deferred to a much later version and the file removed on 2026-08-23:
it is a second supported shape, with its own support surface and its own
compatibility matrix against Home Assistant versions HomeIQ does not control,
before the first shape ships at all. Nothing in the repo referenced the file.

**Shipping without Zeek.** Would remove the privilege constraint entirely and
make the single-image shape viable. Rejected: it costs unclaimed-device discovery
and the fingerprint store, which is the capability the current branch exists to
deliver.

## Open questions

1. **Zeek retention.** Opt-in answers *whether* traffic is captured. It does not
   answer what is kept, for how long, or whether the customer can see and erase
   it. Passive capture of household traffic is the most invasive thing the
   appliance does, and "the wizard asked" is only defensible alongside a
   retention answer. This blocks the wizard step, not the packaging.
2. **Whether tapps-brain ships at all.** Verified 2026-08-23: AgentForge
   degrades gracefully when the brain is *unreachable* — `init_brain` catches and
   sets `app.state.brain = None`, there is a circuit breaker and an offline write
   queue, and `POST /tasks/invoke` still works without its memory block. But
   AgentForge's compose has two hard **deployment** edges: `docker-compose.yml:297`
   uses `${TAPPS_BRAIN_AUTH_TOKEN:?...}` so compose refuses to render without the
   token, and `tapps-brain-net` is `external: true`, owned by tapps-brain's own
   compose. So the brain ships unless someone does the documented escape-hatch
   work. That is a decision to take deliberately, not inherit.

## See also

- [TAP-5283](https://linear.app/tappscodingagents/issue/TAP-5283) — the data-plane
  collapse this ADR depends on; the appliance is its deliverable.
- [docs/operations/init-gateway.md](../operations/init-gateway.md) — the init
  endpoints, the blocker catalogue, and the human-gate semantics.
- [adr-owner-chat-surface.md](adr-owner-chat-surface.md) — the owner surface that
  renders blockers and gates.
- `infrastructure/container-budget.json` — the ratchet that measures progress
  toward a shippable size.
