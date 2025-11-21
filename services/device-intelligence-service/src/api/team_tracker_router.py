"""
Team Tracker Integration API Router

Provides endpoints for managing Team Tracker integration,
team configuration, and entity detection.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db_session
from ..models.database import DeviceEntity, TeamTrackerIntegration, TeamTrackerTeam

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/team-tracker", tags=["Team Tracker"])


# Pydantic Models
class TeamTrackerStatus(BaseModel):
    """Team Tracker integration status response"""
    is_installed: bool
    installation_status: str  # not_installed, detected, configured
    version: str | None = None
    last_checked: datetime
    configured_teams_count: int
    active_teams_count: int


class TeamConfiguration(BaseModel):
    """Team configuration request/response"""
    team_id: str  # Team abbreviation
    league_id: str  # NFL, NBA, MLB, etc.
    team_name: str
    team_long_name: str | None = None
    entity_id: str | None = None
    sensor_name: str | None = None
    is_active: bool = True
    sport: str | None = None
    user_notes: str | None = None
    priority: int = 0


class TeamResponse(BaseModel):
    """Team response with full details"""
    id: int
    team_id: str
    league_id: str
    team_name: str
    team_long_name: str | None
    entity_id: str | None
    sensor_name: str | None
    is_active: bool
    sport: str | None
    team_abbreviation: str | None
    team_logo: str | None
    league_logo: str | None
    configured_in_ha: bool
    last_detected: datetime | None
    user_notes: str | None
    priority: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DetectedTeamSensor(BaseModel):
    """Detected Team Tracker sensor entity"""
    entity_id: str
    name: str | None
    platform: str
    domain: str
    unique_id: str


# API Endpoints

@router.get("/status", response_model=TeamTrackerStatus)
async def get_team_tracker_status(
    session: AsyncSession = Depends(get_db_session),
) -> TeamTrackerStatus:
    """
    Get Team Tracker integration status.

    Returns installation status, configured teams count, and last check time.
    """
    logger.info("📊 Fetching Team Tracker integration status")

    # Get or create integration status
    result = await session.execute(
        select(TeamTrackerIntegration).limit(1),
    )
    integration = result.scalar_one_or_none()

    if not integration:
        # Create default status
        integration = TeamTrackerIntegration(
            is_installed=False,
            installation_status="not_installed",
            last_checked=datetime.now(timezone.utc),
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)

    # Count configured teams
    total_teams_result = await session.execute(
        select(TeamTrackerTeam),
    )
    total_teams = len(total_teams_result.scalars().all())

    # Count active teams
    active_teams_result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.is_active),
    )
    active_teams = len(active_teams_result.scalars().all())

    return TeamTrackerStatus(
        is_installed=integration.is_installed,
        installation_status=integration.installation_status,
        version=integration.version,
        last_checked=integration.last_checked,
        configured_teams_count=total_teams,
        active_teams_count=active_teams,
    )


@router.post("/detect")
async def detect_team_tracker_entities(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Detect Team Tracker sensor entities from Home Assistant.

    Scans for sensor entities with platform 'teamtracker' and updates
    the integration status and team configurations.
    """
    logger.info("🔍 Detecting Team Tracker entities")

    # Query for teamtracker entities
    result = await session.execute(
        select(DeviceEntity).where(DeviceEntity.platform == "teamtracker"),
    )
    team_sensors = result.scalars().all()

    logger.info(f"Found {len(team_sensors)} Team Tracker sensors")

    # Update integration status
    integration_result = await session.execute(
        select(TeamTrackerIntegration).limit(1),
    )
    integration = integration_result.scalar_one_or_none()

    if not integration:
        integration = TeamTrackerIntegration()
        session.add(integration)

    integration.is_installed = len(team_sensors) > 0
    integration.installation_status = "detected" if len(team_sensors) > 0 else "not_installed"
    integration.last_checked = datetime.now(timezone.utc)

    detected_teams = []

    # Process each detected sensor
    for sensor in team_sensors:
        # Check if team already exists
        existing_team_result = await session.execute(
            select(TeamTrackerTeam).where(TeamTrackerTeam.entity_id == sensor.entity_id),
        )
        existing_team = existing_team_result.scalar_one_or_none()

        if existing_team:
            # Update existing team
            existing_team.configured_in_ha = True
            existing_team.last_detected = datetime.now(timezone.utc)
            logger.info(f"Updated existing team: {sensor.entity_id}")
        else:
            # Create new team entry (with minimal info from entity)
            # Note: Full team details would come from HA state attributes
            new_team = TeamTrackerTeam(
                team_id=sensor.unique_id,  # Placeholder, will be updated from state
                league_id="UNKNOWN",  # Will be updated from state attributes
                team_name=sensor.name or sensor.entity_id,
                entity_id=sensor.entity_id,
                sensor_name=sensor.name,
                configured_in_ha=True,
                last_detected=datetime.now(timezone.utc),
                is_active=True,
            )
            session.add(new_team)
            logger.info(f"Created new team entry: {sensor.entity_id}")

        detected_teams.append({
            "entity_id": sensor.entity_id,
            "name": sensor.name,
            "unique_id": sensor.unique_id,
        })

    await session.commit()

    return {
        "detected_count": len(team_sensors),
        "detected_teams": detected_teams,
        "integration_status": integration.installation_status,
    }


