"""
Integration Tests for Phase 3 - Conversational Refinement
===========================================================

Story AI1.23 Phase 3: Conversational Suggestion Refinement

Tests the complete refinement flow:
1. Fetch suggestion from database
2. User edits with natural language
3. Validate against device capabilities
4. Update description via OpenAI
5. Track conversation history
6. Update database

These tests require:
- OpenAI API key set (or mocked)
- data-api running (or mocked)
- Database initialized with suggestions
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch
import json
import os

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

from src.main import app
from src.llm.suggestion_refiner import SuggestionRefiner
from src.database.models import Suggestion as SuggestionModel, init_db, get_db_session


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
async def test_suggestion():
    """Create a test suggestion in database"""
    await init_db()
    
    async with get_db_session() as db:
        suggestion = SuggestionModel(
            pattern_id=1,
            description_only="When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness",
            conversation_history=[],
            device_capabilities={
                "entity_id": "light.living_room",
                "friendly_name": "Living Room Light",
                "domain": "light",
                "supported_features": {
                    "brightness": True,
                    "rgb_color": True,
                    "color_temp": True
                },
                "friendly_capabilities": [
                    "Adjust brightness (0-100%)",
                    "Change color (RGB)",
                    "Set color temperature (warm to cool)"
                ]
            },
            refinement_count=0,
            automation_yaml=None,
            status='draft',
            title="Living Room Motion Lighting",
            category="convenience",
            priority="medium",
            confidence=0.89
        )
        
        db.add(suggestion)
        await db.commit()
        await db.refresh(suggestion)
        
        return suggestion.id


# ============================================================================
# Refinement Flow Tests
# ============================================================================

@pytest.mark.asyncio
async def test_refine_with_color_change(test_suggestion):
    """Test refinement with color change"""
    with patch('src.api.conversational_router.suggestion_refiner') as mock_refiner:
        # Mock refinement response
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=True,
            messages=["✓ Device supports RGB color"],
            warnings=[],
            alternatives=[]
        ))
        
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="When motion is detected in the Living Room after 6PM, turn on the Living Room Light to blue",
            changes_made=["Added color: blue (RGB supported ✓)"],
            validation=ValidationResult(ok=True, messages=["✓ RGB supported"], warnings=[], alternatives=[]),
            clarification_needed=None,
            history_entry={
                "timestamp": "2025-10-17T20:00:00Z",
                "user_input": "Make it blue",
                "updated_description": "When motion is detected in the Living Room after 6PM, turn on the Living Room Light to blue",
                "validation_result": {"ok": True, "messages": ["✓ RGB supported"]},
                "changes_made": ["Added color: blue"]
            }
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/suggestions/{test_suggestion}/refine",
                json={"user_input": "Make it blue"}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "blue" in data['updated_description'].lower()
            assert data['refinement_count'] == 1
            assert data['status'] == 'refining'
            assert len(data['changes_detected']) > 0


@pytest.mark.asyncio
async def test_refine_with_multiple_edits(test_suggestion):
    """Test multiple refinements in sequence"""
    with patch('src.api.conversational_router.suggestion_refiner') as mock_refiner:
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        
        # First refinement: "Make it blue"
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=True, messages=[], warnings=[], alternatives=[]
        ))
        
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="...turn on light to blue",
            changes_made=["Added color: blue"],
            validation=ValidationResult(ok=True, messages=[], warnings=[], alternatives=[]),
            history_entry={
                "timestamp": "2025-10-17T20:00:00Z",
                "user_input": "Make it blue",
                "updated_description": "...turn on light to blue",
                "validation_result": {"ok": True},
                "changes_made": ["Added color"]
            }
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # First refinement
            response1 = await client.post(
                f"/api/v1/suggestions/{test_suggestion}/refine",
                json={"user_input": "Make it blue"}
            )
            
            assert response1.status_code == 200
            assert response1.json()['refinement_count'] == 1
            
            # Second refinement: "Only on weekdays"
            mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
                updated_description="...turn on light to blue on weekdays",
                changes_made=["Added condition: weekdays only"],
                validation=ValidationResult(ok=True, messages=[], warnings=[], alternatives=[]),
                history_entry={
                    "timestamp": "2025-10-17T20:01:00Z",
                    "user_input": "Only on weekdays",
                    "updated_description": "...turn on light to blue on weekdays",
                    "validation_result": {"ok": True},
                    "changes_made": ["Added weekday condition"]
                }
            ))
            
            response2 = await client.post(
                f"/api/v1/suggestions/{test_suggestion}/refine",
                json={"user_input": "Only on weekdays"}
            )
            
            assert response2.status_code == 200
            assert response2.json()['refinement_count'] == 2


@pytest.mark.asyncio
async def test_refine_with_invalid_feature():
    """Test refinement when user requests unsupported feature"""
    with patch('src.api.conversational_router.suggestion_refiner') as mock_refiner:
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=False,
            messages=[],
            warnings=["⚠️ Device does not support RGB color"],
            alternatives=["Try: 'Set brightness to 75%'"]
        ))
        
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="When motion detected, turn on Bedroom Light to 50% brightness",  # Unchanged
            changes_made=[],
            validation=ValidationResult(
                ok=False,
                messages=[],
                warnings=["⚠️ Device does not support RGB color"],
                alternatives=["Try: 'Set brightness to 75%'"]
            ),
            clarification_needed="This light doesn't support colors. Would you like to adjust brightness instead?"
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                f"/api/v1/suggestions/1/refine",
                json={"user_input": "Make it blue"}
            )
            
            # Should still return 200 but with validation warnings
            assert response.status_code == 200
            data = response.json()
            
            assert data['validation']['ok'] == False
            assert len(data['validation']['warnings']) > 0


# ============================================================================
# Conversation History Tests
# ============================================================================

@pytest.mark.asyncio
async def test_conversation_history_tracked():
    """Test that conversation history is properly tracked in database"""
    with patch('src.api.conversational_router.suggestion_refiner') as mock_refiner:
        from src.llm.suggestion_refiner import RefinementResult, ValidationResult
        
        mock_refiner.validate_feasibility = AsyncMock(return_value=ValidationResult(
            ok=True, messages=[], warnings=[], alternatives=[]
        ))
        
        mock_refiner.refine_description = AsyncMock(return_value=RefinementResult(
            updated_description="Updated description",
            changes_made=["Test change"],
            validation=ValidationResult(ok=True, messages=[], warnings=[], alternatives=[]),
            history_entry={
                "timestamp": "2025-10-17T20:00:00Z",
                "user_input": "Make a change",
                "updated_description": "Updated description",
                "validation_result": {"ok": True},
                "changes_made": ["Test change"]
            }
        ))
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            # Make refinement
            await client.post(
                f"/api/v1/suggestions/1/refine",
                json={"user_input": "Make a change"}
            )
            
            # Fetch suggestion detail
            detail_response = await client.get(f"/api/v1/suggestions/1")
            detail = detail_response.json()
            
            # Assert history was saved
            assert 'conversation_history' in detail
            assert len(detail['conversation_history']) >= 1
            assert detail['conversation_history'][-1]['user_input'] == "Make a change"


# ============================================================================
# Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_cannot_refine_deployed_suggestion():
    """Test that deployed suggestions cannot be refined"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to refine a deployed suggestion
        response = await client.post(
            f"/api/v1/suggestions/999/refine",  # Assume 999 is deployed
            json={"user_input": "Change it"}
        )
        
        # Should return 400 or 404
        assert response.status_code in [400, 404]


