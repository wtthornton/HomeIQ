"""
Unit tests for Simple Rollback Functionality
Story AI1.20: Simple Rollback
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.models import Base
from src.rollback import get_versions, rollback_to_previous, store_version


class TestRollbackFunctions:
    """Test suite for rollback functionality"""

    @pytest.mark.asyncio
    async def test_store_version(self, db_session):
        """Test storing a version"""
        # Store version
        version = await store_version(
            db_session,
            automation_id="automation.test_1",
            yaml_content="alias: Test\ntrigger: []\naction: []",
            safety_score=95,
        )

        assert version.id is not None
        assert version.automation_id == "automation.test_1"
        assert version.safety_score == 95
        assert "alias: Test" in version.yaml_content

    @pytest.mark.asyncio
    async def test_get_versions(self, db_session):
        """Test retrieving version history"""
        # Store 2 versions
        await store_version(db_session, "automation.test_1", "yaml_v1", 90)
        await store_version(db_session, "automation.test_1", "yaml_v2", 85)

        # Get versions
        versions = await get_versions(db_session, "automation.test_1")

        assert len(versions) == 2
        assert versions[0].yaml_content == "yaml_v2"  # Most recent first
        assert versions[1].yaml_content == "yaml_v1"

    @pytest.mark.asyncio
    async def test_keeps_last_3_versions_only(self, db_session):
        """Test that only last 3 versions are kept"""
        automation_id = "automation.test_cleanup"

        # Store 5 versions
        for i in range(5):
            await store_version(db_session, automation_id, f"yaml_v{i}", 90)

        # Get versions
        versions = await get_versions(db_session, automation_id)

        # Should only have last 3
        assert len(versions) == 3
        assert versions[0].yaml_content == "yaml_v4"  # Most recent
        assert versions[1].yaml_content == "yaml_v3"
        assert versions[2].yaml_content == "yaml_v2"
        # v0 and v1 should be deleted

    @pytest.mark.asyncio
    async def test_rollback_to_previous_success(self, db_session):
        """Test successful rollback to previous version"""
        automation_id = "automation.test_rollback"

        # Store 2 versions
        await store_version(db_session, automation_id, "yaml_v1", 95)
        await store_version(db_session, automation_id, "yaml_v2", 90)

        # Mock HA client and safety validator
        ha_client = AsyncMock()
        ha_client.deploy_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": automation_id,
        })

        safety_validator = AsyncMock()
        safety_validator.validate = AsyncMock(return_value=MagicMock(
            passed=True,
            safety_score=95,
            issues=[],
            summary="✅ Passed",
        ))

        # Rollback
        result = await rollback_to_previous(
            db_session,
            automation_id,
            ha_client,
            safety_validator,
        )

        assert result["success"] is True
        assert result["automation_id"] == automation_id
        assert result["safety_score"] == 95

        # Verify HA client was called with previous version
        ha_client.deploy_automation.assert_called_once()
        call_args = ha_client.deploy_automation.call_args
        assert "yaml_v1" in call_args.kwargs["automation_yaml"]

    @pytest.mark.asyncio
    async def test_rollback_fails_if_no_previous_version(self, db_session):
        """Test rollback fails when only 1 version exists"""
        automation_id = "automation.test_only_one"

        # Store only 1 version
        await store_version(db_session, automation_id, "yaml_v1", 95)

        # Mock dependencies
        ha_client = AsyncMock()
        safety_validator = AsyncMock()

        # Attempt rollback
        with pytest.raises(ValueError, match="No previous version available"):
            await rollback_to_previous(
                db_session,
                automation_id,
                ha_client,
                safety_validator,
            )

    @pytest.mark.asyncio
    async def test_rollback_fails_if_previous_unsafe(self, db_session):
        """Test rollback blocked if previous version fails safety"""
        automation_id = "automation.test_unsafe_rollback"

        # Store 2 versions
        await store_version(db_session, automation_id, "yaml_unsafe", 40)  # Low score
        await store_version(db_session, automation_id, "yaml_safe", 95)

        # Mock HA client
        ha_client = AsyncMock()

        # Mock safety validator to fail
        safety_validator = AsyncMock()
        safety_validator.validate = AsyncMock(return_value=MagicMock(
            passed=False,
            safety_score=40,
            issues=[],
            summary="❌ Failed",
        ))

        # Attempt rollback
        with pytest.raises(ValueError, match="fails current safety checks"):
            await rollback_to_previous(
                db_session,
                automation_id,
                ha_client,
                safety_validator,
            )

    @pytest.mark.asyncio
    async def test_rollback_creates_new_version(self, db_session):
        """Test that rollback creates a new version record"""
        automation_id = "automation.test_version_creation"

        # Store 2 versions
        await store_version(db_session, automation_id, "yaml_v1", 95)
        await store_version(db_session, automation_id, "yaml_v2", 90)

        # Mock dependencies (success)
        ha_client = AsyncMock()
        ha_client.deploy_automation = AsyncMock(return_value={
            "success": True,
            "automation_id": automation_id,
        })

        safety_validator = AsyncMock()
        safety_validator.validate = AsyncMock(return_value=MagicMock(
            passed=True,
            safety_score=95,
            issues=[],
        ))

        # Rollback
        await rollback_to_previous(db_session, automation_id, ha_client, safety_validator)

        # Get versions - should now have 3 (original 2 + rollback)
        versions = await get_versions(db_session, automation_id)

        # Will have 3: v2 (current), v1 (previous), v1 (rollback copy)
        assert len(versions) == 3


# Fixtures for testing
@pytest_asyncio.fixture
async def db_engine():
    """Create in-memory SQLite database engine for testing"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create database session for testing"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

