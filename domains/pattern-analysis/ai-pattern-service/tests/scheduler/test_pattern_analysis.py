"""
Comprehensive unit and integration tests for Pattern Analysis Scheduler

Epic 39, Story 39.6: Daily Scheduler Migration
Tests cover all phases of pattern analysis including:
- Scheduler initialization and lifecycle
- Event fetching
- Pattern detection (time-of-day, co-occurrence)
- Synergy detection
- Result storage
- MQTT notifications
- Error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timedelta, timezone
import pandas as pd

from src.scheduler.pattern_analysis import PatternAnalysisScheduler


class TestPatternAnalysisSchedulerInitialization:
    """Test scheduler initialization and configuration."""
    
    @pytest.mark.unit
    def test_scheduler_initialization_default(self):
        """Test scheduler initialization with default settings."""
        scheduler = PatternAnalysisScheduler()
        
        assert scheduler.cron_schedule is not None
        assert scheduler.enable_incremental is True
        assert scheduler.is_running is False
        assert scheduler.mqtt_client is None
    
    @pytest.mark.unit
    def test_scheduler_initialization_custom_schedule(self):
        """Test scheduler initialization with custom cron schedule."""
        scheduler = PatternAnalysisScheduler(
            cron_schedule="0 3 * * *",
            enable_incremental=False
        )
        
        assert scheduler.cron_schedule == "0 3 * * *"
        assert scheduler.enable_incremental is False
        assert scheduler.is_running is False
    
    @pytest.mark.unit
    def test_set_mqtt_client(self):
        """Test setting MQTT client."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        
        scheduler.set_mqtt_client(mock_mqtt)
        
        assert scheduler.mqtt_client == mock_mqtt


class TestSchedulerLifecycle:
    """Test scheduler start and stop operations."""
    
    @pytest.mark.unit
    def test_start_scheduler(self):
        """Test starting the scheduler."""
        scheduler = PatternAnalysisScheduler()
        scheduler.scheduler = MagicMock()
        
        scheduler.start()
        
        assert scheduler.is_running is True
        scheduler.scheduler.add_job.assert_called_once()
        scheduler.scheduler.start.assert_called_once()
    
    @pytest.mark.unit
    def test_start_scheduler_failure(self):
        """Test scheduler start failure handling."""
        scheduler = PatternAnalysisScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.add_job.side_effect = Exception("Start failed")
        
        with pytest.raises(Exception):
            scheduler.start()
        
        assert scheduler.is_running is False
    
    @pytest.mark.unit
    def test_stop_scheduler(self):
        """Test stopping the scheduler."""
        scheduler = PatternAnalysisScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.is_running = True
        
        scheduler.stop()
        
        assert scheduler.is_running is False
        scheduler.scheduler.shutdown.assert_called_once_with(wait=True)
    
    @pytest.mark.unit
    def test_stop_scheduler_failure(self):
        """Test scheduler stop failure handling."""
        scheduler = PatternAnalysisScheduler()
        scheduler.scheduler = MagicMock()
        scheduler.scheduler.shutdown.side_effect = Exception("Stop failed")
        scheduler.is_running = True
        
        # Should not raise, just log error
        scheduler.stop()
        
        assert scheduler.is_running is False


class TestEventFetching:
    """Test event fetching phase."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_success(self):
        """Test successful event fetching."""
        scheduler = PatternAnalysisScheduler()
        mock_client = AsyncMock()
        
        # Create sample events DataFrame
        events_df = pd.DataFrame({
            'entity_id': ['light.office', 'light.kitchen'],
            'state': ['on', 'off'],
            'timestamp': [datetime.now(timezone.utc), datetime.now(timezone.utc)]
        })
        mock_client.fetch_events = AsyncMock(return_value=events_df)
        
        result = await scheduler._fetch_events(mock_client)
        
        assert not result.empty
        assert len(result) == 2
        mock_client.fetch_events.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_fetch_events_empty(self):
        """Test fetching when no events are available."""
        scheduler = PatternAnalysisScheduler()
        mock_client = AsyncMock()
        mock_client.fetch_events = AsyncMock(return_value=pd.DataFrame())
        
        result = await scheduler._fetch_events(mock_client)
        
        assert result.empty
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_handle_empty_events(self):
        """Test handling empty events scenario."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        job_result = {
            "status": "running",
            "patterns_detected": 0,
            "synergies_detected": 0,
            "errors": []
        }
        
        await scheduler._handle_empty_events(job_result)
        
        assert job_result["status"] == "completed"
        assert "end_time" in job_result
        mock_mqtt.publish.assert_called_once()


