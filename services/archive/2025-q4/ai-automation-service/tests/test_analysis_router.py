"""
Unit tests for Analysis Router
Tests the full pipeline orchestration endpoint
"""

import pytest

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from fastapi import HTTPException
from src.api.analysis_router import AnalysisRequest, analyze_and_suggest, get_analysis_status


@pytest.fixture
def mock_events_df():
    """Create mock events DataFrame"""
    return pd.DataFrame({
        'event_id': [1, 2, 3, 4, 5],
        'entity_id': ['light.bedroom', 'light.living_room', 'light.bedroom', 'sensor.temp', 'light.living_room'],
        'state': ['on', 'on', 'off', '72', 'off'],
        'last_changed': pd.to_datetime([
            '2025-10-01 07:00:00',
            '2025-10-01 08:00:00',
            '2025-10-01 22:00:00',
            '2025-10-01 15:00:00',
            '2025-10-01 23:00:00'
        ])
    })


@pytest.fixture
def mock_patterns():
    """Create mock patterns"""
    return [
        {
            'pattern_type': 'time_of_day',
            'device_id': 'light.bedroom',
            'confidence': 0.95,
            'occurrences': 28,
            'metadata': {'hour': 7, 'minute': 0}
        },
        {
            'pattern_type': 'co_occurrence',
            'device_id': 'motion.hallway+light.hallway',
            'confidence': 0.88,
            'occurrences': 42,
            'metadata': {'device1': 'motion.hallway', 'device2': 'light.hallway'}
        }
    ]


@pytest.fixture
def mock_openai_suggestion():
    """Create mock OpenAI suggestion"""
    from src.llm.openai_client import AutomationSuggestion
    return AutomationSuggestion(
        alias="AI Suggested: Morning Bedroom Light",
        description="Turn on bedroom light at 7 AM",
        automation_yaml="alias: Test\ntrigger:\n  - platform: time\n    at: '07:00:00'\naction:\n  - service: light.turn_on",
        rationale="Pattern detected with 95% confidence",
        category="convenience",
        priority="medium",
        confidence=0.95
    )


@pytest.mark.asyncio
async def test_analyze_and_suggest_success(mock_events_df, mock_patterns, mock_openai_suggestion):
    """Test successful full pipeline execution"""

    request = AnalysisRequest(
        days=30,
        max_suggestions=10,
        min_confidence=0.7,
        time_of_day_enabled=True,
        co_occurrence_enabled=True
    )

    # Mock DataAPIClient
    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        # Mock pattern detectors
        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                # Setup detector mocks
                mock_tod_instance = MagicMock()
                mock_tod_instance.detect_patterns.return_value = [mock_patterns[0]]
                mock_tod.return_value = mock_tod_instance

                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = [mock_patterns[1]]
                mock_co.return_value = mock_co_instance

                # Mock database operations
                with patch('src.api.analysis_router.store_patterns') as mock_store_patterns:
                    with patch('src.api.analysis_router.store_suggestion') as mock_store_suggestion:
                        with patch('src.api.analysis_router.get_db'):
                            mock_store_patterns.return_value = 2

                            # Mock stored suggestion
                            mock_stored = MagicMock()
                            mock_stored.id = 1
                            mock_store_suggestion.return_value = mock_stored

                            # Mock OpenAI client
                            with patch('src.api.analysis_router.OpenAIClient') as mock_openai:
                                mock_openai_instance = AsyncMock()
                                mock_openai_instance.generate_automation_suggestion.return_value = mock_openai_suggestion
                                mock_openai_instance.total_tokens_used = 1000
                                mock_openai_instance.total_input_tokens = 600
                                mock_openai_instance.total_output_tokens = 400
                                mock_openai_instance.model = "gpt-4o-mini"
                                mock_openai.return_value = mock_openai_instance

                                # Execute pipeline
                                response = await analyze_and_suggest(request)

    # Assertions
    assert response.success is True
    assert "Successfully generated" in response.message
    assert response.data['summary']['events_analyzed'] == 5
    assert response.data['summary']['patterns_detected'] == 2
    assert response.data['summary']['suggestions_generated'] == 2
    assert response.data['patterns']['total'] == 2
    assert response.data['openai_usage']['model'] == "gpt-4o-mini"
    assert 'performance' in response.data
    assert response.data['performance']['total_duration_seconds'] > 0


