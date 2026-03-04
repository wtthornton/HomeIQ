# homeiq-ha

Home Assistant integration utilities for the HomeIQ platform.

## Features

- **HAConnectionManager**: Connection management with primary/Nabu Casa fallback
- **Deployment Validation**: Deployment mode checks to prevent misconfigurations

## Installation

```bash
pip install -e libs/homeiq-ha/
```

## Usage

```python
from homeiq_ha.ha_connection_manager import HAConnectionManager
from homeiq_ha.deployment_validation import validate_deployment_mode
```
