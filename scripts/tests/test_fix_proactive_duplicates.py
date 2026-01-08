"""
Integration tests for fix_proactive_duplicates.py

Tests the refactored async patterns, connection pooling, and retry logic.

Created: January 2026
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Import the module under test
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent
sys.path.insert(0, str(scripts_dir))

from fix_proactive_duplicates import (
    ProactiveDuplicateFixer,
    DuplicateAnalysis,
    TemperatureAnalysis,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_suggestions() -> list[dict[str, Any]]:
    """Sample suggestion data for testing."""
    return [
        {
            "id": "suggestion-1",
            "prompt": "Turn on the living room lights when motion detected",
            "created_at": "2026-01-01T10:00:00Z",
            "quality_score": 0.85,
            "status": "active",
            "context_type": "motion",
        },
        {
            "id": "suggestion-2",
            "prompt": "Turn on the living room lights when motion detected",  # Duplicate
            "created_at": "2026-01-02T10:00:00Z",
            "quality_score": 0.80,
            "status": "active",
            "context_type": "motion",
        },
        {
            "id": "suggestion-3",
            "prompt": "Adjust thermostat based on weather",
            "created_at": "2026-01-01T12:00:00Z",
            "quality_score": 0.90,
            "status": "active",
            "context_type": "weather",
            "prompt_metadata": {"temperature": 72.5},
        },
        {
            "id": "suggestion-4",
            "prompt": "Turn off lights at bedtime",
            "created_at": "2026-01-01T14:00:00Z",
            "quality_score": 0.75,
            "status": "active",
            "context_type": "time",
        },
    ]


@pytest.fixture
def sample_weather() -> dict[str, Any]:
    """Sample weather data for testing."""
    return {
        "temperature": 72.0,
        "location": "Home",
        "humidity": 45,
        "condition": "clear",
    }


@pytest.fixture
def mock_http_responses(sample_suggestions, sample_weather):
    """Create mock HTTP responses."""
    
    async def mock_request(method: str, url: str, **kwargs):
        """Mock HTTP request handler."""
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        
        if "suggestions" in url and method == "GET":
            # Pagination handling
            params = kwargs.get("params", {})
            offset = params.get("offset", 0)
            limit = params.get("limit", 100)
            
            suggestions = sample_suggestions[offset:offset + limit]
            response.json.return_value = {"suggestions": suggestions}
            
        elif "current-weather" in url:
            response.json.return_value = sample_weather
            
        elif method == "DELETE":
            response.status_code = 200
            
        response.raise_for_status = MagicMock()
        return response
    
    return mock_request


# ============================================================================
# Unit Tests - DuplicateAnalysis
# ============================================================================

class TestDuplicateAnalysis:
    """Tests for DuplicateAnalysis dataclass."""
    
    def test_has_duplicates_true(self):
        """Test has_duplicates property when duplicates exist."""
        analysis = DuplicateAnalysis(
            total_suggestions=4,
            duplicate_prompts={"prompt1": [{"id": "1"}, {"id": "2"}]},
            total_duplicates=1,
        )
        assert analysis.has_duplicates is True
    
    def test_has_duplicates_false(self):
        """Test has_duplicates property when no duplicates."""
        analysis = DuplicateAnalysis(
            total_suggestions=4,
            duplicate_prompts={},
            total_duplicates=0,
        )
        assert analysis.has_duplicates is False


class TestTemperatureAnalysis:
    """Tests for TemperatureAnalysis dataclass."""
    
    def test_significant_difference(self):
        """Test has_significant_difference flag."""
        analysis = TemperatureAnalysis(
            current_temp=72.0,
            avg_suggestion_temp=80.0,
            temp_difference=8.0,
            has_significant_difference=True,
        )
        assert analysis.has_significant_difference is True
    
    def test_no_significant_difference(self):
        """Test when temperature difference is small."""
        analysis = TemperatureAnalysis(
            current_temp=72.0,
            avg_suggestion_temp=73.0,
            temp_difference=1.0,
            has_significant_difference=False,
        )
        assert analysis.has_significant_difference is False


# ============================================================================
# Unit Tests - ProactiveDuplicateFixer
# ============================================================================

class TestProactiveDuplicateFixer:
    """Tests for ProactiveDuplicateFixer class."""
    
    def test_find_duplicates(self, sample_suggestions):
        """Test duplicate detection logic."""
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(sample_suggestions)
        
        assert analysis.total_suggestions == 4
        assert analysis.has_duplicates is True
        assert len(analysis.duplicate_prompts) == 1
        assert analysis.total_duplicates == 1
        
        # Check the duplicate prompt
        duplicate_prompt = "Turn on the living room lights when motion detected"
        assert duplicate_prompt in analysis.duplicate_prompts
        assert len(analysis.duplicate_prompts[duplicate_prompt]) == 2
    
    def test_find_duplicates_no_duplicates(self):
        """Test when no duplicates exist."""
        suggestions = [
            {"id": "1", "prompt": "Unique prompt 1"},
            {"id": "2", "prompt": "Unique prompt 2"},
            {"id": "3", "prompt": "Unique prompt 3"},
        ]
        
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(suggestions)
        
        assert analysis.has_duplicates is False
        assert analysis.total_duplicates == 0
    
    def test_find_duplicates_empty_list(self):
        """Test with empty suggestion list."""
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates([])
        
        assert analysis.total_suggestions == 0
        assert analysis.has_duplicates is False
    
    def test_analyze_temperature_data(self, sample_suggestions, sample_weather):
        """Test temperature analysis."""
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.analyze_temperature_data(sample_suggestions, sample_weather)
        
        assert analysis.current_temp == 72.0
        assert analysis.location == "Home"
        assert len(analysis.suggestion_temps) == 1
        assert analysis.suggestion_temps[0] == 72.5
    
    def test_analyze_temperature_no_weather(self, sample_suggestions):
        """Test temperature analysis without weather data."""
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.analyze_temperature_data(sample_suggestions, None)
        
        assert analysis.current_temp is None
        assert len(analysis.suggestion_temps) == 0
    
    def test_select_suggestions_for_deletion(self, sample_suggestions):
        """Test selection of suggestions to keep/delete."""
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(sample_suggestions)
        
        to_keep, to_delete = fixer.select_suggestions_for_deletion(
            analysis.duplicate_prompts
        )
        
        # Should keep the oldest (suggestion-1) and delete the newer one (suggestion-2)
        assert len(to_keep) == 1
        assert len(to_delete) == 1
        assert to_keep[0]["id"] == "suggestion-1"
        assert to_delete[0]["id"] == "suggestion-2"
    
    def test_extract_temperature_from_prompt_metadata(self):
        """Test temperature extraction from prompt_metadata."""
        fixer = ProactiveDuplicateFixer()
        suggestion = {
            "prompt_metadata": {"temperature": 75.5}
        }
        
        temp = fixer._extract_temperature(suggestion)
        assert temp == 75.5
    
    def test_extract_temperature_from_context_metadata(self):
        """Test temperature extraction from context_metadata."""
        fixer = ProactiveDuplicateFixer()
        suggestion = {
            "context_metadata": {
                "weather": {
                    "current": {"temperature": 68.0}
                }
            }
        }
        
        temp = fixer._extract_temperature(suggestion)
        assert temp == 68.0
    
    def test_extract_temperature_from_prompt_text(self):
        """Test temperature extraction from prompt text."""
        fixer = ProactiveDuplicateFixer()
        suggestion = {
            "prompt": "The current temperature is 72.5 °F outside"
        }
        
        temp = fixer._extract_temperature(suggestion)
        assert temp == 72.5
    
    def test_extract_temperature_none(self):
        """Test temperature extraction when not available."""
        fixer = ProactiveDuplicateFixer()
        suggestion = {
            "prompt": "Turn on the lights"
        }
        
        temp = fixer._extract_temperature(suggestion)
        assert temp is None


# ============================================================================
# Integration Tests - Async Operations
# ============================================================================

@pytest.mark.asyncio
class TestAsyncOperations:
    """Integration tests for async operations."""
    
    async def test_context_manager(self):
        """Test async context manager creates and closes client."""
        async with ProactiveDuplicateFixer() as fixer:
            assert fixer._client is not None
            assert isinstance(fixer._client, httpx.AsyncClient)
        
        # Client should be closed after exit
        assert fixer._client is None
    
    async def test_fetch_all_suggestions(self, mock_http_responses):
        """Test fetching suggestions with pagination."""
        async with ProactiveDuplicateFixer() as fixer:
            # Mock the request method
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            suggestions = await fixer.fetch_all_suggestions()
            
            assert len(suggestions) == 4
            assert suggestions[0]["id"] == "suggestion-1"
    
    async def test_get_current_weather(self, mock_http_responses):
        """Test fetching current weather."""
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            weather = await fixer.get_current_weather()
            
            assert weather is not None
            assert weather["temperature"] == 72.0
            assert weather["location"] == "Home"
    
    async def test_delete_suggestion(self, mock_http_responses):
        """Test deleting a suggestion."""
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            result = await fixer.delete_suggestion("suggestion-1")
            
            assert result is True
    
    async def test_delete_duplicates(self, sample_suggestions, mock_http_responses):
        """Test deleting duplicate suggestions."""
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            # Get duplicates
            analysis = fixer.find_duplicates(sample_suggestions)
            _, to_delete = fixer.select_suggestions_for_deletion(
                analysis.duplicate_prompts
            )
            
            successful, failed = await fixer.delete_duplicates(to_delete)
            
            assert successful == 1
            assert failed == 0


# ============================================================================
# Integration Tests - Retry Logic
# ============================================================================

@pytest.mark.asyncio
class TestRetryLogic:
    """Tests for retry logic on network failures."""
    
    async def test_retry_on_timeout(self):
        """Test that requests are retried on timeout."""
        call_count = 0
        
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ReadTimeout("Timeout")
            
            response = MagicMock(spec=httpx.Response)
            response.status_code = 200
            response.json.return_value = {"suggestions": []}
            response.raise_for_status = MagicMock()
            return response
        
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_request)
            
            suggestions = await fixer.fetch_all_suggestions()
            
            assert call_count == 3  # 2 retries + 1 success
            assert suggestions == []
    
    async def test_retry_exhausted(self):
        """Test that exception is raised after retries exhausted."""
        async def mock_request(*args, **kwargs):
            raise httpx.ConnectError("Connection failed")
        
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_request)
            
            with pytest.raises(httpx.ConnectError):
                await fixer.fetch_all_suggestions()
    
    async def test_no_retry_on_http_error(self):
        """Test that HTTP errors (4xx, 5xx) are not retried."""
        call_count = 0
        
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            response = MagicMock(spec=httpx.Response)
            response.status_code = 404
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=response
            )
            return response
        
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_request)
            
            with pytest.raises(httpx.HTTPStatusError):
                await fixer.fetch_all_suggestions()
            
            assert call_count == 1  # No retries


# ============================================================================
# Integration Tests - Full Workflow
# ============================================================================

@pytest.mark.asyncio
class TestFullWorkflow:
    """End-to-end workflow tests."""
    
    async def test_full_analysis_workflow(
        self, sample_suggestions, sample_weather, mock_http_responses
    ):
        """Test complete analysis workflow."""
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            # Fetch data
            suggestions = await fixer.fetch_all_suggestions()
            weather = await fixer.get_current_weather()
            
            # Analyze
            temp_analysis = fixer.analyze_temperature_data(suggestions, weather)
            dup_analysis = fixer.find_duplicates(suggestions)
            
            # Verify results
            assert len(suggestions) == 4
            assert weather is not None
            assert temp_analysis.current_temp == 72.0
            assert dup_analysis.has_duplicates is True
            assert dup_analysis.total_duplicates == 1
    
    async def test_full_deletion_workflow(
        self, sample_suggestions, mock_http_responses
    ):
        """Test complete deletion workflow."""
        async with ProactiveDuplicateFixer() as fixer:
            fixer._client.request = AsyncMock(side_effect=mock_http_responses)
            
            # Find duplicates
            analysis = fixer.find_duplicates(sample_suggestions)
            assert analysis.has_duplicates is True
            
            # Select for deletion
            to_keep, to_delete = fixer.select_suggestions_for_deletion(
                analysis.duplicate_prompts
            )
            
            # Delete
            successful, failed = await fixer.delete_duplicates(to_delete)
            
            # Verify
            assert successful == 1
            assert failed == 0
            assert len(to_keep) == 1
            assert to_keep[0]["id"] == "suggestion-1"  # Oldest kept


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_prompt_handling(self):
        """Test handling of suggestions with empty prompts."""
        suggestions = [
            {"id": "1", "prompt": "Valid prompt"},
            {"id": "2", "prompt": ""},  # Empty
            {"id": "3", "prompt": "   "},  # Whitespace only
            {"id": "4", "prompt": "Valid prompt"},  # Duplicate of first
        ]
        
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(suggestions)
        
        # Empty/whitespace prompts should be ignored
        assert analysis.total_suggestions == 4
        assert analysis.has_duplicates is True
        assert len(analysis.duplicate_prompts) == 1
    
    def test_none_values_in_suggestions(self):
        """Test handling of None values in suggestion fields."""
        suggestions = [
            {"id": "1", "prompt": "Test", "created_at": None, "quality_score": None},
            {"id": "2", "prompt": "Test", "created_at": "2026-01-01", "quality_score": 0.8},
        ]
        
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(suggestions)
        
        to_keep, to_delete = fixer.select_suggestions_for_deletion(
            analysis.duplicate_prompts
        )
        
        # Should handle None values gracefully
        assert len(to_keep) == 1
        assert len(to_delete) == 1
    
    def test_special_characters_in_prompt(self):
        """Test handling of special characters in prompts."""
        suggestions = [
            {"id": "1", "prompt": "Turn on lights 🏠 at 7:00 AM"},
            {"id": "2", "prompt": "Turn on lights 🏠 at 7:00 AM"},  # Duplicate with emoji
        ]
        
        fixer = ProactiveDuplicateFixer()
        analysis = fixer.find_duplicates(suggestions)
        
        assert analysis.has_duplicates is True
        assert analysis.total_duplicates == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
