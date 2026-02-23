"""
Performance tests for Chat API Endpoints
Epic AI-20 Story AI20.11: Comprehensive Testing

Tests performance requirements:
- Chat response time <3 seconds
- Concurrent user handling (10+ simultaneous requests)
- Load testing (sustained load over time)
"""

import pytest
import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List

from httpx import AsyncClient
from fastapi import FastAPI

from src.config import Settings
from src.services.conversation_service import ConversationService
from src.services.context_builder import ContextBuilder
from src.services.openai_client import OpenAIClient
from src.services.prompt_assembly_service import PromptAssemblyService
from src.services.tool_service import ToolService
from src.main import app
from src.api.dependencies import set_services


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        database_url="sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder with fast responses"""
    builder = MagicMock(spec=ContextBuilder)
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with Tier 1 context"
    )
    builder.initialize = AsyncMock()
    builder.close = AsyncMock()
    builder._initialized = True
    return builder


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client with fast responses"""
    client = MagicMock(spec=OpenAIClient)
    client.total_tokens_used = 0
    client.total_requests = 0
    client.total_errors = 0
    return client


@pytest.fixture
def mock_tool_service():
    """Create mock tool service"""
    service = MagicMock(spec=ToolService)
    service.execute_tool_call = AsyncMock()
    return service


@pytest.fixture
async def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.fixture
async def prompt_assembly_service(settings, mock_context_builder, conversation_service):
    """Create prompt assembly service instance"""
    return PromptAssemblyService(settings, mock_context_builder, conversation_service)


@pytest.fixture
async def test_client(
    settings,
    mock_context_builder,
    conversation_service,
    prompt_assembly_service,
    mock_openai_client,
    mock_tool_service,
):
    """Create test client with mocked services"""
    # Set services for dependency injection
    set_services(
        settings=settings,
        conversation_service=conversation_service,
        prompt_assembly_service=prompt_assembly_service,
        openai_client=mock_openai_client,
        tool_service=mock_tool_service,
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


def create_fast_mock_completion(content: str):
    """Create mock OpenAI completion response (fast)"""
    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types.chat.chat_completion import Choice
    from openai.types.completion_usage import CompletionUsage

    message = ChatCompletionMessage(
        role="assistant",
        content=content,
        tool_calls=None,
    )

    return ChatCompletion(
        id="chatcmpl-perf",
        choices=[Choice(finish_reason="stop", index=0, message=message)],
        created=1234567890,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=len(content.split()),
            prompt_tokens=100,
            total_tokens=100 + len(content.split()),
        ),
    )


@pytest.mark.asyncio
async def test_chat_response_time_performance(test_client, mock_openai_client):
    """Test that chat endpoint responds within 3 seconds"""
    # Mock fast OpenAI response (simulate 100ms latency)
    async def fast_completion(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate network latency
        return create_fast_mock_completion("Test response")

    mock_openai_client.chat_completion = AsyncMock(side_effect=fast_completion)

    # Measure response time
    start_time = time.perf_counter()
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Test message",
            "conversation_id": None,
            "refresh_context": False,
        },
    )
    elapsed_time = time.perf_counter() - start_time

    assert response.status_code == 200
    assert elapsed_time < 3.0, f"Chat response took {elapsed_time:.2f}s, expected <3.0s"


@pytest.mark.asyncio
async def test_chat_concurrent_users(test_client, mock_openai_client):
    """Test handling 10+ concurrent users"""
    num_concurrent = 10

    # Mock fast OpenAI responses
    async def fast_completion(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate network latency
        return create_fast_mock_completion(f"Response for request")

    mock_openai_client.chat_completion = AsyncMock(side_effect=fast_completion)

    # Send concurrent requests
    async def send_request(index: int):
        """Send a single chat request"""
        response = await test_client.post(
            "/api/v1/chat",
            json={
                "message": f"Concurrent request {index}",
                "conversation_id": None,
                "refresh_context": False,
            },
        )
        return response.status_code, response.json()

    # Execute concurrent requests
    start_time = time.perf_counter()
    tasks = [send_request(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)
    elapsed_time = time.perf_counter() - start_time

    # Verify all requests succeeded
    assert len(results) == num_concurrent
    for status_code, data in results:
        assert status_code == 200
        assert "message" in data

    # Verify performance (all requests should complete quickly)
    assert elapsed_time < 5.0, f"10 concurrent requests took {elapsed_time:.2f}s, expected <5.0s"

    # Verify OpenAI was called for each request
    assert mock_openai_client.chat_completion.call_count >= num_concurrent


@pytest.mark.asyncio
async def test_chat_sustained_load(test_client, mock_openai_client):
    """Test sustained load over time (50 requests over 30 seconds)"""
    num_requests = 50
    duration_seconds = 30
    requests_per_second = num_requests / duration_seconds

    # Mock fast OpenAI responses
    async def fast_completion(*args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate network latency
        return create_fast_mock_completion("Sustained load response")

    mock_openai_client.chat_completion = AsyncMock(side_effect=fast_completion)

    # Track request results
    results: List[tuple] = []

    async def send_request_with_delay(index: int):
        """Send a request with delay to simulate sustained load"""
        await asyncio.sleep(index / requests_per_second)
        response = await test_client.post(
            "/api/v1/chat",
            json={
                "message": f"Sustained load request {index}",
                "conversation_id": None,
                "refresh_context": False,
            },
        )
        results.append((response.status_code, time.perf_counter()))

    # Execute sustained load
    start_time = time.perf_counter()
    tasks = [send_request_with_delay(i) for i in range(num_requests)]
    await asyncio.gather(*tasks)
    total_elapsed = time.perf_counter() - start_time

    # Verify all requests succeeded
    assert len(results) == num_requests
    success_count = sum(1 for status_code, _ in results if status_code == 200)
    success_rate = success_count / num_requests

    assert success_rate >= 0.95, f"Success rate {success_rate:.2%}, expected >=95%"

    # Verify we can handle sustained load
    assert total_elapsed < duration_seconds * 2, f"Sustained load took too long: {total_elapsed:.2f}s"


@pytest.mark.asyncio
async def test_chat_error_recovery_performance(test_client, mock_openai_client):
    """Test that error scenarios don't significantly impact performance"""
    # Mock OpenAI error (then success)
    from src.services.openai_client import OpenAIError

    call_count = 0

    async def completion_with_error(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise OpenAIError("Temporary error")
        await asyncio.sleep(0.1)
        return create_fast_mock_completion("Recovery response")

    mock_openai_client.chat_completion = AsyncMock(side_effect=completion_with_error)

    # Measure error recovery time
    start_time = time.perf_counter()
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Test with error recovery",
            "conversation_id": None,
            "refresh_context": False,
        },
    )
    elapsed_time = time.perf_counter() - start_time

    # Error recovery should still be reasonable
    # (might be slower due to retry logic, but should complete)
    assert elapsed_time < 10.0, f"Error recovery took {elapsed_time:.2f}s, expected <10.0s"


