"""
Unit tests for Daily Analysis Scheduler
"""

import pytest

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment",
)

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from src.scheduler.daily_analysis import DailyAnalysisScheduler


@pytest.fixture
def mock_events_df():
    """Create mock events DataFrame"""
    return pd.DataFrame({
        "event_id": [1, 2, 3],
        "entity_id": ["light.bedroom", "light.living_room", "sensor.temp"],
        "state": ["on", "on", "72"],
        "last_changed": pd.to_datetime([
            "2025-10-01 07:00:00",
            "2025-10-01 08:00:00",
            "2025-10-01 15:00:00",
        ]),
    })


@pytest.fixture
def mock_patterns():
    """Create mock patterns"""
    return [
        {
            "pattern_type": "time_of_day",
            "device_id": "light.bedroom",
            "confidence": 0.95,
            "occurrences": 28,
            "metadata": {},
        },
    ]


def test_scheduler_initialization():
    """Test scheduler initializes with correct parameters"""
    scheduler = DailyAnalysisScheduler(cron_schedule="0 3 * * *")

    assert scheduler.cron_schedule == "0 3 * * *"
    assert scheduler.is_running is False
    assert scheduler.scheduler is not None


def test_scheduler_initialization_default_schedule():
    """Test scheduler uses default schedule from settings"""
    with patch("src.scheduler.daily_analysis.settings") as mock_settings:
        mock_settings.analysis_schedule = "0 4 * * *"

        scheduler = DailyAnalysisScheduler()

        assert scheduler.cron_schedule == "0 4 * * *"


def test_scheduler_start():
    """Test scheduler starts successfully"""
    scheduler = DailyAnalysisScheduler(cron_schedule="0 3 * * *")

    try:
        scheduler.start()

        assert scheduler.scheduler.running is True

        # Check job was added
        job = scheduler.scheduler.get_job("daily_pattern_analysis")
        assert job is not None
        assert job.name == "Daily Pattern Analysis and Suggestion Generation"

    finally:
        scheduler.stop()


def test_scheduler_stop():
    """Test scheduler stops gracefully"""
    scheduler = DailyAnalysisScheduler()

    scheduler.start()
    assert scheduler.scheduler.running is True

    scheduler.stop()
    assert scheduler.scheduler.running is False


def test_get_next_run_time():
    """Test getting next scheduled run time"""
    scheduler = DailyAnalysisScheduler(cron_schedule="0 3 * * *")

    try:
        scheduler.start()

        next_run = scheduler.get_next_run_time()

        assert next_run is not None
        assert isinstance(next_run, datetime)
        # Should be in the future
        assert next_run > datetime.now(scheduler.scheduler.timezone)

    finally:
        scheduler.stop()


def test_get_job_history():
    """Test job history tracking"""
    scheduler = DailyAnalysisScheduler()

    # Add some job history
    scheduler._store_job_history({"status": "success", "duration": 60})
    scheduler._store_job_history({"status": "failed", "error": "Test error"})

    history = scheduler.get_job_history(limit=10)

    assert len(history) == 2
    assert history[0]["status"] == "success"
    assert history[1]["status"] == "failed"


def test_job_history_limit():
    """Test job history maintains maximum size"""
    scheduler = DailyAnalysisScheduler()

    # Add 35 job results (more than 30 limit)
    for i in range(35):
        scheduler._store_job_history({"run_id": i, "status": "success"})

    # Should only keep last 30
    assert len(scheduler._job_history) == 30
    # First entry should be run_id 5 (0-4 were removed)
    assert scheduler._job_history[0]["run_id"] == 5


@pytest.mark.asyncio
async def test_prevents_concurrent_runs():
    """Test scheduler prevents concurrent runs"""
    scheduler = DailyAnalysisScheduler()
    scheduler.is_running = True  # Simulate running job

    # Try to run again
    await scheduler.run_daily_analysis()

    # Should have returned early without doing anything
    # is_running should still be True (not reset to False)
    assert scheduler.is_running is True


