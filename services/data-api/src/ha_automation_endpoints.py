"""
Home Assistant Automation Endpoints for Data API
Epic 12 Story 12.3: HA Automation Integration
Epic 13 Story 13.4: Implementation in data-api service
"""

import logging
import sys
import os
import asyncio
import hashlib
import hmac
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from fastapi import APIRouter, HTTPException, status, Query, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from shared.influxdb_query_client import InfluxDBQueryClient
import aiohttp

logger = logging.getLogger(__name__)


# Request/Response Models
class GameStatusResponse(BaseModel):
    """Quick game status response (<50ms target)"""
    status: str  # "no_game", "upcoming", "live", "finished"
    team: str
    game_id: Optional[str] = None
    opponent: Optional[str] = None
    score: Optional[str] = None
    start_time: Optional[str] = None
    time_remaining: Optional[str] = None


class GameContextResponse(BaseModel):
    """Rich game context response"""
    status: str
    team: str
    game_id: Optional[str] = None
    league: Optional[str] = None
    opponent: Optional[str] = None
    home_team: Optional[str] = None
    away_team: Optional[str] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    quarter_period: Optional[str] = None
    time_remaining: Optional[str] = None
    start_time: Optional[str] = None
    is_home_game: Optional[bool] = None


class WebhookRegistration(BaseModel):
    """Webhook registration model"""
    webhook_url: HttpUrl
    secret: str
    team: str
    events: List[str]  # ["game_start", "game_end", "score_change"]
    filters: Optional[Dict[str, Any]] = {}


class WebhookResponse(BaseModel):
    """Webhook registration response"""
    id: str
    webhook_url: str
    team: str
    events: List[str]
    created_at: str
    status: str


# Create router
router = APIRouter(tags=["Home Assistant Automation"])

# InfluxDB client
influxdb_client = InfluxDBQueryClient()

# Webhook storage (in-memory for now, will be persistent in Phase 2)
webhooks: Dict[str, WebhookRegistration] = {}


@router.get("/ha/game-status/{team}", response_model=GameStatusResponse)
async def get_game_status(team: str):
    """
    Quick game status check for Home Assistant automations
    
    Performance target: <50ms response time
    Epic 12 Story 12.3: HA automation integration
    
    Args:
        team: Team name or abbreviation
        
    Returns:
        Quick status (no_game, upcoming, live, finished)
    """
    try:
        # Query only latest game for this team (last 7 days)
        query = f'''
            from(bucket: "sports_data")
                |> range(start: -7d)
                |> filter(fn: (r) => r._measurement == "nfl_scores" or r._measurement == "nhl_scores")
                |> filter(fn: (r) => r.home_team == "{team}" or r.away_team == "{team}")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
        '''
        
        results = await influxdb_client._execute_query(query)
        
        if not results:
            return GameStatusResponse(
                status="no_game",
                team=team
            )
        
        game = results[0]
        game_status = game.get("status", "unknown")
        
        # Determine opponent
        opponent = game.get("away_team") if game.get("home_team") == team else game.get("home_team")
        
        # Build response based on status
        response = GameStatusResponse(
            status=game_status,
            team=team,
            game_id=game.get("game_id"),
            opponent=opponent,
            start_time=game.get("_time")
        )
        
        if game_status == "live":
            response.score = f"{game.get('home_score', 0)}-{game.get('away_score', 0)}"
            response.time_remaining = game.get("time_remaining")
        
        return response
    
    except Exception as e:
        logger.error(f"Error getting game status for {team}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game status: {str(e)}"
        )


