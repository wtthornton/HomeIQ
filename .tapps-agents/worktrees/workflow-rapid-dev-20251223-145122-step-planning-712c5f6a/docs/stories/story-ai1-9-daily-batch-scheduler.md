# Story AI1.9: Daily Batch Scheduler

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.9  
**Priority:** Critical  
**Estimated Effort:** 6-8 hours  
**Dependencies:** Story AI1.8 (Suggestion pipeline)

---

## User Story

**As a** system  
**I want** to run pattern analysis and suggestion generation daily at 3 AM  
**so that** users wake up to new automation suggestions

---

## Business Value

- Automated daily analysis (zero user intervention)
- Scheduled for low-usage time (3 AM)
- Ensures fresh suggestions available each day
- Publishes MQTT notifications when complete

---

## Acceptance Criteria

1. ✅ Job runs daily at 3:00 AM automatically
2. ✅ Job completes in <15 minutes (target 10 minutes)
3. ✅ MQTT notification published on completion (ha-ai/status/analysis_complete)
4. ✅ Job history stored (timestamp, duration, results)
5. ✅ Failures logged and retried next day
6. ✅ Manual trigger endpoint available for testing (/api/analyze/trigger)
7. ✅ Scheduler survives container restarts
8. ✅ No memory leaks (stable over 7-day continuous run)

---

## Technical Implementation Notes

### APScheduler Configuration

