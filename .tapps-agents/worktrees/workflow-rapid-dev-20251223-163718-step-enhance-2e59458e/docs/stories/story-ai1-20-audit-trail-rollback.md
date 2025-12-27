# Story AI1.20: Audit Trail & Rollback

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.20  
**Priority:** High  
**Estimated Effort:** 6-8 hours  
**Dependencies:** Story AI1.11 (HA Integration API), Story AI1.19 (Safety Validation)

---

## User Story

**As a** user  
**I want** a complete audit trail of automation changes with rollback capability  
**so that** I can recover from misbehaving automations and understand what changed

---

## Business Value

- Provides safety net for automation deployment
- Enables quick recovery from misbehaving automations
- Tracks who made changes and when (accountability)
- Stores version history for all automations
- Builds user confidence in AI-generated automations
- Supports compliance and debugging needs

---

## Acceptance Criteria

1. ✅ Creates audit record for every automation action (create/modify/delete/rollback)
2. ✅ Stores complete YAML snapshot before every change
3. ✅ Tracks user/source for each change
4. ✅ Provides rollback endpoint to restore previous version
5. ✅ Displays audit history in chronological order
6. ✅ Supports filtering audit log by automation_id, action, date range
7. ✅ Rollback validates safety before restoring
8. ✅ Audit records are immutable (append-only)
9. ✅ Database queries for audit history <100ms
10. ✅ Retains audit history for 90 days minimum

---

## Technical Implementation Notes

### Audit Database Schema

**Update: services/ai-automation-service/src/database/models.py**

```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from typing import Optional

class AutomationAudit(Base):
    """
    Immutable audit trail for all automation changes.
    
    Tracks complete history of:
    - Deployments (created)
    - Modifications (modified)
    - Deletions (deleted)
    - Rollbacks (rolled_back)
    """
    __tablename__ = 'automation_audit'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # What changed
    automation_id: Mapped[str] = mapped_column(String(100), index=True)
    action: Mapped[str] = mapped_column(String(50))  # created, modified, deleted, rolled_back
    
    # When
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )
    
    # YAML snapshot (before change)
    yaml_snapshot: Mapped[str] = mapped_column(Text)
    
    # Who and why
    user: Mapped[str] = mapped_column(String(100))
    source: Mapped[str] = mapped_column(String(50))  # ai_suggestion, manual, rollback
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Safety score at time of change
    safety_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Related suggestion (if applicable)
    suggestion_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Metadata
    metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_audit_automation_timestamp', 'automation_id', 'timestamp'),
        Index('idx_audit_action_timestamp', 'action', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AutomationAudit {self.action} {self.automation_id} @ {self.timestamp}>"


# Migration to add table
# services/ai-automation-service/alembic/versions/003_add_audit_trail.py
"""Add automation audit trail

Revision ID: 003
Revises: 002
Create Date: 2025-10-16
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'automation_audit',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('automation_id', sa.String(100), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('yaml_snapshot', sa.Text(), nullable=False),
        sa.Column('user', sa.String(100), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('safety_score', sa.Integer(), nullable=True),
        sa.Column('suggestion_id', sa.Integer(), nullable=True),
        sa.Column('metadata', sa.Text(), nullable=True),
    )
    
    # Create indexes
    op.create_index('idx_audit_automation', 'automation_audit', ['automation_id'])
    op.create_index('idx_audit_timestamp', 'automation_audit', ['timestamp'])
    op.create_index(
        'idx_audit_automation_timestamp',
        'automation_audit',
        ['automation_id', 'timestamp']
    )
    op.create_index(
        'idx_audit_action_timestamp',
        'automation_audit',
        ['action', 'timestamp']
    )

def downgrade():
    op.drop_table('automation_audit')
```

### Audit Service

**Create: services/ai-automation-service/src/audit_service.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta
from typing import List, Optional
import json
import logging

