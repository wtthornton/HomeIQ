"""
Tests for Huey task definitions
"""

import pytest


def test_get_task_config_default():
    """Test default task configuration"""
    try:
        from src.queue.tasks import _get_task_config
        
        config = _get_task_config(None)
        assert config["retries"] == 3
        assert config["retry_delay"] == 30
        assert config["priority"] == 5
        
    except ImportError:
        pytest.skip("Huey not available")


def test_get_task_config_high_risk():
    """Test task configuration for high-risk automation"""
    try:
        from src.queue.tasks import _get_task_config
        
        spec = {
            "policy": {
                "risk": "high"
            }
        }
        
        config = _get_task_config(spec)
        assert config["retries"] == 10
        assert config["retry_delay"] == 60
        assert config["priority"] == 10
        
    except ImportError:
        pytest.skip("Huey not available")


def test_get_task_config_medium_risk():
    """Test task configuration for medium-risk automation"""
    try:
        from src.queue.tasks import _get_task_config
        
        spec = {
            "policy": {
                "risk": "medium"
            }
        }
        
        config = _get_task_config(spec)
        assert config["retries"] == 5
        assert config["retry_delay"] == 30
        assert config["priority"] == 5
        
    except ImportError:
        pytest.skip("Huey not available")


def test_get_task_config_low_risk():
    """Test task configuration for low-risk automation"""
    try:
        from src.queue.tasks import _get_task_config
        
        spec = {
            "policy": {
                "risk": "low"
            }
        }
        
        config = _get_task_config(spec)
        assert config["retries"] == 3
        assert config["retry_delay"] == 15
        assert config["priority"] == 1
        
    except ImportError:
        pytest.skip("Huey not available")


def test_queue_automation_task():
    """Test queuing automation task"""
    try:
        from src.queue.tasks import queue_automation_task
        
        # This will create a task but may not execute without Huey consumer
        # Just test that it doesn't raise an error
        task = queue_automation_task(
            spec_id="test_spec",
            trigger_data={"type": "manual"},
            home_id="test_home",
            correlation_id="test_correlation"
        )
        
        assert task is not None
        
    except (ImportError, RuntimeError):
        pytest.skip("Huey not available or not configured")
