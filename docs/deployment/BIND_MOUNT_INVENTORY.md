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

A non-zero exit lists every offending `container: resolved-source` pair, plus
how many containers and bind sources it actually examined (see the script's
own docstring for why those counts matter).

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
the developer's tree. Named volumes are out of scope for this move.

## Current inventory (11 containers, 20 bind sources into the checkout)

| Container | Bind source (relative to repo root) | Destination after the move |
|---|---|---|
| `homeiq-setup-service` | `config` | same relative path under the deploy root |
| `homeiq-device-intelligence` | `infrastructure` | same relative path under the deploy root |
| `homeiq-admin` | `docker-compose.yml` | same relative path under the deploy root |
| `homeiq-admin` | `infrastructure` | same relative path under the deploy root |
| `homeiq-data-api` | `infrastructure/service-configs` | same relative path under the deploy root |
| `homeiq-grafana` | `infrastructure/grafana/provisioning` | same relative path under the deploy root |
| `homeiq-grafana` | `infrastructure/grafana/dashboards` | same relative path under the deploy root |
| `homeiq-log-aggregator` | `logs` | same relative path under the deploy root |
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

For every row except `rag-service`, the fix is mechanical: the same path
exists under `master`, so checking out `master` at the deploy root and
redeploying from there reproduces the file at the new location — the mount
source string just moves with the tree.

## The one row that isn't mechanical: `rag-service`

`domains/ml-engine/rag-service/` carries **0 tracked files on `master`** (the
service was merged into `model-server`; the old branch had 31 files there).
The running `homeiq-rag-service` container still binds
`domains/ml-engine/rag-service/data` from the old, untracked checkout state —
content that git does not know about and a fresh clone will not produce.

Before the deploy-window move, whoever re-points this mount must:

1. Copy the live `data/` directory's current contents out of the old checkout
   (not out of git — it was never tracked) to a path under
   `/home/wtthornton/deploy-roots/homeiq-master` that survives the source tree
   being deleted or re-cloned (e.g. a sibling directory outside any git
   working tree, or a named volume seeded from a one-time copy).
2. Record the seed step in the deploy runbook so a future fresh install does
   not silently start `rag-service` with an empty data directory.

This document exists to make that gap visible before the move, not to close
it — closing it is the deploying operator's job in the approved window.

## Verifying the fix later

After the redeploy, re-run the sweep against the checkout being retired:

```
python3 scripts/check-bind-mounts.py /home/wtthornton/code/HomeIQ
```

Exit `0` (with a nonzero "examined N bind source(s)" count printed) confirms no
running container still reaches into the developer checkout. Exit `2` on that
same command would mean the sweep inspected nothing — treat that as a broken
probe, never as success.
