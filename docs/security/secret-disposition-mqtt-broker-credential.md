# Secret disposition — MQTT broker credential

> A decision record, not a status page. It exists so a future reader can
> **re-evaluate** this call rather than inherit it unexamined. If any trigger in
> [Re-evaluation triggers](#re-evaluation-triggers) fires, this decision is void
> until redone.

| | |
|---|---|
| **ID** | SEC-2026-08-21-mqtt-broker-credential |
| **Date** | 2026-08-21 |
| **Ticket** | TAP-6399 (epic TAP-6398) |
| **Decision owner** | Repo owner — **sign-off outstanding**, see [Outstanding](#outstanding-owner-action-required) |
| **Status** | Working-tree removal **done**; rotation question **open** |

## Artifact

| | |
|---|---|
| Path | `infrastructure/config/mqtt_zigbee_config.json` |
| Credential | Username + password for the MQTT broker at `mqtt://192.168.1.100:1883`, plus the topic prefix `zigbee2mqtt`. **Described by reference only — the plaintext is deliberately not reproduced in this record.** |
| Introduced | Commit `3df40097`, 2025-11-10, authored by the repo owner |
| Reachable from | **19 remote branches**, `origin/master` among them, plus 2 local branches (`master`, `device-knowledge-completion`) that still *track* the file at tip. An earlier draft of this record said "ten other branches" — that count was truncated by a `| head` in the command that produced it, and is corrected here. |
| Removed from working tree | 2026-08-21, this change |

## Liveness verification

Point-in-time facts. **Liveness can change; these are not permanent properties.**

| Check | Method | Result | Date |
|---|---|---|---|
| Broker reachable? | `/dev/tcp/192.168.1.100/1883` | **No route to host** — nothing answers on the LAN | 2026-08-21 |
| MQTT configured in Home Assistant? | HA config entries | **No MQTT config entry at all.** Zigbee here is ZHA on an SMLIGHT SLZB-06p7 coordinator | 2026-08-21 |
| Credential reused in-repo? | `grep -rI` over the full tree | **Exactly one occurrence** of the username and one of the password, both in this file | 2026-08-21 |
| Anything read the file? | Call-site search | Its only reader, `apply_overrides()` in the device-intelligence config module, was deleted 2026-08-20. The one remaining *writer* is `admin-api/src/mqtt_config_endpoints.py`, removed under TAP-6400 | 2026-08-21 |
| Reaches the container how? | `docker inspect` mounts | **Bind mount**, `…/HomeIQ/infrastructure → /app/infrastructure`. **Not** baked into an image layer | 2026-08-21 |

## Exposure inventory

| Surface | Assessment |
|---|---|
| **Unauthenticated HTTP endpoint** | **The most serious surface, and it was already known.** `GET /api/v1/config/integrations/mqtt` on `admin-api` was registered with **no authentication** and returned a body containing `MQTT_PASSWORD`. `admin-api` bind-mounts `infrastructure/` at `/app/infrastructure`, and the handler merged that file over env defaults — so **until the file was deleted on 2026-08-21, any host able to reach `admin-api` on the LAN could read the plaintext broker password with no credentials.** Confirmed live before removal: HTTP 200, no auth header, password present. The endpoint's docstring asserted "Configuration values are not sensitive." This was filed as **CRIT-02 in `domains/core-platform/admin-api/REVIEW_AND_FIXES.md` on 2026-02-06** and remained unfixed for six months; the work here rediscovered it independently rather than finding it first. Removed outright under TAP-6400 — a stronger fix than the masking the review proposed, since the endpoint has no remaining purpose. |
| Git history | Private GitHub repo, single human contributor. Anyone who can `git log` to find `3df40097` already holds repo read/push — a strictly larger grant than a password to a dead broker. |
| Container image | **None.** The file arrived by bind mount, so no image layer ever contained it and no registry copy exists. Deleting the file removed it from the running container immediately, verified. |
| AI coding agents | **The material exposure.** Agents with repository access have read this tree repeatedly; the value has appeared in tool output and may persist in provider-side request logs, abuse-monitoring retention, or agent transcript/memory stores. |
| CI / build logs | **Not audited.** See [Residual risk](#residual-risk-accepted). |

## Risk classification

Against three distinct frames:

- **(a) Legally or regulatorily disclosed** — does not apply. Single-owner personal
  smart-home platform, no regulator and no data-subject population; an
  infrastructure credential is not itself notification-triggering data. GDPR/CCPA
  machinery is deliberately *not* invoked here: citing it would mislead a future
  reader into thinking a compliance clock is running when none is.
- **(b) Practically compromised** — no *direct evidence* any unauthorised party
  obtained it, and there is no live target to use it against. But note this is a
  weaker "no" than it first appeared: the unauthenticated `admin-api` endpoint above
  means the password was readable over HTTP by anything on the LAN, with no
  credential and no audit trail. Absence of evidence here is genuinely just that —
  nothing logged who read it.
- **(c) Must be treated as compromised by policy** — **yes, and this is the operative
  frame**, on two independent grounds. First, AI agents read the file, so the
  credential left the owner's exclusive custody into third-party processor retention
  that cannot be audited or verified deleted. Second, the unauthenticated endpoint
  served it to any LAN client on request. Either alone would justify frame (c).

The residual risk is therefore **not** "someone reconnects to 192.168.1.100" — that
target is dead. It is **password reuse**: whether that pair, or the habit that
generated it, is live on any other system.

## Decision

**Decline the git-history rewrite. Record the decline.**

The reasoning that decides it, in one line: *a rewrite cannot claw back the copies
that actually matter.*

A rewrite is justified when a secret is both exploitable and exposed beyond the
trust boundary that repo access already grants. Neither holds. The broker is dead,
so exploitability is nil; the repo is private, so git-history readers are already
inside the boundary. Against that, a rewrite costs `filter-repo`/BFG plus a
force-push across all 19 remote branches carrying it, invalidating every
existing clone and any open PR.

Decisively: the exposure that pushed this to frame (c) — provider-side agent
retention — **already left the git boundary entirely and is untouched by a
rewrite**. Paying the full disruption cost to remove a copy that protects nothing,
while the copies that do matter remain, is negative expected value.

### Actions taken

- [x] File deleted from the working tree **on this branch only** — see the
      branch-local caveat under [Residual risk](#residual-risk-accepted)
- [x] Path added to `.gitignore`, verified with `git check-ignore` — this is a
      backstop, not a substitute: it stops a rebase from one of the 19 branches
      still carrying the file, or the not-yet-removed `admin-api` writer, from
      quietly recommitting it. It does **not** help against `git checkout master`
      — see residual risk 2
- [x] Confirmed gone from the running container. The file arrives by bind mount,
      so no rebuild is needed for removal to take effect — but the acceptance
      criterion asks for a **recreate**, and an independent verifier performed
      one (`up -d --force-recreate --no-deps device-intelligence-service`): new
      container, healthy in 20s, `/api/discovery/status` **HTTP 200**, 93 devices
      / 17 areas / `errors:[]`, config dir holding only `.gitkeep`
- [x] Extended `scripts/check-secrets.py` to detect password fields. The
      criterion "a secret scan reports no remaining broker credential" was
      passing **vacuously**: the scanner's five patterns could not match a
      `*_PASSWORD` field at all — the generic rule keys on `api_key`/`apikey`/
      `secret_key`, and its 16-character floor excluded a 14-character value.
      It reported the original leaked file CLEAN. Now covered, with a test suite
      that proves the gate by breaking it
- [ ] Owner confirmation on password reuse — **open**
- [ ] Owner sign-off on this disposition — **open**

## Residual risk accepted

1. **Password reuse elsewhere — UNRESOLVED.** Provable unique *within this
   repository*; not provable outside it. This is the only place real residual risk
   lives, and it is the one cheap high-value check available.
2. **"Not in the working tree" is branch-local, and one checkout away from false.**
   `master` and `device-knowledge-completion` still **track** the file at tip.
   `.gitignore` never applies to a tracked path, so the backstop is inert against
   this: a plain `git checkout master` re-materialises the plaintext on disk. The
   gitignore rationale anticipated a *rebase* pulling the file back, not a
   *checkout* that simply still has it. This resolves when this branch merges to
   `master`; until then it is live. Deliberately not fixed by committing to
   `master` directly.
3. **CI and build logs — not audited.** If any of the eleven branches ran a
   pipeline that printed or errored on this file, the plaintext may sit in build
   logs under different retention and access control than the repo. None of the
   six acceptance criteria on TAP-6399 would ever look there.
4. **Agent transcripts and memory stores — not audited**, and largely not auditable
   from here.
5. **Low-grade infrastructure fingerprinting.** The RFC1918 address and the
   `zigbee2mqtt` topic prefix are not rotation-worthy alone, but combined with
   device names and routines elsewhere in the repo they contribute to a
   home-profiling picture *if this repo is ever made public*. Noted, not remediated.

## Re-evaluation triggers

This decision is void, and the rewrite must be reconsidered **before** the change
lands, if any of these occur:

- Repository visibility changes to public, or it is forked outside the current
  trust boundary
- A collaborator, CI integration, or automation outside the current boundary gains
  repo access
- **A broker is ever brought up at `192.168.1.100:1883`** — this revives
  exploitability directly
- The credential or its generation pattern is found in use on any live system
- Ownership of the repository transfers

Review cadence: **on trigger only.** There is no scheduled review, by design — a
recurring calendar reminder on a dead credential is noise that trains people to
ignore the trigger list that matters.

## Outstanding — owner action required

Two items cannot be closed by an agent, because they depend on facts only the owner
holds and on a risk acceptance that is the owner's to make.

**1. Password reuse.** The question to answer:

> The MQTT password in commit `3df40097` is confirmed unique within this repository,
> and the broker it belongs to (`192.168.1.100:1883`) is unreachable and appears
> decommissioned. That is the limit of what can be checked from inside the repo —
> have you ever reused this exact password anywhere else: router or AP admin, NAS,
> another broker, a cloud or personal account? If yes, rotate it in those specific
> places. If no, that confirmation is recorded here as the basis for closing the
> rotation criterion.

**2. Sign-off.** Declining a rewrite is a risk-acceptance decision about the owner's
own infrastructure, not a pure engineering judgement, so it should not be closed by
whoever filed the ticket.

## Process gap worth closing

Fixing the recurrence is worth more than relitigating this one dead credential:
configure agent tooling with a deny-list for secret-shaped paths (`*.env`,
`*credential*`, `config/*secret*`) so the next credential does not take this route
in. Not actioned here — it is outside TAP-6399's scope and deserves its own ticket.
