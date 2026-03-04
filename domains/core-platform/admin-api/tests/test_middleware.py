"""Tests for Admin API middleware configuration."""

from unittest.mock import MagicMock, patch

from src.middleware import (
    setup_cors,
    setup_observability,
)


class TestSetupObservability:
    """Tests for observability middleware setup."""

    def test_fallback_when_not_available(self) -> None:
        """Uses FastAPICorrelationMiddleware when observability is unavailable."""
        app = MagicMock()
        with patch("src.middleware.OBSERVABILITY_AVAILABLE", False):
            setup_observability(app)
        app.add_middleware.assert_called_once()

    def test_otel_when_available(self) -> None:
        """Sets up OpenTelemetry tracing when observability is available."""
        app = MagicMock()
        with (
            patch("src.middleware.OBSERVABILITY_AVAILABLE", True),
            patch("src.middleware.setup_tracing", return_value=True),
            patch("src.middleware.instrument_fastapi", return_value=True),
        ):
            setup_observability(app)
        app.add_middleware.assert_called_once()


class TestSetupCors:
    """Tests for CORS middleware setup."""

    def test_wildcard_disables_credentials(self) -> None:
        """Disables credentials when '*' is in allowed origins."""
        app = MagicMock()
        setup_cors(
            app,
            origins=["*"],
            methods=["GET"],
            headers=["*"],
        )
        call_kwargs = app.add_middleware.call_args
        assert call_kwargs.kwargs["allow_credentials"] is False

    def test_specific_origins_enable_credentials(self) -> None:
        """Enables credentials when origins are specific."""
        app = MagicMock()
        setup_cors(
            app,
            origins=["http://localhost:3000"],
            methods=["GET", "POST"],
            headers=["Authorization"],
        )
        call_kwargs = app.add_middleware.call_args
        assert call_kwargs.kwargs["allow_credentials"] is True