@pytest.mark.asyncio
async def test_run_daily_analysis_success(mock_events_df, mock_patterns):
    """Test successful daily analysis execution"""
    scheduler = DailyAnalysisScheduler()

    # Mock DataAPIClient
    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        # Mock pattern detectors
        with patch("src.scheduler.daily_analysis.TimeOfDayPatternDetector") as mock_tod:
            with patch("src.scheduler.daily_analysis.CoOccurrencePatternDetector") as mock_co:
                mock_tod_instance = MagicMock()
                mock_tod_instance.detect_patterns.return_value = mock_patterns
                mock_tod.return_value = mock_tod_instance

                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                # Mock database operations
                with patch("src.scheduler.daily_analysis.store_patterns") as mock_store_patterns:
                    with patch("src.scheduler.daily_analysis.store_suggestion"):
                        with patch("src.scheduler.daily_analysis.get_db"):
                            mock_store_patterns.return_value = 1

                            # Mock OpenAI client
                            with patch("src.scheduler.daily_analysis.OpenAIClient") as mock_openai:
                                from src.llm.openai_client import AutomationSuggestion

                                mock_suggestion = AutomationSuggestion(
                                    alias="Test",
                                    description="Test",
                                    automation_yaml="alias: Test",
                                    rationale="Test",
                                    category="convenience",
                                    priority="medium",
                                    confidence=0.95,
                                )

                                mock_openai_instance = AsyncMock()
                                mock_openai_instance.generate_automation_suggestion.return_value = mock_suggestion
                                mock_openai_instance.total_tokens_used = 1000
                                mock_openai_instance.total_input_tokens = 600
                                mock_openai_instance.total_output_tokens = 400
                                mock_openai.return_value = mock_openai_instance

                                # Run analysis
                                await scheduler.run_daily_analysis()

    # Check job history
    history = scheduler.get_job_history()
    assert len(history) == 1
    assert history[0]["status"] == "success"
    assert history[0]["events_count"] == 3
    assert history[0]["patterns_detected"] == 1
    assert history[0]["suggestions_generated"] == 1
    assert "duration_seconds" in history[0]


@pytest.mark.asyncio
async def test_run_daily_analysis_no_events():
    """Test daily analysis handles no events"""
    scheduler = DailyAnalysisScheduler()

    # Mock empty DataFrame
    empty_df = pd.DataFrame()

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = empty_df
        mock_data_client.return_value = mock_client_instance

        await scheduler.run_daily_analysis()

    # Check job history
    history = scheduler.get_job_history()
    assert len(history) == 1
    assert history[0]["status"] == "no_data"
    assert history[0]["events_count"] == 0


@pytest.mark.asyncio
async def test_run_daily_analysis_no_patterns(mock_events_df):
    """Test daily analysis handles no patterns detected"""
    scheduler = DailyAnalysisScheduler()

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        # Mock pattern detectors returning empty lists
        with patch("src.scheduler.daily_analysis.TimeOfDayPatternDetector") as mock_tod:
            with patch("src.scheduler.daily_analysis.CoOccurrencePatternDetector") as mock_co:
                mock_tod_instance = MagicMock()
                mock_tod_instance.detect_patterns.return_value = []
                mock_tod.return_value = mock_tod_instance

                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                await scheduler.run_daily_analysis()

    # Check job history
    history = scheduler.get_job_history()
    assert len(history) == 1
    assert history[0]["status"] == "no_patterns"
    assert history[0]["patterns_detected"] == 0


@pytest.mark.asyncio
async def test_run_daily_analysis_handles_errors(mock_events_df):
    """Test daily analysis handles exceptions gracefully"""
    scheduler = DailyAnalysisScheduler()

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        # Simulate exception
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.side_effect = Exception("Connection failed")
        mock_data_client.return_value = mock_client_instance

        # Should not raise exception
        await scheduler.run_daily_analysis()

    # Check job history shows failure
    history = scheduler.get_job_history()
    assert len(history) == 1
    assert history[0]["status"] == "failed"
    assert "error" in history[0]
    assert "Connection failed" in history[0]["error"]


@pytest.mark.asyncio
async def test_run_daily_analysis_uses_optimized_detectors():
    """Test uses optimized detectors for large datasets"""
    scheduler = DailyAnalysisScheduler()

    # Create large DataFrame (>50,000 events)
    large_df = pd.DataFrame({
        "event_id": range(60000),
        "entity_id": ["light.test"] * 60000,
        "state": ["on"] * 60000,
        "last_changed": pd.to_datetime(["2025-10-01 00:00:00"] * 60000),
    })

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = large_df
        mock_data_client.return_value = mock_client_instance

        with patch("src.scheduler.daily_analysis.TimeOfDayPatternDetector") as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns_optimized.return_value = []
            mock_tod.return_value = mock_tod_instance

            with patch("src.scheduler.daily_analysis.CoOccurrencePatternDetector") as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns_optimized.return_value = []
                mock_co.return_value = mock_co_instance

                await scheduler.run_daily_analysis()

                # Verify optimized methods were called
                assert mock_tod_instance.detect_patterns_optimized.called
                assert mock_co_instance.detect_patterns_optimized.called


