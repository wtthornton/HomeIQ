# Story AI1.20: Simple Rollback (Simplified for Single Home)

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.20  
**Priority:** High  
**Estimated Effort:** 2-3 hours (Simplified from 6-8 hours)  
**Dependencies:** Story AI1.11 (HA Integration API), Story AI1.19 (Safety Validation)

---

## User Story

**As a** user  
**I want** to rollback automations that aren't working correctly  
**so that** I can quickly restore the previous version

---

## Business Value

- Provides safety net for automation deployment
- Enables quick recovery from misbehaving automations
- Simple version history (last 3 versions)
- Builds user confidence in AI-generated automations

**Simplified for single home use case:**
- No complex audit queries (small dataset)
- No retention policies (disk is cheap)
- No multi-user tracking (1-2 users max)
- Focus on essential rollback functionality

---

## Acceptance Criteria

1. ✅ Stores last 3 versions of each automation
2. ✅ Rollback endpoint restores previous version
3. ✅ Validates safety before rollback
4. ✅ Shows simple version list for automation
5. ✅ Deployment creates version record automatically

---

## Technical Implementation Notes

### Simple Version History Table

**Update: services/ai-automation-service/src/database/models.py**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

class AutomationVersion(Base):
    """
    Simple version history for automations.
    Keeps last 3 versions per automation for rollback.
    """
    __tablename__ = 'automation_versions'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    automation_id: Mapped[str] = mapped_column(String(100), index=True)
    yaml_content: Mapped[str] = mapped_column(Text)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    safety_score: Mapped[int] = mapped_column(Integer)
    
    # Simple! No user tracking, no metadata, no complex fields
```

### Migration

**Create: services/ai-automation-service/alembic/versions/003_add_version_history.py**

```python
"""Add automation version history

Revision ID: 003
Revises: 002
Create Date: 2025-10-16
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'automation_versions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('automation_id', sa.String(100), nullable=False, index=True),
        sa.Column('yaml_content', sa.Text(), nullable=False),
        sa.Column('deployed_at', sa.DateTime(), nullable=False),
        sa.Column('safety_score', sa.Integer(), nullable=False)
    )

def downgrade():
    op.drop_table('automation_versions')
```

### Simple Rollback Functions

**Create: services/ai-automation-service/src/rollback.py**

```python
"""
Simple Rollback Functionality
Story AI1.20: Simple Rollback
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime
from typing import Optional
import logging

from .database.models import AutomationVersion
from .clients.ha_client import HomeAssistantClient
from .safety_validator import SafetyValidator

logger = logging.getLogger(__name__)


