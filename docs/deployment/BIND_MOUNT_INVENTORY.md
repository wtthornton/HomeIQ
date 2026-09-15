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
`master`, not the developer's working checkout at `/home/wtthornton/code/HomeIQ`).
Once compose is re-run from there, `check-bind-mounts.py /home/wtthornton/code/HomeIQ`
should report zero repo-internal binds, because nothing running still points at
the developer's tree.

## Current inventory (11 containers, 20 bind sources into the checkout)

This is every bind source that resolves inside the checkout, `logs`
included. TAP-7646's own text enumerates 18 sources over a narrower
population: it explicitly excludes the gitignored `logs` mount ("it has
zero tracked files, so git never touches it") and never names
`homeiq-device-intelligence`, which this table does list. This document's
20 is the number `check-bind-mounts.py` measures and enforces — it counts
live bind sources, not tracked-file status — so it is the number this repo
gates on.

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
| `homeiq-rag-service` | `domains/ml-engine/rag-service/data` | **see below — not tracked on `master`** |
| `homeiq-prometheus` | `infrastructure/prometheus/alerts.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/prometheus.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/sla-rules.yml` | same relative path under the deploy root |
| `homeiq-prometheus` | `infrastructure/prometheus/zeek-alerts.yml` | same relative path under the deploy root |
| `homeiq-alertmanager` | `infrastructure/alertmanager` | same relative path under the deploy root |

For every row except `rag-service` and `logs`, the fix is mechanical: the
same path exists under `master`, so checking out `master` at the deploy
root and redeploying from there reproduces the file at the new location —
the mount source string just moves with the tree.

## The two rows that aren't mechanical: `logs` and `rag-service`

### `logs`

`logs/` is gitignored (`.gitignore:80`), carries **0 tracked files on
`master`**, and does not exist under
`/home/wtthornton/deploy-roots/homeiq-master` today. A `master` checkout at
the deploy root does not create it — it is an empty directory that
`homeiq-log-aggregator` writes into at container start, not one git ever
populates. Before the deploy-window move, create an empty `logs/` directory
under the deploy root (`mkdir -p logs`); no data needs seeding because the
container itself populates it from empty.

### `rag-service`

`domains/ml-engine/rag-service/` carries **0 tracked files on `master`** (the
service was merged into `model-server`; the old branch had 31 files there).
The running `homeiq-rag-service` container still binds
`domains/ml-engine/rag-service/data` from the old, untracked checkout state —
content that git does not know about and a fresh clone will not produce.

The destination is already decided: a path under
`/home/wtthornton/deploy-roots/homeiq-master`, same as every other row. What
makes that safe here is narrower than "survives deletion or re-clone" — the
deploy root **is** a git working tree (`git -C
/home/wtthornton/deploy-roots/homeiq-master rev-parse
--is-inside-work-tree` returns `true`), and its `HEAD` advances at every
deploy. What protects `domains/ml-engine/rag-service/data` is that it has
**0 tracked files on `master`**
(`git -C <deploy root> ls-tree -r origin/master --
domains/ml-engine/rag-service/` returns nothing), so it is untracked at
that path — and advancing the deploy root's `HEAD` does not touch untracked
files. A fresh clone, however, does **not** reproduce this content at all:
there is nothing in git to clone.

Before the deploy-window move, whoever re-points this mount must:

1. Copy the live `data/` directory's current contents out of the old checkout
   (not out of git — it was never tracked) to
   `domains/ml-engine/rag-service/data` under the deploy root, as a one-time
   copy: `cp -a /home/wtthornton/code/HomeIQ/domains/ml-engine/rag-service/data
   /home/wtthornton/deploy-roots/homeiq-master/domains/ml-engine/rag-service/`.
2. Record that one-time seed command in the deploy runbook so a future fresh
   install does not silently start `rag-service` with an empty data
   directory.

This document exists to make both the `logs` and `rag-service` gaps visible
before the move, not to close them — closing them is the deploying
operator's job in the approved window.

## Verifying the fix later

After the redeploy, re-run the sweep against the checkout being retired:

```
python3 scripts/check-bind-mounts.py /home/wtthornton/code/HomeIQ
```

Exit `0` (with a nonzero "examined N bind source(s)" count printed) confirms no
running container still reaches into the developer checkout. Exit `2` on that
same command would mean the sweep inspected nothing — treat that as a broken
probe, never as success.
