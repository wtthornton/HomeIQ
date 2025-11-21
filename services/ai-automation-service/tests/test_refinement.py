"""
Simple test for Phase 3 refinement flow

Run with: pytest tests/test_refinement.py -v
"""

import os

import pytest
from src.llm.openai_client import OpenAIClient

# Skip if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)


@pytest.mark.asyncio
async def test_refine_description_simple():
    """Test simple refinement"""
    client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))

    result = await client.refine_description(
        current_description="Turn on the Living Room Light at 18:00 every day",
        user_input="Make it blue",
    )

    assert result["updated_description"] != ""
    assert "blue" in result["updated_description"].lower()
    assert len(result["changes_made"]) > 0
    assert result["validation"]["ok"] is not None

    print("\n✅ Original: Turn on the Living Room Light at 18:00 every day")
    print("✅ User input: Make it blue")
    print(f"✅ Updated: {result['updated_description']}")
    print(f"✅ Changes: {result['changes_made']}")


@pytest.mark.asyncio
async def test_refine_with_capabilities():
    """Test refinement with device capabilities"""
    client = OpenAIClient(api_key=os.getenv("OPENAI_API_KEY"))

    capabilities = {
        "features": ["brightness", "rgb_color", "color_temp"],
    }

    result = await client.refine_description(
        current_description="Turn on Kitchen Light in the morning",
        user_input="Set it to warm white",
        device_capabilities=capabilities,
    )

    assert result["updated_description"] != ""
    assert result["validation"]["ok"] is not None

    print(f"\n✅ Capabilities: {capabilities['features']}")
    print(f"✅ Updated: {result['updated_description']}")


@pytest.mark.asyncio
async def test_fallback_on_error():
    """Test fallback when OpenAI fails"""
    client = OpenAIClient(api_key="invalid-key")

    result = await client.refine_description(
        current_description="Original description",
        user_input="Make changes",
    )

    # Should return original description on error
    assert result["updated_description"] == "Original description"
    assert not result["validation"]["ok"]
    assert "error" in result["validation"]

    print("\n✅ Fallback handled gracefully")

