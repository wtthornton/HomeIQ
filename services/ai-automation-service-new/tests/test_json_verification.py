"""
Tests for JSON verification service
"""

import pytest

from ..services.json_verification_service import JSONVerificationService
from shared.homeiq_automation.schema import (
    HomeIQAutomation,
    HomeIQMetadata,
    HomeIQTrigger,
    HomeIQAction,
    DeviceContext,
)


@pytest.mark.asyncio
async def test_json_verification_valid():
    """Test verification of valid HomeIQ JSON."""
    automation = HomeIQAutomation(
        alias="Valid Automation",
        homeiq_metadata=HomeIQMetadata(
            use_case="comfort",
            complexity="low"
        ),
        device_context=DeviceContext(
            entity_ids=["light.test"]
        ),
        triggers=[
            HomeIQTrigger(platform="state", entity_id="light.test", to="on")
        ],
        actions=[
            HomeIQAction(service="light.turn_on", target={"entity_id": "light.test"})
        ]
    )
    
    verification_service = JSONVerificationService(data_api_client=None)
    result = await verification_service.verify(
        automation,
        validate_entities=False,  # Skip entity validation for unit test
        validate_devices=False,
        validate_safety=False
    )
    
    # Should pass basic schema validation
    assert result.valid or len(result.errors) == 0  # May have warnings but should be valid


@pytest.mark.asyncio
async def test_json_verification_consistency():
    """Test consistency checking."""
    automation = HomeIQAutomation(
        alias="Consistency Test",
        homeiq_metadata=HomeIQMetadata(
            use_case="comfort",
            complexity="low"
        ),
        device_context=DeviceContext(
            entity_ids=["light.test", "sensor.temperature"]
        ),
        triggers=[
            HomeIQTrigger(platform="state", entity_id="light.test", to="on")
        ],
        actions=[
            HomeIQAction(service="light.turn_on", target={"entity_id": "light.test"})
        ]
    )
    
    verification_service = JSONVerificationService(data_api_client=None)
    result = await verification_service.verify_consistency(automation)
    
    assert "consistent" in result
    # May have warnings about unused entities, but should be consistent