@pytest.mark.asyncio
async def test_chat_memory_usage_stability(test_client, mock_openai_client):
    """Test that memory usage remains stable under load"""
    import psutil
    import os

    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Mock fast OpenAI responses
    async def fast_completion(*args, **kwargs):
        await asyncio.sleep(0.05)
        return create_fast_mock_completion("Memory test response")

    mock_openai_client.chat_completion = AsyncMock(side_effect=fast_completion)

    # Send multiple requests
    num_requests = 20
    for i in range(num_requests):
        response = await test_client.post(
            "/api/v1/chat",
            json={
                "message": f"Memory test request {i}",
                "conversation_id": None,
                "refresh_context": False,
            },
        )
        assert response.status_code == 200

    # Check final memory usage
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Memory increase should be reasonable (<100MB for 20 requests)
    assert memory_increase < 100, f"Memory increased by {memory_increase:.2f}MB, expected <100MB"


@pytest.mark.asyncio
async def test_chat_context_refresh_performance(test_client, mock_openai_client, mock_context_builder):
    """Test that context refresh doesn't significantly slow down responses"""
    # Mock fast context refresh
    mock_context_builder.build_complete_system_prompt = AsyncMock(
        return_value="Refreshed context"
    )

    # Mock fast OpenAI response
    async def fast_completion(*args, **kwargs):
        await asyncio.sleep(0.1)
        return create_fast_mock_completion("Response with refreshed context")

    mock_openai_client.chat_completion = AsyncMock(side_effect=fast_completion)

    # Measure response time with context refresh
    start_time = time.perf_counter()
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Test with context refresh",
            "conversation_id": None,
            "refresh_context": True,
        },
    )
    elapsed_time = time.perf_counter() - start_time

    assert response.status_code == 200
    # Context refresh adds some overhead, but should still be reasonable
    assert elapsed_time < 5.0, f"Context refresh took {elapsed_time:.2f}s, expected <5.0s"