async def store_version(
    db: AsyncSession,
    automation_id: str,
    yaml_content: str,
    safety_score: int
):
    """
    Store automation version.
    Keeps only last 3 versions per automation.
    """
    # Create new version
    version = AutomationVersion(
        automation_id=automation_id,
        yaml_content=yaml_content,
        deployed_at=datetime.utcnow(),
        safety_score=safety_score
    )
    db.add(version)
    await db.commit()
    
    # Clean up old versions (keep last 3)
    query = (
        select(AutomationVersion)
        .where(AutomationVersion.automation_id == automation_id)
        .order_by(AutomationVersion.deployed_at.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()
    
    # Delete anything beyond the last 3
    if len(versions) > 3:
        for old_version in versions[3:]:
            await db.delete(old_version)
        await db.commit()
        logger.info(f"Cleaned up old versions for {automation_id}, kept last 3")


async def get_versions(
    db: AsyncSession,
    automation_id: str
) -> list[AutomationVersion]:
    """Get version history for automation (last 3 max)"""
    query = (
        select(AutomationVersion)
        .where(AutomationVersion.automation_id == automation_id)
        .order_by(AutomationVersion.deployed_at.desc())
        .limit(3)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def rollback_to_previous(
    db: AsyncSession,
    automation_id: str,
    ha_client: HomeAssistantClient,
    safety_validator: SafetyValidator
) -> dict:
    """
    Rollback to previous version with safety validation.
    
    Returns:
        Result dict with success status
    """
    # Get version history
    versions = await get_versions(db, automation_id)
    
    if len(versions) < 2:
        raise ValueError("No previous version available for rollback")
    
    # Previous version is index 1 (0 is current)
    previous_version = versions[1]
    
    logger.info(f"Rolling back {automation_id} to version from {previous_version.deployed_at}")
    
    # Validate safety of previous version
    safety_result = await safety_validator.validate(previous_version.yaml_content)
    
    if not safety_result.passed:
        raise ValueError(
            f"Previous version fails current safety checks (score: {safety_result.safety_score}). "
            "Safety standards may have changed since original deployment."
        )
    
    # Deploy previous version
    deployment_result = await ha_client.deploy_automation(previous_version.yaml_content)
    
    if not deployment_result.get('success'):
        raise ValueError(f"Failed to deploy previous version: {deployment_result.get('error')}")
    
    # Store rollback as new version
    await store_version(
        db,
        automation_id,
        previous_version.yaml_content,
        safety_result.safety_score
    )
    
    logger.info(f"✅ Successfully rolled back {automation_id}")
    
    return {
        "success": True,
        "automation_id": automation_id,
        "rolled_back_to": previous_version.deployed_at,
        "safety_score": safety_result.safety_score
    }
```

### API Endpoint

**Update: services/ai-automation-service/src/api/deployment_router.py**

Add this simple rollback endpoint:

```python
from ..rollback import store_version, rollback_to_previous

@router.post("/{automation_id}/rollback")
async def rollback_automation(automation_id: str):
    """
    Rollback automation to previous version.
    Simple: just restores the last version.
    """
    try:
        async with get_db_session() as db:
            result = await rollback_to_previous(
                db,
                automation_id,
                ha_client,
                safety_validator
            )
            
            return {
                "success": True,
                "message": "Automation rolled back successfully",
                "data": result
            }
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Rollback failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{automation_id}/versions")
async def get_version_history(automation_id: str):
    """Get version history (last 3 versions)"""
    try:
        async with get_db_session() as db:
            from ..rollback import get_versions
            
            versions = await get_versions(db, automation_id)
            
            return {
                "success": True,
                "automation_id": automation_id,
                "versions": [
                    {
                        "id": v.id,
                        "deployed_at": v.deployed_at.isoformat(),
                        "safety_score": v.safety_score,
                        "yaml_preview": v.yaml_content[:100] + "..."
                    }
                    for v in versions
                ],
                "count": len(versions)
            }
            
    except Exception as e:
        logger.error(f"Error getting versions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Also update deploy_suggestion to store version:**

```python
# After successful deployment, add:
await store_version(
    db,
    deployment_result.get('automation_id'),
    suggestion.automation_yaml,
    safety_result.safety_score if safety_result else 100
)
```

---

## Definition of Done

- [ ] AutomationVersion model created
- [ ] Migration created and tested
- [ ] store_version function implemented (with last-3 cleanup)
- [ ] get_versions function implemented
- [ ] rollback_to_previous function implemented
- [ ] Rollback endpoint added to deployment_router
- [ ] Version history endpoint added
- [ ] Integration with deploy_suggestion (auto-store version)
- [ ] Unit tests (5 tests)
- [ ] Integration test (rollback flow)
- [ ] Documentation updated

---

## Testing Strategy

### Unit Tests (Simple)

```python
# tests/test_rollback.py
async def test_store_version():
    """Test version storage"""
    await store_version(db, "auto_1", "yaml_v1", 95)
    versions = await get_versions(db, "auto_1")
    assert len(versions) == 1

async def test_keeps_last_3_versions():
    """Test cleanup keeps only last 3"""
    # Store 5 versions
    for i in range(5):
        await store_version(db, "auto_1", f"yaml_v{i}", 95)
    
    versions = await get_versions(db, "auto_1")
    assert len(versions) == 3  # Only last 3

async def test_rollback_to_previous():
    """Test rollback restores previous version"""
    await store_version(db, "auto_1", "yaml_v1", 95)
    await store_version(db, "auto_1", "yaml_v2", 90)
    
    result = await rollback_to_previous(db, "auto_1", ha_client, validator)
    
    assert result['success'] is True
```

---

**Story Status:** Simplified and Ready  
**Estimated Effort:** 2-3 hours (vs 6-8 hours)  
**Created:** 2025-10-16

