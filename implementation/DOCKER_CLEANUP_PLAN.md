# Docker Cleanup Plan – HomeIQ-Only Local Environment

**Created:** February 9, 2026  
**Goal:** Clean up old containers, images, volumes, and other Docker resources so only HomeIQ is running and disk usage is minimized.

---

## 1. Current Docker Setup (HomeIQ)

- **Compose project name:** `homeiq` (from `name: homeiq` in `docker-compose.yml`)
- **Containers:** 47+ services; names usually start with `homeiq-` or match service names (e.g. `ai-automation-ui`, `homeiq-influxdb`)
- **Images:** Built from repo (e.g. `homeiq-websocket-ingestion`, `homeiq-data-api`) plus a few pulled images (`influxdb:2.7.12`, `jaegertracing/all-in-one:1.75.0`, `ghcr.io/home-assistant/home-assistant:stable`)
- **Volumes:** Named volumes in `docker-compose.yml` become `homeiq_<volume_name>` (e.g. `homeiq_influxdb_data`, `homeiq_postgres_data`)
- **Network:** `homeiq_homeiq-network`
- **Other compose files:** `docker-compose.dev.yml`, `docker-compose.minimal.yml`, `docker-compose.simple.yml`, and service-specific compose files may create extra containers/volumes when used

---

## 2. What “Only HomeIQ” Means

- **Containers:** Only containers from the `homeiq` project (and any profile you use) are running; no other projects’ containers.
- **Images:** HomeIQ images and their base images are kept; unused images from other projects or old builds can be removed.
- **Volumes:** HomeIQ data volumes are kept; unused anonymous or other-project volumes can be removed.
- **Networks:** Only `homeiq` networks are in use; unused networks can be removed.
- **Build cache:** Can be pruned to free space; next build will be slower.

---

## 3. Cleanup Phases (Safe Order)

### Phase 1: Audit (No Deletion)

Run these in PowerShell to see what exists.

```powershell
# All containers (running + stopped)
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# HomeIQ containers only
docker ps -a --filter "name=homeiq" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
docker ps -a --filter "name=ai-automation-ui" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"
docker ps -a --filter "name=ai-pattern-service" --format "table {{.Names}}\t{{.Status}}\t{{.Image}}"

# All images (repository, tag, size)
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# All volumes
docker volume ls

# All networks
docker network ls

# Disk usage
docker system df
docker system df -v
```

**Action:** Confirm which containers/images/volumes are HomeIQ vs other projects. Note any non-HomeIQ resources you want to remove later.

---

### Phase 2: Stop and Remove Stopped/Orphan Containers

Only removes **stopped** containers. Running HomeIQ stack is untouched.

```powershell
# Optional: stop the entire HomeIQ stack first (if you want a full clean restart)
# docker compose -f docker-compose.yml down

# Remove all stopped containers (any project)
docker container prune -f

# Remove only orphan containers from current project (run from repo root)
docker compose -f docker-compose.yml down --remove-orphans
```

**Safe:** Yes. Only stopped containers are removed. Data in volumes is not deleted.

---

### Phase 3: Remove Dangling and Unused Images

Removes images not used by any container. HomeIQ **running** containers’ images are kept.

```powershell
# Remove dangling images (<none>:<none>) – very safe
docker image prune -f

# Remove all images not used by any container (stops nothing)
docker image prune -a -f
```

**Warning:** `docker image prune -a` removes **all** unused images (including other projects). If you use Docker only for HomeIQ, this is usually fine. If you have other projects, run `docker images` first and avoid `-a`, or use Phase 5 to target non-HomeIQ images only.

---

### Phase 4: Remove Unused Volumes

**Risk:** Volumes store data (InfluxDB, PostgreSQL, logs, etc.). Removing a volume **deletes that data**.

```powershell
# List volumes (confirm names before pruning)
docker volume ls

# DRY RUN: see what would be removed (Docker has no built-in dry run; inspect manually)
# Only “unused” volumes are removed (not attached to any container)

# Remove all unused volumes (DANGER: any non-HomeIQ unused volume is removed too)
docker volume prune -f
```

**Safe approach:**

1. Bring down the stack: `docker compose down` (containers are removed; volumes remain).
2. Run `docker volume ls` and note names like `homeiq_influxdb_data`, `homeiq_postgres_data`, etc.
3. Run `docker volume prune -f` only if you are sure no important **non-HomeIQ** data is in unused volumes.
4. To remove **only** a specific volume (e.g. an old test volume):  
   `docker volume rm <volume_name>`

**Do not** run `docker volume prune` if you might need data from any unused volume.

---

### Phase 5: Remove Unused Networks

Removes networks not used by any container.

```powershell
docker network prune -f
```

**Safe:** Yes. Only unused networks are removed. Your running stack’s network is in use, so it is kept.

---

### Phase 6: Build Cache (Optional)

Frees disk space; next build will be slower.

```powershell
# Remove build cache
docker builder prune -f

# Aggressive: all build cache (including for other projects)
docker builder prune -a -f
```

---

### Phase 7: Nuclear Option – “Only HomeIQ” on the Host

Use only if this machine runs **nothing** else in Docker and you want a clean slate except HomeIQ.

1. **Stop and remove all containers (any project):**
   ```powershell
   docker compose -f docker-compose.yml down
   docker stop $(docker ps -aq) 2>$null; docker rm $(docker ps -aq) 2>$null
   ```

2. **Remove all unused images, networks, build cache:**
   ```powershell
   docker image prune -a -f
   docker network prune -f
   docker builder prune -a -f
   ```

3. **Optionally remove all unused volumes (PERMANENT DATA LOSS for unused volumes):**
   ```powershell
   docker volume prune -f
   ```

4. **Start only HomeIQ:**
   ```powershell
   docker compose -f docker-compose.yml up -d
   # Or with profile: docker compose -f docker-compose.yml --profile production up -d
   ```

---

## 4. Recommended Order for “Clean Up, Keep HomeIQ”

| Step | Action | Command |
|------|--------|--------|
| 1 | Audit | `docker system df -v` and `docker ps -a` |
| 2 | Remove stopped containers | `docker container prune -f` |
| 3 | Remove orphan compose containers | `docker compose down --remove-orphans` (from repo root) |
| 4 | Remove dangling images | `docker image prune -f` |
| 5 | Remove unused images (if only HomeIQ) | `docker image prune -a -f` |
| 6 | Remove unused networks | `docker network prune -f` |
| 7 | Optional: build cache | `docker builder prune -f` |
| 8 | Optional: unused volumes (only if sure) | `docker volume prune -f` |

---

## 5. One-Liner “Safe” Cleanup (No Volumes)

From project root, PowerShell:

```powershell
docker container prune -f; docker compose down --remove-orphans; docker image prune -f; docker network prune -f; docker builder prune -f; docker system df
```

Then start HomeIQ again:

```powershell
docker compose up -d
```

---

## 6. Script

A PowerShell script `scripts/cleanup-docker.ps1` is provided to:

- Run an audit (containers, images, volumes, disk usage)
- Optionally run safe cleanup (containers, dangling images, networks, build cache)
- Optionally run volume prune with confirmation
- Support `-WhatIf` for dry run

See script header for usage.

---

## 7. After Cleanup

- Confirm stack: `docker compose ps`
- Check disk: `docker system df`
- If something is missing: restore from backups (e.g. InfluxDB, PostgreSQL) if you have them; volumes removed with `docker volume prune` are not recoverable.
