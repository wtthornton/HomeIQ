# NFL & NHL Integration - Implementation Guide

## 📋 Quick Start Implementation Guide

This guide provides step-by-step instructions for implementing the NFL and NHL sports integration based on the UX/UI design document.

---

## 🎯 Prerequisites

**Required:**
- Node.js 18+ (for dashboard)
- Python 3.11+ (for backend services)
- Docker & Docker Compose (for deployment)
- Recharts library (already in project)

**API Access:**
- ESPN API key (recommended for MVP) - Free tier available
- Or NHL Official API (free, no key required)
- Or SportsData.io account (paid, but comprehensive)

---

## 🚀 Phase 1: Core Implementation (MVP)

### Step 1: Backend Service Setup

**Create new service:** `services/sports-data/`

```bash
cd services
mkdir sports-data
cd sports-data
```

**File Structure:**
```
services/sports-data/
├── src/
│   ├── main.py                    # FastAPI application
│   ├── sports_api_client.py       # API client for ESPN/NHL
│   ├── cache_service.py           # Redis/in-memory caching
│   ├── models.py                  # Data models (Game, Team, etc.)
│   ├── websocket_handler.py       # Real-time updates
│   └── health_check.py            # Health monitoring
├── tests/
│   └── test_sports_api.py
├── Dockerfile
├── requirements.txt
└── README.md
```

**requirements.txt:**
```txt
fastapi==0.104.1
uvicorn==0.24.0
aiohttp==3.9.0
pydantic==2.5.0
python-dotenv==1.0.0
redis==5.0.1
websockets==12.0
```

**src/main.py:**
```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from sports_api_client import SportsAPIClient
from cache_service import CacheService

app = FastAPI(title="Sports Data Service")

# CORS for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
cache = CacheService()
sports_client = SportsAPIClient(cache=cache)

@app.get("/api/v1/games/live")
async def get_live_games(
    league: str = None,
    team_ids: str = None  # Comma-separated team IDs, e.g., "sf,dal,bos"
):
    """
    Get live games for selected teams only
    
    Args:
        league: Filter by league ('NFL' or 'NHL')
        team_ids: Comma-separated team IDs (e.g., 'sf,dal,bos')
                 If not provided, returns empty list
    
    Returns:
        JSON with games list and count
    """
    # Parse team IDs
    teams = team_ids.split(',') if team_ids else []
    
    # Fetch games for selected teams only
    games = await sports_client.get_live_games(league, teams)
    
    return {
        "games": games,
        "count": len(games),
        "filtered_by_teams": teams
    }

@app.get("/api/v1/games/upcoming")
async def get_upcoming_games(
    league: str = None,
    hours: int = 24,
    team_ids: str = None  # Comma-separated team IDs
):
    """
    Get upcoming games for selected teams in next N hours
    
    Args:
        league: Filter by league ('NFL' or 'NHL')
        hours: Number of hours to look ahead
        team_ids: Comma-separated team IDs (e.g., 'sf,dal,bos')
    
    Returns:
        JSON with games list and count
    """
    # Parse team IDs
    teams = team_ids.split(',') if team_ids else []
    
    # Fetch upcoming games for selected teams
    games = await sports_client.get_upcoming_games(league, hours, teams)
    
    return {
        "games": games,
        "count": len(games),
        "filtered_by_teams": teams
    }

@app.get("/api/v1/teams")
async def get_available_teams(league: str = None):
    """
    Get list of all available teams for selection
    
    Args:
        league: Filter by league ('NFL' or 'NHL')
    
    Returns:
        JSON with teams list organized by league
    """
    teams = await sports_client.get_available_teams(league)
    return {"teams": teams}

@app.get("/api/v1/user/teams")
async def get_user_selected_teams(user_id: str = "default"):
    """Get user's selected teams from preferences"""
    # In production, fetch from database
    # For now, return from environment or config
    selected = os.getenv('SELECTED_TEAMS', '').split(',')
    return {
        "user_id": user_id,
        "selected_teams": [t.strip() for t in selected if t.strip()]
    }

@app.post("/api/v1/user/teams")
async def save_user_selected_teams(teams: dict, user_id: str = "default"):
    """
    Save user's selected teams
    
    Body example:
    {
        "nfl_teams": ["sf", "dal"],
        "nhl_teams": ["bos", "wsh"]
    }
    """
    # In production, save to database
    # For now, log and return success
    print(f"User {user_id} selected teams: {teams}")
    
    # Calculate estimated API usage
    total_teams = len(teams.get('nfl_teams', [])) + len(teams.get('nhl_teams', []))
    estimated_daily_calls = total_teams * 12  # ~12 calls per team per day
    
    return {
        "success": True,
        "user_id": user_id,
        "teams_saved": teams,
        "estimated_daily_api_calls": estimated_daily_calls,
        "within_free_tier": estimated_daily_calls <= 100
    }

@app.get("/api/v1/games/{game_id}")
async def get_game_details(game_id: str):
    """Get detailed game information"""
    game = await sports_client.get_game(game_id)
    return game

@app.get("/api/v1/games/{game_id}/stats")
async def get_game_stats(game_id: str):
    """Get game statistics"""
    stats = await sports_client.get_game_stats(game_id)
    return stats

@app.websocket("/ws/games/{game_id}")
async def game_updates(websocket: WebSocket, game_id: str):
    """WebSocket for real-time game updates"""
    await websocket.accept()
    try:
        while True:
            game = await sports_client.get_game(game_id)
            await websocket.send_json(game)
            await asyncio.sleep(15)  # Update every 15 seconds
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        await websocket.close()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "sports-data",
        "cache_status": cache.is_connected(),
        "api_status": await sports_client.test_connection()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
```

