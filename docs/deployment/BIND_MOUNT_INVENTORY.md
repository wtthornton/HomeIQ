# Bind-mount inventory: what points into the checkout today, and where it moves

**Status:** measured 2026-09-15 against the running stack. Tracking: TAP-7646.

## The hazard

`/home/wtthornton/code/HomeIQ` is both a git checkout and a live deploy root: 20
bind-mount sources across 11 running containers resolve inside it. Switching
that checkout's branch, or deleting a path from it, changes what a running
container reads — with no restart, no log line, and no warning. `scripts/check-bind-mounts.py`
is the committed instrument that detects this; run it against any tree with:

```
python3 scripts/check-bind-mounts.py /home/wtthornton/code/HomeIQ
```

A non-zero exit from violations found (`EXIT_VIOLATIONS_FOUND`) lists every
offending `container: resolved-source` pair, plus how many containers and
bind sources it actually examined (see the script's own docstring for why
those counts matter). The inspection-failure path (`EXIT_INSPECTION_FAILED`,
raised from `load_containers` — `check-bind-mounts.py:115-117`) prints only
`INSPECTION FAILED: <exc>` with no counts; see "Verifying the fix later"
below for that path.

## The fix (scope of a later, operator-approved deploy window)

This lane does not move anything. The destination the orchestrator has already
chosen is a dedicated **deploy root**, separate from any git working tree:

```
/home/wtthornton/deploy-roots/homeiq-master
```

The stack is redeployed *from* that path (a plain `git worktree`/checkout of
`origin/master`, not the developer's working checkout at
`/home/wtthornton/code/HomeIQ`). Once compose is re-run from there,
`check-bind-mounts.py /home/wtthornton/code/HomeIQ` should report zero
repo-internal binds, because no running container *binds* a path inside the
checkout.

That claim is narrower than full independence from the developer's tree: the
deploy root's `.env` is a symlink into the live checkout
(`/home/wtthornton/deploy-roots/homeiq-master/.env` ->
`/home/wtthornton/code/HomeIQ/.env`), a remaining non-bind coupling. A symlink
is not a bind mount, so `check-bind-mounts.py` is correctly unaffected and
"zero repo-internal binds" still means what it says — this note records the
coupling rather than implying it away.

**Use `origin/master`, never the local `master` ref.** On this host the local
ref is stale by 30 commits: `git rev-parse master` = `30c55416` (2026-08-26),
`git rev-parse origin/master` = `c7abe2ae` (2026-09-15). The difference is not
cosmetic for this procedure — the stale local `master` still tracks **31** files
under `domains/ml-engine/rag-service/` and **0** under
`domains/ml-engine/model-server/`, the exact inverse of `origin/master`, so an
operator who checks out `master` literally produces the one tree every
"`0` tracked files" claim below says does not exist. Fetch first, or check the
deploy root out at an explicit sha.

## Current inventory (11 containers, 20 bind sources into the checkout)

