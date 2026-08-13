# homeiq-ha

Home Assistant integration utilities for the HomeIQ platform.

## Features

- **HAConnectionManager**: Connection management with primary/Nabu Casa fallback
- **Deployment Validation**: Deployment mode checks to prevent misconfigurations
- **Shared client** (`homeiq_ha.client`): `HAClient` = REST (`HARestClient`) +
  WebSocket (`HAWebSocketClient`) with auth, auto-reconnect, redaction, config-flow
  driving, and supervisor access (text logs go via `HARestClient.get_supervisor_logs`)
- **Init/setup agent** (`homeiq_ha.agent`): declarative, idempotent recipe engine
  (`check`/`plan`/`apply`/`verify`) behind a read-only audit proxy — serves the
  `:8024` init gateway (`docs/operations/init-gateway.md`); recipes include backup
  gating, organization, ZHA onboarding, and report-only Zigbee diagnostics
  (mesh health + coordinator watchdog)

## Installation

```bash
pip install -e libs/homeiq-ha/
```

## Usage

```python
from homeiq_ha.ha_connection_manager import HAConnectionManager
from homeiq_ha.deployment_validation import validate_deployment_mode
```
