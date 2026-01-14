"""
Device Suggestions API Endpoints
Phase 2: Device-Based Automation Suggestions Feature

POST /api/v1/chat/device-suggestions endpoint for generating automation suggestions.
"""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..api.dependencies import get_settings
from ..api.device_suggestions_models import (
    DeviceSuggestionsRequest,
    DeviceSuggestionsResponse,
)
from ..services.device_suggestion_service import DeviceSuggestionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["device-suggestions"])


@router.post("/device-suggestions", response_model=DeviceSuggestionsResponse)
async def generate_device_suggestions(
    request: DeviceSuggestionsRequest,
    settings=Depends(get_settings),
):
    """
    Generate automation suggestions for a selected device.
    
    Aggregates data from multiple sources:
    - Device attributes and capabilities (data-api)
    - Device synergies (ai-pattern-service)
    - Home Assistant blueprints (blueprint-suggestion-service)
    - Sports data (sports-api, Team Tracker sensors)
    - Weather data (weather-api)
    
    Returns 3-5 ranked automation suggestions with Home Assistant 2025.10+ YAML compatibility.
    
    **Rate Limit:** Same as chat endpoint (100 requests/minute per IP)
    """
    try:
        # Initialize suggestion service
        suggestion_service = DeviceSuggestionService(settings)
        
        # Generate suggestions
        response = await suggestion_service.generate_suggestions(
            device_id=request.device_id,
            conversation_id=request.conversation_id,
            context=request.context,
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"Invalid request for device suggestions: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Failed to generate device suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suggestions: {str(e)}",
        )
