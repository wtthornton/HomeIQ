"""
Tests for Huey configuration
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_db():
    """Create temporary database file"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_huey_initialization(temp_db):
    """Test Huey initialization"""
    try:
        # Mock config to use temp database
        import src.config as config_module
        from src.queue.huey_config import get_huey_instance

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
        import shutil
        import tempfile

        from src.queue.huey_config import get_huey_instance

        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        db_path = str(Path(temp_dir) / "subdir" / "queue.db")

        # Mock config
        import src.config as config_module

        original_path = config_module.settings.huey_database_path
        config_module.settings.huey_database_path = db_path

        try:
            huey = get_huey_instance()
            assert Path(db_path).parent.exists()
            assert huey is not None
        finally:
            config_module.settings.huey_database_path = original_path
            shutil.rmtree(temp_dir, ignore_errors=True)

    except ImportError:
        pytest.skip("Huey not available")