class TestPatternDetection:
    """Test pattern detection phase."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_time_of_day_patterns_success(self):
        """Test successful time-of-day pattern detection."""
        scheduler = PatternAnalysisScheduler()
        events_df = pd.DataFrame({
            'entity_id': ['light.office'],
            'state': ['on'],
            'timestamp': [datetime.now(timezone.utc)]
        })
        job_result = {"errors": []}
        
        mock_detector = MagicMock()
        mock_detector.detect_patterns = MagicMock(return_value=[
            {"pattern_type": "time_of_day", "entity_id": "light.office"}
        ])
        
        with patch('src.scheduler.pattern_analysis.TimeOfDayPatternDetector', return_value=mock_detector):
            with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
                mock_thread.return_value = [{"pattern_type": "time_of_day"}]
                patterns = await scheduler._detect_time_of_day_patterns(events_df, job_result)
        
        assert len(patterns) == 1
        assert len(job_result["errors"]) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_time_of_day_patterns_failure(self):
        """Test time-of-day pattern detection failure handling."""
        scheduler = PatternAnalysisScheduler()
        events_df = pd.DataFrame()
        job_result = {"errors": []}
        
        with patch('src.scheduler.pattern_analysis.TimeOfDayPatternDetector', side_effect=Exception("Detection failed")):
            patterns = await scheduler._detect_time_of_day_patterns(events_df, job_result)
        
        assert patterns == []
        assert len(job_result["errors"]) == 1
        assert "Time-of-day detection" in job_result["errors"][0]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_co_occurrence_patterns_success(self):
        """Test successful co-occurrence pattern detection."""
        scheduler = PatternAnalysisScheduler()
        events_df = pd.DataFrame({
            'entity_id': ['light.office', 'light.kitchen'],
            'state': ['on', 'on'],
            'timestamp': [datetime.now(timezone.utc), datetime.now(timezone.utc)]
        })
        job_result = {"errors": []}
        
        with patch('src.scheduler.pattern_analysis.CoOccurrencePatternDetector', return_value=MagicMock()) as mock_detector:
            with patch('asyncio.to_thread', new_callable=AsyncMock) as mock_thread:
                mock_thread.return_value = [{"pattern_type": "co_occurrence"}]
                patterns = await scheduler._detect_co_occurrence_patterns(events_df, job_result)
        
        assert len(patterns) == 1
        assert len(job_result["errors"]) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_co_occurrence_patterns_failure(self):
        """Test co-occurrence pattern detection failure handling."""
        scheduler = PatternAnalysisScheduler()
        events_df = pd.DataFrame()
        job_result = {"errors": []}
        
        with patch('src.scheduler.pattern_analysis.CoOccurrencePatternDetector', side_effect=Exception("Detection failed")):
            patterns = await scheduler._detect_co_occurrence_patterns(events_df, job_result)
        
        assert patterns == []
        assert len(job_result["errors"]) == 1
        assert "Co-occurrence detection" in job_result["errors"][0]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_patterns_combines_results(self):
        """Test that pattern detection combines time-of-day and co-occurrence results."""
        scheduler = PatternAnalysisScheduler()
        events_df = pd.DataFrame()
        job_result = {"errors": []}
        
        with patch.object(scheduler, '_detect_time_of_day_patterns', new_callable=AsyncMock) as mock_tod:
            with patch.object(scheduler, '_detect_co_occurrence_patterns', new_callable=AsyncMock) as mock_co:
                mock_tod.return_value = [{"type": "tod"}]
                mock_co.return_value = [{"type": "co"}]
                
                patterns = await scheduler._detect_patterns(events_df, job_result)
        
        assert len(patterns) == 2
        assert job_result["patterns_detected"] == 2


class TestSynergyDetection:
    """Test synergy detection phase."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_success(self):
        """Test successful synergy detection."""
        scheduler = PatternAnalysisScheduler()
        mock_client = AsyncMock()
        events_df = pd.DataFrame()
        job_result = {"errors": []}
        
        mock_client.fetch_devices = AsyncMock(return_value=[{"device_id": "device1"}])
        mock_client.fetch_entities = AsyncMock(return_value=[{"entity_id": "entity1"}])
        
        mock_detector = AsyncMock()
        mock_detector.detect_synergies = AsyncMock(return_value=[
            {"synergy_type": "device_pair"}
        ])
        
        with patch('src.scheduler.pattern_analysis.DeviceSynergyDetector', return_value=mock_detector):
            synergies = await scheduler._detect_synergies(mock_client, events_df, job_result)
        
        assert len(synergies) == 1
        assert job_result["synergies_detected"] == 1
        assert len(job_result["errors"]) == 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_detect_synergies_failure(self):
        """Test synergy detection failure handling."""
        scheduler = PatternAnalysisScheduler()
        mock_client = AsyncMock()
        events_df = pd.DataFrame()
        job_result = {"errors": []}
        
        with patch('src.scheduler.pattern_analysis.DeviceSynergyDetector', side_effect=Exception("Synergy failed")):
            synergies = await scheduler._detect_synergies(mock_client, events_df, job_result)
        
        assert synergies == []
        assert len(job_result["errors"]) == 1
        assert "Synergy detection" in job_result["errors"][0]


