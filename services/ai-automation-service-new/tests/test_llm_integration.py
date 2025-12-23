"""
LLM Integration Tests

Epic 39, Story 39.12: Query & Automation Service Testing
Tests for OpenAI client integration and error handling.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from openai import APIError, RateLimitError

from src.clients.openai_client import OpenAIClient


@pytest.mark.unit
class TestOpenAIClientInitialization:
    """Unit tests for OpenAI client initialization."""
    
    @pytest.mark.asyncio
    async def test_client_initialization_with_api_key(self):
        """Test client initialization with API key."""
        with patch('src.clients.openai_client.AsyncOpenAI') as mock_openai:
            client = OpenAIClient(api_key="test-key-123", model="gpt-4o-mini")
            
            assert client.api_key == "test-key-123"
            assert client.model == "gpt-4o-mini"
            assert client.client is not None
            mock_openai.assert_called_once_with(api_key="test-key-123")
    
    @pytest.mark.asyncio
    async def test_client_initialization_without_api_key(self):
        """Test client initialization without API key (warning)."""
        with patch('src.clients.openai_client.settings') as mock_settings:
            mock_settings.openai_api_key = None
            mock_settings.openai_model = "gpt-4o-mini"
            
            client = OpenAIClient()
            
            assert client.api_key is None
            assert client.client is None
    
    @pytest.mark.asyncio
    async def test_client_uses_default_model(self):
        """Test that client uses default model when not specified."""
        with patch('src.clients.openai_client.AsyncOpenAI') as mock_openai:
            with patch('src.clients.openai_client.settings') as mock_settings:
                mock_settings.openai_model = "gpt-4o"
                mock_settings.openai_api_key = "test-key"
                
                client = OpenAIClient()
                
                assert client.model == "gpt-4o"


@pytest.mark.unit
class TestYAMLGeneration:
    """Unit tests for YAML generation via OpenAI."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """id: 'test-123'
alias: Test Automation
trigger:
  - platform: time
    at: '07:00:00'
action:
  - service: light.turn_on
    target:
      entity_id: light.office_lamp
"""
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 150
        return mock_response
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client with mocked client."""
        client = OpenAIClient(api_key="test-key")
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_generate_yaml_success(
        self,
        openai_client: OpenAIClient,
        mock_openai_response
    ):
        """Test successful YAML generation."""
        # Setup
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        
        # Execute
        prompt = "Turn on lights at 7 AM"
        result = await openai_client.generate_yaml(prompt)
        
        # Assert
        assert "id: 'test-123'" in result
        assert "alias: Test Automation" in result
        assert openai_client.total_tokens_used == 150
        openai_client.client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_yaml_removes_markdown_code_blocks(
        self,
        openai_client: OpenAIClient
    ):
        """Test that YAML generation removes markdown code blocks."""
        # Setup: Response with markdown code blocks
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """```yaml
id: 'test-123'
alias: Test Automation
```
"""
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        
        # Execute
        result = await openai_client.generate_yaml("Test prompt")
        
        # Assert: Markdown code blocks removed
        assert not result.startswith("```")
        assert "id: 'test-123'" in result
        assert "alias: Test Automation" in result
    
    @pytest.mark.asyncio
    async def test_generate_yaml_without_api_key_raises_error(
        self
    ):
        """Test that YAML generation raises error without API key."""
        # Setup: Client without API key
        client = OpenAIClient(api_key=None)
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            await client.generate_yaml("Test prompt")
        
        assert "OpenAI API key not configured" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_yaml_tracks_token_usage(
        self,
        openai_client: OpenAIClient,
        mock_openai_response
    ):
        """Test that token usage is tracked correctly."""
        # Setup
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_openai_response
        )
        
        # Execute multiple calls
        await openai_client.generate_yaml("Prompt 1")
        await openai_client.generate_yaml("Prompt 2")
        
        # Assert: Token usage accumulated
        assert openai_client.total_tokens_used == 300  # 150 * 2


