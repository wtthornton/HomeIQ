"""
Unit tests for Pattern Analysis Scheduler

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.scheduler.pattern_analysis import PatternAnalysisScheduler


class TestPatternAnalysisScheduler:
    """Test suite for PatternAnalysisScheduler."""
    
    @pytest.mark.unit
    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        scheduler = PatternAnalysisScheduler(
            cron_schedule="0 3 * * *",
            enable_incremental=True
        )
        
        assert scheduler.cron_schedule == "0 3 * * *"
        assert scheduler.enable_incremental is True
        assert scheduler.is_running is False
    
    @pytest.mark.unit
    def test_set_mqtt_client(self):
        """Test setting MQTT client."""
        scheduler = PatternAnalysisScheduler()
        mock_mqtt = AsyncMock()
        
        scheduler.set_mqtt_client(mock_mqtt)
        
        assert scheduler.mqtt_client == mock_mqtt
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.scheduler
    async def test_run_pattern_analysis_empty_events(
        self, test_db, mock_data_api_client, mock_mqtt_client
    ):
        """Test pattern analysis with empty events."""
        scheduler = PatternAnalysisScheduler()
        scheduler.set_mqtt_client(mock_mqtt_client)
        
        # Mock empty events
        import pandas as pd
        mock_data_api_client.fetch_events = AsyncMock(return_value=pd.DataFrame())
        
        # Run analysis
        await scheduler.run_pattern_analysis()
        
        # Should complete without errors
        assert True  # If we get here, no exceptions were raised
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.scheduler
    @pytest.mark.slow
    async def test_run_pattern_analysis_with_events(
        self, test_db, mock_data_api_client, mock_mqtt_client
    ):
        """Test pattern analysis with sample events."""
        scheduler = PatternAnalysisScheduler()
        scheduler.set_mqtt_client(mock_mqtt_client)
        
        # Mock events (already set up in mock_data_api_client fixture)
        # Run analysis
        await scheduler.run_pattern_analysis()
        
        # Should complete and publish notification
        mock_mqtt_client.publish.assert_called_once()
        
        # Check notification payload
        call_args = mock_mqtt_client.publish.call_args
        assert call_args is not None
        payload = call_args[0][1]  # Second argument is payload
        assert "status" in payload
        assert "patterns_detected" in payload
        assert "synergies_detected" in payload