@pytest.mark.asyncio
async def test_run_daily_analysis_limits_suggestions(mock_events_df):
    """Test limits suggestions to top 10"""
    scheduler = DailyAnalysisScheduler()

    # Create 20 patterns
    many_patterns = [
        {
            "pattern_type": "time_of_day",
            "device_id": f"light.test_{i}",
            "confidence": 0.95 - (i * 0.01),
            "occurrences": 20,
            "metadata": {},
        }
        for i in range(20)
    ]

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch("src.scheduler.daily_analysis.TimeOfDayPatternDetector") as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = many_patterns
            mock_tod.return_value = mock_tod_instance

            with patch("src.scheduler.daily_analysis.CoOccurrencePatternDetector") as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                with patch("src.scheduler.daily_analysis.store_patterns"):
                    with patch("src.scheduler.daily_analysis.store_suggestion"):
                        with patch("src.scheduler.daily_analysis.get_db"):
                            with patch("src.scheduler.daily_analysis.OpenAIClient") as mock_openai:
                                from src.llm.openai_client import AutomationSuggestion

                                mock_suggestion = AutomationSuggestion(
                                    alias="Test",
                                    description="Test",
                                    automation_yaml="alias: Test",
                                    rationale="Test",
                                    category="convenience",
                                    priority="medium",
                                    confidence=0.95,
                                )

                                mock_openai_instance = AsyncMock()
                                mock_openai_instance.generate_automation_suggestion.return_value = mock_suggestion
                                mock_openai_instance.total_tokens_used = 5000
                                mock_openai_instance.total_input_tokens = 3000
                                mock_openai_instance.total_output_tokens = 2000
                                mock_openai.return_value = mock_openai_instance

                                await scheduler.run_daily_analysis()

                                # Should only call OpenAI 10 times despite 20 patterns
                                assert mock_openai_instance.generate_automation_suggestion.call_count == 10


@pytest.mark.asyncio
async def test_trigger_manual_run():
    """Test manual trigger creates async task"""
    scheduler = DailyAnalysisScheduler()

    with patch("src.scheduler.daily_analysis.asyncio.create_task") as mock_create_task:
        await scheduler.trigger_manual_run()

        # Should create background task
        assert mock_create_task.called


@pytest.mark.asyncio
async def test_run_daily_analysis_handles_partial_failures(mock_events_df, mock_patterns):
    """Test continues when some suggestions fail"""
    scheduler = DailyAnalysisScheduler()

    # Create multiple patterns
    patterns = [
        {**mock_patterns[0], "device_id": "light.test1"},
        {**mock_patterns[0], "device_id": "light.test2"},
        {**mock_patterns[0], "device_id": "light.test3"},
    ]

    with patch("src.scheduler.daily_analysis.DataAPIClient") as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch("src.scheduler.daily_analysis.TimeOfDayPatternDetector") as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = patterns
            mock_tod.return_value = mock_tod_instance

            with patch("src.scheduler.daily_analysis.CoOccurrencePatternDetector") as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                with patch("src.scheduler.daily_analysis.store_patterns"):
                    with patch("src.scheduler.daily_analysis.store_suggestion"):
                        with patch("src.scheduler.daily_analysis.get_db"):
                            with patch("src.scheduler.daily_analysis.OpenAIClient") as mock_openai:
                                from src.llm.openai_client import AutomationSuggestion

                                mock_suggestion = AutomationSuggestion(
                                    alias="Test",
                                    description="Test",
                                    automation_yaml="alias: Test",
                                    rationale="Test",
                                    category="convenience",
                                    priority="medium",
                                    confidence=0.95,
                                )

                                mock_openai_instance = AsyncMock()
                                # First succeeds, second fails, third succeeds
                                mock_openai_instance.generate_automation_suggestion.side_effect = [
                                    mock_suggestion,
                                    Exception("OpenAI error"),
                                    mock_suggestion,
                                ]
                                mock_openai_instance.total_tokens_used = 1500
                                mock_openai_instance.total_input_tokens = 900
                                mock_openai_instance.total_output_tokens = 600
                                mock_openai.return_value = mock_openai_instance

                                await scheduler.run_daily_analysis()

    # Check job history
    history = scheduler.get_job_history()
    assert len(history) == 1
    assert history[0]["status"] == "success"
    assert history[0]["suggestions_generated"] == 2
    assert history[0]["suggestions_failed"] == 1