@pytest.mark.asyncio
async def test_refine_nonexistent_suggestion():
    """Test refinement of non-existent suggestion"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            f"/api/v1/suggestions/99999/refine",
            json={"user_input": "Change it"}
        )
        
        assert response.status_code == 404


# ============================================================================
# Real OpenAI Integration Test (Optional, costs money)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv('OPENAI_API_KEY'),
    reason="OPENAI_API_KEY not set - skipping real API tests"
)
@pytest.mark.asyncio
async def test_real_openai_refinement():
    """
    Test real OpenAI refinement (COSTS MONEY - ~$0.0001).
    
    This is a real integration test that calls OpenAI API.
    Only run when you want to verify the actual integration works.
    """
    from openai import AsyncOpenAI
    
    # Initialize real clients
    client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    refiner = SuggestionRefiner(client, model="gpt-4o-mini")
    
    # Test refinement
    result = await refiner.refine_description(
        current_description="When motion is detected in the Living Room after 6PM, turn on the Living Room Light to 50% brightness",
        user_input="Make it blue and only on weekdays",
        device_capabilities={
            "entity_id": "light.living_room",
            "friendly_name": "Living Room Light",
            "domain": "light",
            "supported_features": {
                "brightness": True,
                "rgb_color": True
            },
            "friendly_capabilities": ["Adjust brightness", "Change color (RGB)"]
        },
        conversation_history=[]
    )
    
    # Assertions
    assert result.updated_description is not None
    assert len(result.updated_description) > 0
    assert result.validation.ok == True
    assert len(result.changes_made) > 0
    
    # Check token usage
    stats = refiner.get_usage_stats()
    assert stats['total_tokens'] > 0
    assert stats['estimated_cost_usd'] > 0
    
    print(f"\n✅ Real OpenAI refinement test passed!")
    print(f"   Updated: {result.updated_description}")
    print(f"   Changes: {result.changes_made}")
    print(f"   Tokens: {stats['total_tokens']}")
    print(f"   Cost: ${stats['estimated_cost_usd']:.6f}")


# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio for async tests"""
    return "asyncio"

