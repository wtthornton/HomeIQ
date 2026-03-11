# Example configs

Example pipeline configs that match the schema in `config/schema/`.

| File | Description |
|------|-------------|
| **homeiq-default.yaml** | Matches current HomeIQ `scripts/auto-bugfix.ps1` behavior: paths, manifest, MCP_DOCKER tool prefix, budget allocation (scan 0.30, fix 0.40, chain 0.15, feedback 0.15). Use with runner or `-ConfigPath` once Epic 2/3 are in place. |

No production secrets. These are for development and as a reference for the config shape.