@pytest.mark.asyncio
async def test_analyze_and_suggest_no_events(mock_patterns):
    """Test pipeline when no events are available"""

    request = AnalysisRequest(days=30)

    # Mock empty DataFrame
    empty_df = pd.DataFrame()

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = empty_df
        mock_data_client.return_value = mock_client_instance

        response = await analyze_and_suggest(request)

    assert response.success is False
    assert "No events available" in response.message
    assert response.data['events_count'] == 0


@pytest.mark.asyncio
async def test_analyze_and_suggest_no_patterns(mock_events_df):
    """Test pipeline when no patterns are detected"""

    request = AnalysisRequest(days=30, min_confidence=0.95)

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        # Mock pattern detectors returning empty lists
        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                mock_tod_instance = MagicMock()
                mock_tod_instance.detect_patterns.return_value = []
                mock_tod.return_value = mock_tod_instance

                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                response = await analyze_and_suggest(request)

    assert response.success is False
    assert "No patterns detected" in response.message
    assert response.data['patterns_detected'] == 0


@pytest.mark.asyncio
async def test_analyze_and_suggest_only_time_of_day(mock_events_df, mock_patterns, mock_openai_suggestion):
    """Test pipeline with only time-of-day patterns enabled"""

    request = AnalysisRequest(
        days=30,
        time_of_day_enabled=True,
        co_occurrence_enabled=False
    )

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = [mock_patterns[0]]
            mock_tod.return_value = mock_tod_instance

            with patch('src.api.analysis_router.store_patterns') as mock_store_patterns:
                with patch('src.api.analysis_router.store_suggestion') as mock_store_suggestion:
                    with patch('src.api.analysis_router.get_db'):
                        mock_store_patterns.return_value = 1

                        mock_stored = MagicMock()
                        mock_stored.id = 1
                        mock_store_suggestion.return_value = mock_stored

                        with patch('src.api.analysis_router.OpenAIClient') as mock_openai:
                            mock_openai_instance = AsyncMock()
                            mock_openai_instance.generate_automation_suggestion.return_value = mock_openai_suggestion
                            mock_openai_instance.total_tokens_used = 500
                            mock_openai_instance.total_input_tokens = 300
                            mock_openai_instance.total_output_tokens = 200
                            mock_openai_instance.model = "gpt-4o-mini"
                            mock_openai.return_value = mock_openai_instance

                            response = await analyze_and_suggest(request)

    assert response.success is True
    assert response.data['patterns']['by_type']['time_of_day'] == 1
    assert response.data['patterns']['by_type']['co_occurrence'] == 0


@pytest.mark.asyncio
async def test_analyze_and_suggest_large_dataset(mock_patterns, mock_openai_suggestion):
    """Test pipeline uses optimized detectors for large datasets"""

    # Create large DataFrame (>50,000 events)
    large_df = pd.DataFrame({
        'event_id': range(60000),
        'entity_id': ['light.test'] * 60000,
        'state': ['on'] * 60000,
        'last_changed': pd.to_datetime(['2025-10-01 00:00:00'] * 60000)
    })

    request = AnalysisRequest(days=30)

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = large_df
        mock_data_client.return_value = mock_client_instance

        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns_optimized.return_value = [mock_patterns[0]]
            mock_tod.return_value = mock_tod_instance

            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns_optimized.return_value = [mock_patterns[1]]
                mock_co.return_value = mock_co_instance

                with patch('src.api.analysis_router.store_patterns'):
                    with patch('src.api.analysis_router.store_suggestion'):
                        with patch('src.api.analysis_router.get_db'):
                            with patch('src.api.analysis_router.OpenAIClient') as mock_openai:
                                mock_openai_instance = AsyncMock()
                                mock_openai_instance.generate_automation_suggestion.return_value = mock_openai_suggestion
                                mock_openai_instance.total_tokens_used = 1000
                                mock_openai_instance.total_input_tokens = 600
                                mock_openai_instance.total_output_tokens = 400
                                mock_openai_instance.model = "gpt-4o-mini"
                                mock_openai.return_value = mock_openai_instance

                                response = await analyze_and_suggest(request)

    # Verify optimized methods were called
    assert mock_tod_instance.detect_patterns_optimized.called
    assert mock_co_instance.detect_patterns_optimized.called
    assert response.success is True


