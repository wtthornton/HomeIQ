# Story AI4.4: Weekly Community Refresh

**Epic:** AI-4 (Community Knowledge Augmentation)  
**Status:** InProgress  
**Created:** October 18, 2025  
**Estimated Effort:** 2 days  
**Dependencies:** Story AI4.1 (Community Corpus Foundation) ✅ Complete

---

## Story

**As a** Home Assistant user,  
**I want** the community automation corpus to stay fresh with new ideas,  
**so that** I receive suggestions based on the latest community innovations and trends.

---

## Acceptance Criteria

### Functional Requirements

1. **Weekly Incremental Crawl** (User Requirement: Weekly Refresh)
   - Scheduled job: Every Sunday at 2 AM (local time)
   - Fetches new/updated content since last crawl (incremental, not full re-crawl)
   - Queries Discourse API with `since` parameter (last_crawl_timestamp)
   - Processes 50-200 new posts typical (vs 2,000-3,000 initial)
   - Duration: 15-30 minutes (vs 3 hours initial crawl)

2. **Quality Score Updates**
   - Updates vote counts for existing automations
   - Recalculates quality scores (votes may have increased)
   - Re-ranks automations by updated quality
   - Identifies "trending" automations (rapid vote increase)

3. **Corpus Pruning**
   - Removes low-quality entries (quality_score < 0.4)
   - Removes stale entries (>2 years old, <100 votes)
   - Removes duplicates discovered since last refresh
   - Target: Keep corpus under 3,000 high-quality automations

4. **Automatic Cache Invalidation**
   - Clear query result caches after refresh (Stories AI4.2, AI4.3)
   - Notify dependent services (ai-automation-service) of corpus update
   - Trigger re-analysis if significant corpus changes (>100 new automations)

### Reliability Requirements

5. **Job Robustness**
   - Retry logic: 3 attempts with exponential backoff (1min, 5min, 15min)
   - Graceful degradation: If refresh fails, use existing corpus (no data loss)
   - Alert if refresh fails 3 consecutive weeks
   - Health check: Track last successful refresh timestamp

6. **Data Integrity**
   - Atomic updates: Use database transactions (commit all or rollback all)
   - Backup before pruning: Keep deleted entries for 30 days
   - Audit log: Track all changes (added, updated, deleted counts)

### Performance Requirements

7. **Resource Efficiency**
   - Network: <20MB data transfer per refresh (incremental only)
   - Memory: <200MB peak usage
   - CPU: <10% average during refresh
   - Storage: Corpus growth <50MB/month after pruning

8. **Non-Disruptive**
   - Does NOT impact daily AI analysis job (3 AM, 1 hour after refresh)
   - Query API remains available during refresh (read-only mode)
   - Refresh completes in <30 minutes (99% of cases)

---

## Tasks / Subtasks

