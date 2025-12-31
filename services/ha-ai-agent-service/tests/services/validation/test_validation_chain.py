"""
Tests for validation_chain.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.validation.validation_chain import ValidationChain
from src.services.validation.validation_strategy import ValidationStrategy
from src.models.automation_models import ValidationResult


class MockValidationStrategy(ValidationStrategy):
    """Mock validation strategy for testing"""

    def __init__(self, name: str, should_succeed: bool = True, should_raise: bool = False):
        self._name = name
        self._should_succeed = should_succeed
        self._should_raise = should_raise

    @property
    def name(self) -> str:
        return self._name

    async def validate(self, automation_yaml: str) -> ValidationResult:
        if self._should_raise:
            raise Exception(f"Strategy {self._name} failed")
        if self._should_succeed:
            return ValidationResult(
                valid=True,
                errors=[],
                warnings=[],
                score=100.0
            )
        return ValidationResult(
            valid=False,
            errors=[f"Error from {self._name}"],
            warnings=[],
            score=50.0
        )


class TestValidationChain:
    """Test ValidationChain class."""

    def test___init__(self):
        """Test __init__ method."""
        strategies = [
            MockValidationStrategy("strategy1"),
            MockValidationStrategy("strategy2")
        ]
        chain = ValidationChain(strategies)
        assert len(chain.strategies) == 2
        assert chain.strategies[0].name == "strategy1"
        assert chain.strategies[1].name == "strategy2"

    @pytest.mark.asyncio
    async def test_validate_first_strategy_succeeds(self):
        """Test validation when first strategy succeeds."""
        strategies = [
            MockValidationStrategy("strategy1", should_succeed=True),
            MockValidationStrategy("strategy2", should_succeed=False)
        ]
        chain = ValidationChain(strategies)

        result = await chain.validate("alias: test")
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_validate_second_strategy_succeeds(self):
        """Test validation when first fails but second succeeds."""
        strategies = [
            MockValidationStrategy("strategy1", should_succeed=False),
            MockValidationStrategy("strategy2", should_succeed=True)
        ]
        chain = ValidationChain(strategies)

        result = await chain.validate("alias: test")
        assert result.valid is True
        assert len(result.errors) == 0
        assert result.score == 100.0

    @pytest.mark.asyncio
    async def test_validate_all_strategies_fail(self):
        """Test validation when all strategies fail."""
        strategies = [
            MockValidationStrategy("strategy1", should_succeed=False),
            MockValidationStrategy("strategy2", should_succeed=False)
        ]
        chain = ValidationChain(strategies)

        result = await chain.validate("alias: test")
        assert result.valid is False
        assert len(result.errors) == 2
        assert "Error from strategy1" in result.errors
        assert "Error from strategy2" in result.errors

    @pytest.mark.asyncio
    async def test_validate_strategy_raises_exception(self):
        """Test validation when strategy raises exception."""
        strategies = [
            MockValidationStrategy("strategy1", should_raise=True),
            MockValidationStrategy("strategy2", should_succeed=True)
        ]
        chain = ValidationChain(strategies)

        result = await chain.validate("alias: test")
        # Should fall back to second strategy and succeed
        assert result.valid is True
        assert len(result.errors) == 0  # Second strategy succeeded

    @pytest.mark.asyncio
    async def test_validate_empty_strategies(self):
        """Test validation with empty strategy list."""
        chain = ValidationChain([])
        result = await chain.validate("alias: test")
        assert result.valid is False
        assert len(result.errors) == 1
        assert "All validation strategies failed" in result.errors[0] or "unavailable" in result.errors[0]