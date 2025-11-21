"""
Unit tests for OpenAI Client
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.llm.openai_client import AutomationSuggestion, OpenAIClient


@pytest.fixture
def mock_openai_response():
    """Create a mock OpenAI API response"""
    response = MagicMock()
    response.choices = [
        MagicMock(
            message=MagicMock(
                content="""```yaml
alias: "AI Suggested: Morning Bedroom Light"
description: "Turn on bedroom light at 7 AM"
trigger:
  - platform: time
    at: "07:00:00"
action:
  - service: light.turn_on
    target:
      entity_id: light.bedroom
```

RATIONALE: This automation activates the bedroom light at 7 AM based on consistent usage patterns observed 28 times with 93% confidence.
CATEGORY: convenience
PRIORITY: medium
""",
            ),
        ),
    ]
    response.usage = MagicMock(
        prompt_tokens=250,
        completion_tokens=200,
        total_tokens=450,
    )
    return response


@pytest.fixture
def openai_client():
    """Create an OpenAI client instance"""
    return OpenAIClient(api_key="test-api-key", model="gpt-4o-mini")


class TestOpenAIClient:
    """Test OpenAI Client"""

    def test_initialization(self):
        """Test client initialization"""
        client = OpenAIClient(api_key="test-key", model="gpt-4o-mini")
        assert client.model == "gpt-4o-mini"
        assert client.total_tokens_used == 0
        assert client.total_input_tokens == 0
        assert client.total_output_tokens == 0

    @pytest.mark.asyncio
    async def test_generate_time_of_day_suggestion(self, openai_client, mock_openai_response):
        """Test successful suggestion generation for time-of-day pattern"""
        pattern = {
            "device_id": "light.bedroom",
            "pattern_type": "time_of_day",
            "hour": 7,
            "minute": 0,
            "occurrences": 28,
            "confidence": 0.93,
            "metadata": {},
        }

        # Use AsyncMock for async method
        with patch.object(openai_client.client.chat.completions, "create", new=AsyncMock(return_value=mock_openai_response)):
            suggestion = await openai_client.generate_automation_suggestion(pattern)

            assert isinstance(suggestion, AutomationSuggestion)
            assert "Morning" in suggestion.alias or "Bedroom" in suggestion.alias
            assert "light.bedroom" in suggestion.automation_yaml
            assert suggestion.category in ["energy", "comfort", "security", "convenience"]
            assert suggestion.priority in ["high", "medium", "low"]
            assert suggestion.confidence == 0.93

            call_kwargs = openai_client.client.chat.completions.create.call_args.kwargs
            messages = call_kwargs["messages"]
            roles = [message["role"] for message in messages]
            assert "developer" in roles
            developer_message = next(msg for msg in messages if msg["role"] == "developer")
            assert "Pattern Summary" in developer_message["content"]

    @pytest.mark.asyncio
    async def test_generate_co_occurrence_suggestion(self, openai_client):
        """Test suggestion generation for co-occurrence pattern"""
        pattern = {
            "device_id": "motion.hallway+light.hallway",
            "device1": "binary_sensor.motion_hallway",
            "device2": "light.hallway",
            "pattern_type": "co_occurrence",
            "occurrences": 42,
            "confidence": 0.95,
            "metadata": {
                "avg_time_delta_seconds": 25.0,
            },
        }

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""```yaml
alias: "AI Suggested: Hallway Motion Light"
description: "Turn on light when motion detected"
trigger:
  - platform: state
    entity_id: binary_sensor.motion_hallway
    to: 'on'
action:
  - delay: '00:00:25'
  - service: light.turn_on
    target:
      entity_id: light.hallway
```

RATIONALE: Motion sensor and hallway light are used together 42 times with 95% confidence.
CATEGORY: convenience
PRIORITY: medium
""",
                ),
            ),
        ]
        mock_response.usage = MagicMock(prompt_tokens=300, completion_tokens=250, total_tokens=550)

        with patch.object(openai_client.client.chat.completions, "create", new=AsyncMock(return_value=mock_response)):
            suggestion = await openai_client.generate_automation_suggestion(pattern)

            assert isinstance(suggestion, AutomationSuggestion)
            assert "motion" in suggestion.alias.lower() or "hallway" in suggestion.alias.lower()
            assert "binary_sensor.motion_hallway" in suggestion.automation_yaml
            assert "light.hallway" in suggestion.automation_yaml

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self, openai_client, mock_openai_response):
        """Test token usage tracking"""
        pattern = {
            "device_id": "light.test",
            "pattern_type": "time_of_day",
            "hour": 7,
            "occurrences": 10,
            "confidence": 0.8,
        }

        with patch.object(openai_client.client.chat.completions, "create", new=AsyncMock(return_value=mock_openai_response)):
            await openai_client.generate_automation_suggestion(pattern)

            assert openai_client.total_tokens_used == 450
            assert openai_client.total_input_tokens == 250
            assert openai_client.total_output_tokens == 200

    @pytest.mark.asyncio
    async def test_retry_on_api_error(self, openai_client, mock_openai_response):
        """Test retry logic on API failures"""
        pattern = {
            "device_id": "light.test",
            "pattern_type": "time_of_day",
            "hour": 7,
            "occurrences": 10,
            "confidence": 0.8,
        }

        # Create async mock with side effects
        async_mock = AsyncMock()
        async_mock.side_effect = [
            Exception("Rate limit error"),
            Exception("Timeout error"),
            mock_openai_response,
        ]

        with patch.object(openai_client.client.chat.completions, "create", new=async_mock):
            suggestion = await openai_client.generate_automation_suggestion(pattern)

            # Should have retried 3 times
            assert async_mock.call_count == 3
            assert isinstance(suggestion, AutomationSuggestion)

    @pytest.mark.asyncio
    async def test_get_usage_stats(self, openai_client, mock_openai_response):
        """Test usage statistics retrieval"""
        pattern = {
            "device_id": "light.test",
            "pattern_type": "time_of_day",
            "hour": 7,
            "occurrences": 10,
            "confidence": 0.8,
        }

        with patch.object(openai_client.client.chat.completions, "create", new=AsyncMock(return_value=mock_openai_response)):
            await openai_client.generate_automation_suggestion(pattern)

            stats = openai_client.get_usage_stats()

            assert stats["total_tokens"] == 450
            assert stats["input_tokens"] == 250
            assert stats["output_tokens"] == 200
            assert "estimated_cost_usd" in stats
            assert stats["model"] == "gpt-4o-mini"

    def test_reset_usage_stats(self, openai_client):
        """Test usage statistics reset"""
        openai_client.total_tokens_used = 1000
        openai_client.total_input_tokens = 600
        openai_client.total_output_tokens = 400

        openai_client.reset_usage_stats()

        assert openai_client.total_tokens_used == 0
        assert openai_client.total_input_tokens == 0
        assert openai_client.total_output_tokens == 0

    def test_infer_category_light(self, openai_client):
        """Test category inference for light devices"""
        pattern = {"device_id": "light.bedroom", "pattern_type": "time_of_day"}
        category = openai_client._infer_category(pattern)
        assert category == "convenience"

    def test_infer_category_climate(self, openai_client):
        """Test category inference for climate devices"""
        pattern = {"device_id": "climate.living_room", "pattern_type": "time_of_day"}
        category = openai_client._infer_category(pattern)
        assert category == "comfort"

    def test_infer_category_security(self, openai_client):
        """Test category inference for security devices"""
        pattern = {"device_id": "binary_sensor.motion_hallway", "pattern_type": "co_occurrence"}
        category = openai_client._infer_category(pattern)
        assert category == "security"

    def test_extract_alias(self, openai_client):
        """Test alias extraction from LLM response"""
        text = 'alias: "AI Suggested: Morning Light"\nOther content'
        alias = openai_client._extract_alias(text)
        assert alias == "AI Suggested: Morning Light"

    def test_extract_yaml(self, openai_client):
        """Test YAML extraction from LLM response"""
        text = """```yaml
alias: "Test Automation"
trigger:
  - platform: time
action:
  - service: light.turn_on
```"""
        yaml_content = openai_client._extract_yaml(text)
        assert 'alias: "Test Automation"' in yaml_content
        assert "trigger:" in yaml_content

    def test_extract_rationale(self, openai_client):
        """Test rationale extraction from LLM response"""
        text = "RATIONALE: This automation makes sense because it follows a consistent pattern.\nCATEGORY: convenience"
        rationale = openai_client._extract_rationale(text)
        assert "consistent pattern" in rationale

    def test_extract_category(self, openai_client):
        """Test category extraction from LLM response"""
        text = "CATEGORY: energy\nPRIORITY: high"
        category = openai_client._extract_category(text)
        assert category == "energy"

    def test_extract_priority(self, openai_client):
        """Test priority extraction from LLM response"""
        text = "CATEGORY: comfort\nPRIORITY: high"
        priority = openai_client._extract_priority(text)
        assert priority == "high"

    def test_generate_fallback_yaml_time_of_day(self, openai_client):
        """Test fallback YAML generation for time-of-day pattern"""
        pattern = {
            "device_id": "light.bedroom",
            "pattern_type": "time_of_day",
            "hour": 7,
            "minute": 30,
            "confidence": 0.8,
        }

        yaml_content = openai_client._generate_fallback_yaml(pattern)

        assert "alias:" in yaml_content
        assert "light.bedroom" in yaml_content
        assert "07:30:00" in yaml_content
        assert "trigger:" in yaml_content
        assert "action:" in yaml_content

    def test_generate_fallback_yaml_co_occurrence(self, openai_client):
        """Test fallback YAML generation for co-occurrence pattern"""
        pattern = {
            "pattern_type": "co_occurrence",
            "device1": "binary_sensor.motion",
            "device2": "light.hallway",
            "confidence": 0.9,
        }

        yaml_content = openai_client._generate_fallback_yaml(pattern)

        assert "alias:" in yaml_content
        assert "binary_sensor.motion" in yaml_content
        assert "light.hallway" in yaml_content
        assert "trigger:" in yaml_content
        assert "action:" in yaml_content