### Task 1: Implement Weekly Crawl Job (AC: 1, 5)
- [ ] Create `services/automation-miner/src/jobs/weekly_refresh_job.py`
  ```python
  from apscheduler import AsyncScheduler
  from apscheduler.triggers.cron import CronTrigger
  from datetime import datetime, timedelta
  import logging
  
  logger = logging.getLogger(__name__)
  
  class WeeklyRefreshJob:
      def __init__(
          self,
          discourse_client: DiscourseClient,
          parser: AutomationParser,
          repo: CorpusRepository
      ):
          self.client = discourse_client
          self.parser = parser
          self.repo = repo
      
      async def run(self):
          """
          Weekly corpus refresh
          Runs every Sunday at 2 AM
          """
          correlation_id = str(uuid4())
          logger.info(f"[{correlation_id}] Starting weekly corpus refresh...")
          
          try:
              # Step 1: Get last crawl timestamp
              last_crawl = await self.repo.get_last_crawl_timestamp()
              logger.info(f"[{correlation_id}] Last crawl: {last_crawl}")
              
              # Step 2: Fetch new/updated posts
              new_posts = await self.client.fetch_blueprints(
                  min_likes=100,  # Lower threshold for recent posts
                  since=last_crawl,
                  limit=500
              )
              logger.info(f"[{correlation_id}] Found {len(new_posts)} new/updated posts")
              
              # Step 3: Process new posts
              added_count = 0
              for post in new_posts:
                  try:
                      details = await self.client.fetch_post_details(post['id'])
                      metadata = self.parser.parse_automation(details)
                      
                      # Check if already exists (by source_id)
                      existing = await self.repo.get_by_source_id(
                          source='discourse',
                          source_id=str(post['id'])
                      )
                      
                      if existing:
                          # Update existing (votes may have increased)
                          await self.repo.update(existing.id, metadata)
                      else:
                          # Add new
                          if not await self.repo.is_duplicate(metadata):
                              await self.repo.save(metadata)
                              added_count += 1
                  
                  except Exception as e:
                      logger.error(f"[{correlation_id}] Failed to process post {post['id']}: {e}")
                      continue
              
              # Step 4: Update quality scores for existing entries
              updated_count = await self._update_quality_scores(correlation_id)
              
              # Step 5: Prune low-quality entries
              pruned_count = await self._prune_corpus(correlation_id)
              
              # Step 6: Update last crawl timestamp
              await self.repo.set_last_crawl_timestamp(datetime.utcnow())
              
              # Step 7: Invalidate caches
              await self._invalidate_caches(correlation_id)
              
              # Step 8: Log summary
              stats = await self.repo.get_stats()
              logger.info(f"[{correlation_id}] ✅ Weekly refresh complete:")
              logger.info(f"  - Added: {added_count} new automations")
              logger.info(f"  - Updated: {updated_count} quality scores")
              logger.info(f"  - Pruned: {pruned_count} stale entries")
              logger.info(f"  - Total corpus: {stats['total']} automations")
              logger.info(f"  - Avg quality: {stats['avg_quality']:.2f}")
              
              # Alert if significant changes
              if added_count > 100:
                  await self._notify_significant_update(added_count)
          
          except Exception as e:
              logger.error(f"[{correlation_id}] ❌ Weekly refresh failed: {e}")
              raise  # APScheduler will retry
  ```
- [ ] Implement `_update_quality_scores()`
  ```python
  async def _update_quality_scores(self, correlation_id: str) -> int:
      """
      Re-fetch vote counts and update quality scores
      """
      updated = 0
      
      # Get all discourse automations
      all_autos = await self.repo.get_all(source='discourse')
      
      for auto in all_autos:
          try:
              # Re-fetch vote count from Discourse
              post = await self.client.fetch_post_metadata(auto.source_id)
              
              if post['likes'] != auto.vote_count:
                  # Votes changed, recalculate quality
                  new_quality = self.parser.calculate_quality_score(
                      votes=post['likes'],
                      age_days=(datetime.utcnow() - auto.created_at).days,
                      completeness=auto.metadata.get('completeness', 1.0)
                  )
                  
                  await self.repo.update(auto.id, {
                      'vote_count': post['likes'],
                      'quality_score': new_quality
                  })
                  updated += 1
          
          except Exception as e:
              logger.warning(f"[{correlation_id}] Failed to update {auto.id}: {e}")
              continue
      
      return updated
  ```
- [ ] Implement `_prune_corpus()` (AC: 3, 6)
  ```python
  async def _prune_corpus(self, correlation_id: str) -> int:
      """
      Remove low-quality and stale entries
      """
      pruned = 0
      
      # Criteria for pruning
      cutoff_date = datetime.utcnow() - timedelta(days=730)  # 2 years
      
      # Find candidates
      to_prune = await self.repo.find({
          'OR': [
              {'quality_score': {'<': 0.4}},
              {
                  'AND': [
                      {'created_at': {'<': cutoff_date}},
                      {'vote_count': {'<': 100}}
                  ]
              }
          ]
      })
      
      # Backup before deletion (soft delete)
      for auto in to_prune:
          await self.repo.soft_delete(auto.id)  # Marks as deleted, keeps for 30 days
          pruned += 1
      
      logger.info(f"[{correlation_id}] Pruned {pruned} low-quality/stale entries")
      
      return pruned
  ```
- [ ] Add retry logic to job scheduler
  ```python
  from apscheduler.triggers.cron import CronTrigger
  from apscheduler.job import Job
  
  async def setup_weekly_refresh(scheduler: AsyncScheduler):
      """Setup weekly refresh job with retry"""
      
      await scheduler.add_schedule(
          weekly_refresh_job.run,
          CronTrigger(day_of_week='sun', hour=2, minute=0),
          id="weekly_corpus_refresh",
          max_instances=1,  # Prevent overlap
          coalesce=True,     # Skip if previous run still active
          misfire_grace_time=3600  # Allow 1 hour delay if server was down
      )
  ```

