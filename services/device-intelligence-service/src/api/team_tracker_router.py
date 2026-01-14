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
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
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
    session: AsyncSession = Depends(get_db_session)
) -> TeamTrackerStatus:
    """
    Get Team Tracker integration status.

    Returns installation status, configured teams count, and last check time.
    """
    logger.info("📊 Fetching Team Tracker integration status")

    # Get or create integration status
    result = await session.execute(
        select(TeamTrackerIntegration).limit(1)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        # Create default status
        integration = TeamTrackerIntegration(
            is_installed=False,
            installation_status="not_installed",
            last_checked=datetime.now(timezone.utc)
        )
        session.add(integration)
        await session.commit()
        await session.refresh(integration)

    # Count configured teams
    total_teams_result = await session.execute(
        select(TeamTrackerTeam)
    )
    total_teams = len(total_teams_result.scalars().all())

    # Count active teams
    active_teams_result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.is_active == True)
    )
    active_teams = len(active_teams_result.scalars().all())

    return TeamTrackerStatus(
        is_installed=integration.is_installed,
        installation_status=integration.installation_status,
        version=integration.version,
        last_checked=integration.last_checked,
        configured_teams_count=total_teams,
        active_teams_count=active_teams
    )


@router.post("/detect")
async def detect_team_tracker_entities(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Detect Team Tracker sensor entities from Home Assistant.

    Scans for sensor entities with multiple platform value variations and
    entity_id patterns, then updates the integration status and team configurations.
    
    Uses data-api service to query entities (where they are actually stored).
    """
    try:
        logger.info("🔍 Detecting Team Tracker entities")

        # Try multiple platform value variations
        platform_variations = ["teamtracker", "team_tracker", "TeamTracker", "TEAMTRACKER", "team-tracker"]
        logger.debug(f"Searching for Team Tracker entities with platform variations: {platform_variations}")

        # Query entities from data-api (where they are actually stored)
        data_api_client = DataAPIClient()
        team_sensors = []
        data_api_error = None
        
        try:
            logger.info(f"Querying data-api at {data_api_client.base_url} for sensor entities...")
            # Fetch all sensor entities from data-api
            all_sensor_entities = await data_api_client.fetch_entities(
                domain="sensor",
                limit=10000
            )
            
            logger.info(f"Received {len(all_sensor_entities)} sensor entities from data-api")
            
            # Filter for Team Tracker entities using multiple strategies
            # NOTE: Platform matching is PRIMARY and works for ANY team configuration.
            # Team Tracker always uses platform="teamtracker" regardless of:
            # - Team selection (any league: NFL, NBA, MLB, etc.)
            # - Team abbreviation (any team: DAL, VGK, MSU, LAL, etc.)
            # - Custom entity name (users can set custom "name" parameter)
            # Entity ID patterns are FALLBACK for edge cases where platform might be missing.
            for entity in all_sensor_entities:
                entity_id = entity.get("entity_id", "").lower()
                platform = entity.get("platform", "").lower() if entity.get("platform") else ""
                original_entity_id = entity.get("entity_id", "")  # Keep original case for logging
                
                # PRIMARY: Check platform field (works for ANY team/league/name configuration)
                # Team Tracker integration always sets platform="teamtracker" in YAML config
                platform_match = (
                    platform in [p.lower() for p in platform_variations] or
                    ("team" in platform and "tracker" in platform)
                )
                
                # FALLBACK: Check entity_id patterns (catches edge cases where platform might be missing)
                # Entity IDs can vary based on custom "name" parameter:
                # - name="Cowboys" → sensor.cowboys (no "team_tracker" in ID, but platform match works)
                # - name="Spartan Football" → sensor.spartan_football (no "team_tracker" in ID, but platform match works)
                # - No name → sensor.dal_team_tracker (has "team_tracker" in ID)
                # - Default → sensor.team_tracker_cowboys (has "team_tracker" in ID)
                entity_id_match = (
                    "team_tracker" in entity_id or  # Matches any entity with team_tracker (dal_team_tracker, vgk_team_tracker, etc.)
                    "teamtracker" in entity_id or   # Matches teamtracker_* variations
                    entity_id.endswith("_team_tracker") or  # Exact suffix match (any_prefix_team_tracker)
                    entity_id.startswith("sensor.team_tracker") or  # Starts with team_tracker
                    entity_id.startswith("sensor.teamtracker")  # Starts with teamtracker
                )
                
                # Match if platform OR entity_id indicates Team Tracker
                # Platform match is sufficient for any team configuration
                if platform_match or entity_id_match:
                    team_sensors.append(entity)
                    logger.info(
                        f"✅ Team Tracker entity detected: entity_id={original_entity_id}, "
                        f"platform={entity.get('platform')}, name={entity.get('friendly_name') or entity.get('name')}"
                    )
            
            logger.info(f"Found {len(team_sensors)} Team Tracker sensors from data-api")
        except Exception as e:
            data_api_error = str(e)
            logger.error(f"❌ Failed to query data-api: {e}", exc_info=True)
            logger.warning(f"Falling back to local database query...")
            # Fallback to local database query - use flexible pattern matching
            conditions = [
                DeviceEntity.domain == "sensor",
                or_(
                    DeviceEntity.platform.in_(platform_variations),
                    DeviceEntity.platform.ilike("%team%tracker%"),
                    # Flexible entity_id matching - matches dal_team_tracker, vgk_team_tracker, team_tracker_*, etc.
                    DeviceEntity.entity_id.ilike("%team_tracker%"),  # Matches any entity_id containing team_tracker
                    DeviceEntity.entity_id.ilike("%teamtracker%"),   # Matches any entity_id containing teamtracker
                    DeviceEntity.entity_id.like("%_team_tracker"),    # Matches entities ending with _team_tracker
                    DeviceEntity.entity_id.like("sensor.team_tracker%"),  # Matches sensor.team_tracker*
                    DeviceEntity.entity_id.like("sensor.teamtracker%")    # Matches sensor.teamtracker*
                )
            ]
            result = await session.execute(
                select(DeviceEntity).where(*conditions)
            )
            local_entities = result.scalars().all()
            # Convert DeviceEntity objects to dict format
            team_sensors = [
                {
                    "entity_id": e.entity_id,
                    "platform": e.platform,
                    "domain": e.domain,
                    "name": e.name,
                    "friendly_name": e.name,
                    "unique_id": e.unique_id
                }
                for e in local_entities
            ]
            logger.info(f"Found {len(team_sensors)} Team Tracker sensors from local database")
        finally:
            await data_api_client.close()
        
        # Log details of detected entities for debugging
        if not team_sensors:
            logger.warning("⚠️ No Team Tracker entities found.")
            if data_api_error:
                logger.warning(f"Data-api query failed: {data_api_error}")
            # Try to get debug info from data-api
            try:
                debug_client = DataAPIClient()
                all_sensors = await debug_client.fetch_entities(domain="sensor", limit=1000)
                platforms = {}
                for sensor in all_sensors:
                    platform = sensor.get("platform", "unknown")
                    platforms[platform] = platforms.get(platform, 0) + 1
                logger.info(f"📊 Available sensor platforms in data-api: {platforms}")
                await debug_client.close()
            except Exception as e:
                logger.warning(f"Could not get platform debug info: {e}")

        # Update integration status
        integration_result = await session.execute(
            select(TeamTrackerIntegration).limit(1)
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
            try:
                entity_id = sensor.get("entity_id") if isinstance(sensor, dict) else sensor.entity_id
                sensor_name = sensor.get("friendly_name") or sensor.get("name") if isinstance(sensor, dict) else sensor.name
                unique_id = sensor.get("unique_id") if isinstance(sensor, dict) else sensor.unique_id
                platform = sensor.get("platform") if isinstance(sensor, dict) else sensor.platform
                
                # Check if team already exists
                existing_team_result = await session.execute(
                    select(TeamTrackerTeam).where(TeamTrackerTeam.entity_id == entity_id)
                )
                existing_team = existing_team_result.scalar_one_or_none()

                if existing_team:
                    # Update existing team
                    existing_team.configured_in_ha = True
                    existing_team.last_detected = datetime.now(timezone.utc)
                    logger.info(f"Updated existing team: {entity_id}")
                else:
                    # Create new team entry (with minimal info from entity)
                    # Note: Full team details would come from HA state attributes
                    new_team = TeamTrackerTeam(
                        team_id=unique_id or entity_id.split(".")[-1],  # Use unique_id or extract from entity_id
                        league_id="UNKNOWN",  # Will be updated from state attributes
                        team_name=sensor_name or entity_id,
                        entity_id=entity_id,
                        sensor_name=sensor_name,
                        configured_in_ha=True,
                        last_detected=datetime.now(timezone.utc),
                        is_active=True
                    )
                    session.add(new_team)
                    logger.info(f"Created new team entry: {entity_id}")

                detected_teams.append({
                    "entity_id": entity_id,
                    "name": sensor_name,
                    "unique_id": unique_id or entity_id,
                    "platform": platform
                })
            except Exception as e:
                entity_id = sensor.get("entity_id") if isinstance(sensor, dict) else getattr(sensor, "entity_id", "unknown")
                logger.error(f"Error processing team sensor {entity_id}: {e}", exc_info=True)
                # Continue processing other sensors even if one fails

        await session.commit()

        response = {
            "detected_count": len(team_sensors),
            "detected_teams": detected_teams,
            "integration_status": integration.installation_status
        }
        
        if data_api_error and len(team_sensors) == 0:
            response["warning"] = f"Data-api query failed, used local database: {data_api_error}"
        
        return response
    except Exception as e:
        logger.error(f"❌ Error detecting Team Tracker entities: {e}", exc_info=True)
        await session.rollback()
        error_detail = str(e)
        # Include more context in error message
        if "data-api" in error_detail.lower() or "connection" in error_detail.lower():
            error_detail = f"Could not connect to data-api service. {error_detail}"
        raise HTTPException(
            status_code=500,
            detail=f"Failed to detect Team Tracker entities: {error_detail}"
        ) from e


@router.get("/teams", response_model=list[TeamResponse])
async def get_configured_teams(
    active_only: bool = False,
    session: AsyncSession = Depends(get_db_session)
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
        query = query.where(TeamTrackerTeam.is_active == True)

    query = query.order_by(TeamTrackerTeam.priority.desc(), TeamTrackerTeam.team_name)

    result = await session.execute(query)
    teams = result.scalars().all()

    return [TeamResponse.model_validate(team) for team in teams]


@router.post("/teams", response_model=TeamResponse)
async def add_team(
    team_config: TeamConfiguration,
    session: AsyncSession = Depends(get_db_session)
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
            select(TeamTrackerTeam).where(TeamTrackerTeam.entity_id == team_config.entity_id)
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
        configured_in_ha=False  # Will be updated by detection
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
    session: AsyncSession = Depends(get_db_session)
) -> TeamResponse:
    """
    Update an existing Team Tracker team configuration.
    """
    logger.info(f"✏️ Updating team: {team_id}")

    result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.id == team_id)
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
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, str]:
    """
    Delete a Team Tracker team configuration.
    """
    logger.info(f"🗑️ Deleting team: {team_id}")

    result = await session.execute(
        select(TeamTrackerTeam).where(TeamTrackerTeam.id == team_id)
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
    session: AsyncSession = Depends(get_db_session)
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
        "message": "Teams synchronized from Home Assistant"
    }


@router.get("/debug/diagnostics", response_model=dict[str, Any])
async def get_diagnostics(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Comprehensive diagnostic endpoint for Team Tracker integration.
    
    Provides detailed information about:
    - Integration status
    - Entity detection status
    - Database state
    - Data API connectivity
    - Platform distribution
    - Team Tracker candidates
    """
    logger.info("🔍 Generating Team Tracker diagnostics")
    
    diagnostics: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "integration_status": None,
        "entity_detection": {
            "candidates_found": 0,
            "candidates": [],
            "platform_distribution": {},
            "data_api_accessible": False
        },
        "database_state": {
            "configured_teams": 0,
            "active_teams": 0,
            "integration_records": 0
        },
        "connectivity": {
            "data_api": False,
            "error": None
        }
    }
    
    try:
        # Get integration status
        result = await session.execute(
            select(TeamTrackerIntegration).limit(1)
        )
        integration = result.scalar_one_or_none()
        
        if integration:
            diagnostics["integration_status"] = {
                "is_installed": integration.is_installed,
                "installation_status": integration.installation_status,
                "version": integration.version,
                "last_checked": integration.last_checked.isoformat() if integration.last_checked else None
            }
            diagnostics["database_state"]["integration_records"] = 1
        
        # Get team counts
        teams_result = await session.execute(select(TeamTrackerTeam))
        all_teams = teams_result.scalars().all()
        diagnostics["database_state"]["configured_teams"] = len(all_teams)
        diagnostics["database_state"]["active_teams"] = len([t for t in all_teams if t.is_active])
        
        # Check data-api connectivity and get entity info
        data_api_client = DataAPIClient()
        try:
            all_sensor_entities = await data_api_client.fetch_entities(
                domain="sensor",
                limit=10000
            )
            diagnostics["connectivity"]["data_api"] = True
            
            # Platform distribution
            platform_counts: dict[str, int] = {}
            team_tracker_candidates = []
            platform_variations = ["teamtracker", "team_tracker", "TeamTracker", "TEAMTRACKER", "team-tracker"]
            
            for entity in all_sensor_entities:
                platform = entity.get("platform", "unknown")
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                
                entity_id = entity.get("entity_id", "").lower()
                platform_lower = platform.lower() if platform else ""
                
                # Check if this is a Team Tracker candidate
                platform_match = (
                    platform_lower in [p.lower() for p in platform_variations] or
                    ("team" in platform_lower and "tracker" in platform_lower)
                )
                entity_id_match = (
                    "team_tracker" in entity_id or
                    "teamtracker" in entity_id or
                    entity_id.endswith("_team_tracker") or
                    entity_id.startswith("sensor.team_tracker") or
                    entity_id.startswith("sensor.teamtracker")
                )
                
                if platform_match or entity_id_match:
                    team_tracker_candidates.append({
                        "entity_id": entity.get("entity_id"),
                        "platform": platform,
                        "name": entity.get("name") or entity.get("friendly_name"),
                        "domain": entity.get("domain"),
                        "matched_by": "platform" if platform_match else "entity_id"
                    })
            
            diagnostics["entity_detection"]["candidates_found"] = len(team_tracker_candidates)
            diagnostics["entity_detection"]["candidates"] = team_tracker_candidates
            diagnostics["entity_detection"]["platform_distribution"] = dict(sorted(
                platform_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:20])  # Top 20 platforms
            
        except Exception as e:
            diagnostics["connectivity"]["data_api"] = False
            diagnostics["connectivity"]["error"] = str(e)
            logger.warning(f"Data API connectivity check failed: {e}")
        finally:
            await data_api_client.close()
        
        return diagnostics
        
    except Exception as e:
        logger.error(f"Error generating diagnostics: {e}", exc_info=True)
        diagnostics["error"] = str(e)
        return diagnostics


