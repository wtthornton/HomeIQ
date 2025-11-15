"""
Comprehensive Tests for Correlation Middleware
Modern 2025 Patterns: Middleware testing, async patterns

Module: shared/correlation_middleware.py
Coverage Target: >85%
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

# Import module under test
from correlation_middleware import (
    CorrelationMiddleware,
    correlation_context,
    with_correlation_id,
    propagate_correlation_id,
    extract_correlation_id,
    FastAPICorrelationMiddleware,
    AioHTTPCorrelationMiddleware,
    create_correlation_context,
    update_correlation_context,
    get_correlation_context,
    create_correlation_middleware
)
from logging_config import get_correlation_id, set_correlation_id, correlation_id


# ============================================================================
# Correlation Context Tests
# ============================================================================

class TestCorrelationContext:
    """Test correlation context manager"""

    def test_correlation_context_generates_id(self):
        """Test context manager generates correlation ID"""
        with correlation_context() as corr_id:
            assert corr_id is not None
            assert corr_id.startswith('req_')
            assert get_correlation_id() == corr_id

        # Context should be cleared after exit
        assert get_correlation_id() is None

    def test_correlation_context_with_provided_id(self):
        """Test context manager with provided correlation ID"""
        test_id = "custom_correlation_123"

        with correlation_context(test_id) as corr_id:
            assert corr_id == test_id
            assert get_correlation_id() == test_id

    def test_correlation_context_restores_previous_id(self):
        """Test context manager restores previous correlation ID"""
        set_correlation_id("outer_id")

        with correlation_context("inner_id"):
            assert get_correlation_id() == "inner_id"

        # Should restore outer ID
        assert get_correlation_id() == "outer_id"

        # Cleanup
        correlation_id.set(None)


# ============================================================================
# Decorator Tests
# ============================================================================

class TestCorrelationDecorator:
    """Test correlation ID decorator"""

    def test_with_correlation_id_decorator(self):
        """Test correlation ID decorator sets context"""
        test_id = "decorator_test_123"

        @with_correlation_id(test_id)
        def test_function():
            return get_correlation_id()

        result = test_function()

        assert result == test_id

    def test_with_correlation_id_generates_id(self):
        """Test decorator generates ID if not provided"""

        @with_correlation_id()
        def test_function():
            corr_id = get_correlation_id()
            assert corr_id is not None
            return corr_id

        result = test_function()
        assert result.startswith('req_')


# ============================================================================
# Header Propagation Tests
# ============================================================================

class TestHeaderPropagation:
    """Test correlation ID header propagation"""

    def test_propagate_correlation_id_adds_header(self):
        """Test correlation ID is added to headers"""
        set_correlation_id("propagate_test_123")

        headers = {"Content-Type": "application/json"}
        result = propagate_correlation_id(headers)

        assert result['X-Correlation-ID'] == "propagate_test_123"
        assert result['Content-Type'] == "application/json"

        # Cleanup
        correlation_id.set(None)

    def test_propagate_correlation_id_no_id(self):
        """Test propagation with no correlation ID"""
        correlation_id.set(None)

        headers = {"Content-Type": "application/json"}
        result = propagate_correlation_id(headers)

        assert 'X-Correlation-ID' not in result

    def test_propagate_correlation_id_custom_header(self):
        """Test propagation with custom header name"""
        set_correlation_id("custom_header_test")

        headers = {}
        result = propagate_correlation_id(headers, header_name='X-Request-ID')

        assert result['X-Request-ID'] == "custom_header_test"

        # Cleanup
        correlation_id.set(None)

    def test_extract_correlation_id_from_headers(self):
        """Test extracting correlation ID from headers"""
        headers = {
            'X-Correlation-ID': 'extract_test_123',
            'Content-Type': 'application/json'
        }

        corr_id = extract_correlation_id(headers)

        assert corr_id == 'extract_test_123'

    def test_extract_correlation_id_not_present(self):
        """Test extracting when correlation ID not in headers"""
        headers = {'Content-Type': 'application/json'}

        corr_id = extract_correlation_id(headers)

        assert corr_id is None


# ============================================================================
# FastAPI Middleware Tests
# ============================================================================

class TestFastAPICorrelationMiddleware:
    """Test FastAPI correlation middleware"""

    @pytest.mark.asyncio
    async def test_fastapi_middleware_adds_correlation_id(self):
        """Test FastAPI middleware adds correlation ID"""
        # Mock ASGI app
        mock_app = AsyncMock()

        middleware = FastAPICorrelationMiddleware(mock_app)

        # Mock scope (HTTP request)
        scope = {
            "type": "http",
            "headers": []
        }

        receive = AsyncMock()
        send = AsyncMock()

        # Call middleware
        await middleware(scope, receive, send)

        # Verify correlation ID was set in scope
        assert 'correlation_id' in scope
        assert scope['correlation_id'].startswith('req_')

    @pytest.mark.asyncio
    async def test_fastapi_middleware_uses_existing_id(self):
        """Test FastAPI middleware uses existing correlation ID"""
        mock_app = AsyncMock()
        middleware = FastAPICorrelationMiddleware(mock_app)

        existing_id = "existing_correlation_123"

        scope = {
            "type": "http",
            "headers": [
                (b"x-correlation-id", existing_id.encode())
            ]
        }

        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        assert scope['correlation_id'] == existing_id

    @pytest.mark.asyncio
    async def test_fastapi_middleware_adds_response_header(self):
        """Test FastAPI middleware adds correlation ID to response"""
        mock_app = AsyncMock()
        middleware = FastAPICorrelationMiddleware(mock_app)

        scope = {
            "type": "http",
            "headers": []
        }

        receive = AsyncMock()
        send_messages = []

        async def capture_send(message):
            send_messages.append(message)

        await middleware(scope, receive, capture_send)

        # Find response.start message
        response_start = next(
            (msg for msg in send_messages if msg.get("type") == "http.response.start"),
            None
        )

        if response_start:
            headers = dict(response_start.get("headers", []))
            assert b"X-Correlation-ID" in headers

    @pytest.mark.asyncio
    async def test_fastapi_middleware_skips_non_http(self):
        """Test middleware skips non-HTTP requests"""
        mock_app = AsyncMock()
        middleware = FastAPICorrelationMiddleware(mock_app)

        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await middleware(scope, receive, send)

        # Should pass through to app without modification
        mock_app.assert_called_once_with(scope, receive, send)


# ============================================================================
# AioHTTP Middleware Tests
# ============================================================================

class TestAioHTTPCorrelationMiddleware:
    """Test aiohttp correlation middleware"""

    @pytest.mark.asyncio
    async def test_aiohttp_middleware_generates_correlation_id(self):
        """Test aiohttp middleware generates correlation ID"""
        middleware = AioHTTPCorrelationMiddleware()

        # Mock request and handler
        mock_request = Mock()
        mock_request.headers = {}

        mock_response = Mock()
        mock_response.headers = {}

        async def mock_handler(request):
            return mock_response

        response = await middleware(mock_request, mock_handler)

        # Verify correlation ID was added to response
        assert 'X-Correlation-ID' in response.headers

    @pytest.mark.asyncio
    async def test_aiohttp_middleware_uses_existing_id(self):
        """Test aiohttp middleware uses existing correlation ID"""
        middleware = AioHTTPCorrelationMiddleware()

        existing_id = "existing_aiohttp_123"
        mock_request = Mock()
        mock_request.headers = {'X-Correlation-ID': existing_id}

        mock_response = Mock()
        mock_response.headers = {}

        async def mock_handler(request):
            return mock_response

        response = await middleware(mock_request, mock_handler)

        assert response.headers['X-Correlation-ID'] == existing_id

    @pytest.mark.asyncio
    async def test_aiohttp_middleware_handles_non_request(self):
        """Test middleware handles non-request objects"""
        middleware = AioHTTPCorrelationMiddleware()

        # Object without headers attribute
        non_request = "not a request"

        async def mock_handler(obj):
            return "handled"

        result = await middleware(non_request, mock_handler)

        assert result == "handled"


# ============================================================================
# Middleware Factory Tests
# ============================================================================

class TestCorrelationMiddlewareFactory:
    """Test correlation middleware factory"""

    @pytest.mark.asyncio
    async def test_create_correlation_middleware(self):
        """Test middleware factory creates proper middleware"""
        middleware_func = create_correlation_middleware()

        # Test that it's a valid aiohttp middleware
        assert callable(middleware_func)

        # Mock request and handler
        mock_request = Mock()
        mock_request.headers = {}

        mock_response = Mock()
        mock_response.headers = {}

        async def mock_handler(request):
            return mock_response

        response = await middleware_func(mock_request, mock_handler)

        assert 'X-Correlation-ID' in response.headers

    @pytest.mark.asyncio
    async def test_create_correlation_middleware_custom_header(self):
        """Test middleware factory with custom header name"""
        middleware_func = create_correlation_middleware(header_name='X-Request-ID')

        mock_request = Mock()
        mock_request.headers = {}

        mock_response = Mock()
        mock_response.headers = {}

        async def mock_handler(request):
            return mock_response

        response = await middleware_func(mock_request, mock_handler)

        assert 'X-Request-ID' in response.headers


# ============================================================================
# Context Helper Tests
# ============================================================================

class TestCorrelationContextHelpers:
    """Test correlation context helper functions"""

    def test_create_correlation_context(self):
        """Test creating correlation context"""
        context = create_correlation_context()

        assert 'correlation_id' in context
        assert 'start_time' in context
        assert context['correlation_id'].startswith('req_')

    def test_create_correlation_context_with_id(self):
        """Test creating context with provided ID"""
        test_id = "provided_id_123"
        context = create_correlation_context(test_id)

        assert context['correlation_id'] == test_id

    def test_update_correlation_context(self):
        """Test updating correlation context"""
        context = create_correlation_context("test_id")

        updated = update_correlation_context(
            context,
            user_id=123,
            request_path="/api/test"
        )

        assert updated['user_id'] == 123
        assert updated['request_path'] == "/api/test"
        assert updated['correlation_id'] == "test_id"

    def test_get_correlation_context(self):
        """Test getting current correlation context"""
        set_correlation_id("context_test_123")

        context = get_correlation_context()

        assert context['correlation_id'] == "context_test_123"
        assert 'timestamp' in context

        # Cleanup
        correlation_id.set(None)


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestCorrelationMiddlewareIntegration:
    """Integration tests for correlation middleware"""

    @pytest.mark.asyncio
    async def test_complete_request_flow_with_correlation(self):
        """Test complete request flow maintains correlation ID"""
        test_id = "integration_flow_123"

        # Simulate incoming request with correlation ID
        with correlation_context(test_id):
            # Verify ID is set
            assert get_correlation_id() == test_id

            # Simulate propagating to downstream service
            headers = {}
            headers_with_corr = propagate_correlation_id(headers)

            assert headers_with_corr['X-Correlation-ID'] == test_id

            # Extract from headers (simulating downstream service)
            extracted_id = extract_correlation_id(headers_with_corr)
            assert extracted_id == test_id

        # Context should be cleared
        assert get_correlation_id() is None