### Task 2: Implement Cache Invalidation (AC: 4)
- [ ] Extend `MinerClient` (from Story AI4.2) with cache management
  ```python
  class MinerClient:
      _cache: Dict[str, Any] = {}
      _cache_timestamps: Dict[str, datetime] = {}
      
      async def invalidate_all_caches(self):
          """Clear all cached query results"""
          self._cache.clear()
          self._cache_timestamps.clear()
          logger.info("✅ All Miner caches invalidated")
      
      async def notify_corpus_updated(self, added_count: int):
          """Notify dependent services of corpus update"""
          # Webhook to ai-automation-service
          try:
              async with httpx.AsyncClient() as client:
                  await client.post(
                      "http://localhost:8018/api/webhooks/miner-updated",
                      json={"added_count": added_count, "timestamp": datetime.utcnow().isoformat()}
                  )
          except Exception as e:
              logger.warning(f"Failed to notify ai-automation-service: {e}")
  ```
- [ ] Implement webhook endpoint in `ai-automation-service`
  ```python
  @router.post("/webhooks/miner-updated")
  async def handle_miner_update(payload: dict):
      """Handle Miner corpus update notification"""
      added_count = payload['added_count']
      
      logger.info(f"Miner corpus updated: {added_count} new automations")
      
      # Clear local caches
      await miner_client.invalidate_all_caches()
      
      # Trigger re-analysis if significant update (>100 new)
      if added_count > 100:
          logger.info("Significant corpus update, scheduling re-analysis...")
          await scheduler.add_schedule(
              run_daily_analysis,
              DateTrigger(run_time=datetime.now() + timedelta(minutes=5)),
              id="corpus_update_reanalysis"
          )
      
      return {"status": "acknowledged"}
  ```

### Task 3: Implement Health Check & Monitoring (AC: 5, 7)
- [ ] Extend health check endpoint
  ```python
  @router.get("/health")
  async def health_check(db: AsyncSession = Depends(get_db_session)):
      repo = CorpusRepository(db)
      
      last_refresh = await repo.get_last_crawl_timestamp()
      days_since_refresh = (datetime.utcnow() - last_refresh).days
      
      # Alert if >7 days since last refresh (missed weekly job)
      refresh_status = "healthy" if days_since_refresh <= 7 else "unhealthy"
      
      stats = await repo.get_stats()
      
      return {
          "status": "healthy" if refresh_status == "healthy" else "degraded",
          "components": {
              "database": "healthy",
              "corpus": {
                  "status": refresh_status,
                  "total_automations": stats['total'],
                  "avg_quality": stats['avg_quality'],
                  "last_refresh": last_refresh.isoformat(),
                  "days_since_refresh": days_since_refresh,
                  "next_refresh": "Sunday 2 AM"
              }
          }
      }
  ```
- [ ] Add Prometheus metrics
  ```python
  from shared.metrics_collector import MetricsCollector
  
  metrics = MetricsCollector()
  
  # During refresh
  metrics.record_timing('miner.refresh.duration', refresh_duration_seconds)
  metrics.increment('miner.refresh.added', added_count)
  metrics.increment('miner.refresh.updated', updated_count)
  metrics.increment('miner.refresh.pruned', pruned_count)
  metrics.gauge('miner.corpus.total', stats['total'])
  metrics.gauge('miner.corpus.avg_quality', stats['avg_quality'])
  
  # Alert metrics
  if days_since_refresh > 7:
      metrics.increment('miner.refresh.missed')
  ```
- [ ] Add alerting (if available)
  ```python
  from shared.alert_manager import AlertManager
  
  alert_manager = AlertManager()
  
  # Alert if 3 consecutive failures
  if consecutive_failures >= 3:
      await alert_manager.send_alert(
          severity="warning",
          title="Miner weekly refresh failing",
          message=f"Refresh job has failed {consecutive_failures} times. Last error: {last_error}",
          tags=["automation-miner", "weekly-refresh"]
      )
  ```

