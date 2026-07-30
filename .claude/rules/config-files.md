---
paths:
  - "**/*.yaml"
  - "**/*.yml"
  - "**/*.toml"
  - "**/*.json"
  - "**/Dockerfile*"
  - "**/docker-compose*"
---
# Configuration File Rules (TappsMCP)

Run `tapps_validate_config(file_path)` when editing Dockerfile, docker-compose, or infrastructure config.

## YAML/TOML

- Use consistent indentation (2 spaces for YAML)
- Quote strings containing special characters
- Validate against known schemas when available

## Docker

- Pin base image versions (no `latest` tag)
- Use multi-stage builds for production images
- Run as non-root user
- Don't copy secrets into images

## JSON Config

- Use environment variable expansion (`${VAR}`) for secrets — never hardcode
- Add `"type"` field to MCP server entries
- Validate with `$schema` when available
