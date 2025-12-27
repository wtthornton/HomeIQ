# Story 46.2: Built-in Nightly Training Scheduler

**Story ID:** 46.2  
**Epic:** 46 (Enhanced ML Training Data and Nightly Training Automation)  
**Status:** 📋 Ready for Development  
**Priority:** P1 (High for Alpha)  
**Story Points:** 5  
**Complexity:** Medium  
**Estimated Effort:** 4-5 hours

---

## Story Description

Integrate APScheduler into device-intelligence-service to enable automatic nightly model training without requiring users to set up external cron/Task Scheduler. This provides a seamless experience where models improve automatically with user data. Follows the proven APScheduler pattern from `ai-automation-service` (already in production). **NUC-optimized**: Uses incremental learning by default (10-50x faster, less resource-intensive).

## User Story

**As a** system user  
**I want** automatic nightly model training  
**So that** my models improve continuously without manual setup or intervention

## Acceptance Criteria

### AC1: APScheduler Integration
- [ ] Install APScheduler dependency in requirements.txt
- [ ] Create `training_scheduler.py` module
- [ ] Integrate scheduler with FastAPI lifecycle (startup/shutdown)
- [ ] Configurable training schedule via environment variables
- [ ] Default schedule: 2 AM daily
- [ ] Support for cron expressions and interval-based scheduling

### AC2: Training Schedule Configuration
- [ ] Environment variable: `ML_TRAINING_SCHEDULE` (default: "0 2 * * *")
- [ ] Environment variable: `ML_TRAINING_ENABLED` (default: true)
- [ ] Environment variable: `ML_TRAINING_MODE` (default: "incremental")
- [ ] Support for "full" and "incremental" training modes
- [ ] Configuration validation on startup
- [ ] Clear error messages for invalid configurations

### AC3: Automatic Training Execution
- [ ] Scheduler triggers training at configured time
- [ ] Support for full retrain mode (complete model retraining)
- [ ] Support for incremental update mode (10-50x faster) - **default mode**
- [ ] Automatic data collection (last 180 days by default)
- [ ] Training runs in background (non-blocking)
- [ ] Concurrent run prevention (skip if already running)
- [ ] **NUC-optimized**: Resource-efficient, CPU-only, no GPU required

### AC4: Health Monitoring and Error Handling
- [ ] Training status tracking (running, completed, failed)
- [ ] Error handling and logging
- [ ] Retry logic for transient failures
- [ ] Health check integration (training status in health endpoint)
- [ ] Metrics tracking (last training time, success/failure)
- [ ] Alert on repeated failures

### AC5: Manual Trigger Capability
- [ ] API endpoint: `POST /api/predictions/train/schedule` - Trigger training now
- [ ] API endpoint: `GET /api/predictions/train/status` - Get scheduler status
- [ ] Support for immediate training (bypass schedule)
- [ ] Support for scheduled training (add to queue)
- [ ] Response includes training status and estimated completion time

### AC6: Logging and Observability
- [ ] Log scheduler startup and shutdown
- [ ] Log training trigger events
- [ ] Log training completion and results
- [ ] Log errors with context
- [ ] Training metrics in health endpoint
- [ ] Last training time and status visible

### AC7: Graceful Shutdown
- [ ] Wait for running training to complete on shutdown
- [ ] Cancel scheduled training on shutdown
- [ ] Clean resource cleanup
- [ ] No data loss or corruption

## Technical Requirements

### Modified Files

**1. `services/device-intelligence-service/src/main.py`**
```python
from src.scheduler.training_scheduler import TrainingScheduler

@app.on_event("startup")
async def startup_event():
    # Start training scheduler
    scheduler = TrainingScheduler(settings)
    scheduler.start()
    app.state.training_scheduler = scheduler

@app.on_event("shutdown")
async def shutdown_event():
    # Stop training scheduler
    if hasattr(app.state, 'training_scheduler'):
        app.state.training_scheduler.stop()
```

**2. `services/device-intelligence-service/src/config.py`**
```python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Training Scheduler Configuration
    ML_TRAINING_SCHEDULE: str = Field(
        default="0 2 * * *",
        description="Cron expression for training schedule (default: 2 AM daily)"
    )
    ML_TRAINING_ENABLED: bool = Field(
        default=True,
        description="Enable automatic nightly training"
    )
    ML_TRAINING_MODE: str = Field(
        default="incremental",
        description="Training mode: 'full' or 'incremental'"
    )
```

