"""
Sports Data Endpoints for Data API
Epic 12 Story 12.2: Historical Sports Data Queries
Epic 13 Story 13.4: Integration into data-api service
"""

import logging
import os
import sys
from datetime import datetime

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../shared'))

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from shared.influxdb_query_client import InfluxDBQueryClient
from .sports_influxdb_writer import get_sports_writer

logger = logging.getLogger(__name__)


# Response Models
class GameResponse(BaseModel):
    """Game response model"""
    game_id: str
    league: str  # NFL or NHL
    season: int
    week: str | None = None  # For NFL
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    status: str  # scheduled, live, finished
    quarter_period: str | None = None  # Quarter (NFL) or Period (NHL)
    time_remaining: str | None = None
    timestamp: str


class GameListResponse(BaseModel):
    """Game list response"""
    games: list[GameResponse]
    count: int
    team: str | None = None
    season: int | None = None


class TeamScheduleResponse(BaseModel):
    """Team schedule response"""
    team: str
    season: int
    games: list[GameResponse]
    total_games: int
    wins: int
    losses: int
    ties: int
    win_percentage: float


class ScoreTimelinePoint(BaseModel):
    """Score timeline point"""
    timestamp: str
    home_score: int
    away_score: int
    quarter_period: str
    time_remaining: str


class ScoreTimelineResponse(BaseModel):
    """Score timeline response"""
    game_id: str
    home_team: str
    away_team: str
    timeline: list[ScoreTimelinePoint]
    final_score: str


# Create router
router = APIRouter(tags=["Sports Data"])

# InfluxDB client (shared instance)
influxdb_client = InfluxDBQueryClient()

# Sports InfluxDB writer (Epic 12 Story 12.1)
sports_writer = get_sports_writer()


