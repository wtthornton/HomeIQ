"""
Unit tests for AI Pattern Service Main Application

Epic 39, Story 39.5: Pattern Service Foundation
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
        from src.main import app
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "ai-pattern-service"
            assert data["version"] == "1.0.0"
            assert data["status"] == "operational"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_success(self, mock_settings, mock_init_db):
        """Test lifespan startup with successful initialization."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        async with lifespan(app):
            # Startup should complete without errors
            mock_init_db.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_database_failure(self, mock_settings, mock_init_db):
        """Test lifespan startup handles database initialization failure."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            async with lifespan(app):
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.OBSERVABILITY_AVAILABLE', True)
    @patch('src.main.setup_tracing')
    @patch('src.main.settings')
    async def test_lifespan_startup_with_observability(
        self, mock_settings, mock_setup_tracing, mock_init_db
    ):
        """Test lifespan startup with observability enabled."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        mock_setup_tracing.return_value = None
        
        async with lifespan(app):
            mock_setup_tracing.assert_called_once_with("ai-pattern-service")
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.MQTTNotificationClient')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_with_mqtt_success(
        self, mock_settings, mock_mqtt_client_class, mock_init_db
    ):
        """Test lifespan startup with successful MQTT connection."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = "mqtt://localhost"
        mock_settings.mqtt_port = 1883
        mock_settings.mqtt_username = None
        mock_settings.mqtt_password = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.connect.return_value = True
        mock_mqtt_client.broker = "localhost"
        mock_mqtt_client.port = 1883
        mock_mqtt_client_class.return_value = mock_mqtt_client
        
        async with lifespan(app):
            mock_mqtt_client_class.assert_called_once()
            mock_mqtt_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.MQTTNotificationClient')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_with_mqtt_failure(
        self, mock_settings, mock_mqtt_client_class, mock_init_db
    ):
        """Test lifespan startup handles MQTT connection failure gracefully."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = "mqtt://localhost"
        mock_settings.mqtt_port = 1883
        mock_settings.mqtt_username = None
        mock_settings.mqtt_password = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.connect.return_value = False
        mock_mqtt_client.broker = "localhost"
        mock_mqtt_client.port = 1883
        mock_mqtt_client_class.return_value = mock_mqtt_client
        
        async with lifespan(app):
            # Should continue even if MQTT fails
            mock_mqtt_client_class.assert_called_once()
            mock_mqtt_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.PatternAnalysisScheduler')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_with_scheduler_success(
        self, mock_settings, mock_scheduler_class, mock_init_db
    ):
        """Test lifespan startup with successful scheduler initialization."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        async with lifespan(app):
            mock_scheduler_class.assert_called_once_with(
                cron_schedule="0 2 * * *",
                enable_incremental=True
            )
            mock_scheduler.start.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.PatternAnalysisScheduler')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_startup_with_scheduler_failure(
        self, mock_settings, mock_scheduler_class, mock_init_db
    ):
        """Test lifespan startup handles scheduler failure gracefully."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_scheduler_class.side_effect = Exception("Scheduler initialization failed")
        
        async with lifespan(app):
            # Should continue even if scheduler fails
            mock_scheduler_class.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.PatternAnalysisScheduler')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_shutdown_stops_scheduler(
        self, mock_settings, mock_scheduler_class, mock_init_db
    ):
        """Test lifespan shutdown stops scheduler."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        mock_scheduler.stop.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.MQTTNotificationClient')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_shutdown_disconnects_mqtt(
        self, mock_settings, mock_mqtt_client_class, mock_init_db
    ):
        """Test lifespan shutdown disconnects MQTT client."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = "mqtt://localhost"
        mock_settings.mqtt_port = 1883
        mock_settings.mqtt_username = None
        mock_settings.mqtt_password = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.connect.return_value = True
        mock_mqtt_client_class.return_value = mock_mqtt_client
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        mock_mqtt_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.PatternAnalysisScheduler')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_shutdown_handles_scheduler_error(
        self, mock_settings, mock_scheduler_class, mock_init_db
    ):
        """Test lifespan shutdown handles scheduler stop error gracefully."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_scheduler = MagicMock()
        mock_scheduler.stop.side_effect = Exception("Stop error")
        mock_scheduler_class.return_value = mock_scheduler
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        # Should not raise exception
        mock_scheduler.stop.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.MQTTNotificationClient')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_shutdown_handles_mqtt_error(
        self, mock_settings, mock_mqtt_client_class, mock_init_db
    ):
        """Test lifespan shutdown handles MQTT disconnect error gracefully."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = "mqtt://localhost"
        mock_settings.mqtt_port = 1883
        mock_settings.mqtt_username = None
        mock_settings.mqtt_password = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.connect.return_value = True
        mock_mqtt_client.disconnect.side_effect = Exception("Disconnect error")
        mock_mqtt_client_class.return_value = mock_mqtt_client
        
        async with lifespan(app):
            pass  # Exit context to trigger shutdown
        
        # Should not raise exception
        mock_mqtt_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.PatternAnalysisScheduler')
    @patch('src.main.MQTTNotificationClient')
    @patch('src.main.init_db')
    @patch('src.main.OBSERVABILITY_AVAILABLE', False)
    @patch('src.main.settings')
    async def test_lifespan_scheduler_receives_mqtt_client(
        self, mock_settings, mock_init_db, mock_mqtt_client_class, mock_scheduler_class
    ):
        """Test scheduler receives MQTT client when available."""
        from src.main import lifespan, app
        
        mock_settings.mqtt_broker = "mqtt://localhost"
        mock_settings.mqtt_port = 1883
        mock_settings.mqtt_username = None
        mock_settings.mqtt_password = None
        mock_settings.analysis_schedule = "0 2 * * *"
        mock_settings.enable_incremental = True
        mock_init_db.return_value = AsyncMock()
        
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.connect.return_value = True
        mock_mqtt_client_class.return_value = mock_mqtt_client
        
        mock_scheduler = MagicMock()
        mock_scheduler_class.return_value = mock_scheduler
        
        async with lifespan(app):
            mock_scheduler.set_mqtt_client.assert_called_once_with(mock_mqtt_client)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_app_creation(self):
        """Test FastAPI app is created with correct configuration."""
        from src.main import app
        
        assert app.title == "AI Pattern Service"
        assert app.version == "1.0.0"
        assert app.description == "Pattern detection, synergy analysis, and community patterns service"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_cors_middleware_configured(self):
        """Test CORS middleware is configured."""
        from src.main import app
        
        # Check that CORS middleware is added by checking middleware stack
        # FastAPI stores middleware in user_middleware list
        middleware_found = False
        for middleware in app.user_middleware:
            if hasattr(middleware, 'cls'):
                if 'CORS' in str(middleware.cls) or 'CORSMiddleware' in str(middleware.cls):
                    middleware_found = True
                    break
        
        assert middleware_found, "CORS middleware should be configured"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    def test_health_router_included(self):
        """Test health router is included in app."""
        from src.main import app
        
        # Check that health router routes exist
        route_paths = []
        for route in app.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
        
        # Health router should add /health endpoint
        assert any('/health' in path for path in route_paths)

