# homeiq-data

Shared data access utilities for the HomeIQ platform.

## Features

- **DatabaseManager**: Standardized PostgreSQL lifecycle manager with graceful degradation
- **BaseServiceSettings**: Common Pydantic settings inherited by all services
- **StandardDataAPIClient**: Unified client for Data API with circuit breaker protection
- **Database Pool**: Shared engine management, connection pooling, schema isolation
- **Alembic Helpers**: Schema-per-domain migration utilities

## Installation

```bash
pip install -e libs/homeiq-data/
```

## Usage

```python
from homeiq_data import DatabaseManager, BaseServiceSettings, StandardDataAPIClient
```
