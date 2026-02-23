"""
Unit tests for LoggingMiddleware and metrics functions.

Tests request/response logging, metrics collection, and edge cases.
"""

import pytest
from fastapi import Request
from starlette.responses import Response

from src.middleware import LoggingMiddleware, get_metrics, record_execution, record_request


@pytest.fixture
def middleware():
    """Create a LoggingMiddleware instance for testing."""
    return LoggingMiddleware(lambda request: Response())


class TestMetrics:
    """Test suite for metrics functions."""

    def test_get_metrics_initial_state(self):
        """Test that initial metrics are zero."""
        metrics = get_metrics()
        assert metrics["total_requests"] == 0
        assert metrics["total_executions"] == 0
        assert metrics["successful_executions"] == 0
        assert metrics["failed_executions"] == 0
        assert metrics["average_execution_time"] == 0.0
        assert metrics["average_memory_used_mb"] == 0.0

    def test_record_request(self):
        """Test recording a request."""
        initial_requests = get_metrics()["total_requests"]
        record_request()
        metrics = get_metrics()
        assert metrics["total_requests"] == initial_requests + 1

    def test_record_execution_success(self):
        """Test recording a successful execution."""
        initial_executions = get_metrics()["total_executions"]
        initial_successful = get_metrics()["successful_executions"]
        
        record_execution(success=True, execution_time=1.5, memory_used_mb=50.0)
        
        metrics = get_metrics()
        assert metrics["total_executions"] == initial_executions + 1
        assert metrics["successful_executions"] == initial_successful + 1
        assert metrics["failed_executions"] == get_metrics()["failed_executions"]
        assert metrics["total_execution_time"] > 0
        assert metrics["total_memory_used"] > 0

    def test_record_execution_failure(self):
        """Test recording a failed execution."""
        initial_executions = get_metrics()["total_executions"]
        initial_failed = get_metrics()["failed_executions"]
        
        record_execution(success=False, execution_time=0.5, memory_used_mb=25.0)
        
        metrics = get_metrics()
        assert metrics["total_executions"] == initial_executions + 1
        assert metrics["failed_executions"] == initial_failed + 1
        assert metrics["successful_executions"] == get_metrics()["successful_executions"]

    def test_average_execution_time(self):
        """Test average execution time calculation."""
        # Record multiple executions
        record_execution(success=True, execution_time=1.0, memory_used_mb=10.0)
        record_execution(success=True, execution_time=2.0, memory_used_mb=20.0)
        record_execution(success=True, execution_time=3.0, memory_used_mb=30.0)
        
        metrics = get_metrics()
        # Average should be (1.0 + 2.0 + 3.0) / 3 = 2.0
        assert metrics["average_execution_time"] == pytest.approx(2.0, rel=0.1)

    def test_average_memory_used(self):
        """Test average memory used calculation."""
        # Record multiple executions
        record_execution(success=True, execution_time=1.0, memory_used_mb=10.0)
        record_execution(success=True, execution_time=1.0, memory_used_mb=20.0)
        record_execution(success=True, execution_time=1.0, memory_used_mb=30.0)
        
        metrics = get_metrics()
        # Average should be (10.0 + 20.0 + 30.0) / 3 = 20.0
        assert metrics["average_memory_used_mb"] == pytest.approx(20.0, rel=0.1)


@pytest.mark.asyncio
class TestLoggingMiddleware:
    """Test suite for LoggingMiddleware."""

    async def test_middleware_processes_request(self, middleware):
        """Test that middleware processes requests correctly."""
        # Create a mock request
        request = Request(
            scope={
                "type": "http",
                "method": "GET",
                "path": "/health",
                "headers": [],
            }
        )
        
        # Mock call_next
        async def call_next(request):
            return Response(status_code=200)
        
        # Process request
        response = await middleware.dispatch(request, call_next)
        
        assert response.status_code == 200

    async def test_middleware_logs_request_info(self, middleware, caplog):
        """Test that middleware logs request information."""
        import logging
        
        caplog.set_level(logging.INFO)
        
        request = Request(
            scope={
                "type": "http",
                "method": "POST",
                "path": "/execute",
                "headers": [],
            }
        )
        
        async def call_next(request):
            return Response(status_code=200)
        
        await middleware.dispatch(request, call_next)
        
        # Check that request was logged
        assert len(caplog.records) > 0
        assert any("Request:" in record.message for record in caplog.records)

