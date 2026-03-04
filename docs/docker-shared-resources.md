# Docker Shared Resources

**Last Updated:** March 4, 2026

This document defines the ownership and referencing rules for Docker volumes that are shared across domain groups.

---

## Shared Volume Inventory

| Volume | Owner Domain | Consuming Domains | Env Variable | Standalone Default | Full-Stack Name |
|--------|-------------|-------------------|--------------|-------------------|-----------------|
| `homeiq_logs` | core-platform | data-collectors, device-management | `HOMEIQ_LOGS_VOLUME` | `homeiq-core-platform_homeiq_logs` | `homeiq_homeiq_logs` |
| `ai_automation_data` | ml-engine | automation-core, pattern-analysis | `AI_AUTOMATION_DATA_VOLUME` | `homeiq-ml-engine_ai_automation_data` | `homeiq_ai_automation_data` |
| `ai_automation_models` | ml-engine | automation-core | `AI_AUTOMATION_MODELS_VOLUME` | `homeiq-ml-engine_ai_automation_models` | `homeiq_ai_automation_models` |

---

## Ownership Rule

**A volume must have exactly one owner domain. All other consumers declare it `external: true`.**

- The **owner** domain declares the volume as a normal (non-external) volume in its `compose.yml`. Docker creates and manages this volume under the owner's project prefix.
- **Consumer** domains declare the volume as `external: true` with a `name:` that references an environment variable. The env var defaults to the owner's project-prefixed name for standalone operation.

### Owner declaration (unchanged)

```yaml
# In the owner's compose.yml (e.g., ml-engine/compose.yml)
volumes:
  ai_automation_data:
```

### Consumer declaration (external reference)

```yaml
# In a consumer's compose.yml (e.g., automation-core/compose.yml)
volumes:
  ai_automation_data:
    external: true
    name: ${AI_AUTOMATION_DATA_VOLUME:-homeiq-ml-engine_ai_automation_data}
```

---

## Environment Variables

All shared volume env vars are defined in the root `.env` file. When running the full stack via the root `docker-compose.yml`, these variables point to the root project prefix (`homeiq_`):

```env
HOMEIQ_LOGS_VOLUME=homeiq_homeiq_logs
AI_AUTOMATION_DATA_VOLUME=homeiq_ai_automation_data
AI_AUTOMATION_MODELS_VOLUME=homeiq_ai_automation_models
```

When running a domain standalone (without the root `.env`), the default in the compose file falls back to the owner domain's project-prefixed name (e.g., `homeiq-core-platform_homeiq_logs`). This requires the owner domain to be running first.

---

## Adding a New Shared Volume

1. **Choose an owner domain** -- the domain that creates and primarily manages the data.
2. In the owner's `compose.yml`, declare the volume as a normal volume (no `external`).
3. In each consumer's `compose.yml`, declare the volume as:
   ```yaml
   volumes:
     my_shared_volume:
       external: true
       name: ${MY_SHARED_VOLUME:-<owner-project>_my_shared_volume}
   ```
4. Add the env var to the root `.env`:
   ```env
   MY_SHARED_VOLUME=homeiq_my_shared_volume
   ```
5. Update the inventory table in this document.

---

## Migration: Renaming Existing Volumes

If volumes already exist under old project-prefixed names (e.g., from before the `name:` directive was added to compose files), you can copy data to the new name:

```bash
# 1. Stop all services that use the volume
docker compose -f domains/<group>/compose.yml down

# 2. Create a temporary container to copy data
docker volume create <new_volume_name>
docker run --rm \
  -v <old_volume_name>:/source:ro \
  -v <new_volume_name>:/dest \
  alpine sh -c "cp -a /source/. /dest/"

# 3. Verify the new volume has the data
docker run --rm -v <new_volume_name>:/data alpine ls -la /data

# 4. Restart services -- they will now use the new volume name
docker compose -f domains/<group>/compose.yml up -d

# 5. Once confirmed working, remove the old volume
docker volume rm <old_volume_name>
```

---

## Network Reference

All domain compose files also share the `homeiq-network` bridge network. The network is created by `core-platform/compose.yml` and referenced as `external: true` by all other domains. This is not a volume concern but follows the same ownership pattern.