from src.database.models import AutomationAudit
from src.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class AuditService:
    """
    Manages audit trail and rollback functionality.
    
    Key Responsibilities:
    - Record all automation changes
    - Provide audit history queries
    - Enable rollback to previous versions
    - Enforce immutability of audit records
    """
    
    @staticmethod
    async def record_deployment(
        db: AsyncSession,
        automation_id: str,
        yaml_content: str,
        user: str,
        suggestion_id: Optional[int] = None,
        safety_score: Optional[int] = None
    ) -> AutomationAudit:
        """
        Record automation deployment in audit trail.
        
        Args:
            db: Database session
            automation_id: HA automation ID
            yaml_content: Full YAML content
            user: User who approved deployment
            suggestion_id: Related suggestion ID
            safety_score: Safety validation score
        
        Returns:
            Created audit record
        """
        audit_record = AutomationAudit(
            automation_id=automation_id,
            action='created',
            yaml_snapshot=yaml_content,
            user=user,
            source='ai_suggestion',
            suggestion_id=suggestion_id,
            safety_score=safety_score,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_record)
        await db.commit()
        await db.refresh(audit_record)
        
        logger.info(f"Audit: recorded deployment of {automation_id} by {user}")
        return audit_record
    
    @staticmethod
    async def record_deletion(
        db: AsyncSession,
        automation_id: str,
        yaml_content: str,
        user: str,
        reason: Optional[str] = None
    ) -> AutomationAudit:
        """Record automation deletion in audit trail."""
        audit_record = AutomationAudit(
            automation_id=automation_id,
            action='deleted',
            yaml_snapshot=yaml_content,
            user=user,
            source='manual',
            reason=reason,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_record)
        await db.commit()
        await db.refresh(audit_record)
        
        logger.info(f"Audit: recorded deletion of {automation_id} by {user}")
        return audit_record
    
    @staticmethod
    async def record_rollback(
        db: AsyncSession,
        automation_id: str,
        yaml_content: str,
        user: str,
        reason: str,
        rolled_back_to: int  # audit record ID
    ) -> AutomationAudit:
        """Record automation rollback in audit trail."""
        metadata = json.dumps({
            'rolled_back_to_audit_id': rolled_back_to,
            'rollback_reason': reason
        })
        
        audit_record = AutomationAudit(
            automation_id=automation_id,
            action='rolled_back',
            yaml_snapshot=yaml_content,
            user=user,
            source='rollback',
            reason=reason,
            metadata=metadata,
            timestamp=datetime.utcnow()
        )
        
        db.add(audit_record)
        await db.commit()
        await db.refresh(audit_record)
        
        logger.info(
            f"Audit: recorded rollback of {automation_id} "
            f"to version {rolled_back_to} by {user}"
        )
        return audit_record
    
    @staticmethod
    async def get_history(
        db: AsyncSession,
        automation_id: str,
        limit: int = 50
    ) -> List[AutomationAudit]:
        """
        Get audit history for specific automation.
        
        Returns most recent changes first.
        """
        query = (
            select(AutomationAudit)
            .where(AutomationAudit.automation_id == automation_id)
            .order_by(AutomationAudit.timestamp.desc())
            .limit(limit)
        )
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_all_audits(
        db: AsyncSession,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AutomationAudit]:
        """
        Get audit records with optional filtering.
        
        Args:
            db: Database session
            action: Filter by action type (created, deleted, rolled_back)
            start_date: Filter by date range start
            end_date: Filter by date range end
            limit: Maximum records to return
        
        Returns:
            List of audit records (most recent first)
        """
        query = select(AutomationAudit)
        
        # Apply filters
        conditions = []
        if action:
            conditions.append(AutomationAudit.action == action)
        if start_date:
            conditions.append(AutomationAudit.timestamp >= start_date)
        if end_date:
            conditions.append(AutomationAudit.timestamp <= end_date)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(AutomationAudit.timestamp.desc()).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    @staticmethod
    async def get_previous_version(
        db: AsyncSession,
        automation_id: str
    ) -> Optional[AutomationAudit]:
        """
        Get the most recent non-deletion audit record for rollback.
        
        Returns:
            Previous version audit record, or None if no history
        """
        query = (
            select(AutomationAudit)
            .where(
                and_(
                    AutomationAudit.automation_id == automation_id,
                    AutomationAudit.action.in_(['created', 'modified', 'rolled_back'])
                )
            )
            .order_by(AutomationAudit.timestamp.desc())
            .limit(2)  # Get last 2 to skip current version
        )
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Return second most recent (first is current)
        return records[1] if len(records) > 1 else None
    
    @staticmethod
    async def cleanup_old_audits(
        db: AsyncSession,
        retention_days: int = 90
    ) -> int:
        """
        Clean up audit records older than retention period.
        
        Note: This should be run periodically (e.g., monthly)
        
        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
        
        query = select(AutomationAudit).where(
            AutomationAudit.timestamp < cutoff_date
        )
        
        result = await db.execute(query)
        old_records = result.scalars().all()
        
        count = len(old_records)
        
        for record in old_records:
            await db.delete(record)
        
        await db.commit()
        
        logger.info(f"Audit cleanup: removed {count} records older than {retention_days} days")
        return count
```

### Rollback Endpoint

**Update: services/ai-automation-service/src/api/deployment.py**

```python
from src.audit_service import AuditService
from src.safety_validator import SafetyValidator

@router.post("/{automation_id}/rollback")
async def rollback_automation(
    automation_id: str,
    reason: str,
    user: str = "system",  # TODO: Get from auth
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    safety_validator: SafetyValidator = Depends(get_safety_validator),
    db: AsyncSession = Depends(get_db)
):
    """
    Rollback automation to previous version.
    
    Workflow:
    1. Get previous version from audit trail
    2. Validate safety of previous version
    3. Deploy previous version to HA
    4. Record rollback in audit trail
    
    Args:
        automation_id: HA automation ID to rollback
        reason: Reason for rollback
        user: User requesting rollback
    
    Returns:
        Rollback result with new automation state
    """
    
    # 1. Get previous version
    previous_version = await AuditService.get_previous_version(db, automation_id)
    
    if not previous_version:
        raise HTTPException(
            status_code=404,
            detail="No previous version found for rollback"
        )
    
    logger.info(
        f"Rolling back {automation_id} to version from "
        f"{previous_version.timestamp} (audit ID: {previous_version.id})"
    )
    
    # 2. Validate safety of previous version
    existing_automations = await ha_client.get_automations()
    safety_result = await safety_validator.validate(
        previous_version.yaml_snapshot,
        existing_automations
    )
    
    if not safety_result.passed:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Previous version fails current safety checks",
                "safety_score": safety_result.safety_score,
                "issues": [
                    {
                        "rule": issue.rule,
                        "severity": issue.severity,
                        "message": issue.message
                    }
                    for issue in safety_result.issues
                ],
                "summary": safety_result.summary,
                "note": "Safety standards may have changed since original deployment"
            }
        )
    
    # 3. Get current version before overwriting (for audit)
    current_automations = await ha_client.get_automations()
    current_automation = next(
        (a for a in current_automations if a.get('id') == automation_id),
        None
    )
    
    if not current_automation:
        raise HTTPException(
            status_code=404,
            detail=f"Automation {automation_id} not found in Home Assistant"
        )
    
    current_yaml = yaml.dump(current_automation)
    
    # 4. Deploy previous version to HA
    try:
        automation_dict = yaml.safe_load(previous_version.yaml_snapshot)
        await ha_client.update_automation(automation_id, automation_dict)
    except Exception as e:
        logger.error(f"Rollback deployment failed for {automation_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to deploy previous version: {e}"
        )
    
    # 5. Record rollback in audit trail
    await AuditService.record_rollback(
        db,
        automation_id=automation_id,
        yaml_content=current_yaml,  # Store what we're rolling back FROM
        user=user,
        reason=reason,
        rolled_back_to=previous_version.id
    )
    
    logger.info(f"Successfully rolled back {automation_id} by {user}")
    
    return {
        "success": True,
        "automation_id": automation_id,
        "rolled_back_to": previous_version.timestamp.isoformat(),
        "rolled_back_from": datetime.utcnow().isoformat(),
        "reason": reason,
        "safety_score": safety_result.safety_score
    }


@router.get("/{automation_id}/history")
async def get_automation_history(
    automation_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete audit history for automation.
    
    Returns chronological list of all changes.
    """
    history = await AuditService.get_history(db, automation_id, limit)
    
    return {
        "automation_id": automation_id,
        "history": [
            {
                "id": record.id,
                "action": record.action,
                "timestamp": record.timestamp.isoformat(),
                "user": record.user,
                "source": record.source,
                "reason": record.reason,
                "safety_score": record.safety_score,
                "yaml_preview": record.yaml_snapshot[:200] + "..." 
                    if len(record.yaml_snapshot) > 200 else record.yaml_snapshot
            }
            for record in history
        ],
        "total_changes": len(history)
    }