@router.get("/debug/platforms")
async def debug_platform_values(
    session: AsyncSession = Depends(get_db_session)
) -> dict[str, Any]:
    """
    Debug endpoint to see what platform values exist for sensor entities.
    
    This helps identify the actual platform value used by Team Tracker
    integration in Home Assistant.
    
    Queries data-api service (where entities are actually stored).
    """
    try:
        data_api_client = DataAPIClient()
        try:
            # Get all sensor entities from data-api
            all_sensors = await data_api_client.fetch_entities(domain="sensor", limit=10000)
            
            # Count platforms
            platforms = {}
            for sensor in all_sensors:
                platform = sensor.get("platform", "unknown")
                platforms[platform] = platforms.get(platform, 0) + 1
            
            # Find team tracker-like entities
            team_like_by_platform = []
            team_like_by_entity_id = []
            
            for sensor in all_sensors:
                entity_id = sensor.get("entity_id", "")
                platform = sensor.get("platform", "").lower() if sensor.get("platform") else ""
                
                # Check by platform
                if "team" in platform and "tracker" in platform:
                    team_like_by_platform.append({
                        "entity_id": entity_id,
                        "platform": sensor.get("platform"),
                        "name": sensor.get("friendly_name") or sensor.get("name"),
                        "domain": sensor.get("domain")
                    })
                
                # Check by entity_id
                if "team" in entity_id.lower() and "tracker" in entity_id.lower():
                    team_like_by_entity_id.append({
                        "entity_id": entity_id,
                        "platform": sensor.get("platform"),
                        "name": sensor.get("friendly_name") or sensor.get("name"),
                        "domain": sensor.get("domain")
                    })
            
            return {
                "source": "data-api",
                "sensor_platforms": platforms,
                "team_tracker_like_by_platform": team_like_by_platform,
                "team_tracker_like_by_entity_id": team_like_by_entity_id,
                "total_sensor_entities": len(all_sensors),
                "total_team_tracker_candidates": len(set(
                    [e["entity_id"] for e in team_like_by_platform] +
                    [e["entity_id"] for e in team_like_by_entity_id]
                ))
            }
        finally:
            await data_api_client.close()
    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}", exc_info=True)
        # Fallback to local database
        try:
            result = await session.execute(
                select(DeviceEntity.platform, func.count(DeviceEntity.entity_id))
                .where(DeviceEntity.domain == "sensor")
                .group_by(DeviceEntity.platform)
            )
            platforms = {row[0]: row[1] for row in result.all() if row[0]}
            
            return {
                "source": "local-database-fallback",
                "sensor_platforms": platforms,
                "team_tracker_like_by_platform": [],
                "team_tracker_like_by_entity_id": [],
                "total_sensor_entities": sum(platforms.values()),
                "total_team_tracker_candidates": 0,
                "error": f"data-api query failed, using local database: {str(e)}"
            }
        except Exception as fallback_error:
            logger.error(f"Fallback query also failed: {fallback_error}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get platform debug info: {str(e)} (fallback also failed: {str(fallback_error)})"
            ) from e