### Task 4: Audit Logging (AC: 6)
- [ ] Create `corpus_audit_log` table
  ```python
  class CorpusAuditLog(Base):
      __tablename__ = "corpus_audit_log"
      
      id = Column(Integer, primary_key=True)
      timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
      operation = Column(String(20), nullable=False)  # 'add', 'update', 'delete', 'prune'
      automation_id = Column(Integer, nullable=True, index=True)
      source_id = Column(String(200), nullable=True)
      before_quality = Column(Float, nullable=True)
      after_quality = Column(Float, nullable=True)
      reason = Column(String(200), nullable=True)  # e.g., "pruned: quality < 0.4"
      correlation_id = Column(String(36), nullable=False, index=True)
  ```
- [ ] Log all changes during refresh
  ```python
  async def _log_audit(
      operation: str,
      automation_id: int,
      before_quality: float = None,
      after_quality: float = None,
      reason: str = None
  ):
      audit_entry = CorpusAuditLog(
          operation=operation,
          automation_id=automation_id,
          before_quality=before_quality,
          after_quality=after_quality,
          reason=reason,
          correlation_id=correlation_id
      )
      db.add(audit_entry)
      await db.commit()
  ```
- [ ] Add audit report endpoint
  ```python
  @router.get("/corpus/audit")
  async def get_audit_log(
      since: datetime = Query(None),
      operation: str = Query(None),
      limit: int = 100,
      db: AsyncSession = Depends(get_db_session)
  ):
      """Get corpus audit log"""
      query = db.query(CorpusAuditLog)
      
      if since:
          query = query.filter(CorpusAuditLog.timestamp >= since)
      if operation:
          query = query.filter(CorpusAuditLog.operation == operation)
      
      logs = await query.order_by(CorpusAuditLog.timestamp.desc()).limit(limit).all()
      
      return {"audit_log": logs, "count": len(logs)}
  ```

### Task 5: Testing & Documentation (AC: All)
- [ ] Unit tests:
  - [ ] `WeeklyRefreshJob.run()` with mocked Discourse client
  - [ ] `_update_quality_scores()` with changed votes
  - [ ] `_prune_corpus()` with various quality/age combinations
  - [ ] Cache invalidation logic
- [ ] Integration tests:
  - [ ] Full weekly refresh flow: Fetch → Update → Prune → Invalidate
  - [ ] Test with no new posts (corpus unchanged)
  - [ ] Test with 200+ new posts (stress test)
  - [ ] Test retry logic (simulate API failure)
- [ ] Performance tests:
  - [ ] Measure refresh duration with 100, 200, 500 new posts
  - [ ] Verify memory usage <200MB
  - [ ] Verify API remains available during refresh
- [ ] Documentation:
  - [ ] Update call tree: Add "Weekly Refresh Flow"
  - [ ] Runbook: "How to debug failed weekly refresh"
  - [ ] Admin guide: "How to manually trigger refresh"

### Task 6: Manual Trigger CLI (AC: 5)
- [ ] Add CLI command for manual refresh
  ```python
  # services/automation-miner/src/cli.py
  
  import click
  from miner.jobs.weekly_refresh_job import WeeklyRefreshJob
  
  @click.group()
  def cli():
      pass
  
  @cli.command()
  @click.option('--since', help='Fetch posts since date (YYYY-MM-DD)', default=None)
  @click.option('--dry-run', is_flag=True, help='Show changes without saving')
  async def refresh(since, dry_run):
      """Manually trigger corpus refresh"""
      click.echo("Starting manual corpus refresh...")
      
      # Initialize components
      client = DiscourseClient()
      parser = AutomationParser()
      repo = CorpusRepository(db)
      
      job = WeeklyRefreshJob(client, parser, repo)
      
      if dry_run:
          click.echo("DRY RUN MODE: No changes will be saved")
      
      await job.run()
      click.echo("✅ Refresh complete!")
  
  if __name__ == '__main__':
      cli()
  ```
- [ ] Usage documentation:
  ```bash
  # Manual refresh (development)
  python -m miner.cli refresh
  
  # Dry run (see what would change)
  python -m miner.cli refresh --dry-run
  
  # Fetch since specific date
  python -m miner.cli refresh --since 2025-10-01
  ```

---

## Dev Notes

### APScheduler Configuration [[memory:10014278]]

**From Context7 best practices:**

```python
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger

async def main():
    async with AsyncScheduler() as scheduler:
        # Weekly refresh: Every Sunday at 2 AM
        await scheduler.add_schedule(
            weekly_refresh_job.run,
            CronTrigger(day_of_week='sun', hour=2, minute=0),
            id="weekly_corpus_refresh",
            max_instances=1,      # Prevent multiple instances
            coalesce=True,        # Skip if previous run still active
            misfire_grace_time=3600  # Allow 1 hour delay
        )
        
        await scheduler.run_until_stopped()
```

