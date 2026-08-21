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
| **Decision owner** | Repo owner — answered the reuse question 2026-08-21; see [Owner response](#owner-response) |
| **Status** | **RESOLVED 2026-08-21 (second pass).** Reopened earlier the same day when the private-repo premise proved false; closed again after the corrected facts were established by measurement. Two further errors were found and fixed in this pass — the credential *was* reused, and five other secret families were never assessed. See [Second pass](#second-pass-2026-08-21-what-measurement-changed). |

## Artifact

| | |
|---|---|
| Path | `infrastructure/config/mqtt_zigbee_config.json` |
| Credential | Username + password for the MQTT broker at `mqtt://192.168.1.100:1883`, plus the topic prefix `zigbee2mqtt`. **Described by reference only — the plaintext is deliberately not reproduced in this record.** |
| Introduced | Commit `3df40097`, 2025-11-10, authored by the repo owner |
| Introduced (corrected) | The *file* arrived in `3df40097` (2025-11-10), but the **password predates it**: first committed `43d4e86b`, **2025-08-23**. |
| Reachable from | **Now `origin/master` only.** The 14 remote branches that carried it at tip were verified merged and deleted 2026-08-21. One **local** branch, `device-knowledge-completion`, still tracks it. The earlier "19 remote branches" figure counted refs carrying the *commit*, not tracking the *file*. |
| Removed from working tree | 2026-08-21, this change |

## Liveness verification

Point-in-time facts. **Liveness can change; these are not permanent properties.**

| Check | Method | Result | Date |
|---|---|---|---|
| Broker reachable? | `/dev/tcp/192.168.1.100/1883` | **No route to host** — nothing answers on the LAN | 2026-08-21 |
| MQTT configured in Home Assistant? | HA config entries | **No MQTT config entry at all.** Zigbee here is ZHA on an SMLIGHT SLZB-06p7 coordinator | 2026-08-21 |
| Credential reused in-repo? | `grep -rI` over the full tree | ~~**Exactly one occurrence**~~ **— THIS ROW IS FALSE.** The grep covered the *working tree*, never history. The same string appears in **17 files across 13 commits** from **2025-08-23**, serving as Grafana admin, InfluxDB admin, and InfluxDB API token. See [Error 1](#error-1--the-credential-was-reused-not-reused-was-false). | corrected 2026-08-21 |
| Anything read the file? | Call-site search | Its only reader, `apply_overrides()` in the device-intelligence config module, was deleted 2026-08-20. The one remaining *writer* is `admin-api/src/mqtt_config_endpoints.py`, removed under TAP-6400 | 2026-08-21 |
| Reaches the container how? | `docker inspect` mounts | **Bind mount**, `…/HomeIQ/infrastructure → /app/infrastructure`. **Not** baked into an image layer | 2026-08-21 |

## Exposure inventory

| Surface | Assessment |
|---|---|
| **Unauthenticated HTTP endpoint** | **The most serious surface, and it was already known.** `GET /api/v1/config/integrations/mqtt` on `admin-api` was registered with **no authentication** and returned a body containing `MQTT_PASSWORD`. `admin-api` bind-mounts `infrastructure/` at `/app/infrastructure`, and the handler merged that file over env defaults — so **until the file was deleted on 2026-08-21, any host able to reach `admin-api` on the LAN could read the plaintext broker password with no credentials.** Confirmed live before removal: HTTP 200, no auth header, password present. The endpoint's docstring asserted "Configuration values are not sensitive." This was filed as **CRIT-02 in `domains/core-platform/admin-api/REVIEW_AND_FIXES.md` on 2026-02-06** and remained unfixed for six months; the work here rediscovered it independently rather than finding it first. Removed outright under TAP-6400 — a stronger fix than the masking the review proposed, since the endpoint has no remaining purpose. |
| Git history | **PUBLIC. This row was wrong when written.** `github.com/wtthornton/HomeIQ` is a public repository (`gh repo view` → `visibility: PUBLIC`, 4 stars, 0 forks). Commit `3df40097`, dated **2025-11-10**, is an ancestor of `origin/master`, so the credential has been world-readable for roughly nine months. No repo grant was ever needed to read it. |
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


## Correction 2026-08-21: the repo is public

**Everything above that reasons from "private repo" is wrong.** `gh repo view
wtthornton/HomeIQ` returns `visibility: PUBLIC`, `isPrivate: false`, 4 stars,
0 forks, created 2025-08-19. Commit `3df40097` (2025-11-10) is an ancestor of
`origin/master` and carries the file with the password in cleartext. The
credential has therefore been world-readable for about nine months.

This was never checked. The claim was asserted from assumption and then used as
the load-bearing premise of the decline. The document even lists "Repository
visibility changes to public" as a trigger that voids the decision — a trigger
written for a condition that was already true.

### What actually changes

**Exploitability was never the binding constraint; disclosure is.** The broker
at `192.168.1.100:1883` is still dead, so nothing is directly attackable. What
is now established is that the username, the password, and the *pattern that
generated it* have been publicly indexed for months. Credential-stuffing does
not care that the original target is dead.

**A history rewrite is no longer sufficient, and is barely relevant.** The
original reasoning — "a rewrite cannot claw back the copies that actually
matter" — survives the correction and gets stronger, not weaker. Against nine
months of public exposure a rewrite cannot reach: clones taken by anyone,
GitHub's retention of unreachable commits (which stay fetchable by SHA), or any
search index or scraper that has already read the tree. Rotation is the control.
The rewrite is cosmetic beside it.

**Rotation is no longer closeable by "confirmed unique to a dead broker".** The
repo owner's 2026-08-21 answer — that the password is not reused — was given
against a stated private-repo blast radius. It was answered honestly to a
question that had the wrong premise attached, so it cannot carry the rotation
criterion any more. The owner needs to re-answer knowing the string is public.

### Required actions (all closed in the second pass below)

- [ ] Owner treats the password and its construction pattern as burned, and
      retires it anywhere the same string or a variant may have been used
- [ ] Rotation criterion re-answered against public disclosure, not against the
      private-repo framing it was asked under
- [ ] Decide the history rewrite again on the corrected facts, recording that it
      is a tidiness measure and not a containment one
- [ ] Audit whether any other credential in this repo's history was assessed
      under the same false premise

Until those are closed this document is **not** a disposition. It is an open
finding.

## Second pass 2026-08-21: what measurement changed

The first correction fixed the visibility premise but left every other claim in
this document unmeasured. This pass measured them. **Two of them were wrong.**

### Error 1 — the credential WAS reused. "Not reused" was false.

The liveness table above records *"Credential reused in-repo? → **Exactly one
occurrence**"*, and residual risk 1 closed the rotation criterion on it. That
grep ran over the **working tree**. It never looked at history.

The same 14-character string (fingerprint `2d184279`, SHA-256 prefix — the
plaintext is deliberately not reproduced) appears in **17 files across 13
commits**, first committed **2025-08-23** in `43d4e86b` — **79 days before**
`3df40097`, the commit this record was opened about. It was not an MQTT password
that happened to be committed. It was **one shared secret used as the
authenticator for the entire stack**:

| Role it served | Field | Representative path |
|---|---|---|
| MQTT broker password | `MQTT_PASSWORD`, `HA_MQTT_PASSWORD` | `infrastructure/config/mqtt_zigbee_config.json`, `local.env` |
| **Grafana admin password** | `GF_SECURITY_ADMIN_PASSWORD` | `docker-compose.monitoring.yml` |
| **InfluxDB admin password** | `DOCKER_INFLUXDB_INIT_PASSWORD` | `docker-compose.yml` |
| **InfluxDB admin API token** | `DOCKER_INFLUXDB_INIT_ADMIN_TOKEN`, `INFLUXDB_TOKEN` | `docker-compose.yml`, `docker-compose.production.yml` |
| Grafana datasource password | `secureJsonData.password` | `grafana/provisioning/datasources/datasource.yml`, `setup_grafana_automated.py` |

Consequences for this record:

- **Public exposure began 2025-08-23, not 2025-11-10** — roughly **12 months**,
  not nine.
- **The blast radius was never "one dead broker."** It included Grafana admin and
  InfluxDB admin — and both of those services are **live right now**, healthy,
  and published on `0.0.0.0` (`:3002` and `:8086`).
- Residual risk 1 was closed on a false finding. It is corrected below.

### Error 2 — five other secret families were never assessed at all

| # | Secret | Count | First committed | Verified state |
|---|---|---|---|---|
| A | **Home Assistant long-lived access tokens** | **6 distinct**, 6 distinct HA user accounts | `efa2843a`, **2025-08-19 — repo day one** | Nominally valid to **2034–2035**. **All 6 return HTTP 401** against the live instance — revoked. |
| B | **Context7 API keys** (`ctx7sk-`) | **6 distinct** | 2025-12-02 | Publicly disclosed. The **current** key is **not** among them — never committed. The 6 disclosed keys are an **external** service; revocation is not verifiable from here. |
| C | OpenWeatherMap API key | 1 | 2025-10-03 | Tracked ~3.5 months. External service — not verifiable from here. |
| D | InfluxDB/admin/JWT/simulator secrets in `.env.backup*` | 5 | 2025-10-03 | Weak literal values matching `scripts/setup-secure-env.sh` defaults. |
| E | `tmp_states*.json` — full HA state dumps, 469 KB each | 3 files | `d47f7c08` | Camera tokens **expired 2026-02-12**; negligible credential risk. Remains a **home-profiling** disclosure, still tracked at `master` tip. |

### Liveness re-verified by measurement, not inference

Every credential this record touches was probed against the live services on
2026-08-21. **None of them still works.**

| Probe | Scheme | Result |
|---|---|---|
| 6 HA tokens → `GET /api/` on `192.168.1.80:8123` | `Bearer` | **401 × 6** — revoked |
| Leaked string → Grafana `GET /api/org` (users `admin`, broker username) | Basic | **401** |
| Leaked string → InfluxDB `GET /api/v2/orgs`, `/api/v2/buckets` | **Token** (the scheme InfluxDB actually uses) | **401** |
| Control: InfluxDB `GET /health` | none | **200** — proves the probe reached a live service, so the 401s are real rejections and not a connectivity artifact |

That control matters: a 401 from an unreachable host proves nothing. The 200
establishes the negative result is genuine.

**So the corrected picture is worse on disclosure and better on exploitability.**
The secret was shared across the whole stack and public for a year — but every
instance of it has already been rotated out of service at some earlier point.
Nothing leaked is currently live.

### Owner re-answer on rotation (asked against the corrected blast radius)

The first answer — "unique to this dead broker" — was given against a stated
*private-repo, one-broker* radius, and the repo's own history contradicts it. The
question was re-put with the corrected facts: public for ~12 months, reused as
Grafana and InfluxDB admin credentials.

> **Answered 2026-08-21: treat the password and its construction pattern as
> burned.** Retire not only the exact string but any variant built from the same
> scheme, anywhere it may have been used — router/AP admin, NAS, brokers,
> personal accounts. Credential-stuffing seeds guesses from the *pattern*; the
> original target being dead is irrelevant to that.

This **supersedes** the "no, unique to this broker" answer recorded under
[Owner response](#owner-response). Rotation is closed on *retirement*, not on a
uniqueness claim that measurement disproved.

### Branch cleanup — done

14 remote branches still served the plaintext at their tip on a public repo.
All 14 were verified **fully merged into `origin/master`** (no unmerged work),
their SHAs recorded for restoration, then deleted. `origin` now holds **only
`master`**, and **no remote branch carries the credential at tip**.

Restore any one with `git push origin <sha>:refs/heads/<branch>`.

This is **discoverability reduction, not containment** — the blob stays fetchable
by SHA. It removes the file from GitHub's branch UI, from code search over branch
heads, and from tip-following scrapers.

Still outstanding: the **local** branch `device-knowledge-completion` tracks the
file at tip. It is merged into `origin/master`, so deleting it loses nothing, but
it is local-only and was left for the owner to remove.

### The history rewrite, re-decided on corrected facts

**Still declined — but the reasoning is now the opposite of the original.**

The original decline rested on "the repo is private, so history readers are
already inside the trust boundary." That premise was false and is void.

The decline survives on the *stronger* ground the first correction identified:
against **12 months of public exposure**, a rewrite cannot reach clones taken by
anyone, GitHub's retention of unreachable commits (fetchable by SHA), or any
search index or scraper that already read the tree. **Rotation is the control;
the rewrite is cosmetic beside it** — and rotation is now confirmed complete by
measurement, with every leaked credential returning 401.

Recorded explicitly: **this is a tidiness decision, not a containment one.**
A rewrite would still cost `filter-repo`/BFG plus a force-push invalidating every
clone, to remove a copy that protects nothing.

---

## Decision

**Decline the git-history rewrite. Record the decline.**

The reasoning that decides it, in one line: *a rewrite cannot claw back the copies
that actually matter.*

A rewrite is justified when a secret is both exploitable and exposed beyond the
trust boundary that repo access already grants. Neither holds. The broker is dead,
so exploitability is nil; the repo is private, so git-history readers are already
inside the boundary. **<- FALSE. The repo is public. This clause is the error that
voids the decision below; see [Correction](#correction-2026-08-21-the-repo-is-public).** Against that, a rewrite costs `filter-repo`/BFG plus a
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
- [x] Owner confirmation on password reuse — **answered 2026-08-21, see below**
- [x] Rotation criterion closed on that confirmation

## Residual risk accepted

1. **Password reuse elsewhere — ~~RESOLVED~~ CORRECTED, then closed by retirement.**
   The original text recorded the owner's "not reused anywhere else" answer and
   closed the criterion on it. **Measurement disproved it**: the string was reused
   as Grafana admin, InfluxDB admin, and the InfluxDB API token across 17 files
   from 2025-08-23. The claim "nothing in the repository could have established
   it" was itself wrong — a history search would have, and none was run.
   **Now closed on a different basis:** the owner has re-answered against the
   corrected radius and treats the password *and its construction pattern* as
   burned, and all three live services reject it (401). See
   [Second pass](#second-pass-2026-08-21-what-measurement-changed).
2. **"Not in the working tree" is branch-local — now nearly closed.** `master` no
   longer tracks the file (the branch merged), and the 14 remote branches that did
   were deleted. Only the **local** `device-knowledge-completion` remains.
   Historical text follows.
   ~~`master` and `device-knowledge-completion` still **track** the file at tip.~~
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

## Owner response

Asked 2026-08-21, because neither item could be settled from inside the repository.

**1. Password reuse — answered: NO.**

> Asked: "The MQTT password in commit `3df40097` is confirmed unique within this
> repository, and the broker it belongs to (`192.168.1.100:1883`) is unreachable
> and appears decommissioned. That is the limit of what can be checked from
> inside the repo — have you ever reused this exact password anywhere else:
> router or AP admin, NAS, another broker, a cloud or personal account?"
>
> **Answered: "No — unique to this dead broker."**

That closes the rotation criterion. The credential is unique to a broker that no
longer exists, so there is nothing to rotate. Recorded as the owner's statement
rather than as a verified fact, because it is not verifiable from here — if that
statement is ever found to be mistaken, this disposition is void under the
re-evaluation triggers above.

**2. Sign-off on declining the rewrite.** The owner was given the decline, its
reasoning and its cost, and did not ask for a rewrite. Treated as accepted.

## Process gap worth closing

Fixing the recurrence is worth more than relitigating this one dead credential:
configure agent tooling with a deny-list for secret-shaped paths (`*.env`,
`*credential*`, `config/*secret*`) so the next credential does not take this route
in. Not actioned here — it is outside TAP-6399's scope and deserves its own ticket.