@router.get("/sports/games/live")
async def get_live_games(
    team_ids: str | None = Query(None, description="Comma-separated team IDs"),
    league: str | None = Query(None, description="NFL or NHL")
):
    """
    Get currently live games
    
    Story 21.2: Live games endpoint for Sports Tab
    Epic 12 Story 12.1: InfluxDB persistence - writes game data to InfluxDB
    
    This endpoint queries InfluxDB for live games and writes new data when fetched.
    For historical data, use /sports/games/history endpoint.
    """
    try:
        # Query InfluxDB for live games
        query = '''
            from(bucket: "sports_data")
                |> range(start: -24h)
                |> filter(fn: (r) => r._measurement == "nfl_scores" or r._measurement == "nhl_scores")
                |> filter(fn: (r) => r.status == "live")
                |> sort(columns: ["_time"], desc: true)
                |> limit(n: 50)
        '''
        
        if league:
            query = f'''
                from(bucket: "sports_data")
                    |> range(start: -24h)
                    |> filter(fn: (r) => r._measurement == "{league.lower()}_scores")
                    |> filter(fn: (r) => r.status == "live")
                    |> sort(columns: ["_time"], desc: true)
                    |> limit(n: 50)
            '''
        
        results = await influxdb_client._execute_query(query)
        
        games = []
        for record in results:
            # Filter by team_ids if provided
            if team_ids:
                team_list = [t.strip().lower() for t in team_ids.split(",")]
                home_team = record.get("home_team", "").lower()
                away_team = record.get("away_team", "").lower()
                if home_team not in team_list and away_team not in team_list:
                    continue
            
            game = GameResponse(
                game_id=record.get("game_id", ""),
                league=record.get("_measurement", "").split('_')[0].upper(),
                season=int(record.get("season", datetime.now().year)),
                week=record.get("week"),
                home_team=record.get("home_team", ""),
                away_team=record.get("away_team", ""),
                home_score=record.get("home_score"),
                away_score=record.get("away_score"),
                status=record.get("status", "live"),
                quarter_period=record.get("quarter") or record.get("period"),
                time_remaining=record.get("time_remaining"),
                timestamp=record.get("_time", datetime.now().isoformat())
            )
            games.append(game)
            
            # Write to InfluxDB (Epic 12 Story 12.1) - ensures data is persisted
            if sports_writer.is_connected:
                game_data = {
                    "game_id": game.game_id,
                    "league": game.league,
                    "season": game.season,
                    "week": game.week,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "status": game.status,
                    "quarter": game.quarter_period,
                    "time_remaining": game.time_remaining,
                    "start_time": game.timestamp
                }
                await sports_writer.write_game(game_data)
        
        return {
            "games": [game.model_dump() for game in games],
            "count": len(games),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error fetching live games: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch live games: {str(e)}")


@router.get("/sports/games/upcoming")
async def get_upcoming_games(
    team_ids: str | None = Query(None, description="Comma-separated team IDs"),
    hours: int = Query(default=24, description="Hours ahead to look for games"),
    league: str | None = Query(None, description="NFL or NHL")
):
    """
    Get upcoming games
    
    Story 21.2: Upcoming games endpoint for Sports Tab
    Epic 12 Story 12.1: InfluxDB persistence - writes game data to InfluxDB
    
    This endpoint queries InfluxDB for upcoming games and writes new data when fetched.
    For historical data, use /sports/games/history endpoint.
    """
    try:
        # Query InfluxDB for upcoming games
        query = f'''
            from(bucket: "sports_data")
                |> range(start: now(), stop: now() + {hours}h)
                |> filter(fn: (r) => r._measurement == "nfl_scores" or r._measurement == "nhl_scores")
                |> filter(fn: (r) => r.status == "scheduled" or r.status == "upcoming")
                |> sort(columns: ["_time"], desc: false)
                |> limit(n: 50)
        '''
        
        if league:
            query = f'''
                from(bucket: "sports_data")
                    |> range(start: now(), stop: now() + {hours}h)
                    |> filter(fn: (r) => r._measurement == "{league.lower()}_scores")
                    |> filter(fn: (r) => r.status == "scheduled" or r.status == "upcoming")
                    |> sort(columns: ["_time"], desc: false)
                    |> limit(n: 50)
            '''
        
        results = await influxdb_client._execute_query(query)
        
        games = []
        for record in results:
            # Filter by team_ids if provided
            if team_ids:
                team_list = [t.strip().lower() for t in team_ids.split(",")]
                home_team = record.get("home_team", "").lower()
                away_team = record.get("away_team", "").lower()
                if home_team not in team_list and away_team not in team_list:
                    continue
            
            game = GameResponse(
                game_id=record.get("game_id", ""),
                league=record.get("_measurement", "").split('_')[0].upper(),
                season=int(record.get("season", datetime.now().year)),
                week=record.get("week"),
                home_team=record.get("home_team", ""),
                away_team=record.get("away_team", ""),
                home_score=record.get("home_score"),
                away_score=record.get("away_score"),
                status=record.get("status", "upcoming"),
                quarter_period=record.get("quarter") or record.get("period"),
                time_remaining=record.get("time_remaining"),
                timestamp=record.get("_time", datetime.now().isoformat())
            )
            games.append(game)
            
            # Write to InfluxDB (Epic 12 Story 12.1) - ensures data is persisted
            if sports_writer.is_connected:
                game_data = {
                    "game_id": game.game_id,
                    "league": game.league,
                    "season": game.season,
                    "week": game.week,
                    "home_team": game.home_team,
                    "away_team": game.away_team,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
                    "status": game.status,
                    "quarter": game.quarter_period,
                    "time_remaining": game.time_remaining,
                    "start_time": game.timestamp
                }
                await sports_writer.write_game(game_data)
        
        return {
            "games": [game.model_dump() for game in games],
            "count": len(games),
            "hours": hours
        }
    except Exception as e:
        logger.error(f"Error fetching upcoming games: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch upcoming games: {str(e)}")


@router.get("/sports/teams")
async def get_teams(
    league: str | None = Query(None, description="NFL or NHL")
):
    """
    Get available teams
    
    Story 21.2: Teams endpoint for Setup Wizard
    """
    try:
        # For now, return sample teams
        nfl_teams = [
            {"id": "BAL", "name": "Baltimore Ravens", "league": "NFL"},
            {"id": "BUF", "name": "Buffalo Bills", "league": "NFL"},
            {"id": "CIN", "name": "Cincinnati Bengals", "league": "NFL"},
            {"id": "CLE", "name": "Cleveland Browns", "league": "NFL"},
            {"id": "DEN", "name": "Denver Broncos", "league": "NFL"},
            {"id": "HOU", "name": "Houston Texans", "league": "NFL"},
            {"id": "IND", "name": "Indianapolis Colts", "league": "NFL"},
            {"id": "JAX", "name": "Jacksonville Jaguars", "league": "NFL"},
            {"id": "KC", "name": "Kansas City Chiefs", "league": "NFL"},
            {"id": "LAC", "name": "Los Angeles Chargers", "league": "NFL"},
            {"id": "LV", "name": "Las Vegas Raiders", "league": "NFL"},
            {"id": "MIA", "name": "Miami Dolphins", "league": "NFL"},
            {"id": "NE", "name": "New England Patriots", "league": "NFL"},
            {"id": "NYJ", "name": "New York Jets", "league": "NFL"},
            {"id": "PIT", "name": "Pittsburgh Steelers", "league": "NFL"},
            {"id": "TEN", "name": "Tennessee Titans", "league": "NFL"},
        ]

        nhl_teams = [
            {"id": "BOS", "name": "Boston Bruins", "league": "NHL"},
            {"id": "BUF", "name": "Buffalo Sabres", "league": "NHL"},
            {"id": "DET", "name": "Detroit Red Wings", "league": "NHL"},
            {"id": "FLA", "name": "Florida Panthers", "league": "NHL"},
            {"id": "MTL", "name": "Montreal Canadiens", "league": "NHL"},
            {"id": "OTT", "name": "Ottawa Senators", "league": "NHL"},
            {"id": "TB", "name": "Tampa Bay Lightning", "league": "NHL"},
            {"id": "TOR", "name": "Toronto Maple Leafs", "league": "NHL"},
        ]

        if league == "NFL":
            return {"teams": nfl_teams, "count": len(nfl_teams)}
        elif league == "NHL":
            return {"teams": nhl_teams, "count": len(nhl_teams)}
        else:
            return {"teams": nfl_teams + nhl_teams, "count": len(nfl_teams) + len(nhl_teams)}
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch teams: {str(e)}")


@router.get("/sports/games/history", response_model=GameListResponse)
async def get_game_history(
    team: str = Query(..., description="Team name or abbreviation"),
    season: int | None = Query(None, description="Season year (default: current)"),
    league: str | None = Query(None, description="NFL or NHL"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of games")
):
    """
    Get historical games for a team
    
    Epic 12 Story 12.2: Query sports data from InfluxDB
    
    Args:
        team: Team name (e.g., "Patriots", "Bruins")
        season: Season year (e.g., 2025)
        league: Filter by league (NFL or NHL)
        status_filter: Filter by game status (scheduled, live, finished)
        limit: Maximum results
        
    Returns:
        List of games with scores and details
    """
    try:
        # Build query
        current_year = datetime.now().year
        season = season or current_year

        # Determine measurement based on league
        measurements = []
        if league:
            measurements.append(f"{league.lower()}_scores")
        else:
            measurements.extend(["nfl_scores", "nhl_scores"])

        all_games = []

        for measurement in measurements:
            query = f'''
                from(bucket: "sports_data")
                    |> range(start: {season}-01-01T00:00:00Z, stop: {season+1}-01-01T00:00:00Z)
                    |> filter(fn: (r) => r._measurement == "{measurement}")
                    |> filter(fn: (r) => r.home_team == "{team}" or r.away_team == "{team}")
            '''

            if status_filter:
                query += f'|> filter(fn: (r) => r.status == "{status_filter}")'

            query += '|> sort(columns: ["_time"], desc: true)'
            query += f'|> limit(n: {limit})'

            try:
                results = await influxdb_client._execute_query(query)

                for record in results:
                    game = GameResponse(
                        game_id=record.get("game_id", ""),
                        league=measurement.split('_')[0].upper(),
                        season=int(record.get("season", season)),
                        week=record.get("week"),
                        home_team=record.get("home_team", ""),
                        away_team=record.get("away_team", ""),
                        home_score=record.get("home_score"),
                        away_score=record.get("away_score"),
                        status=record.get("status", "unknown"),
                        quarter_period=record.get("quarter") or record.get("period"),
                        time_remaining=record.get("time_remaining"),
                        timestamp=record.get("_time", datetime.now().isoformat())
                    )
                    all_games.append(game)

            except Exception as e:
                logger.warning(f"Error querying {measurement}: {e}")

        return GameListResponse(
            games=all_games,
            count=len(all_games),
            team=team,
            season=season
        )

    except Exception as e:
        logger.error(f"Error getting game history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game history: {str(e)}"
        )


@router.get("/sports/games/timeline/{game_id}", response_model=ScoreTimelineResponse)
async def get_game_timeline(
    game_id: str,
    league: str | None = Query(None, description="NFL or NHL")
):
    """
    Get score progression timeline for a specific game
    
    Shows how the score changed throughout the game (useful for comeback visualizations)
    
    Args:
        game_id: Unique game identifier
        league: NFL or NHL (optional, will search both if not specified)
        
    Returns:
        Score timeline with timestamps
    """
    try:
        measurements = []
        if league:
            measurements.append(f"{league.lower()}_scores")
        else:
            measurements.extend(["nfl_scores", "nhl_scores"])

        for measurement in measurements:
            query = f'''
                from(bucket: "sports_data")
                    |> range(start: -7d)
                    |> filter(fn: (r) => r._measurement == "{measurement}")
                    |> filter(fn: (r) => r.game_id == "{game_id}")
                    |> sort(columns: ["_time"])
            '''

            try:
                results = await influxdb_client._execute_query(query)

                if not results:
                    continue

                # Build timeline
                timeline = []
                for record in results:
                    point = ScoreTimelinePoint(
                        timestamp=record.get("_time", ""),
                        home_score=record.get("home_score", 0),
                        away_score=record.get("away_score", 0),
                        quarter_period=record.get("quarter") or record.get("period", ""),
                        time_remaining=record.get("time_remaining", "")
                    )
                    timeline.append(point)

                if timeline:
                    first_record = results[0]
                    final_record = results[-1]

                    return ScoreTimelineResponse(
                        game_id=game_id,
                        home_team=first_record.get("home_team", ""),
                        away_team=first_record.get("away_team", ""),
                        timeline=timeline,
                        final_score=f"{final_record.get('home_score', 0)}-{final_record.get('away_score', 0)}"
                    )

            except Exception as e:
                logger.warning(f"Error querying {measurement} for game {game_id}: {e}")

        # Game not found in any measurement
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting game timeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get game timeline: {str(e)}"
        )


@router.get("/sports/schedule/{team}", response_model=TeamScheduleResponse)
async def get_team_schedule(
    team: str,
    season: int | None = Query(None, description="Season year (default: current)"),
    league: str | None = Query(None, description="NFL or NHL")
):
    """
    Retrieve complete season schedule for a team with calculated win/loss record.
    
    Fetches all games for the specified team and season from ESPN API via sports-data service,
    then calculates team record (wins/losses/ties) by analyzing game scores.
    
    Complexity: C (14) - Moderate-high complexity due to game data processing and record calculation
    
    Args:
        team (str): Team identifier/name (e.g., "49ers", "Patriots")
        season (Optional[int]): Season year (default: current year)
        league (Optional[str]): League identifier - "NFL" or "NHL" (auto-detected if None)
        
    Returns:
        TeamScheduleResponse: Complete schedule containing:
            - team: Team name
            - season: Season year
            - games: List of all games (GameResponse objects)
            - record: Win-loss-tie record as string (e.g., "10-5-1")
            - wins: Number of wins
            - losses: Number of losses
            - ties: Number of ties
            
    Process Flow:
        1. Determine current season (if not provided)
        2. Fetch all games via get_game_history() endpoint
        3. Iterate through finished games
        4. Calculate wins/losses/ties based on score comparison
        5. Distinguish home vs away game logic
        6. Return complete schedule with calculated record
    
    Example:
        >>> # Get 49ers current season schedule
        >>> response = await get_team_schedule("49ers", league="NFL")
        >>> print(f"Record: {response.record}")  # "10-5-1"
        >>> print(f"Total games: {len(response.games)}")
        >>> for game in response.games:
        ...     print(f"{game.home_team} vs {game.away_team}: {game.home_score}-{game.away_score}")
    
    Note:
        Complexity arises from:
        - Iteration through all team games (up to 200 games)
        - Conditional logic for home vs away team
        - Score comparison for wins/losses/ties
        - Null/None handling for unfinished games
        - Record calculation logic
        - Response formatting
        
    Performance:
        - Typical response time: <500ms
        - Caches team data where possible
        - Limit of 200 games prevents excessive memory usage
    """
    try:
        current_year = datetime.now().year
        season = season or current_year

        # Get all games for team
        response = await get_game_history(team=team, season=season, league=league, limit=200)
        games = response.games

        # Calculate record
        wins = 0
        losses = 0
        ties = 0

        for game in games:
            if game.status == "finished" and game.home_score is not None and game.away_score is not None:
                if game.home_team == team:
                    if game.home_score > game.away_score:
                        wins += 1
                    elif game.home_score < game.away_score:
                        losses += 1
                    else:
                        ties += 1
                else:  # away team
                    if game.away_score > game.home_score:
                        wins += 1
                    elif game.away_score < game.home_score:
                        losses += 1
                    else:
                        ties += 1

        total_games_played = wins + losses + ties
        win_percentage = (wins / total_games_played) if total_games_played > 0 else 0.0

        return TeamScheduleResponse(
            team=team,
            season=season,
            games=games,
            total_games=len(games),
            wins=wins,
            losses=losses,
            ties=ties,
            win_percentage=round(win_percentage, 3)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get team schedule: {str(e)}"
        )