**src/sports_api_client.py:**
```python
import aiohttp
import os
from typing import List, Optional, Set
from models import Game, Team
from cache_service import CacheService

class SportsAPIClient:
    """Client for sports data APIs (ESPN, NHL, etc.)"""
    
    def __init__(self, cache: CacheService):
        self.cache = cache
        self.api_key = os.getenv('SPORTS_API_KEY', '')
        self.provider = os.getenv('SPORTS_API_PROVIDER', 'espn')
        
        # API endpoints
        self.endpoints = {
            'espn': {
                'nfl_scoreboard': 'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard',
                'nhl_scoreboard': 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard',
            },
            'nhl_official': {
                'scoreboard': 'https://statsapi.web.nhl.com/api/v1/schedule',
                'game': 'https://statsapi.web.nhl.com/api/v1/game/{game_id}/feed/live',
            }
        }
    
    async def get_live_games(
        self, 
        league: Optional[str] = None,
        team_ids: Optional[List[str]] = None
    ) -> List[Game]:
        """
        Fetch live games, optionally filtered by team IDs
        
        Args:
            league: Filter by league ('NFL' or 'NHL')
            team_ids: List of team IDs to filter by (e.g., ['sf', 'dal', 'bos'])
                     If None or empty, returns NO games (opt-in model)
        
        Returns:
            List of Game objects matching the filters
        """
        # CRITICAL: If no teams selected, return empty list
        if not team_ids:
            return []
        
        cache_key = f"live_games_{league or 'all'}_{'_'.join(sorted(team_ids))}"
        
        # Check cache first
        cached = await self.cache.get(cache_key)
        if cached:
            return cached
        
        # Fetch from API
        games = []
        
        if not league or league.upper() == 'NFL':
            nfl_games = await self._fetch_nfl_scoreboard(team_ids)
            games.extend(nfl_games)
        
        if not league or league.upper() == 'NHL':
            nhl_games = await self._fetch_nhl_scoreboard(team_ids)
            games.extend(nhl_games)
        
        # Filter only live games involving selected teams
        live_games = [
            g for g in games 
            if g.status == 'live' and self._game_has_selected_team(g, team_ids)
        ]
        
        # Cache for 15 seconds (live data changes frequently)
        await self.cache.set(cache_key, live_games, ttl=15)
        
        return live_games
    
    def _game_has_selected_team(self, game: Game, team_ids: List[str]) -> bool:
        """Check if game involves any of the selected teams"""
        if not team_ids:
            return False
        return game.home_team.id in team_ids or game.away_team.id in team_ids
    
    async def _fetch_nfl_scoreboard(self) -> List[Game]:
        """Fetch NFL scoreboard from ESPN"""
        url = self.endpoints['espn']['nfl_scoreboard']
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_espn_games(data, 'NFL')
                else:
                    print(f"Error fetching NFL data: {response.status}")
                    return []
    
    async def _fetch_nhl_scoreboard(self) -> List[Game]:
        """Fetch NHL scoreboard"""
        if self.provider == 'nhl_official':
            url = self.endpoints['nhl_official']['scoreboard']
        else:
            url = self.endpoints['espn']['nhl_scoreboard']
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._parse_espn_games(data, 'NHL')
                else:
                    print(f"Error fetching NHL data: {response.status}")
                    return []
    
    def _parse_espn_games(self, data: dict, league: str) -> List[Game]:
        """Parse ESPN API response into Game objects"""
        games = []
        
        for event in data.get('events', []):
            competition = event['competitions'][0]
            competitors = competition['competitors']
            
            # Find home and away teams
            home_team = next(c for c in competitors if c['homeAway'] == 'home')
            away_team = next(c for c in competitors if c['homeAway'] == 'away')
            
            game = Game(
                id=event['id'],
                league=league,
                status=self._map_status(competition['status']['type']['state']),
                start_time=event['date'],
                home_team=Team(
                    id=home_team['id'],
                    name=home_team['team']['displayName'],
                    abbreviation=home_team['team']['abbreviation'],
                    logo=home_team['team'].get('logo', ''),
                    colors={
                        'primary': home_team['team'].get('color', '#000000'),
                        'secondary': home_team['team'].get('alternateColor', '#FFFFFF')
                    },
                    record={
                        'wins': int(home_team.get('records', [{}])[0].get('wins', 0)),
                        'losses': int(home_team.get('records', [{}])[0].get('losses', 0)),
                    }
                ),
                away_team=Team(
                    id=away_team['id'],
                    name=away_team['team']['displayName'],
                    abbreviation=away_team['team']['abbreviation'],
                    logo=away_team['team'].get('logo', ''),
                    colors={
                        'primary': away_team['team'].get('color', '#000000'),
                        'secondary': away_team['team'].get('alternateColor', '#FFFFFF')
                    },
                    record={
                        'wins': int(away_team.get('records', [{}])[0].get('wins', 0)),
                        'losses': int(away_team.get('records', [{}])[0].get('losses', 0)),
                    }
                ),
                score={
                    'home': int(home_team['score']),
                    'away': int(away_team['score'])
                },
                period={
                    'current': int(competition['status'].get('period', 1)),
                    'total': 4 if league == 'NFL' else 3,
                    'time_remaining': competition['status'].get('displayClock', '0:00')
                }
            )
            
            games.append(game)
        
        return games
    
    def _map_status(self, espn_status: str) -> str:
        """Map ESPN status to our status"""
        mapping = {
            'pre': 'scheduled',
            'in': 'live',
            'post': 'final'
        }
        return mapping.get(espn_status, 'scheduled')
    
    async def test_connection(self) -> bool:
        """Test API connection"""
        try:
            async with aiohttp.ClientSession() as session:
                url = self.endpoints['espn']['nfl_scoreboard']
                async with session.get(url) as response:
                    return response.status == 200
        except:
            return False
```