class TestCostTracker:
    """Test Cost Tracker"""

    def test_calculate_cost_basic(self):
        """Test basic cost calculation"""
        from src.llm.cost_tracker import CostTracker

        # 1000 input tokens, 500 output tokens
        cost = CostTracker.calculate_cost(1000, 500)

        # Expected: (1000/1M * 0.15) + (500/1M * 0.60)
        #         = 0.00015 + 0.0003 = 0.00045
        assert cost == pytest.approx(0.00045, abs=0.000001)

    def test_calculate_cost_large_usage(self):
        """Test cost calculation for large usage"""
        from src.llm.cost_tracker import CostTracker

        # 1M input tokens, 500k output tokens
        cost = CostTracker.calculate_cost(1_000_000, 500_000)

        # Expected: (1M/1M * 0.15) + (500k/1M * 0.60)
        #         = 0.15 + 0.30 = 0.45
        assert cost == pytest.approx(0.45, abs=0.01)

    def test_estimate_monthly_cost(self):
        """Test monthly cost estimation"""
        from src.llm.cost_tracker import CostTracker

        # 10 suggestions per day, 800 tokens average
        estimate = CostTracker.estimate_monthly_cost(
            suggestions_per_day=10,
            avg_tokens_per_suggestion=800,
        )

        assert estimate["suggestions_per_day"] == 10
        assert estimate["monthly_cost_usd"] > 0
        assert estimate["monthly_cost_usd"] < 5.0  # Should be well under $5/month
        assert "assumptions" in estimate

    def test_check_budget_alert_ok(self):
        """Test budget alert when usage is low"""
        from src.llm.cost_tracker import CostTracker

        alert = CostTracker.check_budget_alert(total_cost=2.0, budget=10.0)

        assert alert["alert_level"] == "ok"
        assert alert["usage_percent"] == 20.0
        assert alert["remaining_usd"] == 8.0
        assert alert["should_alert"] is False

    def test_check_budget_alert_warning(self):
        """Test budget alert when usage is at warning level"""
        from src.llm.cost_tracker import CostTracker

        alert = CostTracker.check_budget_alert(total_cost=8.0, budget=10.0)

        assert alert["alert_level"] == "warning"
        assert alert["usage_percent"] == 80.0
        assert alert["should_alert"] is True

    def test_check_budget_alert_critical(self):
        """Test budget alert when usage is critical"""
        from src.llm.cost_tracker import CostTracker

        alert = CostTracker.check_budget_alert(total_cost=9.5, budget=10.0)

        assert alert["alert_level"] == "critical"
        assert alert["usage_percent"] == 95.0
        assert alert["should_alert"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_openai_api():
    """
    Integration test with real OpenAI API.
    Requires: OPENAI_API_KEY environment variable
    """
    import os

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not set")

    client = OpenAIClient(api_key=api_key, model="gpt-4o-mini")

    pattern = {
        "device_id": "light.test",
        "pattern_type": "time_of_day",
        "hour": 7,
        "minute": 0,
        "occurrences": 20,
        "confidence": 0.9,
        "metadata": {},
    }

    try:
        suggestion = await client.generate_automation_suggestion(pattern)

        # Verify structure
        assert isinstance(suggestion, AutomationSuggestion)
        assert len(suggestion.alias) > 0
        assert len(suggestion.automation_yaml) > 0
        assert "alias:" in suggestion.automation_yaml
        assert "trigger:" in suggestion.automation_yaml
        assert len(suggestion.rationale) > 10

        # Verify token tracking
        stats = client.get_usage_stats()
        assert stats["total_tokens"] > 0
        assert stats["estimated_cost_usd"] > 0

        print("\n✅ Real OpenAI test successful:")
        print(f"   Tokens: {stats['total_tokens']}")
        print(f"   Cost: ${stats['estimated_cost_usd']:.4f}")
        print(f"   Alias: {suggestion.alias}")

    except Exception as e:
        pytest.fail(f"Real OpenAI API test failed: {e}")