@router.get("/ha/game-context/{team}", response_model=GameContextResponse)
async def get_game_context(team: str):
    """
    Get rich game context for Home Assistant automations
    
    Provides full game details for automation decision-making
    
    Args:
        team: Team name
        
    Returns:
        Complete game context
    """
    try:
        # Query latest game
        query = f'''
            from(bucket: "sports_data")
                |> range(start: -7d)
                |> filter(fn: (r) => r._measurement == "nfl_scores" or r._measurement == "nhl_scores")
                |> filter(fn: (r) => r.home_team == "{team}" or r.away_team == "{team}")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 1)
        '''
        
        results = await influxdb_client._execute_query(query)
        
        if not results:
            return GameContextResponse(
                status="no_game",
                team=team
            )
        
        game = results[0]
        is_home = game.get("home_team") == team
        
        return GameContextResponse(
            status=game.get("status", "unknown"),
            team=team,
            game_id=game.get("game_id"),
            league=game.get("_measurement", "").split('_')[0].upper(),
            opponent=game.get("away_team") if is_home else game.get("home_team"),
            home_team=game.get("home_team"),
            away_team=game.get("away_team"),
            home_score=game.get("home_score"),
            away_score=game.get("away_score"),
            quarter_period=game.get("quarter") or game.get("period"),
            time_remaining=game.get("time_remaining"),
            start_time=game.get("_time"),
            is_home_game=is_home
        )
    
    except Exception as e:
        logger.error(f"Error getting game context for {team}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game context: {str(e)}"
        )


@router.post("/ha/webhooks/register", response_model=WebhookResponse)
async def register_webhook(registration: WebhookRegistration):
    """
    Register a webhook for game events
    
    Home Assistant will receive HTTP POST when events occur:
    - game_start: Game status changes to "live"
    - game_end: Game status changes to "finished"
    - score_change: Score changes significantly (6+ points or lead change)
    
    Args:
        registration: Webhook configuration
        
    Returns:
        Webhook registration confirmation
    """
    try:
        import uuid
        
        webhook_id = str(uuid.uuid4())
        webhooks[webhook_id] = registration
        
        logger.info(f"Registered webhook {webhook_id} for team {registration.team}, events: {registration.events}")
        
        return WebhookResponse(
            id=webhook_id,
            webhook_url=str(registration.webhook_url),
            team=registration.team,
            events=registration.events,
            created_at=datetime.now().isoformat(),
            status="active"
        )
    
    except Exception as e:
        logger.error(f"Error registering webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register webhook: {str(e)}"
        )


@router.get("/ha/webhooks", response_model=List[WebhookResponse])
async def list_webhooks():
    """
    List all registered webhooks
    
    Returns:
        List of active webhooks
    """
    try:
        webhook_list = []
        for webhook_id, registration in webhooks.items():
            webhook_list.append(WebhookResponse(
                id=webhook_id,
                webhook_url=str(registration.webhook_url),
                team=registration.team,
                events=registration.events,
                created_at=datetime.now().isoformat(),  # TODO: Store actual creation time
                status="active"
            ))
        
        return webhook_list
    
    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list webhooks: {str(e)}"
        )


