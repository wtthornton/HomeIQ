# HomeIQ Deployment — Single Configuration

**Last Updated:** March 11, 2026  
**Status:** Canonical reference for local deployment

---

## One Configuration

HomeIQ uses **domain-based deployment** with **production profile** as the single canonical configuration. All scripts and documentation should reference this approach only.

| Do | Don't |
|----|-------|
| `.\scripts\start-stack.ps1` (Windows) | `docker compose up -d` from root |
| `./scripts/start-stack.sh` (Linux/Mac) | `docker compose --profile production up -d` from root |
| `.\scripts\domain.ps1 start <domain>` | Root compose — creates orphan "homeiq" project |
| `./scripts/domain.sh start <domain>` | |

---

## Full Stack Startup

```powershell
# Windows
.\scripts\start-stack.ps1
.\scripts\start-stack.ps1 -SkipWait   # Skip health polling
```

```bash
# Linux/Mac
./scripts/start-stack.sh
./scripts/start-stack.sh --skip-wait   # Skip health polling
```

**What this does:**
- Starts each of 9 domains via its own compose file
- Uses `--profile production` (includes air-quality, carbon-intensity, electricity-pricing, calendar in data-collectors)
- Each domain appears as a separate group in Docker Desktop: homeiq-core-platform, homeiq-data-collectors, homeiq-ml-engine, etc.

---

## Single Domain

```powershell
# Windows
.\scripts\domain.ps1 start data-collectors
.\scripts\domain.ps1 status core-platform
.\scripts\domain.ps1 logs ml-engine ai-core-service
```

```bash
# Linux/Mac
./scripts/domain.sh start data-collectors
./scripts/domain.sh status core-platform
./scripts/domain.sh logs ml-engine ai-core-service
```

---

## Why Not Root Compose?

Running `docker compose up -d` from the project root:
- Merges all services into one project named `homeiq`
- Profile-gated services (air-quality, carbon-intensity, etc.) get the root project name
- Results in a flat list or orphan groupings in Docker Desktop
- Causes the "air-quality under homeiq" problem

**Always use the domain scripts.**

---

## Verify

```bash
./scripts/domain.sh verify   # Detects containers in wrong project
```

---

## Domain Order (for reference)

1. core-platform
2. data-collectors
3. ml-engine
4. automation-core
5. blueprints
6. energy-analytics
7. device-management
8. pattern-analysis
9. frontends

---

## Required Environment Variables

Copy `infrastructure/env.example` to `.env` and set at minimum:

| Variable | Purpose |
|----------|---------|
| `AI_CORE_API_KEY` | Required for ai-core-service. Add to `.env` or it falls back to `API_KEY` / dev default. |
| `API_KEY` | Dashboard/admin API key. Often used as fallback for AI_CORE_API_KEY in local dev. |

If `ai-core-service` fails to start with "AI_CORE_API_KEY must be set", add to your `.env`:
```
AI_CORE_API_KEY=homeiq-dev-ai-core-key
```

---

## See Also

- [Deployment Runbook](DEPLOYMENT_RUNBOOK.md) — Full deployment guide
- [scripts/README.md](../../scripts/README.md) — Script reference
