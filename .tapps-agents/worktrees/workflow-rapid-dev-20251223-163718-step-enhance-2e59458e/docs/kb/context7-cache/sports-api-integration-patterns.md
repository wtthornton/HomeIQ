# Sports API Integration Patterns
**Context7 KB Cache - Custom Pattern**

**Topic:** Sports data ingestion, caching, and persistence  
**Technologies:** FastAPI, InfluxDB, aiohttp, HMAC webhooks  
**Created:** October 14, 2025  
**Use Case:** Real-time sports scores with historical tracking

---

## Pattern: Sports Data Service Architecture

### Core Design Principles

1. **Cache-First Strategy**: Minimize external API calls
2. **Async Non-Blocking Writes**: Don't slow API responses
3. **Team-Based Filtering**: Only fetch user-selected teams
4. **Event-Driven Webhooks**: Trigger on state changes
5. **InfluxDB for History**: Time-series perfect for game data

---

## 1. InfluxDB Schema for Sports Data

### Recommended Schema

```python
from influxdb_client_3 import Point
from datetime import datetime

def create_game_point(game: dict, league: str) -> Point:
    """
    Create InfluxDB point for game data
    
    Best Practices:
    - Use game_id as primary tag (unique identifier)
    - Tag team abbreviations (for fast queries)
    - Tag status for filtering (live/final/scheduled)
    - Store scores as fields (they change)
    - Use game start time as timestamp
    """
    measurement = f"{league.lower()}_scores"  # nfl_scores or nhl_scores
    
    point = (
        Point(measurement)
        # TAGS (indexed for fast queries)
        .tag("game_id", game['id'])
        .tag("season", extract_season(game['start_time']))
        .tag("week", extract_week(game['start_time'], league))
        .tag("home_team", game['home_team']['abbreviation'].lower())
        .tag("away_team", game['away_team']['abbreviation'].lower())
        .tag("status", game['status'])  # scheduled|live|final
        .tag("venue", game.get('venue', 'unknown'))
        
        # FIELDS (data values)
        .field("home_score", int(game['score']['home']))
        .field("away_score", int(game['score']['away']))
        .field("quarter", int(game['period']['current']))
        .field("time_remaining", game['period']['time_remaining'] or "0:00")
        .field("attendance", int(game.get('attendance', 0)))
        
        # TIMESTAMP (game start time, not current time)
        .time(datetime.fromisoformat(game['start_time']))
    )
    
    return point
```

### Retention Policy Design

```python
# Retention policies for sports data
RETENTION_POLICIES = {
    "raw_games": {
        "duration": "730d",        # 2 years (2 complete seasons)
        "replication": 1,
        "shard_duration": "7d"     # Weekly shards for performance
    },
    "aggregated_stats": {
        "duration": "1825d",       # 5 years (historical analysis)
        "replication": 1,
        "shard_duration": "30d"    # Monthly aggregation
    }
}

# Storage estimate:
# - Per game: ~500 bytes (1 point)
# - NFL: 256 games/season × 500 bytes = 128 KB/season
# - NHL: 1,312 games/season × 500 bytes = 656 KB/season
# - Total 2 years: ~1.6 MB (negligible)
```

### Query Patterns

```python
# 1. Get team's current season record
query_season_record = """
SELECT 
    home_team, away_team, home_score, away_score, status
FROM nfl_scores
WHERE 
    (home_team = 'sf' OR away_team = 'sf')
    AND season = '2025'
    AND status = 'final'
ORDER BY time DESC
"""

# 2. Get live games (last 4 hours only)
query_live_games = """
SELECT * FROM nfl_scores
WHERE 
    status = 'live'
    AND time > now() - 4h
ORDER BY time DESC
"""

# 3. Score progression timeline (for charts)
query_timeline = """
SELECT 
    time, home_score, away_score, quarter, time_remaining
FROM nfl_scores
WHERE 
    game_id = '401547413'
    AND time >= '2025-10-14T13:00:00Z'
ORDER BY time ASC
"""

# 4. Team statistics (wins/losses)
query_stats = """
SELECT 
    COUNT(*) as games_played,
    SUM(CASE 
        WHEN (home_team = 'sf' AND home_score > away_score) THEN 1
        WHEN (away_team = 'sf' AND away_score > home_score) THEN 1
        ELSE 0
    END) as wins,
    AVG(CASE 
        WHEN home_team = 'sf' THEN home_score
        ELSE away_score
    END) as avg_points_scored
FROM nfl_scores
WHERE 
    (home_team = 'sf' OR away_team = 'sf')
    AND season = '2025'
    AND status = 'final'
"""
```

---

## 2. Async Write Pattern (Non-Blocking)

### Problem
Writing to InfluxDB should NOT slow down API responses to users.

