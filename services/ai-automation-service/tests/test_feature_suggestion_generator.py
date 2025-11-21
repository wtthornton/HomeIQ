"""
Unit Tests for FeatureSuggestionGenerator (Epic AI-2, Story AI2.4)

Tests LLM-powered feature suggestion generation.
"""

from unittest.mock import AsyncMock, Mock

import pytest
from src.device_intelligence.feature_suggestion_generator import FeatureSuggestionGenerator


class TestFeatureSuggestionGenerator:
    """Test FeatureSuggestionGenerator LLM-based suggestion creation"""

    def setup_method(self):
        """Initialize mocks for each test"""
        self.mock_llm_client = Mock()
        self.mock_llm_client.client = AsyncMock()
        self.mock_llm_client.model = "gpt-4o-mini"
        self.mock_llm_client.total_input_tokens = 0
        self.mock_llm_client.total_output_tokens = 0
        self.mock_llm_client.total_tokens_used = 0

        self.mock_analyzer = AsyncMock()
        self.mock_db_session = AsyncMock()

        self.generator = FeatureSuggestionGenerator(
            llm_client=self.mock_llm_client,
            feature_analyzer=self.mock_analyzer,
            db_session=self.mock_db_session,
        )

    # =========================================================================
    # Suggestion Generation Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_suggestions_success(self):
        """Test generating suggestions from opportunities"""
        # Mock analyzer to return opportunities
        self.mock_analyzer.analyze_all_devices = AsyncMock(return_value={
            "opportunities": [
                {
                    "device_id": "light.kitchen",
                    "device_name": "Kitchen Switch",
                    "manufacturer": "Inovelli",
                    "model": "VZM31-SN",
                    "feature_name": "led_notifications",
                    "feature_type": "composite",
                    "complexity": "medium",
                    "impact": "high",
                },
            ],
        })

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Your Inovelli switch supports LED notifications!"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        self.mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Generate suggestions
        suggestions = await self.generator.generate_suggestions(max_suggestions=10)

        # Should have generated 1 suggestion
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "feature_discovery"
        assert suggestions[0]["feature_name"] == "led_notifications"
        assert suggestions[0]["device_id"] == "light.kitchen"
        assert "description" in suggestions[0]

    @pytest.mark.asyncio
    async def test_generate_suggestions_no_opportunities(self):
        """Test when no opportunities found"""
        self.mock_analyzer.analyze_all_devices = AsyncMock(return_value={
            "opportunities": [],  # No opportunities
        })

        suggestions = await self.generator.generate_suggestions()

        assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_generate_suggestions_limits_to_max(self):
        """Test max_suggestions parameter limits output"""
        # Mock 20 opportunities
        opportunities = [
            {
                "device_id": f"light.device_{i}",
                "device_name": f"Device {i}",
                "manufacturer": "Test",
                "model": "TEST",
                "feature_name": f"feature_{i}",
                "feature_type": "test",
                "complexity": "easy",
                "impact": "medium",
            }
            for i in range(20)
        ]

        self.mock_analyzer.analyze_all_devices = AsyncMock(return_value={
            "opportunities": opportunities,
        })

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test suggestion"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        self.mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Generate with max=5
        suggestions = await self.generator.generate_suggestions(max_suggestions=5)

        # Should only generate 5 (not 20)
        assert len(suggestions) == 5

    # =========================================================================
    # Confidence Calculation Tests
    # =========================================================================

    def test_calculate_confidence_high_impact_easy(self):
        """Test high confidence for high impact + easy complexity"""
        opp = {"impact": "high", "complexity": "easy"}
        confidence = self.generator._calculate_confidence(opp)

        assert confidence == 0.9  # High impact, no penalty

    def test_calculate_confidence_high_impact_advanced(self):
        """Test reduced confidence for high impact + advanced complexity"""
        opp = {"impact": "high", "complexity": "advanced"}
        confidence = self.generator._calculate_confidence(opp)

        assert confidence == 0.7  # 0.9 - 0.2 penalty

    def test_calculate_confidence_low_impact(self):
        """Test low confidence for low impact"""
        opp = {"impact": "low", "complexity": "easy"}
        confidence = self.generator._calculate_confidence(opp)

        assert confidence == 0.5

    # =========================================================================
    # Category Determination Tests
    # =========================================================================

    def test_determine_category_energy(self):
        """Test energy category for power-related features"""
        assert self.generator._determine_category({"feature_name": "power_monitoring"}) == "energy"
        assert self.generator._determine_category({"feature_name": "energy_consumption"}) == "energy"

    def test_determine_category_security(self):
        """Test security category for alert/notification features"""
        assert self.generator._determine_category({"feature_name": "led_notifications"}) == "security"
        assert self.generator._determine_category({"feature_name": "alert_system"}) == "security"

    def test_determine_category_comfort(self):
        """Test comfort category for climate features"""
        assert self.generator._determine_category({"feature_name": "temperature_control"}) == "comfort"
        assert self.generator._determine_category({"feature_name": "climate_preset"}) == "comfort"

    def test_determine_category_default_convenience(self):
        """Test default category is convenience"""
        assert self.generator._determine_category({"feature_name": "unknown_feature"}) == "convenience"

    # =========================================================================
    # Priority Mapping Tests
    # =========================================================================

    def test_map_impact_to_priority(self):
        """Test impact to priority mapping"""
        assert self.generator._map_impact_to_priority("high") == "high"
        assert self.generator._map_impact_to_priority("medium") == "medium"
        assert self.generator._map_impact_to_priority("low") == "low"
        assert self.generator._map_impact_to_priority("unknown") == "medium"  # Default

    # =========================================================================
    # Prompt Building Tests
    # =========================================================================

    def test_build_feature_prompt_includes_device_info(self):
        """Test prompt includes all required device information"""
        opp = {
            "device_name": "Kitchen Switch",
            "manufacturer": "Inovelli",
            "model": "VZM31-SN",
            "feature_name": "led_notifications",
            "feature_type": "composite",
            "complexity": "medium",
            "impact": "high",
        }

        prompt = self.generator._build_feature_prompt(opp)

        assert "Kitchen Switch" in prompt
        assert "Inovelli" in prompt
        assert "VZM31-SN" in prompt
        assert "Led Notifications" in prompt or "LED Notifications" in prompt
        assert "medium" in prompt.lower()
        assert "high" in prompt.lower()

    # =========================================================================
    # Performance Tests (NFR15: 10 suggestions in <60s)
    # =========================================================================

    @pytest.mark.asyncio
    async def test_generate_10_suggestions_performance(self):
        """Test generating 10 suggestions completes quickly"""
        import time

        # Mock 10 opportunities
        opportunities = [
            {
                "device_id": f"light.device_{i}",
                "device_name": f"Device {i}",
                "manufacturer": "Test",
                "model": "TEST",
                "feature_name": f"feature_{i}",
                "feature_type": "test",
                "complexity": "easy",
                "impact": "medium",
            }
            for i in range(10)
        ]

        self.mock_analyzer.analyze_all_devices = AsyncMock(return_value={
            "opportunities": opportunities,
        })

        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test suggestion"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        self.mock_llm_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        start = time.time()
        suggestions = await self.generator.generate_suggestions(max_suggestions=10)
        duration = time.time() - start

        # Should complete in <60 seconds (NFR15)
        assert duration < 60
        assert len(suggestions) == 10

    # =========================================================================
    # Error Handling Tests
    # =========================================================================

    @pytest.mark.asyncio
    async def test_continues_after_llm_error(self):
        """Test generator continues after LLM error on one suggestion"""
        opportunities = [
            {"device_id": "d1", "device_name": "D1", "manufacturer": "T", "model": "M", "feature_name": "f1", "feature_type": "t", "complexity": "easy", "impact": "high"},
            {"device_id": "d2", "device_name": "D2", "manufacturer": "T", "model": "M", "feature_name": "f2", "feature_type": "t", "complexity": "easy", "impact": "high"},
        ]

        self.mock_analyzer.analyze_all_devices = AsyncMock(return_value={
            "opportunities": opportunities,
        })

        # First call fails, second succeeds
        mock_response_success = Mock()
        mock_response_success.choices = [Mock()]
        mock_response_success.choices[0].message.content = "Success"
        mock_response_success.usage = Mock()
        mock_response_success.usage.prompt_tokens = 100
        mock_response_success.usage.completion_tokens = 50
        mock_response_success.usage.total_tokens = 150

        self.mock_llm_client.client.chat.completions.create = AsyncMock(
            side_effect=[
                Exception("API Error"),  # First fails
                mock_response_success,   # Second succeeds
            ],
        )

        suggestions = await self.generator.generate_suggestions()

        # Should have 1 suggestion (second one succeeded)
        assert len(suggestions) == 1