**Key Settings:**
- `max_instances=1`: Ensures only one refresh runs at a time
- `coalesce=True`: If missed due to server downtime, run once when back online (not multiple times)
- `misfire_grace_time=3600`: If scheduled for 2 AM but server was down, run when server comes up (within 1 hour)

### Incremental Crawl Optimization

**Full Crawl** (Story AI4.1):
- Query: `GET /c/blueprints-exchange/53.json?page=1`
- Processes: 2,000-3,000 posts
- Duration: 2-3 hours
- Network: 50-100MB

**Incremental Crawl** (Story AI4.4):
- Query: `GET /c/blueprints-exchange/53.json?page=1&since=2025-10-11`
- Processes: 50-200 posts typical
- Duration: 15-30 minutes
- Network: 5-20MB

**Efficiency Gain:** 6-12× faster, 5-10× less data

### Pruning Strategy

**Low Quality:**
- `quality_score < 0.4` (very low votes, poor completeness)
- Action: Soft delete (keep for 30 days, then hard delete)

**Stale:**
- Created >2 years ago AND votes <100
- Rationale: Old automations with few votes are outdated practices
- Action: Soft delete

**Duplicates:**
- Fuzzy title match >90% similarity AND same device list
- Action: Keep higher quality score, soft delete lower

**Retention:**
- Soft deleted entries kept 30 days in `deleted_automations` table
- Hard delete after 30 days (cleanup job runs monthly)

### Cache Invalidation Flow

```
Weekly Refresh Job (2 AM Sunday)
        ↓
  Process Updates
        ↓
  Invalidate Miner Caches (Story AI4.2, AI4.3)
        ↓
  Webhook → ai-automation-service
        ↓
  ai-automation-service clears caches
        ↓
  (Optional) Trigger re-analysis if >100 new automations
```

**Affected Caches:**
1. **MinerClient query cache** (Story AI4.2): Pattern enhancement queries
2. **Device possibilities cache** (Story AI4.3): "What can I do with X" queries
3. **Device recommendations cache** (Story AI4.3): Smart shopping results

### Error Scenarios & Recovery

1. **Discourse API Down:**
   - Retry: 3 attempts (1min, 5min, 15min backoff)
   - If all fail: Log error, use existing corpus, alert admin
   - Next week: Try again (corpus slightly stale but functional)

2. **Database Connection Lost:**
   - Retry: 3 attempts with backoff
   - If fail: Rollback transaction, alert admin
   - Data integrity: No partial updates (atomic transactions)

3. **Parsing Failures:**
   - Invalid YAML in new post: Skip post, log warning
   - Continue processing other posts
   - Track parse failure rate (alert if >20%)

4. **Duplicate Detection False Positive:**
   - Manual review: Admin can un-delete from audit log
   - Audit log shows before/after quality scores

### Monitoring Dashboard

**Metrics to Display:**
- Last refresh timestamp
- Corpus size trend (weekly growth)
- Average quality score trend
- Refresh duration trend
- New automations added per week
- Pruned automations per week
- Parse failure rate
- Cache hit rate

**Alerts:**
- 🔴 Critical: Refresh failed 3 consecutive weeks
- 🟡 Warning: Refresh duration >45 minutes
- 🟡 Warning: Parse failure rate >20%
- ℹ️ Info: >100 new automations added (trigger re-analysis)

### Integration with Existing Jobs

**Current Schedule:**
- **3 AM Daily:** AI Analysis Job (Phase 1)

**New Schedule:**
- **2 AM Sunday:** Weekly Corpus Refresh (Story AI4.4)
- **3 AM Daily:** AI Analysis Job (unchanged)

**No Conflicts:**
- Refresh completes in 15-30 minutes (done by 2:30 AM)
- AI Analysis starts at 3 AM (30-minute buffer)
- If refresh runs long (rare), AI Analysis can still access corpus (read-only during refresh)

---

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Story created with weekly refresh job | BMad Master |

---

## Dev Agent Record

### Agent Model Used
*Populated during implementation*

### Debug Log References
*Populated during implementation*

### Completion Notes List
*Populated during implementation*

### File List
*Populated during implementation*

---

## QA Results
*QA Agent review pending*