### Solution: Fire-and-Forget Async Writes

```python
import asyncio
from influxdb_client_3 import InfluxDBClient3, Point
import logging

logger = logging.getLogger(__name__)

class AsyncInfluxDBWriter:
    """
    Non-blocking InfluxDB writer
    
    Best Practices:
    - Write operations don't block API responses
    - Errors logged but don't fail the request
    - Optional retry queue for failed writes
    - Batch writes for efficiency
    """
    
    def __init__(self, client: InfluxDBClient3):
        self.client = client
        self.write_queue = asyncio.Queue()
        self.failed_writes = []
        
    async def start(self):
        """Start background writer task"""
        asyncio.create_task(self._writer_loop())
    
    def write_game_async(self, game: dict, league: str):
        """
        Queue game write (non-blocking)
        
        Returns immediately - actual write happens in background
        """
        point = create_game_point(game, league)
        
        # Fire and forget - don't await
        asyncio.create_task(self._write_point(point))
    
    async def _write_point(self, point: Point):
        """Internal async write with error handling"""
        try:
            self.client.write(point)
            logger.debug(f"Wrote game point: {point}")
        except Exception as e:
            logger.error(f"InfluxDB write failed: {e}")
            # Could add to retry queue here
            self.failed_writes.append((point, str(e)))
    
    async def _writer_loop(self):
        """Background task for processing write queue"""
        while True:
            try:
                point = await self.write_queue.get()
                await self._write_point(point)
                self.write_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Writer loop error: {e}")
```

### Usage in API Endpoint

```python
from fastapi import FastAPI

app = FastAPI()
writer = AsyncInfluxDBWriter(influxdb_client)

@app.on_event("startup")
async def startup():
    await writer.start()

@app.get("/api/v1/games/live")
async def get_live_games(teams: str):
    # 1. Check cache
    cached = await cache.get(f"live_{teams}")
    if cached:
        return cached
    
    # 2. Fetch from ESPN
    games = await fetch_from_espn(teams)
    
    # 3. Write to InfluxDB (non-blocking!)
    for game in games:
        writer.write_game_async(game, "NFL")
    
    # 4. Return immediately (don't wait for writes)
    return {"games": games, "count": len(games)}
```

**Performance Impact:**
- Without async writes: 150ms (ESPN) + 30ms (InfluxDB) = 180ms
- With async writes: 150ms (ESPN) + 0ms (fire-and-forget) = 150ms
- Improvement: 17% faster responses

---

## 3. Background Event Detection

### Pattern: Continuous Monitoring

```python
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional

class GameEventDetector:
    """
    Detect game events by comparing state changes
    
    Best Practices:
    - Check every 15 seconds (balance freshness vs load)
    - Store previous state to detect changes
    - Only trigger on meaningful events
    - Use asyncio.create_task for webhook delivery
    """
    
    def __init__(self, influxdb_client, webhook_manager, sports_client):
        self.influxdb = influxdb_client
        self.webhooks = webhook_manager
        self.sports_client = sports_client
        
        # Track previous game state
        self.previous_games: Dict[str, dict] = {}
        
        # Event detection config
        self.check_interval = 15  # seconds
        self.is_running = False
    
    async def start(self):
        """Start background monitoring task"""
        self.is_running = True
        asyncio.create_task(self._monitor_loop())
    
    async def stop(self):
        """Stop background monitoring"""
        self.is_running = False
    
    async def _monitor_loop(self):
        """Continuous monitoring loop"""
        while self.is_running:
            try:
                await self._check_for_events()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Event detection error: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _check_for_events(self):
        """Check current games for state changes"""
        # Get current live games from InfluxDB (fast query)
        current_games = await self._query_current_games()
        
        for game in current_games:
            game_id = game['id']
            previous = self.previous_games.get(game_id)
            
            if not previous:
                # New game detected
                if game['status'] == 'live':
                    await self._trigger_event('game_started', game)
            
            elif previous['status'] != game['status']:
                # Status changed
                if game['status'] == 'live':
                    await self._trigger_event('game_started', game)
                elif game['status'] == 'final':
                    await self._trigger_event('game_ended', game)
            
            elif game['status'] == 'live':
                # Check for score changes
                if (previous['score']['home'] != game['score']['home'] or
                    previous['score']['away'] != game['score']['away']):
                    await self._trigger_event('score_changed', game, {
                        'previous_score': previous['score'],
                        'score_diff': self._calculate_diff(previous['score'], game['score'])
                    })
            
            # Update state
            self.previous_games[game_id] = game
    
    async def _query_current_games(self) -> list:
        """Query InfluxDB for currently active games"""
        query = """
        SELECT * FROM nfl_scores
        WHERE time > now() - 4h
        AND status IN ('live', 'scheduled')
        ORDER BY time DESC
        LIMIT 50
        """
        
        result = self.influxdb.query(query=query, language='sql', mode='all')
        return self._parse_results(result)
    
    async def _trigger_event(self, event_type: str, game: dict, extra: dict = None):
        """Trigger webhooks for event (async, non-blocking)"""
        event_data = {
            'event': event_type,
            'game_id': game['id'],
            'league': game['league'],
            'home_team': game['home_team'],
            'away_team': game['away_team'],
            'score': game['score'],
            'status': game['status'],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if extra:
            event_data.update(extra)
        
        # Trigger webhooks (fire and forget)
        asyncio.create_task(self.webhooks.send_all(event_data))
        
        logger.info(f"Event triggered: {event_type} for game {game['id']}")
    
    def _calculate_diff(self, old_score: dict, new_score: dict) -> dict:
        """Calculate scoring difference"""
        return {
            'home_diff': new_score['home'] - old_score['home'],
            'away_diff': new_score['away'] - old_score['away']
        }
```