**3. `services/device-intelligence-service/src/api/predictions_router.py`**
- Add manual trigger endpoint
- Add scheduler status endpoint

### New Files

**1. `services/device-intelligence-service/src/scheduler/training_scheduler.py`**
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class TrainingScheduler:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
    
    def start(self):
        """Start the training scheduler."""
        if not self.settings.ML_TRAINING_ENABLED:
            logger.info("Training scheduler disabled")
            return
        
        # Add scheduled job
        self.scheduler.add_job(
            self._run_training,
            trigger=CronTrigger.from_crontab(self.settings.ML_TRAINING_SCHEDULE),
            id='nightly_training',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"Training scheduler started (schedule: {self.settings.ML_TRAINING_SCHEDULE})")
    
    async def _run_training(self):
        """Execute scheduled training."""
        if self.is_running:
            logger.warning("Training already running, skipping scheduled run")
            return
        
        self.is_running = True
        try:
            # Execute training based on mode
            if self.settings.ML_TRAINING_MODE == "incremental":
                # Use incremental update if available
                await self._run_incremental_training()
            else:
                # Full retrain
                await self._run_full_training()
        except Exception as e:
            logger.error(f"Error during scheduled training: {e}")
        finally:
            self.is_running = False
```

**2. `services/device-intelligence-service/requirements.txt`**
- Add: `APScheduler>=3.10.0,<4.0.0`

### Integration Points

**With Existing Training:**
- Uses `PredictiveAnalyticsEngine.train_models()` for full retrain
- Uses `PredictiveAnalyticsEngine.update_models_incremental()` for incremental updates
- Respects existing model configuration (ML_FAILURE_MODEL, etc.)

**With Health Monitoring:**
- Training status in health endpoint
- Last training time and status
- Training metrics tracking

## Testing Requirements

### Unit Tests
- [ ] Scheduler initialization and configuration
- [ ] Schedule parsing and validation
- [ ] Training trigger logic
- [ ] Concurrent run prevention
- [ ] Error handling

### Integration Tests
- [ ] Scheduler starts with FastAPI
- [ ] Training executes at scheduled time
- [ ] Manual trigger works
- [ ] Status endpoint returns correct information
- [ ] Graceful shutdown works

### Manual Testing
- [ ] Test with different schedules (every minute for testing)
- [ ] Test full retrain mode
- [ ] Test incremental update mode
- [ ] Test manual trigger
- [ ] Test error scenarios
- [ ] Test graceful shutdown

## Dependencies

**Depends on:**
- APScheduler library (already used in ai-automation-service)
- Existing `PredictiveAnalyticsEngine` training methods
- FastAPI lifecycle events

**Enables:**
- User autonomy (no manual setup)
- Continuous model improvement
- Alpha release with automated training

## Configuration Examples

**Default (Nightly at 2 AM, Incremental):**
```bash
ML_TRAINING_SCHEDULE="0 2 * * *"
ML_TRAINING_ENABLED=true
ML_TRAINING_MODE=incremental
```

**Weekly (Sundays at 2 AM, Full Retrain):**
```bash
ML_TRAINING_SCHEDULE="0 2 * * 0"
ML_TRAINING_MODE=full
```

**Disable Automatic Training:**
```bash
ML_TRAINING_ENABLED=false
```

## Definition of Done

- [ ] APScheduler integrated into device-intelligence-service
- [ ] Configurable training schedule
- [ ] Automatic training executes at scheduled time
- [ ] Manual trigger endpoint works
- [ ] Health monitoring integration
- [ ] Graceful shutdown handling
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Documentation complete
- [ ] Code reviewed and approved

## Related Stories

- **Story 46.1**: Synthetic Device Data Generator (initial training data)
- **Story 46.3**: Enhanced Initial Training Pipeline (uses scheduler for validation)
- **Epic DI-3.3**: Predictive Analytics Engine (training infrastructure)

---

**Last Updated:** December 2025  
**Status:** 📋 Ready for Development

