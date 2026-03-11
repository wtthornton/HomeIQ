# HomeIQ Scripts

Operational scripts for deploying, managing, and monitoring the HomeIQ stack.

**Single configuration:** Use domain scripts only. See [docs/deployment/DEPLOYMENT_QUICK_REFERENCE.md](../docs/deployment/DEPLOYMENT_QUICK_REFERENCE.md).

```powershell
# Full stack (Windows)
.\scripts\start-stack.ps1

# Full stack (Linux/Mac)
./scripts/start-stack.sh
```

**Do not** use `docker compose up -d` from the project root — it creates orphan project groups.

## Current Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `domain.sh` / `domain.ps1` | Per-domain Docker Compose helper (start, stop, restart, status, logs, build) | Day-to-day domain management |
| `start-stack.sh` / `start-stack.ps1` | Start all 9 domains in dependency order with health polling | Full stack startup |
| `ensure-network.sh` / `ensure-network.ps1` | Create the `homeiq-network` Docker bridge if it doesn't exist | Called automatically by other scripts; run manually if network issues occur |
| `deploy-phase-5.sh` | Tiered production deployment with health gates and smoke tests | Production deployments |
| `check-service-health.sh` | Check health of all services, with JSON and critical-only modes | Health monitoring and CI checks |
| `backup-postgres.sh` | Back up PostgreSQL databases | Scheduled or pre-deployment backups |
| `backup-influxdb.sh` | Back up InfluxDB data | Scheduled or pre-deployment backups |
| `check-pg-stability.sh` | Verify PostgreSQL connection stability and schema health | After DB changes or suspected instability |

## Archived Scripts

Deprecated scripts from the pre-domain-split era are in [`scripts/archive/`](archive/). See [`archive/README.md`](archive/README.md) for details.

## Quick Start

Start a single domain:
```bash
./scripts/domain.sh start core-platform
```

Start the full stack (all 9 domains in order):
```bash
./scripts/start-stack.sh
```

Start the full stack without waiting for health checks:
```bash
./scripts/start-stack.sh --skip-wait
```

Check domain status:
```bash
./scripts/domain.sh status data-collectors
```

View logs for a specific service:
```bash
./scripts/domain.sh logs ml-engine ai-core-service
```

List all valid domain names:
```bash
./scripts/domain.sh list
```

Build images for a domain:
```bash
./scripts/domain.sh build core-platform
```

Run a full health check:
```bash
./scripts/check-service-health.sh
./scripts/check-service-health.sh --json
./scripts/check-service-health.sh --critical-only
```
