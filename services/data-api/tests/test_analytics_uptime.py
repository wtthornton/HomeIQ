"""
Unit tests for analytics endpoint uptime calculation
Story 24.1: Fix Hardcoded Monitoring Metrics
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.analytics_endpoints import calculate_service_uptime


def test_calculate_service_uptime_returns_100():
    """Test that uptime calculation returns 100% for running service"""
    # Mock SERVICE_START_TIME to be 1 hour ago
    start_time = datetime.utcnow() - timedelta(hours=1)
    
    with patch('src.analytics_endpoints.SERVICE_START_TIME', start_time):
        uptime = calculate_service_uptime()
        
        # Service has been running, should return 100%
        assert uptime == 100.0


def test_calculate_service_uptime_handles_errors():
    """Test that uptime calculation handles errors gracefully"""
    # Mock MODULE import to raise an exception
    with patch('src.analytics_endpoints.SERVICE_START_TIME', side_effect=ImportError("Cannot import")):
        uptime = calculate_service_uptime()
        
        # Should return None on error
        assert uptime is None


def test_calculate_service_uptime_recent_start():
    """Test uptime calculation for recently started service"""
    # Mock SERVICE_START_TIME to be 30 seconds ago
    start_time = datetime.utcnow() - timedelta(seconds=30)
    
    with patch('src.analytics_endpoints.SERVICE_START_TIME', start_time):
        uptime = calculate_service_uptime()
        
        # Service just started, should still return 100%
        assert uptime == 100.0


def test_calculate_service_uptime_not_hardcoded():
    """Regression test: Ensure uptime is NOT hardcoded to 99.9"""
    start_time = datetime.utcnow() - timedelta(hours=1)
    
    with patch('src.analytics_endpoints.SERVICE_START_TIME', start_time):
        uptime = calculate_service_uptime()
        
        # Should NOT be the old hardcoded value
        assert uptime != 99.9
        # Should be the new calculated value
        assert uptime == 100.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