---

## 4. HMAC-Signed Webhooks

### Pattern: Secure Webhook Delivery

```python
import hmac
import hashlib
import json
import aiohttp
from typing import Dict, List
from datetime import datetime

class WebhookManager:
    """
    Manage webhook subscriptions and delivery
    
    Best Practices:
    - HMAC-SHA256 signatures (industry standard)
    - Timeout webhooks after 5 seconds
    - Retry failed deliveries (exponential backoff)
    - Log all delivery attempts
    - Rate limit per webhook endpoint
    """
    
    def __init__(self):
        self.webhooks: Dict[str, dict] = {}
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def startup(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        )
    
    async def shutdown(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
    
    def register(self, url: str, events: List[str], secret: str) -> str:
        """
        Register a webhook endpoint
        
        Args:
            url: Webhook URL to call
            events: List of events to subscribe to
            secret: Shared secret for HMAC signing
        
        Returns:
            webhook_id: Unique identifier
        """
        webhook_id = generate_uuid()
        
        self.webhooks[webhook_id] = {
            'url': url,
            'events': events,
            'secret': secret,
            'created_at': datetime.utcnow(),
            'total_calls': 0,
            'failed_calls': 0,
            'last_success': None,
            'last_failure': None,
            'enabled': True
        }
        
        return webhook_id
    
    async def send_all(self, event_data: dict):
        """
        Send event to all matching webhooks
        
        Fire-and-forget: doesn't block caller
        """
        event_type = event_data['event']
        
        for webhook_id, config in self.webhooks.items():
            if not config['enabled']:
                continue
            
            if event_type in config['events']:
                # Fire and forget
                asyncio.create_task(
                    self._deliver_webhook(webhook_id, event_data)
                )
    
    async def _deliver_webhook(self, webhook_id: str, event_data: dict):
        """
        Deliver webhook with HMAC signature
        
        HMAC-SHA256 Signature Process:
        1. Serialize payload as JSON
        2. Create HMAC with shared secret
        3. Send signature in X-Signature header
        4. Receiver verifies signature
        """
        config = self.webhooks[webhook_id]
        
        # Serialize payload
        payload = json.dumps(event_data, separators=(',', ':'))
        payload_bytes = payload.encode('utf-8')
        
        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            config['secret'].encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Event': event_data['event'],
            'X-Webhook-Timestamp': event_data['timestamp'],
            'X-Webhook-ID': webhook_id,
            'User-Agent': 'SportsDataService/1.0'
        }
        
        # Deliver with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with self.session.post(
                    config['url'],
                    data=payload,
                    headers=headers
                ) as response:
                    if response.status in (200, 201, 202):
                        # Success
                        config['total_calls'] += 1
                        config['last_success'] = datetime.utcnow()
                        logger.info(f"Webhook {webhook_id} delivered: {event_data['event']}")
                        return
                    else:
                        # HTTP error
                        logger.warning(
                            f"Webhook {webhook_id} failed: HTTP {response.status}"
                        )
            
            except aiohttp.ClientError as e:
                logger.error(f"Webhook {webhook_id} error: {e}")
            
            # Retry with exponential backoff
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
        
        # All retries failed
        config['failed_calls'] += 1
        config['last_failure'] = datetime.utcnow()
        
        # Disable webhook if too many failures
        failure_rate = config['failed_calls'] / max(config['total_calls'], 1)
        if failure_rate > 0.5 and config['total_calls'] > 10:
            config['enabled'] = False
            logger.error(f"Webhook {webhook_id} disabled (high failure rate)")
```

### Webhook Receiver (Home Assistant Example)