class TestResultStorage:
    """Test result storage phase."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_results_success(self):
        """Test successful result storage."""
        scheduler = PatternAnalysisScheduler()
        patterns = [{"pattern_id": 1}, {"pattern_id": 2}]
        synergies = [{"synergy_id": 1}]
        job_result = {"errors": []}
        
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        # Create a proper async context manager mock
        mock_session_local = AsyncMock()
        mock_session_local.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.scheduler.pattern_analysis.AsyncSessionLocal', return_value=mock_session_local):
            with patch('src.scheduler.pattern_analysis.store_patterns', new_callable=AsyncMock) as mock_store_patterns:
                with patch('src.scheduler.pattern_analysis.store_synergy_opportunities', new_callable=AsyncMock) as mock_store_synergies:
                    mock_store_patterns.return_value = 2
                    mock_store_synergies.return_value = 1
                    
                    await scheduler._store_results(patterns, synergies, job_result)
        
        assert len(job_result["errors"]) == 0
        mock_db.commit.assert_called_once()
        mock_store_patterns.assert_called_once()
        mock_store_synergies.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_store_results_failure(self):
        """Test result storage failure handling."""
        scheduler = PatternAnalysisScheduler()
        patterns = [{"pattern_id": 1}]
        synergies = []
        job_result = {"errors": []}
        
        mock_db = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_db.rollback = AsyncMock()
        
        # Create a proper async context manager mock
        mock_session_local = AsyncMock()
        mock_session_local.__aenter__ = AsyncMock(return_value=mock_db)
        mock_session_local.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.scheduler.pattern_analysis.AsyncSessionLocal', return_value=mock_session_local):
            with patch('src.scheduler.pattern_analysis.store_patterns', side_effect=Exception("Storage failed")):
                await scheduler._store_results(patterns, synergies, job_result)
        
        assert len(job_result["errors"]) == 1
        assert "Storage" in job_result["errors"][0]


class TestNotification:
    """Test MQTT notification publishing."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_publish_notification_success(self):
        """Test successful notification publishing."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        job_result = {
            "status": "completed",
            "patterns_detected": 5,
            "synergies_detected": 2,
            "duration_seconds": 10.5,
            "errors": []
        }
        
        await scheduler._publish_notification(job_result)
        
        mock_mqtt.publish.assert_called_once()
        call_args = mock_mqtt.publish.call_args
        assert call_args[0][0] == "homeiq/ai-automation/analysis/pattern/complete"
        assert call_args[0][1]["status"] == "completed"
        assert call_args[0][1]["patterns_detected"] == 5
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_publish_notification_no_client(self):
        """Test notification when MQTT client is not configured."""
        scheduler = PatternAnalysisScheduler()
        job_result = {"status": "completed"}
        
        # Should not raise, just skip
        await scheduler._publish_notification(job_result)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_publish_notification_failure(self):
        """Test notification publishing failure handling."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        mock_mqtt.publish.side_effect = Exception("Publish failed")
        scheduler.set_mqtt_client(mock_mqtt)
        
        job_result = {"status": "completed"}
        
        # Should not raise, just log warning
        await scheduler._publish_notification(job_result)


