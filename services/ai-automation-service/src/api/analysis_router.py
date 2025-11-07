"""
Analysis Router - Orchestrates full pattern detection and suggestion generation pipeline
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
import logging
import asyncio

from ..clients.data_api_client import DataAPIClient
from ..pattern_analyzer.time_of_day import TimeOfDayPatternDetector
from ..pattern_analyzer.co_occurrence import CoOccurrencePatternDetector
from ..llm.openai_client import OpenAIClient
from ..database.crud import store_patterns, store_suggestion, get_patterns, get_latest_analysis_run
from ..database.models import get_db, get_db_session
from ..config import settings
from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# Global reference to scheduler (will be set by main.py)
_scheduler = None

def set_scheduler(scheduler):
    """Set the scheduler instance for manual triggers"""
    global _scheduler
    _scheduler = scheduler


class AnalysisRequest(BaseModel):
    """Request parameters for analysis"""
    days: int = Field(default=30, ge=1, le=90, description="Number of days to analyze")
    max_suggestions: int = Field(default=10, ge=1, le=50, description="Maximum suggestions to generate")
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum pattern confidence")
    time_of_day_enabled: bool = Field(default=True, description="Enable time-of-day pattern detection")
    co_occurrence_enabled: bool = Field(default=True, description="Enable co-occurrence pattern detection")


class AnalysisResponse(BaseModel):
    """Response from analysis pipeline"""
    success: bool
    message: str
    data: Dict


@router.post("/analyze-and-suggest", response_model=AnalysisResponse)
async def analyze_and_suggest(request: AnalysisRequest, timeout: int = 300):
    """
    Run complete analysis pipeline: Fetch events → Detect patterns → Generate suggestions.
    
    This is the main orchestration endpoint that runs the full AI automation workflow:
    1. Fetch historical events from Data API
    2. Detect patterns (time-of-day and/or co-occurrence)
    3. Generate automation suggestions using OpenAI
    4. Store patterns and suggestions in database
    5. Return comprehensive results with performance metrics
    
    Args:
        request: Analysis request parameters
    
    Returns:
        Analysis results with patterns, suggestions, costs, and performance metrics
    """
    start_time = datetime.now(timezone.utc)
    
    logger.info("=" * 80)
    logger.info("🚀 Starting Analysis Pipeline")
    logger.info("=" * 80)
    logger.info(f"Parameters: days={request.days}, max_suggestions={request.max_suggestions}, "
                f"min_confidence={request.min_confidence}, timeout={timeout}s")
    
    try:
        # Add timeout wrapper to prevent hanging
        async def run_analysis():
            return await _run_analysis_pipeline(request)
        
        # Run with timeout
        result = await asyncio.wait_for(run_analysis(), timeout=timeout)
        return result
        
    except asyncio.TimeoutError:
        logger.error(f"❌ Analysis timed out after {timeout} seconds")
        raise HTTPException(
            status_code=408, 
            detail=f"Analysis timed out after {timeout} seconds. Try reducing the analysis scope."
        )


async def _run_analysis_pipeline(request: AnalysisRequest):
    """Internal analysis pipeline function"""
    start_time = datetime.now(timezone.utc)
    try:
        # ========================================================================
        # Phase 1: Fetch Events from Data API
        # ========================================================================
        logger.info("📊 Phase 1: Fetching events from Data API...")
        phase1_start = datetime.now(timezone.utc)
        
        data_client = DataAPIClient(
            base_url=settings.data_api_url,
            influxdb_url=settings.influxdb_url,
            influxdb_token=settings.influxdb_token,
            influxdb_org=settings.influxdb_org,
            influxdb_bucket=settings.influxdb_bucket
        )
        start_date = datetime.now(timezone.utc) - timedelta(days=request.days)
        
        # Optimize event fetching with reasonable limits
        events_df = await data_client.fetch_events(
            start_time=start_date,
            limit=50000  # Reduced from 100k to 50k for better performance
        )
        
        phase1_duration = (datetime.now(timezone.utc) - phase1_start).total_seconds()
        
        if events_df.empty:
            logger.warning("❌ No events retrieved from Data API")
            return AnalysisResponse(
                success=False,
                message="No events available for analysis",
                data={"events_count": 0}
            )
        
        logger.info(f"✅ Phase 1 complete: {len(events_df)} events fetched in {phase1_duration:.1f}s")
        
        # ========================================================================
        # Phase 2: Pattern Detection
        # ========================================================================
        logger.info("🔍 Phase 2: Detecting patterns...")
        phase2_start = datetime.now(timezone.utc)
        
        all_patterns = []
        pattern_summary = {
            'time_of_day': 0,
            'co_occurrence': 0
        }
        
        # Time-of-day patterns
        if request.time_of_day_enabled:
            logger.info("  → Running time-of-day detector...")
            tod_detector = TimeOfDayPatternDetector(
                min_occurrences=max(3, settings.time_of_day_min_occurrences // 2),
                min_confidence=max(settings.time_of_day_base_confidence, request.min_confidence),
                domain_occurrence_overrides=dict(settings.time_of_day_occurrence_overrides),
                domain_confidence_overrides=dict(settings.time_of_day_confidence_overrides)
            )
            
            # Time-of-day detector doesn't have optimized version
            tod_patterns = tod_detector.detect_patterns(events_df)
            
            all_patterns.extend(tod_patterns)
            pattern_summary['time_of_day'] = len(tod_patterns)
            logger.info(f"    ✅ Found {len(tod_patterns)} time-of-day patterns")
        
        # Co-occurrence patterns
        if request.co_occurrence_enabled:
            logger.info("  → Running co-occurrence detector...")
            co_detector = CoOccurrencePatternDetector(
                window_minutes=5,
                min_support=max(3, settings.co_occurrence_min_support // 2),
                min_confidence=max(settings.co_occurrence_base_confidence, request.min_confidence),
                domain_support_overrides=dict(settings.co_occurrence_support_overrides),
                domain_confidence_overrides=dict(settings.co_occurrence_confidence_overrides)
            )
            
            if len(events_df) > 50000:
                co_patterns = co_detector.detect_patterns_optimized(events_df)
            else:
                co_patterns = co_detector.detect_patterns(events_df)
            
            all_patterns.extend(co_patterns)
            pattern_summary['co_occurrence'] = len(co_patterns)
            logger.info(f"    ✅ Found {len(co_patterns)} co-occurrence patterns")
        
        phase2_duration = (datetime.now(timezone.utc) - phase2_start).total_seconds()
        logger.info(f"✅ Phase 2 complete: {len(all_patterns)} total patterns in {phase2_duration:.1f}s")
        
        if not all_patterns:
            logger.warning("❌ No patterns detected")
            return AnalysisResponse(
                success=False,
                message="No patterns detected with current thresholds",
                data={
                    "events_analyzed": len(events_df),
                    "patterns_detected": 0,
                    "min_confidence": request.min_confidence
                }
            )
        
        # ========================================================================
        # Phase 3: Store Patterns in Database
        # ========================================================================
        logger.info("💾 Phase 3: Storing patterns...")
        phase3_start = datetime.now(timezone.utc)
        
        async with get_db_session() as db:
            patterns_stored = await store_patterns(db, all_patterns)
        
        phase3_duration = (datetime.now(timezone.utc) - phase3_start).total_seconds()
        logger.info(f"✅ Phase 3 complete: {patterns_stored} patterns stored in {phase3_duration:.1f}s")
        
        # ========================================================================
        # Phase 4: Generate Suggestions via OpenAI
        # ========================================================================
        logger.info("🤖 Phase 4: Generating automation suggestions...")
        phase4_start = datetime.now(timezone.utc)
        
        # Rank patterns by confidence and limit to max_suggestions
        sorted_patterns = sorted(all_patterns, key=lambda p: p['confidence'], reverse=True)
        top_patterns = sorted_patterns[:request.max_suggestions]
        
        logger.info(f"  → Processing top {len(top_patterns)} patterns for suggestions")
        
        openai_client = OpenAIClient(api_key=settings.openai_api_key)
        prompt_builder = UnifiedPromptBuilder()
        suggestions_generated = []
        suggestions_failed = []
        
        for i, pattern in enumerate(top_patterns, 1):
            try:
                logger.info(f"  → [{i}/{len(top_patterns)}] Generating suggestion for {pattern['device_id']}")
                
                # Story AI1.24: Generate description-only (no YAML until user approves)
                # Build prompt using UnifiedPromptBuilder
                prompt_dict = await prompt_builder.build_pattern_prompt(
                    pattern=pattern,
                    device_context=None,
                    output_mode="description"
                )
                
                # Generate with unified method
                result = await openai_client.generate_with_unified_prompt(
                    prompt_dict=prompt_dict,
                    temperature=0.7,
                    max_tokens=300,
                    output_format="description"
                )
                
                # Parse result to match expected format
                description_data = {
                    'title': result.get('title', pattern.get('device_id', 'Automation')),
                    'description': result.get('description', ''),
                    'rationale': result.get('rationale', ''),
                    'category': result.get('category', 'convenience'),
                    'priority': result.get('priority', 'medium')
                }
                
                # Store suggestion in database
                async with get_db_session() as db:
                    stored_suggestion = await store_suggestion(db, {
                        'pattern_id': pattern.get('id'),
                        'title': description_data['title'],
                        'description': description_data['description'],
                        'automation_yaml': None,  # Story AI1.24: No YAML until approved
                        'confidence': pattern['confidence'],
                        'category': description_data['category'],
                        'priority': description_data['priority'],
                        'status': 'draft',
                        'device_id': pattern.get('device_id'),
                        'device1': pattern.get('device1'),
                        'device2': pattern.get('device2'),
                        'devices_involved': pattern.get('devices_involved') or ([pattern.get('device_id')] if pattern.get('device_id') else None),
                        'metadata': pattern.get('metadata') or {},
                        'device_info': pattern.get('device_info')
                    })
                
                suggestions_generated.append({
                    'id': stored_suggestion.id,
                    'title': description_data['title'],
                    'category': description_data['category'],
                    'priority': description_data['priority'],
                    'confidence': pattern['confidence'],
                    'pattern_type': pattern['pattern_type']
                })
                
            except Exception as e:
                logger.error(f"    ❌ Failed to generate suggestion: {e}")
                suggestions_failed.append({
                    'device_id': pattern['device_id'],
                    'error': str(e)
                })
        
        phase4_duration = (datetime.now(timezone.utc) - phase4_start).total_seconds()
        
        # Get OpenAI usage stats
        openai_stats = {
            'total_tokens': openai_client.total_tokens_used,
            'input_tokens': openai_client.total_input_tokens,
            'output_tokens': openai_client.total_output_tokens,
            'estimated_cost_usd': round(
                (openai_client.total_input_tokens * 0.00000015) +
                (openai_client.total_output_tokens * 0.00000060),
                6
            ),
            'model': openai_client.model
        }
        
        logger.info(f"✅ Phase 4 complete: {len(suggestions_generated)} suggestions in {phase4_duration:.1f}s")
        logger.info(f"  → OpenAI cost: ${openai_stats['estimated_cost_usd']:.6f}")
        
        # ========================================================================
        # Final Summary
        # ========================================================================
        total_duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info(f"✅ Analysis Pipeline Complete!")
        logger.info(f"  → Events analyzed: {len(events_df)}")
        logger.info(f"  → Patterns detected: {len(all_patterns)}")
        logger.info(f"  → Suggestions generated: {len(suggestions_generated)}")
        logger.info(f"  → Total duration: {total_duration:.1f}s")
        logger.info(f"  → Cost: ${openai_stats['estimated_cost_usd']:.6f}")
        logger.info("=" * 80)
        
        return AnalysisResponse(
            success=True,
            message=f"Successfully generated {len(suggestions_generated)} automation suggestions",
            data={
                'summary': {
                    'events_analyzed': len(events_df),
                    'patterns_detected': len(all_patterns),
                    'suggestions_generated': len(suggestions_generated),
                    'suggestions_failed': len(suggestions_failed)
                },
                'patterns': {
                    'total': len(all_patterns),
                    'by_type': pattern_summary,
                    'top_confidence': max(p['confidence'] for p in all_patterns) if all_patterns else 0,
                    'avg_confidence': sum(p['confidence'] for p in all_patterns) / len(all_patterns) if all_patterns else 0
                },
                'suggestions': suggestions_generated,
                'openai_usage': openai_stats,
                'performance': {
                    'total_duration_seconds': round(total_duration, 2),
                    'phase1_fetch_seconds': round(phase1_duration, 2),
                    'phase2_detect_seconds': round(phase2_duration, 2),
                    'phase3_store_seconds': round(phase3_duration, 2),
                    'phase4_generate_seconds': round(phase4_duration, 2),
                    'avg_time_per_suggestion': round(phase4_duration / len(suggestions_generated), 2) if suggestions_generated else 0
                },
                'time_range': {
                    'start': start_date.isoformat(),
                    'end': datetime.now(timezone.utc).isoformat(),
                    'days': request.days
                }
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Analysis pipeline failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {str(e)}")


@router.get("/status", response_model=Dict)
async def get_analysis_status():
    """
    Get current analysis status and latest run information.
    
    Returns:
        Status information including pattern counts and last run details
    """
    try:
        async with get_db_session() as db:
            # Get recent patterns
            from ..database.crud import get_pattern_stats
            pattern_stats = await get_pattern_stats(db)
            
            # Get recent suggestions
            from ..database.crud import get_suggestions
            recent_suggestions = await get_suggestions(db, status='pending', limit=10)

            latest_run = await get_latest_analysis_run(db)
            
            return {
                'status': 'ready',
                'patterns': pattern_stats,
                'suggestions': {
                    'pending_count': len(recent_suggestions),
                    'recent': [
                        {
                            'id': s.id,
                            'title': s.title,
                            'confidence': s.confidence,
                            'created_at': s.created_at.isoformat()
                        }
                        for s in recent_suggestions
                    ]
                },
                'analysis_run': {
                    'status': latest_run.status,
                    'started_at': latest_run.started_at.isoformat(),
                    'finished_at': latest_run.finished_at.isoformat() if latest_run.finished_at else None,
                    'duration_seconds': latest_run.duration_seconds
                } if latest_run else None
            }
    
    except Exception as e:
        logger.error(f"Failed to get analysis status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_analysis(background_tasks: BackgroundTasks):
    """
    Manually trigger daily analysis job (for testing or on-demand execution).
    
    The analysis runs in the background and doesn't block the request.
    Use /api/analysis/status to check progress.
    
    Returns:
        Status message indicating the job was triggered
    """
    if _scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    if _scheduler.is_running:
        raise HTTPException(
            status_code=409,
            detail="Analysis is already running"
        )
    
    # Trigger manual run in background
    background_tasks.add_task(_scheduler.trigger_manual_run)
    
    logger.info("🔧 Manual analysis triggered via API")
    
    return {
        "success": True,
        "message": "Analysis job triggered successfully",
        "status": "running_in_background",
        "next_scheduled_run": _scheduler.get_next_run_time().isoformat() if _scheduler.get_next_run_time() else None
    }


@router.get("/schedule")
async def get_schedule_info():
    """
    Get information about the analysis schedule.
    
    Returns:
        Schedule configuration and next run time
    """
    if _scheduler is None:
        raise HTTPException(
            status_code=503,
            detail="Scheduler not initialized"
        )
    
    next_run = _scheduler.get_next_run_time()
    
    return {
        "schedule": _scheduler.cron_schedule,
        "next_run": next_run.isoformat() if next_run else None,
        "is_running": _scheduler.is_running,
        "recent_jobs": _scheduler.get_job_history(limit=5)
    }

