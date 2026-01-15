"""
Tests for Huey configuration
"""

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    """Create temporary database file"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as f:
        db_path = f.name
    yield db_path
    # Cleanup
    if os.path.exists(db_path):
        os.unlink(db_path)


def test_huey_initialization(temp_db):
    """Test Huey initialization with SQLite backend"""
    try:
        from src.queue.huey_config import get_huey_instance
        
        # Mock config to use temp database
        import src.config as config_module
        original_path = config_module.settings.huey_database_path
        config_module.settings.huey_database_path = temp_db
        
        try:
            huey = get_huey_instance()
            assert huey is not None
            assert huey.results is True
        finally:
            config_module.settings.huey_database_path = original_path
            
    except ImportError:
        pytest.skip("Huey not available")


def test_huey_database_path_creation():
    """Test that database directory is created if it doesn't exist"""
    try:
        from src.queue.huey_config import get_huey_instance
        import tempfile
        import shutil
        
        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        db_path = os.path.join(temp_dir, "subdir", "queue.db")
        
        # Mock config
        import src.config as config_module
        original_path = config_module.settings.huey_database_path
        config_module.settings.huey_database_path = db_path
        
        try:
            huey = get_huey_instance()
            assert os.path.exists(os.path.dirname(db_path))
            assert huey is not None
        finally:
            config_module.settings.huey_database_path = original_path
            shutil.rmtree(temp_dir, ignore_errors=True)
            
    except ImportError:
        pytest.skip("Huey not available")