class TestFullAnalysisFlow:
    """Test complete analysis flow integration."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.scheduler
    async def test_run_pattern_analysis_empty_events(self):
        """Test full analysis flow with empty events."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        mock_client = AsyncMock()
        mock_client.fetch_events = AsyncMock(return_value=pd.DataFrame())
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.scheduler.pattern_analysis.DataAPIClient', return_value=mock_client):
            await scheduler.run_pattern_analysis()
        
        mock_mqtt.publish.assert_called_once()
        call_args = mock_mqtt.publish.call_args
        payload = call_args[0][1]
        assert payload["status"] == "completed"
        assert payload["patterns_detected"] == 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.scheduler
    async def test_run_pattern_analysis_with_events(self):
        """Test full analysis flow with events."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        events_df = pd.DataFrame({
            'entity_id': ['light.office'],
            'state': ['on'],
            'timestamp': [datetime.now(timezone.utc)]
        })
        
        mock_client = AsyncMock()
        mock_client.fetch_events = AsyncMock(return_value=events_df)
        mock_client.fetch_devices = AsyncMock(return_value=[])
        mock_client.fetch_entities = AsyncMock(return_value=[])
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.scheduler.pattern_analysis.DataAPIClient', return_value=mock_client):
            with patch.object(scheduler, '_detect_patterns', new_callable=AsyncMock) as mock_detect:
                with patch.object(scheduler, '_detect_synergies', new_callable=AsyncMock) as mock_synergies:
                    with patch.object(scheduler, '_store_results', new_callable=AsyncMock):
                        mock_detect.return_value = []
                        mock_synergies.return_value = []
                        
                        await scheduler.run_pattern_analysis()
        
        mock_mqtt.publish.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.scheduler
    async def test_run_pattern_analysis_failure(self):
        """Test full analysis flow with failure."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(side_effect=Exception("Analysis failed"))
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch('src.scheduler.pattern_analysis.DataAPIClient', return_value=mock_client):
            await scheduler.run_pattern_analysis()
        
        # Should still publish notification with failed status
        mock_mqtt.publish.assert_called_once()
        call_args = mock_mqtt.publish.call_args
        payload = call_args[0][1]
        assert payload["status"] == "failed"
        assert len(payload["errors"]) > 0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_finalize_analysis(self):
        """Test analysis finalization."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        scheduler.set_mqtt_client(mock_mqtt)
        
        start_time = datetime.now(timezone.utc) - timedelta(seconds=10)
        job_result = {
            "status": "running",
            "patterns_detected": 3,
            "synergies_detected": 1,
            "errors": []
        }
        
        await scheduler._finalize_analysis(start_time, job_result)
        
        assert job_result["status"] == "completed"
        assert "end_time" in job_result
        assert "duration_seconds" in job_result
        assert job_result["duration_seconds"] > 0
        mock_mqtt.publish.assert_called_once()