This is every bind source that resolves inside the checkout, `logs`
included. TAP-7646 itself states **20** in three places — its title ("20
bind-mounts make the git checkout live production config"), `## What`
("Twenty bind-mounts") and `## Why` ("Twenty bind sources") — while its
itemized list sums to **18** (prometheus 4, postgres 3, grafana 2, admin 2,
automation-linter 3, data-api 1, setup-service 1, rag-service 1,
alertmanager 1 = 18). Two separate things account for that gap, and only one
of them is an oversight:

1. `homeiq-device-intelligence` (1 source, `infrastructure`) is genuinely
   absent from TAP-7646's body — it appears in no sentence and no list entry.
2. The `logs` mount under `homeiq-log-aggregator` (1 source) is **named, and
   deliberately excluded with a stated reason**. TAP-7646's `## Why` ends:
   "The mount that targets the gitignored `logs` directory is excluded: it has
   zero tracked files, so git never touches it." That is a scope decision the
   issue author made on purpose, not a miscount.

**This document deliberately re-includes the `logs` mount.** Its population is
therefore 20 where the issue's enumeration is 18, and the difference is one of
scope, disclosed here rather than left for a reader to trip over. The two
artifacts are asking different questions. TAP-7646 asks whether git *rewrites*
the content behind a mount, and its exclusion is correct on those terms: `logs`
holds zero tracked files, so a branch switch never rewrites it. This sweep asks
the prior and broader question — does a running container read a path inside
the checkout at all? `logs` does, so it is one of the 20. Neither count is
wrong; they are counts over different populations. This table's 20 is the one
`check-bind-mounts.py` measures and enforces.

| Container | Bind source (relative to repo root) | Destination after the move |
|---|---|---|
| `homeiq-setup-service` | `config` | same relative path under the deploy root |
| `homeiq-device-intelligence` | `infrastructure` | same relative path under the deploy root |
| `homeiq-admin` | `docker-compose.yml` | same relative path under the deploy root |
| `homeiq-admin` | `infrastructure` | same relative path under the deploy root |
| `homeiq-data-api` | `infrastructure/service-configs` | same relative path under the deploy root |
| `homeiq-grafana` | `infrastructure/grafana/provisioning` | same relative path under the deploy root |
| `homeiq-grafana` | `infrastructure/grafana/dashboards` | same relative path under the deploy root |
| `homeiq-log-aggregator` | `logs` | same relative path under the deploy root — **see below, not present on a fresh checkout** |
| `homeiq-automation-linter` | `domains/automation-core/automation-linter/src` | same relative path under the deploy root |
| `homeiq-automation-linter` | `domains/automation-core/automation-linter/ui` | same relative path under the deploy root |
| `homeiq-automation-linter` | `libs/homeiq-ha/src/homeiq_ha/ha_automation_lint` | same relative path under the deploy root |
| `homeiq-postgres` | `infrastructure/postgres/init-schemas.sql` | same relative path under the deploy root |
| `homeiq-postgres` | `infrastructure/postgres/init-monitoring.sql` | same relative path under the deploy root |
| `homeiq-postgres` | `infrastructure/postgres/postgresql.conf` | same relative path under the deploy root |
| `homeiq-rag-service` | `domains/ml-engine/rag-service/data` | **see below — already served by `model-server` on `origin/master`; container to be stopped, not seeded** |
| `homeiq-prometheus` | `infrastructure/prometheus/alerts.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/prometheus.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/sla-rules.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/zeek-alerts.yml` | same relative path under the deploy root |
| `homeiq-alertmanager` | `infrastructure/alertmanager` | same relative path under the deploy root |

For every row except `logs`, the fix is mechanical: the same path (or, for
`rag-service`, the same bytes tracked under a different, already-existing
path) exists under `origin/master`, so checking out `origin/master` at the deploy root and
redeploying from there reproduces the content at the new location — no seed
copy needed. `rag-service` is mechanical for the data; what it needs instead
is a retirement action, covered below.

## The one row that needs an empty directory, and the one that was misdiagnosed: `logs` and `rag-service`

### `logs`

`logs/` is gitignored (`.gitignore:80`), carries **0 tracked files on
`origin/master`**, and does not exist under
`/home/wtthornton/deploy-roots/homeiq-master` today. An `origin/master`
checkout at the deploy root does not create it — it is an empty directory that
`homeiq-log-aggregator` writes into at container start, not one git ever
populates. Before the deploy-window move, create an empty `logs/` directory
under the deploy root (`mkdir -p logs`); no data needs seeding because the
container itself populates it from empty.

### `rag-service`

`domains/ml-engine/rag-service/` carries **0 tracked files on `origin/master`**
(the service was merged into `model-server`; the stale local `master` ref still
carries 31 files there — see the ref warning above).
That is true, but its data is **not** lost: it moved with the merge and is
tracked, byte-identical, under `model-server`'s path:

```
md5 /home/wtthornton/code/HomeIQ/domains/ml-engine/rag-service/data/rag_service.db
  = 95f214551a83d3b209b08729d92c01f6
md5 of git show origin/master:domains/ml-engine/model-server/data/rag_service.db
  = 95f214551a83d3b209b08729d92c01f6
git ls-tree -r --name-only origin/master -- domains/ml-engine/model-server/data/
  = domains/ml-engine/model-server/data/rag_service.db
```

`rag-service` is not a service on `origin/master` at all — three services fold
into `model-server`: openvino-service, ml-service and rag-service.
`ner-service` is dropped outright, not folded — no fold target, no caller
(`docs/architecture/collapse-map.md:365`). So nothing on `origin/master`
mounts `domains/ml-engine/rag-service/`. The successor already reads its own
copy of the same bytes:

```
domains/ml-engine/compose.yml:24   - RAG_DATABASE_PATH=/app/data/rag_service.db
domains/ml-engine/compose.yml:29   - ./model-server/data:/app/data
```

An `origin/master` checkout at the deploy root reproduces that file with no copy
step — the row needs no seed, and the fresh-clone framing this section used
to carry ("content that git does not know about and a fresh clone will not
produce") is backwards: a fresh clone reproduces it exactly, under
`model-server`'s path.

The `homeiq-rag-service` bind mount is live today only because the **old**
checkout still has the pre-merge `rag-service` directory and its data file
on disk; `origin/master` never creates that path and `model-server` never reads
from it. What this row needs during the deploy-window move is not a seed
command but a retirement step: stop the `homeiq-rag-service` container (it
is already scheduled for retirement, having been folded into `model-server`)
so nothing keeps a mount open into the old tree after cutover. Do not copy
`domains/ml-engine/rag-service/data` anywhere — that would seed a path
nothing on `origin/master` reads.

This document exists to make the `logs` `mkdir` step and the `rag-service`
retirement step visible before the move, not to perform them — that is the
deploying operator's job in the approved window.

## Verifying the fix later

After the redeploy, re-run the sweep against the checkout being retired:

```
python3 scripts/check-bind-mounts.py /home/wtthornton/code/HomeIQ
```

Exit `0` (with a nonzero "examined N bind source(s)" count printed) confirms no
running container still reaches into the developer checkout. Exit `2` on that
same command would mean the sweep inspected nothing — treat that as a broken
probe, never as success.
