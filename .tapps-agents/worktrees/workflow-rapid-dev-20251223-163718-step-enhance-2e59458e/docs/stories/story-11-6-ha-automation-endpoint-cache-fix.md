# Story 11.6: HA Automation Endpoint Cache Fix ⚠️ CRITICAL BUG FIX

**Epic**: Epic 11 - Sports Data Integration  
**Status**: 🔄 READY FOR IMPLEMENTATION  
**Priority**: CRITICAL  
**Estimated Effort**: 0.5 days  
**Created**: October 19, 2025

---

## Problem Statement

HA automation endpoints return "none" even for live games due to cache key mismatch:

- **Main API Cache Keys**: `live_games_nhl_nfl-dal_nhl-vgk` (with team IDs)
- **HA Endpoints Look For**: `live_games_nhl` (without team IDs)
- **Result**: HA endpoints always return "none" status
- **Impact**: HA automations cannot detect when teams are playing

## Acceptance Criteria

- [ ] HA endpoints return "playing" for live games
- [ ] HA endpoints return "upcoming" for scheduled games
- [ ] Cache key format consistent across all endpoints
- [ ] HA automation endpoints respond in <50ms
- [ ] No cache key mismatches
- [ ] Fallback cache key lookups work
- [ ] HA endpoints work with multiple team formats

## Technical Implementation

### Current Cache Key Format
```python
# Sports API Client
cache_key = f"live_games_{league or 'all'}_{'_'.join(sorted(team_ids))}"
# Examples: "live_games_nhl_nfl-dal_nhl-vgk", "live_games_nfl_all"
```

### HA Endpoint Cache Lookup Fix
```python
# Current (broken)
live_games = await cache.get(f"live_games_{sport}")

# Fixed (with fallbacks)
live_games = await cache.get(f"live_games_{sport}")
if not live_games:
    live_games = await cache.get(f"live_games_{sport}_all")
if not live_games:
    # Try with actual team combinations
    live_games = await cache.get(f"live_games_{sport}_nfl-dal_nhl-vgk")
```

### Standardized Cache Key Strategy
```python
# Option 1: Always use team-specific keys
cache_key = f"live_games_{sport}_{'_'.join(sorted(team_ids))}"

# Option 2: Use fallback lookup pattern
async def get_live_games_from_cache(sport: str, team_ids: List[str] = None):
    # Try multiple cache key formats
    # Return first non-empty result
```

## Implementation Steps

1. **Update HA endpoints to use fallback cache lookups**
2. **Standardize cache key format across all endpoints**
3. **Add cache key debugging/logging**
4. **Test HA endpoints with live games**
5. **Verify response times <50ms**
6. **Test with different team combinations**

## Files to Modify

- `services/sports-data/src/ha_endpoints.py`
- `services/sports-data/src/sports_api_client.py` (optional)
- `services/sports-data/src/cache_service.py` (optional)

## Testing

- [ ] HA endpoint returns "playing" when VGK game is live
- [ ] HA endpoint returns "upcoming" for scheduled games
- [ ] Response time <50ms for HA endpoints
- [ ] Cache key lookups work with different team combinations
- [ ] No cache key mismatches in logs
- [ ] Fallback lookups work when primary cache miss

## Dependencies

- Story 11.5: Team Persistence Implementation (for consistent team data)
- Existing cache service
- Live games data (VGK game currently live)

## Definition of Done

- [ ] All acceptance criteria met
- [ ] HA endpoints return correct game status
- [ ] Response times <50ms verified
- [ ] Cache key consistency verified
- [ ] Manual testing with live games
- [ ] No regression in main API endpoints
- [ ] Documentation updated
