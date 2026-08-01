#!/bin/bash
# DEPRECATED: start-prod.sh is superseded by start-stack.sh.
# The old docker-compose.prod.yml no longer exists; the production stack is
# started per-domain (correct Docker project names) via scripts/start-stack.sh.
# This shim forwards all arguments and will be removed in a future release.

echo "WARNING: scripts/start-prod.sh is deprecated — forwarding to scripts/start-stack.sh" >&2
exec "$(cd "$(dirname "$0")" && pwd)/start-stack.sh" "$@"