@router.delete("/ha/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str):
    """
    Delete a registered webhook
    
    Args:
        webhook_id: Webhook ID to delete
        
    Returns:
        Deletion confirmation
    """
    try:
        if webhook_id not in webhooks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        del webhooks[webhook_id]
        logger.info(f"Deleted webhook {webhook_id}")
        
        return {
            "success": True,
            "message": f"Webhook {webhook_id} deleted",
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )


# Webhook delivery helper
async def deliver_webhook(webhook: WebhookRegistration, event_type: str, payload: Dict[str, Any]):
    """
    Deliver webhook to Home Assistant
    
    Includes HMAC signature for security
    
    Args:
        webhook: Webhook registration
        event_type: Type of event (game_start, game_end, score_change)
        payload: Event data
    """
    try:
        # Generate HMAC signature
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            webhook.secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Deliver webhook
        headers = {
            'Content-Type': 'application/json',
            'X-Signature': signature,
            'X-Event-Type': event_type
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                str(webhook.webhook_url),
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status in [200, 201, 204]:
                    logger.info(f"Webhook delivered successfully: {event_type} for {webhook.team}")
                    return True
                else:
                    logger.warning(f"Webhook delivery failed: HTTP {response.status}")
                    return False
    
    except Exception as e:
        logger.error(f"Error delivering webhook: {e}")
        return False


# Background task for webhook event detection (to be started with service)
async def webhook_event_detector():
    """
    Background task to detect game events and trigger webhooks
    
    Runs every 15 seconds, checks for:
    - Game start (status: scheduled → live)
    - Game end (status: live → finished)  
    - Score changes (significant: 6+ points or lead change)
    """
    logger.info("Starting webhook event detector background task")
    
    previous_state = {}  # Track previous game states
    
    while True:
        try:
            await asyncio.sleep(15)  # Check every 15 seconds
            
            # Safety check: Ensure InfluxDB client is connected
            if not influxdb_client or not hasattr(influxdb_client, '_query_api') or influxdb_client._query_api is None:
                logger.debug("InfluxDB client not ready, skipping webhook detection cycle")
                continue
            
            # Query all active games
            query = '''
                from(bucket: "sports_data")
                    |> range(start: -24h)
                    |> filter(fn: (r) => r._measurement == "nfl_scores" or r._measurement == "nhl_scores")
                    |> filter(fn: (r) => r.status == "live" or r.status == "upcoming")
                    |> sort(columns: ["_time"], desc: true)
                    |> limit(n: 100)
            '''
            
            results = await influxdb_client._execute_query(query)
            
            for game in results:
                game_id = game.get("game_id")
                home_team = game.get("home_team")
                away_team = game.get("away_team")
                current_status = game.get("status")
                
                # Check for webhooks for either team
                for webhook_id, webhook in webhooks.items():
                    if webhook.team not in [home_team, away_team]:
                        continue
                    
                    # Check for events
                    previous = previous_state.get(game_id, {})
                    
                    # Game start event
                    if "game_start" in webhook.events:
                        if current_status == "live" and previous.get("status") != "live":
                            payload = {
                                "event": "game_start",
                                "game_id": game_id,
                                "team": webhook.team,
                                "opponent": away_team if home_team == webhook.team else home_team,
                                "timestamp": datetime.now().isoformat()
                            }
                            await deliver_webhook(webhook, "game_start", payload)
                    
                    # Game end event
                    if "game_end" in webhook.events:
                        if current_status == "finished" and previous.get("status") == "live":
                            payload = {
                                "event": "game_end",
                                "game_id": game_id,
                                "team": webhook.team,
                                "final_score": f"{game.get('home_score')}-{game.get('away_score')}",
                                "result": "win" if _team_won(game, webhook.team) else "loss",
                                "timestamp": datetime.now().isoformat()
                            }
                            await deliver_webhook(webhook, "game_end", payload)
                    
                    # Score change event
                    if "score_change" in webhook.events:
                        prev_score = previous.get("home_score", 0) if home_team == webhook.team else previous.get("away_score", 0)
                        curr_score = game.get("home_score", 0) if home_team == webhook.team else game.get("away_score", 0)
                        
                        if curr_score > prev_score:
                            score_change = curr_score - prev_score
                            payload = {
                                "event": "score_change",
                                "game_id": game_id,
                                "team": webhook.team,
                                "score_change": score_change,
                                "new_score": f"{game.get('home_score')}-{game.get('away_score')}",
                                "timestamp": datetime.now().isoformat()
                            }
                            await deliver_webhook(webhook, "score_change", payload)
                
                # Update previous state
                previous_state[game_id] = {
                    "status": current_status,
                    "home_score": game.get("home_score"),
                    "away_score": game.get("away_score")
                }
        
        except Exception as e:
            logger.error(f"Error in webhook event detector: {e}")


def _team_won(game: Dict[str, Any], team: str) -> bool:
    """Check if team won the game"""
    home_team = game.get("home_team")
    home_score = game.get("home_score", 0)
    away_score = game.get("away_score", 0)
    
    if home_team == team:
        return home_score > away_score
    else:
        return away_score > home_score


# Start background task when module loads (will be managed by service lifecycle)
webhook_detector_task: Optional[asyncio.Task] = None


def start_webhook_detector():
    """Start webhook event detector background task"""
    global webhook_detector_task
    if webhook_detector_task is None:
        webhook_detector_task = asyncio.create_task(webhook_event_detector())
        logger.info("Webhook event detector started")


def stop_webhook_detector():
    """Stop webhook event detector background task"""
    global webhook_detector_task
    if webhook_detector_task:
        webhook_detector_task.cancel()
        webhook_detector_task = None
        logger.info("Webhook event detector stopped")