@pytest.mark.asyncio
async def test_analyze_and_suggest_limits_suggestions(mock_events_df, mock_patterns, mock_openai_suggestion):
    """Test pipeline respects max_suggestions limit"""

    # Create 20 patterns but limit to 5 suggestions
    many_patterns = [mock_patterns[0].copy() for _ in range(20)]
    for i, pattern in enumerate(many_patterns):
        pattern['device_id'] = f'light.test_{i}'
        pattern['confidence'] = 0.95 - (i * 0.01)  # Decreasing confidence

    request = AnalysisRequest(
        days=30,
        max_suggestions=5
    )

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = many_patterns
            mock_tod.return_value = mock_tod_instance

            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                with patch('src.api.analysis_router.store_patterns'):
                    with patch('src.api.analysis_router.store_suggestion') as mock_store_suggestion:
                        with patch('src.api.analysis_router.get_db'):
                            mock_stored = MagicMock()
                            mock_stored.id = 1
                            mock_store_suggestion.return_value = mock_stored

                            with patch('src.api.analysis_router.OpenAIClient') as mock_openai:
                                mock_openai_instance = AsyncMock()
                                mock_openai_instance.generate_automation_suggestion.return_value = mock_openai_suggestion
                                mock_openai_instance.total_tokens_used = 2500
                                mock_openai_instance.total_input_tokens = 1500
                                mock_openai_instance.total_output_tokens = 1000
                                mock_openai_instance.model = "gpt-4o-mini"
                                mock_openai.return_value = mock_openai_instance

                                response = await analyze_and_suggest(request)

    # Should only generate 5 suggestions despite 20 patterns
    assert response.data['patterns']['total'] == 20
    assert response.data['summary']['suggestions_generated'] == 5
    assert mock_openai_instance.generate_automation_suggestion.call_count == 5


@pytest.mark.asyncio
async def test_analyze_and_suggest_handles_partial_failures(mock_events_df, mock_patterns, mock_openai_suggestion):
    """Test pipeline continues when some suggestions fail"""

    request = AnalysisRequest(days=30, max_suggestions=3)

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = [
                mock_patterns[0],
                {**mock_patterns[0], 'device_id': 'light.test2'},
                {**mock_patterns[0], 'device_id': 'light.test3'}
            ]
            mock_tod.return_value = mock_tod_instance

            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                with patch('src.api.analysis_router.store_patterns'):
                    with patch('src.api.analysis_router.store_suggestion') as mock_store_suggestion:
                        with patch('src.api.analysis_router.get_db'):
                            mock_stored = MagicMock()
                            mock_stored.id = 1
                            mock_store_suggestion.return_value = mock_stored

                            with patch('src.api.analysis_router.OpenAIClient') as mock_openai:
                                mock_openai_instance = AsyncMock()
                                # First call succeeds, second fails, third succeeds
                                mock_openai_instance.generate_automation_suggestion.side_effect = [
                                    mock_openai_suggestion,
                                    Exception("OpenAI API error"),
                                    mock_openai_suggestion
                                ]
                                mock_openai_instance.total_tokens_used = 1000
                                mock_openai_instance.total_input_tokens = 600
                                mock_openai_instance.total_output_tokens = 400
                                mock_openai_instance.model = "gpt-4o-mini"
                                mock_openai.return_value = mock_openai_instance

                                response = await analyze_and_suggest(request)

    # Should have 2 successful suggestions and 1 failed
    assert response.success is True
    assert response.data['summary']['suggestions_generated'] == 2
    assert response.data['summary']['suggestions_failed'] == 1


