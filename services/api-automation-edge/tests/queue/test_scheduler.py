"""
Tests for cron-based scheduling
"""

import pytest


def test_parse_cron_to_crontab():
    """Test parsing cron expression to Huey crontab"""
    try:
        from src.queue.scheduler import parse_cron_to_crontab
        
        # Test standard cron expression
        cron = parse_cron_to_crontab("0 7 * * *")
        assert cron is not None
        
        # Test with minutes interval
        cron = parse_cron_to_crontab("*/15 * * * *")
        assert cron is not None
        
    except ImportError:
        pytest.skip("Huey not available")


def test_parse_cron_invalid():
    """Test parsing invalid cron expression"""
    try:
        from src.queue.scheduler import parse_cron_to_crontab
        
        with pytest.raises(ValueError):
            parse_cron_to_crontab("invalid")
        
        with pytest.raises(ValueError):
            parse_cron_to_crontab("0 7 *")
            
    except ImportError:
        pytest.skip("Huey not available")


def test_automation_scheduler_initialization():
    """Test AutomationScheduler initialization"""
    try:
        from src.queue.scheduler import AutomationScheduler
        
        scheduler = AutomationScheduler()
        assert scheduler is not None
        assert scheduler.registered_schedules == {}
        
    except (ImportError, RuntimeError):
        pytest.skip("Huey not available or not configured")