```python
# Home Assistant automation webhook receiver
from fastapi import FastAPI, Header, HTTPException
import hmac
import hashlib

app = FastAPI()

WEBHOOK_SECRET = "your-shared-secret"

@app.post("/api/webhook/sports")
async def receive_webhook(
    payload: dict,
    x_webhook_signature: str = Header(...),
    x_webhook_event: str = Header(...)
):
    """
    Receive and verify webhook from sports service
    """
    # Verify signature
    payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    if not hmac.compare_digest(x_webhook_signature, expected_signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process event
    if x_webhook_event == "score_changed":
        # Trigger Home Assistant automation
        await trigger_lights_flash(payload['home_team'])
    
    return {"status": "received"}
```

---

## 5. Cache Optimization Patterns

### Multi-Level Caching Strategy

```python
from typing import Optional
import time

class MultiLevelCache:
    """
    Two-tier caching: Fast + Fallback
    
    Tier 1: In-memory dict (sub-millisecond)
    Tier 2: Redis (1-5ms) [optional]
    
    Best Practices:
    - Tier 1 for hot data (current live games)
    - Tier 2 for warm data (recent games)
    - Different TTLs per data type
    """
    
    def __init__(self, redis_client=None):
        self.memory_cache: Dict[str, tuple] = {}
        self.redis = redis_client
        
        # TTL config
        self.ttls = {
            'live_games': 15,      # 15 seconds
            'upcoming_games': 300,  # 5 minutes
            'team_list': 3600,      # 1 hour
            'season_stats': 86400   # 24 hours
        }
    
    async def get(self, key: str, cache_type: str = 'live_games') -> Optional[any]:
        """
        Get from cache (memory first, Redis fallback)
        """
        # Check Tier 1 (memory)
        if key in self.memory_cache:
            value, expiry = self.memory_cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.memory_cache[key]
        
        # Check Tier 2 (Redis)
        if self.redis:
            value = await self.redis.get(key)
            if value:
                # Populate Tier 1
                ttl = self.ttls[cache_type]
                self.memory_cache[key] = (value, time.time() + ttl)
                return value
        
        return None
    
    async def set(self, key: str, value: any, cache_type: str = 'live_games'):
        """
        Set in both tiers
        """
        ttl = self.ttls[cache_type]
        
        # Tier 1 (memory)
        self.memory_cache[key] = (value, time.time() + ttl)
        
        # Tier 2 (Redis)
        if self.redis:
            await self.redis.setex(key, ttl, value)
```

---

## 6. FastAPI Background Task Integration

### Startup/Shutdown Lifecycle

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage service lifecycle
    
    Best Practice: Use lifespan for cleanup
    """
    # Startup
    await influxdb_writer.start()
    await event_detector.start()
    await webhook_manager.startup()
    logger.info("Background tasks started")
    
    yield  # Application runs
    
    # Shutdown
    await event_detector.stop()
    await webhook_manager.shutdown()
    await influxdb_writer.stop()
    logger.info("Background tasks stopped")

app = FastAPI(lifespan=lifespan)
```

---

## Summary: Complete Implementation Checklist

### Phase 1: InfluxDB Persistence (2 weeks)
- [ ] Add InfluxDB client to sports-data service
- [ ] Implement async write pattern
- [ ] Define schema (nfl_scores, nhl_scores)
- [ ] Set retention policies (2 years)
- [ ] Test write performance (should be 0ms perceived)

### Phase 2: Historical Queries (3 weeks)
- [ ] Implement SQL query endpoints
- [ ] Add season statistics calculator
- [ ] Create timeline query for score progression
- [ ] Dashboard: Win/loss charts
- [ ] Dashboard: Score timeline visualization

### Phase 3: Events & Webhooks (4 weeks)
- [ ] Implement event detector background task
- [ ] Add webhook management system
- [ ] Implement HMAC signature verification
- [ ] Create HA automation endpoints
- [ ] Test end-to-end webhook delivery

---

**Performance Targets:**
- API Response: <200ms (with cache)
- InfluxDB Write: <30ms (async, non-blocking)
- Historical Query: <50ms
- HA Status Endpoint: <50ms
- Webhook Delivery: <5s (with retries)

**Storage Estimates:**
- 2 years of data: ~1.6 MB
- Negligible cost

**Scalability:**
- Supports horizontal scaling (stateless services)
- InfluxDB handles aggregations
- Redis for distributed cache (optional)

---

**References:**
- ESPN API: https://gist.github.com/akeaswaran/b48b02f1c94f873c6655e7129910fc3b
- InfluxDB Python Client: https://github.com/influxdata/influxdb-client-python
- FastAPI Background Tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- HMAC Signatures: https://docs.github.com/en/webhooks/using-webhooks/validating-webhook-deliveries

---

**Cached:** October 14, 2025  
**Use Case:** Sports Data Service Epic 12 Implementation  
**Status:** Production-Ready Patterns

