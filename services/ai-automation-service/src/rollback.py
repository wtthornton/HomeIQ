"""
Simple Rollback Functionality
Story AI1.20: Simple Rollback

Provides version history (last 3 versions) and rollback capability.
Simplified for single-home use case - no complex audit, just undo functionality.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .clients.ha_client import HomeAssistantClient
from .database.models import AutomationVersion
from .safety_validator import SafetyResult, SafetyValidator

logger = logging.getLogger(__name__)


async def store_version(
    db: AsyncSession,
    automation_id: str,
    yaml_content: str,
    safety_score: int,
) -> AutomationVersion:
    """
    Store automation version.
    Automatically keeps only last 3 versions per automation.

    Args:
        db: Database session
        automation_id: HA automation ID
        yaml_content: Complete YAML content
        safety_score: Safety validation score (0-100)

    Returns:
        Created version record
    """
    # Create new version
    version = AutomationVersion(
        automation_id=automation_id,
        yaml_content=yaml_content,
        deployed_at=datetime.utcnow(),
        safety_score=safety_score,
    )
    db.add(version)
    await db.commit()
    await db.refresh(version)

    logger.info(f"📝 Stored version for {automation_id} (score: {safety_score})")

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
        logger.info(f"🧹 Cleaned up old versions for {automation_id}, kept last 3")

    return version


async def get_versions(
    db: AsyncSession,
    automation_id: str,
) -> list[AutomationVersion]:
    """
    Get version history for automation.

    Args:
        db: Database session
        automation_id: HA automation ID

    Returns:
        List of versions (most recent first, max 3)
    """
    query = (
        select(AutomationVersion)
        .where(AutomationVersion.automation_id == automation_id)
        .order_by(AutomationVersion.deployed_at.desc())
        .limit(3)
    )
    result = await db.execute(query)
    versions = result.scalars().all()

    logger.debug(f"Found {len(versions)} versions for {automation_id}")
    return versions


async def rollback_to_previous(
    db: AsyncSession,
    automation_id: str,
    ha_client: HomeAssistantClient,
    safety_validator: SafetyValidator,
) -> dict:
    """
    Rollback automation to previous version.
    Simple: just restores the last version with safety check.

    Args:
        db: Database session
        automation_id: HA automation ID to rollback
        ha_client: HA API client
        safety_validator: Safety validator instance

    Returns:
        Result dict with success status and details

    Raises:
        ValueError: If no previous version or safety validation fails
    """
    # Get version history
    versions = await get_versions(db, automation_id)

    if len(versions) < 2:
        msg = (
            f"No previous version available for {automation_id}. "
            "Need at least 2 versions to rollback."
        )
        raise ValueError(
            msg,
        )

    # Previous version is index 1 (0 is current)
    previous_version = versions[1]

    logger.info(
        f"⏪ Rolling back {automation_id} to version from "
        f"{previous_version.deployed_at.isoformat()}",
    )

    # Validate safety of previous version
    safety_result: SafetyResult = await safety_validator.validate(
        previous_version.yaml_content,
    )

    if not safety_result.passed:
        error_msg = (
            f"Previous version fails current safety checks (score: {safety_result.safety_score}/100). "
            f"Safety standards may have changed since original deployment. "
            f"Issues: {safety_result.summary}"
        )
        logger.error(f"❌ Rollback blocked: {error_msg}")
        raise ValueError(error_msg)

    logger.info(
        f"✅ Previous version passes safety (score: {safety_result.safety_score})",
    )

    # Deploy previous version to HA
    deployment_result = await ha_client.deploy_automation(
        automation_yaml=previous_version.yaml_content,
        automation_id=automation_id,
    )

    if not deployment_result.get("success"):
        error = deployment_result.get("error", "Unknown error")
        msg = f"Failed to deploy previous version: {error}"
        raise ValueError(msg)

    # Store this rollback as new version (creates audit trail)
    await store_version(
        db,
        automation_id,
        previous_version.yaml_content,
        safety_result.safety_score,
    )

    logger.info(f"✅ Successfully rolled back {automation_id}")

    return {
        "success": True,
        "automation_id": automation_id,
        "rolled_back_to": previous_version.deployed_at.isoformat(),
        "rolled_back_at": datetime.utcnow().isoformat(),
        "safety_score": safety_result.safety_score,
        "previous_version_id": previous_version.id,
    }


async def get_latest_version(
    db: AsyncSession,
    automation_id: str,
) -> AutomationVersion | None:
    """
    Get the most recent version for an automation.

    Args:
        db: Database session
        automation_id: HA automation ID

    Returns:
        Latest version or None if not found
    """
    query = (
        select(AutomationVersion)
        .where(AutomationVersion.automation_id == automation_id)
        .order_by(AutomationVersion.deployed_at.desc())
        .limit(1)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

