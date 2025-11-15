# Issue #8: [P1] Add Database Migration Tests

**Status:** 🟢 Open
**Priority:** 🟡 P1 - High
**Effort:** 4-6 hours
**Dependencies:** None

## Description

Test Alembic database migrations for data integrity, idempotency, and upgrade/downgrade cycles.

## Acceptance Criteria

- [ ] Migration upgrade/downgrade cycle tests
- [ ] Data integrity after migration tests
- [ ] Migration idempotency tests
- [ ] Rollback functionality tests
- [ ] Coverage for all migrations

## Code Template

```python
# tests/migrations/test_alembic_migrations.py
import pytest
from alembic import command
from alembic.config import Config

@pytest.fixture
def alembic_config():
    """Alembic configuration for testing"""
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", "sqlite:///test.db")
    return config

def test_upgrade_downgrade_cycle(alembic_config):
    """Test migration can upgrade and downgrade"""
    # Upgrade to latest
    command.upgrade(alembic_config, "head")

    # Downgrade one version
    command.downgrade(alembic_config, "-1")

    # Upgrade again
    command.upgrade(alembic_config, "head")

def test_migration_idempotency(alembic_config):
    """Test running migration twice doesn't cause errors"""
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")  # Should be safe
```