**src/models.py:**
```python
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

class Team(BaseModel):
    id: str
    name: str
    abbreviation: str
    logo: str
    colors: dict[str, str]
    record: Optional[dict[str, int]] = None

class Game(BaseModel):
    id: str
    league: Literal['NFL', 'NHL']
    status: Literal['scheduled', 'live', 'final']
    start_time: str
    home_team: Team
    away_team: Team
    score: dict[str, int]
    period: dict[str, any]
    is_favorite: bool = False

class GameStats(BaseModel):
    game_id: str
    stats: dict[str, dict[str, int]]
```

**src/cache_service.py:**
```python
import asyncio
from typing import Optional, Any
import json

class CacheService:
    """Simple in-memory cache (use Redis in production)"""
    
    def __init__(self):
        self.cache: dict[str, tuple[Any, float]] = {}
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > asyncio.get_event_loop().time():
                return value
            else:
                del self.cache[key]
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60):
        """Set value in cache with TTL"""
        expiry = asyncio.get_event_loop().time() + ttl
        self.cache[key] = (value, expiry)
    
    def is_connected(self) -> bool:
        """Check if cache is available"""
        return True  # Always true for in-memory
```

### Step 2: Dashboard Frontend Integration

**Create new components in:** `services/health-dashboard/src/components/sports/`

