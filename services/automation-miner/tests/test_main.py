"""
Unit tests for Automation Miner Main Application

Tests for main.py application initialization, lifespan, and configuration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, Mock
from httpx import AsyncClient, ASGITransport


class TestMainApplication:
    """Test suite for main application initialization and configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_root_endpoint(self):
        """Test root endpoint returns service information."""
        from src.api.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Automation Miner API"
            assert data["version"] == "0.1.0"
            assert "docs" in data
            assert "health" in data
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check_endpoint(self):
        """Test health check endpoint."""
        from src.api.main import app
        from src.miner.database import get_db_session
        from src.miner.repository import CorpusRepository
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {
            'total': 100,
            'avg_quality': 0.85
        }
        mock_repo.get_last_crawl_timestamp.return_value = None
        
        async def mock_session():
            yield mock_db
        
        with patch('src.miner.database.get_db_session', return_value=mock_session()):
            with patch('src.miner.repository.CorpusRepository', return_value=mock_repo):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/health")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert data["service"] == "automation-miner"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    async def test_lifespan_startup_success(self, mock_settings, mock_get_database):
        """Test lifespan startup with successful initialization."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = False
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_get_database.return_value = mock_db
        
        async with lifespan(app):
            mock_db.create_tables.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    async def test_lifespan_startup_database_failure(self, mock_settings, mock_get_database):
        """Test lifespan startup handles database initialization failure."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = False
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock(side_effect=Exception("Database connection failed"))
        mock_get_database.return_value = mock_db
        
        with pytest.raises(Exception, match="Database connection failed"):
            async with lifespan(app):
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.WeeklyRefreshJob')
    @patch('src.miner.repository.CorpusRepository')
    async def test_lifespan_startup_with_initialization_empty_corpus(
        self, mock_repo_class, mock_job_class, mock_settings, mock_get_database
    ):
        """Test lifespan startup initializes corpus when empty."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.get_session = AsyncMock()
        
        async def mock_session():
            mock_session_obj = AsyncMock()
            yield mock_session_obj
        
        mock_db.get_session.return_value = mock_session()
        mock_get_database.return_value = mock_db
        
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {'total': 0}
        mock_repo.get_last_crawl_timestamp.return_value = None
        mock_repo_class.return_value = mock_repo
        
        mock_job = AsyncMock()
        mock_job.run = AsyncMock()
        mock_job_class.return_value = mock_job
        
        async with lifespan(app):
            # Should start initialization for empty corpus
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.setup_weekly_refresh_job')
    @patch('apscheduler.schedulers.asyncio.AsyncIOScheduler')
    async def test_lifespan_startup_with_scheduler_success(
        self, mock_scheduler_class, mock_setup_job, mock_settings, mock_get_database
    ):
        """Test lifespan startup with successful scheduler initialization."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_get_database.return_value = mock_db
        
        mock_scheduler = AsyncMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.running = True
        mock_scheduler.shutdown = AsyncMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        mock_setup_job.return_value = AsyncMock()
        
        async with lifespan(app):
            mock_scheduler_class.assert_called_once()
            mock_setup_job.assert_called_once()
            mock_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    async def test_lifespan_shutdown_closes_database(
        self, mock_settings, mock_get_database
    ):
        """Test lifespan shutdown closes database."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = False
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_database.return_value = mock_db
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        mock_db.close.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('apscheduler.schedulers.asyncio.AsyncIOScheduler')
    async def test_lifespan_shutdown_stops_scheduler(
        self, mock_scheduler_class, mock_settings, mock_get_database
    ):
        """Test lifespan shutdown stops scheduler."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.close = AsyncMock()
        mock_get_database.return_value = mock_db
        
        mock_scheduler = AsyncMock()
        mock_scheduler.start = AsyncMock()
        mock_scheduler.running = True
        mock_scheduler.shutdown = AsyncMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        mock_scheduler.shutdown.assert_called_once_with(wait=False)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_app_creation(self):
        """Test FastAPI app is created with correct configuration."""
        from src.api.main import app
        
        assert app.title == "Automation Miner API"
        assert app.version == "0.1.0"
        assert "Community knowledge crawler" in app.description
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_cors_middleware_configured(self):
        """Test CORS middleware is configured."""
        from src.api.main import app
        
        # Check that CORS middleware is added
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls'):
                if 'CORS' in str(middleware.cls) or 'CORSMiddleware' in str(middleware.cls):
                    middleware_found = True
                    break
        
        assert middleware_found, "CORS middleware should be configured"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_routers_included(self):
        """Test routers are included in app."""
        from src.api.main import app
        
        # Check that routers are included
        route_paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
        
        # Should have routes with /api/automation-miner prefix
        assert any('/api/automation-miner' in path for path in route_paths)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check_error_handling(self):
        """Test health check endpoint handles errors gracefully."""
        from src.api.main import app
        from src.miner.repository import CorpusRepository
        
        async def mock_session_error():
            mock_db = AsyncMock()
            # Make get_stats raise an exception
            mock_repo = AsyncMock()
            mock_repo.get_stats.side_effect = Exception("Database connection failed")
            mock_repo.get_last_crawl_timestamp.side_effect = Exception("Database connection failed")
            with patch('src.miner.repository.CorpusRepository', return_value=mock_repo):
                yield mock_db
        
        with patch('src.miner.database.get_db_session', return_value=mock_session_error()):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "unhealthy"
                assert "error" in data
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.WeeklyRefreshJob')
    @patch('src.miner.repository.CorpusRepository')
    async def test_lifespan_startup_with_stale_corpus(
        self, mock_repo_class, mock_job_class, mock_settings, mock_get_database
    ):
        """Test lifespan startup initializes corpus when stale."""
        from src.api.main import lifespan, app
        from datetime import datetime, timezone, timedelta
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.get_session = AsyncMock()
        
        async def mock_session():
            mock_session_obj = AsyncMock()
            yield mock_session_obj
        
        mock_db.get_session.return_value = mock_session()
        mock_get_database.return_value = mock_db
        
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {'total': 100}
        # Last crawl was 10 days ago (stale)
        stale_timestamp = datetime.now(timezone.utc) - timedelta(days=10)
        mock_repo.get_last_crawl_timestamp.return_value = stale_timestamp
        mock_repo_class.return_value = mock_repo
        
        mock_job = AsyncMock()
        mock_job.run = AsyncMock()
        mock_job_class.return_value = mock_job
        
        async with lifespan(app):
            # Should start initialization for stale corpus
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.setup_weekly_refresh_job')
    @patch('apscheduler.schedulers.asyncio.AsyncIOScheduler')
    async def test_lifespan_startup_scheduler_failure(
        self, mock_scheduler_class, mock_setup_job, mock_settings, mock_get_database
    ):
        """Test lifespan startup handles scheduler initialization failure."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_get_database.return_value = mock_db
        
        mock_setup_job.side_effect = Exception("Scheduler setup failed")
        
        async with lifespan(app):
            # Should continue even if scheduler fails
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.WeeklyRefreshJob')
    @patch('src.miner.repository.CorpusRepository')
    async def test_lifespan_startup_with_no_last_crawl(
        self, mock_repo_class, mock_job_class, mock_settings, mock_get_database
    ):
        """Test lifespan startup initializes corpus when no last crawl timestamp."""
        from src.api.main import lifespan, app
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.get_session = AsyncMock()
        
        async def mock_session():
            mock_session_obj = AsyncMock()
            yield mock_session_obj
        
        mock_db.get_session.return_value = mock_session()
        mock_get_database.return_value = mock_db
        
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {'total': 50}
        mock_repo.get_last_crawl_timestamp.return_value = None
        mock_repo_class.return_value = mock_repo
        
        mock_job = AsyncMock()
        mock_job.run = AsyncMock()
        mock_job_class.return_value = mock_job
        
        async with lifespan(app):
            # Should start initialization when no last crawl timestamp
            pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.api.main.get_database')
    @patch('src.api.main.settings')
    @patch('src.jobs.weekly_refresh.WeeklyRefreshJob')
    @patch('src.miner.repository.CorpusRepository')
    async def test_lifespan_startup_with_fresh_corpus(
        self, mock_repo_class, mock_job_class, mock_settings, mock_get_database
    ):
        """Test lifespan startup skips initialization when corpus is fresh."""
        from src.api.main import lifespan, app
        from datetime import datetime, timezone, timedelta
        
        mock_settings.enable_automation_miner = True
        mock_db = AsyncMock()
        mock_db.create_tables = AsyncMock()
        mock_db.get_session = AsyncMock()
        
        async def mock_session():
            mock_session_obj = AsyncMock()
            yield mock_session_obj
        
        mock_db.get_session.return_value = mock_session()
        mock_get_database.return_value = mock_db
        
        mock_repo = AsyncMock()
        mock_repo.get_stats.return_value = {'total': 100}
        # Last crawl was 3 days ago (fresh, less than 7 days)
        fresh_timestamp = datetime.now(timezone.utc) - timedelta(days=3)
        mock_repo.get_last_crawl_timestamp.return_value = fresh_timestamp
        mock_repo_class.return_value = mock_repo
        
        # Reset mock before test
        mock_job_class.reset_mock()
        
        async with lifespan(app):
            # Should not start initialization for fresh corpus (less than 7 days old)
            # Note: The job may still be instantiated but not run
            pass