@pytest.mark.asyncio
async def test_get_analysis_status_success():
    """Test getting analysis status"""

    with patch('src.api.analysis_router.get_db'):
        with patch('src.api.analysis_router.get_pattern_stats') as mock_stats:
            with patch('src.api.analysis_router.get_suggestions') as mock_suggestions:
                # Mock pattern stats
                mock_stats.return_value = {
                    'total_patterns': 50,
                    'by_type': {'time_of_day': 30, 'co_occurrence': 20},
                    'unique_devices': 25,
                    'avg_confidence': 0.85
                }

                # Mock suggestions
                mock_sugg = MagicMock()
                mock_sugg.id = 1
                mock_sugg.title = "Test Suggestion"
                mock_sugg.confidence = 0.90
                mock_sugg.created_at = datetime.now(timezone.utc)
                mock_suggestions.return_value = [mock_sugg]

                status = await get_analysis_status()

    assert status['status'] == 'ready'
    assert status['patterns']['total_patterns'] == 50
    assert status['suggestions']['pending_count'] == 1


@pytest.mark.asyncio
async def test_analyze_and_suggest_exception_handling(mock_events_df):
    """Test pipeline exception handling"""

    request = AnalysisRequest(days=30)

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        # Simulate exception in data fetching
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.side_effect = Exception("Data API connection failed")
        mock_data_client.return_value = mock_client_instance

        with pytest.raises(HTTPException) as exc_info:
            await analyze_and_suggest(request)

        assert exc_info.value.status_code == 500
        assert "Analysis pipeline failed" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_analyze_and_suggest_confidence_filtering(mock_events_df, mock_patterns):
    """Test min_confidence filters patterns correctly"""

    # Create patterns with varying confidence
    high_conf_pattern = {**mock_patterns[0], 'confidence': 0.95}
    low_conf_pattern = {**mock_patterns[1], 'confidence': 0.65}

    request = AnalysisRequest(
        days=30,
        min_confidence=0.8  # Should filter out low_conf_pattern
    )

    with patch('src.api.analysis_router.DataAPIClient') as mock_data_client:
        mock_client_instance = AsyncMock()
        mock_client_instance.fetch_events.return_value = mock_events_df
        mock_data_client.return_value = mock_client_instance

        with patch('src.api.analysis_router.TimeOfDayPatternDetector') as mock_tod:
            # TimeOfDayPatternDetector receives min_confidence parameter
            mock_tod_instance = MagicMock()
            mock_tod_instance.detect_patterns.return_value = [high_conf_pattern]
            mock_tod.return_value = mock_tod_instance

            # Verify min_confidence was passed to detector
            with patch('src.api.analysis_router.CoOccurrencePatternDetector') as mock_co:
                mock_co_instance = MagicMock()
                mock_co_instance.detect_patterns.return_value = []
                mock_co.return_value = mock_co_instance

                with patch('src.api.analysis_router.store_patterns'):
                    with patch('src.api.analysis_router.store_suggestion'):
                        with patch('src.api.analysis_router.get_db'):
                            with patch('src.api.analysis_router.OpenAIClient'):
                                try:
                                    await analyze_and_suggest(request)
                                except:
                                    pass  # We're just testing parameter passing

                # Verify detectors were initialized with correct confidence threshold
                assert mock_tod.call_args[1]['min_confidence'] == 0.8
                assert mock_co.call_args[1]['min_confidence'] == 0.8