```bash
cd services/health-dashboard/src/components
mkdir sports
```

**components/sports/SportsTab.tsx:**
```typescript
import React, { useState } from 'react';
import { useSportsData } from '../../hooks/useSportsData';
import { LiveGameCard } from './LiveGameCard';
import { UpcomingGameCard } from './UpcomingGameCard';

export const SportsTab: React.FC = () => {
  const [selectedLeague, setSelectedLeague] = useState<'all' | 'NFL' | 'NHL'>('all');
  const { liveGames, upcomingGames, loading } = useSportsData(selectedLeague);

  if (loading) {
    return <div className="text-center py-8">Loading sports data...</div>;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">🏈 NFL & 🏒 NHL Sports Center</h2>
        <button className="btn-primary">⚙️ Configure</button>
      </div>

      {/* League Filter */}
      <div className="flex gap-3">
        {(['all', 'NFL', 'NHL'] as const).map(league => (
          <button
            key={league}
            onClick={() => setSelectedLeague(league)}
            className={`px-6 py-2 rounded-lg ${
              selectedLeague === league ? 'bg-blue-500 text-white' : 'bg-gray-200'
            }`}
          >
            {league === 'all' ? 'All Sports' : league}
          </button>
        ))}
      </div>

      {/* Live Games */}
      {liveGames.length > 0 && (
        <div>
          <h3 className="text-xl font-bold mb-4">📍 LIVE NOW ({liveGames.length})</h3>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {liveGames.map(game => (
              <LiveGameCard key={game.id} game={game} />
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Games */}
      {upcomingGames.length > 0 && (
        <div>
          <h3 className="text-xl font-bold mb-4">📅 UPCOMING ({upcomingGames.length})</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {upcomingGames.map(game => (
              <UpcomingGameCard key={game.id} game={game} />
            ))}
          </div>
        </div>
      )}

      {liveGames.length === 0 && upcomingGames.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No games scheduled at this time
        </div>
      )}
    </div>
  );
};
```

**hooks/useSportsData.ts:**
```typescript
import { useState, useEffect } from 'react';
import { Game } from '../types/sports';

export const useSportsData = (league: 'all' | 'NFL' | 'NHL' = 'all') => {
  const [liveGames, setLiveGames] = useState<Game[]>([]);
  const [upcomingGames, setUpcomingGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchGames = async () => {
      try {
        setLoading(true);
        
        // Fetch live games
        const liveResponse = await fetch(
          `/api/sports/games/live${league !== 'all' ? `?league=${league}` : ''}`
        );
        const liveData = await liveResponse.json();
        setLiveGames(liveData.games);

        // Fetch upcoming games
        const upcomingResponse = await fetch(
          `/api/sports/games/upcoming${league !== 'all' ? `?league=${league}` : ''}`
        );
        const upcomingData = await upcomingResponse.json();
        setUpcomingGames(upcomingData.games);

        setError(null);
      } catch (err) {
        setError('Failed to fetch sports data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchGames();
    
    // Poll every 30 seconds
    const interval = setInterval(fetchGames, 30000);
    return () => clearInterval(interval);
  }, [league]);

  return { liveGames, upcomingGames, loading, error };
};
```