@pytest.mark.unit
class TestErrorHandling:
    """Unit tests for error handling in OpenAI client."""
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client with mocked client."""
        client = OpenAIClient(api_key="test-key")
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_api_error_raises_exception(
        self,
        openai_client: OpenAIClient
    ):
        """Test that APIError is raised and not caught."""
        # Setup: Mock API error
        openai_client.client.chat.completions.create = AsyncMock(
            side_effect=APIError(
                message="API error",
                request=None,
                body=None
            )
        )
        
        # Execute & Assert
        with pytest.raises(APIError):
            await openai_client.generate_yaml("Test prompt")
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_retries(
        self,
        openai_client: OpenAIClient
    ):
        """Test that RateLimitError triggers retry logic."""
        # Setup: First call fails with rate limit, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "id: 'test'"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 50
        
        # Create a proper RateLimitError
        rate_limit_error = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None
        )
        
        openai_client.client.chat.completions.create = AsyncMock(
            side_effect=[
                rate_limit_error,
                mock_response  # Second call succeeds
            ]
        )
        
        # Execute: Should retry and succeed
        result = await openai_client.generate_yaml("Test prompt")
        
        # Assert: Retried and succeeded
        assert "id: 'test'" in result
        assert openai_client.client.chat.completions.create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_fails_after_max_retries(
        self,
        openai_client: OpenAIClient
    ):
        """Test that RateLimitError fails after max retries."""
        # Setup: All retries fail
        rate_limit_error = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=None
        )
        openai_client.client.chat.completions.create = AsyncMock(
            side_effect=rate_limit_error
        )
        
        # Execute & Assert: Should fail after 3 attempts
        with pytest.raises(RateLimitError):
            await openai_client.generate_yaml("Test prompt")
        
        # Assert: Retried 3 times (max attempts)
        assert openai_client.client.chat.completions.create.call_count == 3
    
    @pytest.mark.asyncio
    async def test_unexpected_error_raises_exception(
        self,
        openai_client: OpenAIClient
    ):
        """Test that unexpected errors are raised."""
        # Setup: Unexpected error
        openai_client.client.chat.completions.create = AsyncMock(
            side_effect=ValueError("Unexpected error")
        )
        
        # Execute & Assert
        with pytest.raises(ValueError):
            await openai_client.generate_yaml("Test prompt")


@pytest.mark.unit
class TestSuggestionDescriptionGeneration:
    """Unit tests for suggestion description generation."""
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client with mocked client."""
        client = OpenAIClient(api_key="test-key")
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_generate_suggestion_description_success(
        self,
        openai_client: OpenAIClient
    ):
        """Test successful suggestion description generation."""
        # Setup
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Turn on office lights at 7 AM every weekday"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 75
        
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        
        # Execute
        pattern_data = {
            "trigger": "time",
            "time": "07:00:00",
            "action": "light.turn_on",
            "entity": "light.office_lamp"
        }
        result = await openai_client.generate_suggestion_description(pattern_data)
        
        # Assert
        assert "Turn on office lights" in result
        assert openai_client.total_tokens_used == 75
        openai_client.client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_suggestion_description_without_api_key(
        self
    ):
        """Test that description generation raises error without API key."""
        # Setup: Client without API key
        client = OpenAIClient(api_key=None)
        
        # Execute & Assert
        with pytest.raises(ValueError) as exc_info:
            await client.generate_suggestion_description({})
        
        assert "OpenAI API key not configured" in str(exc_info.value)


@pytest.mark.unit
class TestUsageStats:
    """Unit tests for usage statistics tracking."""
    
    @pytest.fixture
    def openai_client(self):
        """Create OpenAI client with mocked client."""
        client = OpenAIClient(api_key="test-key")
        client.client = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_get_usage_stats(
        self,
        openai_client: OpenAIClient
    ):
        """Test getting usage statistics."""
        # Setup: Make some API calls
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        
        await openai_client.generate_yaml("Test")
        
        # Execute
        stats = openai_client.get_usage_stats()
        
        # Assert
        assert stats["total_tokens"] == 100
        assert stats["model"] == "gpt-4o-mini"
        assert stats["total_cost_usd"] == 0.0
    
    @pytest.mark.asyncio
    async def test_reset_usage_stats(
        self,
        openai_client: OpenAIClient
    ):
        """Test resetting usage statistics."""
        # Setup: Make some API calls
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "test"
        mock_response.usage = MagicMock()
        mock_response.usage.total_tokens = 100
        
        openai_client.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )
        
        await openai_client.generate_yaml("Test")
        assert openai_client.total_tokens_used == 100
        
        # Execute
        openai_client.reset_usage_stats()
        
        # Assert
        assert openai_client.total_tokens_used == 0
        assert openai_client.total_cost_usd == 0.0