@router.get("/audit/all")
async def get_all_audit_logs(
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get audit logs with optional filtering.
    
    Query params:
        action: Filter by action (created, deleted, rolled_back)
        start_date: ISO format date (2025-01-01)
        end_date: ISO format date (2025-12-31)
        limit: Max records (default 100)
    """
    # Parse dates
    start_dt = datetime.fromisoformat(start_date) if start_date else None
    end_dt = datetime.fromisoformat(end_date) if end_date else None
    
    audits = await AuditService.get_all_audits(
        db,
        action=action,
        start_date=start_dt,
        end_date=end_dt,
        limit=limit
    )
    
    return {
        "audits": [
            {
                "id": record.id,
                "automation_id": record.automation_id,
                "action": record.action,
                "timestamp": record.timestamp.isoformat(),
                "user": record.user,
                "source": record.source,
                "reason": record.reason,
                "safety_score": record.safety_score
            }
            for record in audits
        ],
        "total": len(audits),
        "filters": {
            "action": action,
            "start_date": start_date,
            "end_date": end_date
        }
    }
```

### Update Deployment to Record Audit

**Update: services/ai-automation-service/src/api/deployment.py (deploy_automation)**

```python
# Add after successful deployment
await AuditService.record_deployment(
    db,
    automation_id=ha_automation_id,
    yaml_content=suggestion.automation_yaml,
    user=user,  # TODO: Get from auth context
    suggestion_id=suggestion_id,
    safety_score=safety_result.safety_score
)
```

---

## Integration Verification

**IV1: Audit trail records all actions**
- Deploy automation → verify audit record created
- Delete automation → verify audit record created
- Rollback → verify audit record created

**IV2: Rollback restores previous version**
- Deploy version 1
- Modify to version 2
- Rollback → verify version 1 restored in HA
- Check audit shows rollback action

**IV3: Audit queries performant**
- Insert 1000 audit records
- Query by automation_id → verify <100ms
- Query by date range → verify <100ms
- Query all audits → verify <200ms

**IV4: Immutability enforced**
- Attempt to modify audit record → verify rejected
- Attempt to delete audit record → verify rejected
- Only append operations allowed

**IV5: Rollback validates safety**
- Create automation that later fails safety checks
- Attempt rollback → verify blocked with clear message

---

## Tasks Breakdown

1. **Create AutomationAudit model** (1 hour)
2. **Create Alembic migration** (0.5 hours)
3. **Implement AuditService class** (1.5 hours)
4. **Create rollback endpoint** (1.5 hours)
5. **Create audit history endpoints** (1 hour)
6. **Integrate audit recording with deployment** (0.5 hours)
7. **Unit tests for AuditService** (1 hour)
8. **Integration test for rollback** (1 hour)

**Total:** 6-8 hours

---

## Definition of Done

- [ ] AutomationAudit model created
- [ ] Alembic migration for audit table
- [ ] AuditService implemented with all methods
- [ ] Rollback endpoint functional
- [ ] Audit history endpoints created
- [ ] Audit recording integrated with deployment
- [ ] Database indexes created for performance
- [ ] Unit tests >80% coverage
- [ ] Integration test for complete rollback flow
- [ ] Query performance <100ms verified
- [ ] Immutability enforced
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

## Testing Strategy

### Unit Tests

```python
# tests/test_audit_service.py
import pytest
from src.audit_service import AuditService
from src.database.models import AutomationAudit

async def test_record_deployment():
    """Test audit record created on deployment"""
    audit = await AuditService.record_deployment(
        db,
        automation_id="test_auto_1",
        yaml_content="alias: Test\n...",
        user="test_user",
        safety_score=95
    )
    
    assert audit.action == "created"
    assert audit.automation_id == "test_auto_1"
    assert audit.user == "test_user"
    assert audit.safety_score == 95

async def test_get_history():
    """Test retrieving audit history"""
    # Create 3 audit records
    await AuditService.record_deployment(db, "auto_1", "v1", "user")
    await AuditService.record_deployment(db, "auto_1", "v2", "user")
    await AuditService.record_deletion(db, "auto_1", "v2", "user")
    
    history = await AuditService.get_history(db, "auto_1")
    
    assert len(history) == 3
    assert history[0].action == "deleted"  # Most recent first
    assert history[2].action == "created"

async def test_get_previous_version():
    """Test getting previous version for rollback"""
    # Deploy v1
    audit1 = await AuditService.record_deployment(db, "auto_1", "v1", "user")
    # Deploy v2
    await AuditService.record_deployment(db, "auto_1", "v2", "user")
    
    previous = await AuditService.get_previous_version(db, "auto_1")
    
    assert previous.id == audit1.id
    assert previous.yaml_snapshot == "v1"

async def test_audit_immutability():
    """Test that audit records cannot be modified"""
    audit = await AuditService.record_deployment(db, "auto_1", "v1", "user")
    
    # Attempt to modify
    audit.user = "hacker"
    
    # Refresh from DB
    await db.refresh(audit)
    
    # Should still be original user
    assert audit.user == "user"
```

### Integration Tests

```python
# tests/test_rollback_flow.py
async def test_complete_rollback_flow():
    """Test end-to-end rollback"""
    # 1. Deploy initial version
    response1 = client.post("/api/deploy/1")
    automation_id = response1.json()["ha_automation_id"]
    
    # 2. Modify automation in HA (simulated)
    # ... modify logic ...
    
    # 3. Rollback
    response2 = client.post(
        f"/api/deploy/{automation_id}/rollback",
        json={"reason": "Misbehaving", "user": "test_user"}
    )
    
    assert response2.status_code == 200
    assert "rolled_back_to" in response2.json()
    
    # 4. Verify audit trail
    response3 = client.get(f"/api/deploy/{automation_id}/history")
    history = response3.json()["history"]
    
    assert len(history) >= 2
    assert history[0]["action"] == "rolled_back"
    assert history[1]["action"] == "created"
```

---

## Reference Files

**Copy patterns from:**
- Story AI1.11 (HA Integration) for deployment flow
- Story AI1.19 (Safety Validation) for validation integration
- `services/data-api/src/models/` for SQLAlchemy model patterns
- `services/data-api/alembic/` for migration patterns

---

## Notes

- Audit trail is **append-only** - never modify or delete records
- Store complete YAML snapshots (not diffs) for simplicity
- Rollback validates against **current** safety rules (may block old automations)
- Cleanup task should run monthly via cron or scheduled task
- Consider adding audit log export for compliance (CSV/JSON)
- Future enhancement: Compare YAML diffs between versions
- Future enhancement: Batch rollback multiple automations

---

**Story Status:** Ready for Development  
**Assigned To:** TBD  
**Created:** 2025-10-16  
**Updated:** 2025-10-16