@router.get("/teams", response_model=list[TeamResponse])
async def get_configured_teams(
    active_only: bool = False,
    session: AsyncSession = Depends(get_db_session),
) -> list[TeamResponse]:
    """
    Get all configured Team Tracker teams.

    Args:
        active_only: If True, only return active teams

    Returns:
        List of configured teams
    """
    logger.info(f"📋 Fetching configured teams (active_only={active_only})")

    query = select(TeamTrackerTeam)
    if active_only:
        query = query.where(TeamTrackerTeam.is_active)

    query = query.order_by(TeamTrackerTeam.priority.desc(), TeamTrackerTeam.team_name)

    result = await session.execute(query)
    teams = result.scalars().all()

    return [TeamResponse.model_validate(team) for team in teams]


@router.post("/teams", response_model=TeamResponse)
async def add_team(
    team_config: TeamConfiguration,
    session: AsyncSession = Depends(get_db_session),
) -> TeamResponse:
    """
    Add a new Team Tracker team configuration.

    This allows users to pre-configure teams they want to track,
    even if they haven't set them up in Home Assistant yet.
    """
    logger.info(f"➕ Adding team: {team_config.team_name} ({team_config.league_id})")

    # Check if team already exists
    if team_config.entity_id:
        existing_result = await session.execute(
            select(TeamTrackerTeam).where(TeamTrackerTeam.entity_id == team_config.entity_id),
        )
        if existing_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Team with this entity_id already exists")

    # Create new team
    new_team = TeamTrackerTeam(
        team_id=team_config.team_id,
        league_id=team_config.league_id,
        team_name=team_config.team_name,
        team_long_name=team_config.team_long_name,
        entity_id=team_config.entity_id,
        sensor_name=team_config.sensor_name,
        is_active=team_config.is_active,
        sport=team_config.sport,
        user_notes=team_config.user_notes,
        priority=team_config.priority,
        configured_in_ha=False,  # Will be updated by detection
    )

    session.add(new_team)
    await session.commit()
    await session.refresh(new_team)

    logger.info(f"✅ Team added successfully: {new_team.id}")

    return TeamResponse.model_validate(new_team)


@router.put("/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int,
    team_config: TeamConfiguration,
    session: AsyncSession = Depends(get_db_session),
) -> TeamResponse:
    """
    Update an existing Team Tracker team configuration.
    """
    logger.info(f"✏️ Updating team: {team_id}")

    result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.id == team_id),
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Update fields
    team.team_id = team_config.team_id
    team.league_id = team_config.league_id
    team.team_name = team_config.team_name
    team.team_long_name = team_config.team_long_name
    team.entity_id = team_config.entity_id
    team.sensor_name = team_config.sensor_name
    team.is_active = team_config.is_active
    team.sport = team_config.sport
    team.user_notes = team_config.user_notes
    team.priority = team_config.priority

    await session.commit()
    await session.refresh(team)

    logger.info(f"✅ Team updated successfully: {team.id}")

    return TeamResponse.model_validate(team)


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: int,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Delete a Team Tracker team configuration.
    """
    logger.info(f"🗑️ Deleting team: {team_id}")

    result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.id == team_id),
    )
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    await session.delete(team)
    await session.commit()

    logger.info(f"✅ Team deleted successfully: {team_id}")

    return {"message": "Team deleted successfully"}


@router.post("/sync-from-ha")
async def sync_teams_from_ha(
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """
    Sync team configurations from Home Assistant state attributes.

    This fetches the current state and attributes of all detected Team Tracker
    sensors and updates our database with the latest information.
    """
    logger.info("🔄 Syncing teams from Home Assistant")

    # First detect entities
    detection_result = await detect_team_tracker_entities(session=session)

    # TODO: Implement HA state fetching to get full team attributes
    # This would require calling the HA API to get state + attributes for each sensor
    # For now, we just return the detection results

    return {
        "synced": True,
        "detected_count": detection_result["detected_count"],
        "message": "Teams synchronized from Home Assistant",
    }