**Create: src/scheduler/daily_analysis.py**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DailyAnalysisScheduler:
    """Schedules daily pattern analysis and suggestion generation"""
    
    def __init__(self, cron_schedule: str = "0 3 * * *"):
        self.scheduler = AsyncIOScheduler()
        self.cron_schedule = cron_schedule
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        
        # Add daily analysis job
        self.scheduler.add_job(
            self.run_daily_analysis,
            CronTrigger.from_crontab(self.cron_schedule),
            id='daily_pattern_analysis',
            name='Daily Pattern Analysis',
            replace_existing=True,
            misfire_grace_time=3600  # Allow 1 hour late start
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started: daily analysis at {self.cron_schedule}")
    
    async def run_daily_analysis(self):
        """
        Main daily batch job:
        1. Fetch data from Data API
        2. Run pattern detection
        3. Generate suggestions
        4. Store in database
        5. Publish MQTT notification
        """
        
        if self.is_running:
            logger.warning("Previous analysis still running, skipping")
            return
        
        self.is_running = True
        start_time = datetime.now()
        
        try:
            logger.info("=== Starting daily analysis ===")
            
            # 1. Fetch historical data
            from src.data_api_client import DataAPIClient
            api_client = DataAPIClient()
            events = await api_client.fetch_events(start="-30d")
            logger.info(f"Fetched {len(events)} events")
            
            # 2. Run all pattern detectors
            from src.pattern_analyzer.coordinator import PatternAnalysisCoordinator
            coordinator = PatternAnalysisCoordinator()
            patterns = await coordinator.analyze_all_patterns(events)
            logger.info(f"Detected {patterns['total_patterns']} patterns")
            
            # 3. Generate suggestions
            from src.suggestion_generator import SuggestionGenerator
            from src.llm.openai_client import OpenAIClient
            
            llm = OpenAIClient(api_key=settings.openai_api_key)
            generator = SuggestionGenerator(llm)
            suggestions = await generator.generate_suggestions(patterns)
            logger.info(f"Generated {len(suggestions)} suggestions")
            
            # 4. Store in database
            from src.database.crud import store_suggestions
            await store_suggestions(suggestions)
            
            # 5. Publish MQTT notification
            from src.mqtt.client import mqtt_client
            await mqtt_client.publish(
                "ha-ai/status/analysis_complete",
                {
                    "timestamp": datetime.now().isoformat(),
                    "patterns_detected": patterns['total_patterns'],
                    "suggestions_generated": len(suggestions),
                    "duration_seconds": (datetime.now() - start_time).total_seconds()
                }
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"=== Analysis complete: {duration:.1f} seconds ===")
            
            # Store job history
            await self.store_job_history(
                status='success',
                duration=duration,
                patterns=patterns['total_patterns'],
                suggestions=len(suggestions)
            )
            
        except Exception as e:
            logger.error(f"Daily analysis failed: {e}", exc_info=True)
            await self.store_job_history(status='failed', error=str(e))
            
        finally:
            self.is_running = False
    
    async def store_job_history(self, **kwargs):
        """Store job execution history"""
        # Simple logging to database for tracking
        pass
```

### Manual Trigger Endpoint

```python
# src/api/analysis.py
from fastapi import APIRouter, BackgroundTasks

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

@router.post("/trigger")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """Manual trigger for pattern analysis (for testing)"""
    
    background_tasks.add_task(scheduler.run_daily_analysis)
    
    return {
        "message": "Analysis triggered",
        "status": "running_in_background"
    }

@router.get("/status")
async def get_analysis_status():
    """Check if analysis is currently running"""
    return {
        "is_running": scheduler.is_running,
        "last_run": await get_last_job_history()
    }
```

### FastAPI Integration

**Update: src/main.py**

```python
from src.scheduler.daily_analysis import DailyAnalysisScheduler

scheduler = DailyAnalysisScheduler(cron_schedule=settings.analysis_schedule)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting scheduler")
    scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Stopping scheduler")
    scheduler.scheduler.shutdown()
```

---

## Integration Verification

**IV1: 3 AM execution doesn't impact other services**
- Monitor CPU/memory during 3 AM run
- Verify no impact on HA automations
- Check other services responsive

**IV2: Scheduler respects container stop signals**
- Graceful shutdown on SIGTERM
- Jobs complete before shutdown if possible
- No zombie processes

**IV3: MQTT notifications received by HA**
- Home Assistant subscribes to ha-ai/status/*
- Notifications logged in HA
- Can trigger HA automations (optional)

**IV4: Job doesn't interfere with HA nightly backups**
- HA backups typically run at 4 AM
- Our job at 3 AM completes before 4 AM
- No resource contention

---

## Tasks Breakdown

1. **Create DailyAnalysisScheduler class** (2 hours)
2. **Implement run_daily_analysis workflow** (2 hours)
3. **Add job history tracking** (1 hour)
4. **Create manual trigger endpoint** (1 hour)
5. **Integrate with FastAPI lifecycle** (1 hour)
6. **Error handling and retry logic** (1 hour)
7. **MQTT notification publishing** (1 hour)
8. **Testing (unit + integration)** (1.5 hours)

**Total:** 6-8 hours

---

## Testing Strategy

### Unit Tests

```python
# tests/test_daily_analysis_scheduler.py
import pytest
from src.scheduler.daily_analysis import DailyAnalysisScheduler
from unittest.mock import AsyncMock, patch
from datetime import datetime

@pytest.mark.asyncio
async def test_scheduler_runs_job():
    """Test scheduler executes job"""
    scheduler = DailyAnalysisScheduler()
    
    with patch.object(scheduler, 'run_daily_analysis') as mock_job:
        scheduler.start()
        
        # Trigger job manually for testing
        await scheduler.run_daily_analysis()
        
        assert mock_job.called

@pytest.mark.asyncio
async def test_prevents_concurrent_runs():
    """Test doesn't start new job if previous still running"""
    scheduler = DailyAnalysisScheduler()
    scheduler.is_running = True
    
    await scheduler.run_daily_analysis()
    
    # Should skip (is_running = True)
    # Log should show "Previous analysis still running"
```

### Integration Tests

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_daily_analysis_workflow():
    """Test complete workflow end-to-end"""
    scheduler = DailyAnalysisScheduler()
    
    await scheduler.run_daily_analysis()
    
    # Verify patterns were detected
    patterns = await fetch_patterns_from_db()
    assert len(patterns) > 0
    
    # Verify suggestions were generated
    suggestions = await fetch_suggestions_from_db()
    assert len(suggestions) > 0
    
    # Verify MQTT notification sent
    # (requires MQTT test subscriber)
```

---

## Definition of Done

- [ ] DailyAnalysisScheduler implemented
- [ ] Job runs at 3 AM daily (tested)
- [ ] Complete workflow functional (fetch → analyze → generate → store)
- [ ] Job history tracking implemented
- [ ] MQTT notifications published
- [ ] Manual trigger endpoint working
- [ ] Error handling and retry logic
- [ ] Scheduler survives container restarts
- [ ] No memory leaks over 7 days
- [ ] Unit tests pass
- [ ] Integration test passes
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- APScheduler docs: https://apscheduler.readthedocs.io/
- Existing service startup patterns from `services/*/src/main.py`

---

## Notes

- 3 AM chosen for minimal HA activity
- Misfire grace time allows 1 hour late start (if system busy)
- Manual trigger critical for testing without waiting for 3 AM
- Job history helps debug failures
- MQTT notification enables HA automations (e.g., notify user)

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