### Step 3: Docker Integration

**Add to docker-compose.yml:**
```yaml
  sports-data:
    build:
      context: ./services/sports-data
      dockerfile: Dockerfile
    container_name: homeiq-sports
    ports:
      - "8005:8005"
    environment:
      - SPORTS_API_KEY=${SPORTS_API_KEY}
      - SPORTS_API_PROVIDER=${SPORTS_API_PROVIDER:-espn}
    networks:
      - homeiq-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8005/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Update dashboard proxy in vite.config.ts:**
```typescript
proxy: {
  '/api/sports': {
    target: 'http://localhost:8005',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api\/sports/, '/api/v1'),
  },
}
```

### Step 4: Environment Variables

**Add to `.env`:**
```env
# Sports Data API Configuration
SPORTS_API_KEY=your_api_key_here
SPORTS_API_PROVIDER=espn  # or 'nhl_official', 'sportsdata'
SPORTS_UPDATE_INTERVAL=15  # seconds for live games
```

---

## 📊 Testing

### Run Backend Tests
```bash
cd services/sports-data
pytest tests/ -v
```

### Run E2E Tests
```bash
cd services/health-dashboard
npm run test:e2e -- --grep "Sports Tab"
```

---

## 🚀 Deployment

### Development
```bash
docker-compose -f docker-compose.dev.yml up -d sports-data
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d sports-data
```

---

## 📈 Monitoring

Add to Services tab monitoring:

**API Metrics to Track:**
- API call rate (calls per minute)
- Cache hit rate (should be >80%)
- Average response time (<500ms)
- Error rate (<1%)
- WebSocket connections

**Alerts to Configure:**
- API rate limit approaching (>90%)
- Cache failures
- High error rate (>5%)
- Service downtime

---

## 🔧 Configuration UI

Add sports configuration to Configuration tab:

```typescript
// In Dashboard.tsx, add new tab button:
<button onClick={() => setSelectedTab('sports-config')}>
  🏈🏒 Sports
</button>

// Add configuration form component
{selectedTab === 'sports-config' && <SportsConfiguration />}
```

---

## 📚 API Documentation

Full API documentation available at:
- http://localhost:8005/docs (Swagger UI)
- http://localhost:8005/redoc (ReDoc)

---

## 🎯 Next Steps

After Phase 1 MVP is complete:

1. **Phase 2: Enhanced Stats**
   - Implement Recharts visualizations
   - Add player statistics
   - Historical trend analysis

2. **Phase 3: Advanced Features**
   - WebSocket real-time updates
   - Push notifications
   - Fantasy integration

3. **Phase 4: More Leagues**
   - MLB integration
   - NBA integration
   - Premier League / Soccer

---

## 🐛 Troubleshooting

**API Returns 401/403:**
- Check API key is correct
- Verify API key has necessary permissions
- Check rate limits haven't been exceeded

**No Data Showing:**
- Verify backend service is running: `docker ps | grep sports`
- Check logs: `docker logs homeiq-sports`
- Test API manually: `curl http://localhost:8005/health`

**Slow Updates:**
- Check cache hit rate (should be >80%)
- Verify network connectivity
- Consider upgrading API tier for faster updates

---

## 📝 Resources

- [ESPN Hidden API Docs](http://www.espn.com/apis/devcenter/docs/)
- [NHL Official API](https://gitlab.com/dword4/nhlapi)
- [SportsData.io Documentation](https://sportsdata.io/developers)
- [Recharts Documentation](https://recharts.org/)

---

*Implementation Guide v1.0*  
*Last Updated: October 12, 2025*

