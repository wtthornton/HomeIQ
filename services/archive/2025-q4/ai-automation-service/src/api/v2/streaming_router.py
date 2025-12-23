"""
Streaming Router v2

Server-Sent Events (SSE) streaming for conversation turns.
Provides real-time updates as suggestions are generated.

Created: Phase 3 - New API Routers
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...services.service_container import ServiceContainer, get_service_container
from .models import MessageRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/conversations", tags=["Conversations v2 - Streaming"])


@router.post("/{conversation_id}/stream")
async def stream_conversation_turn(
    conversation_id: str,
    request: MessageRequest,
    container: ServiceContainer = Depends(get_service_container)
):
    """
    Stream conversation turn responses using Server-Sent Events.
    
    Provides real-time updates as:
    - Entities are extracted
    - Suggestions are generated
    - Confidence is calculated
    """

    async def generate_events():
        """Generate SSE events for conversation turn"""
        try:
            # Event: Start
            yield f"data: {json.dumps({'event': 'start', 'conversation_id': conversation_id})}\n\n"

            # Extract entities
            entity_extractor = container.entity_extractor
            entities = await entity_extractor.extract(request.message)

            yield f"data: {json.dumps({'event': 'entities', 'data': entities})}\n\n"

            # Match intent
            intent_matcher = container.intent_matcher
            intent = intent_matcher.match_intent(request.message)

            yield f"data: {json.dumps({'event': 'intent', 'intent': intent.value})}\n\n"

            # Generate suggestions (if automation intent)
            if intent.value == "automation":
                # Placeholder for suggestion generation
                # Full implementation would stream suggestions as they're generated
                suggestions = []  # await generate_suggestions_stream(...)

                for suggestion in suggestions:
                    yield f"data: {json.dumps({'event': 'suggestion', 'data': suggestion})}\n\n"

            # Calculate confidence
            confidence_calculator = container.confidence_calculator
            confidence = await confidence_calculator.calculate_confidence(
                query=request.message,
                entities=entities,
                ambiguities=[],
                validation_result={}
            )

            yield f"data: {json.dumps({'event': 'confidence', 'confidence': confidence.overall, 'explanation': confidence.explanation})}\n\n"

            # Event: Complete
            yield f"data: {json.dumps({'event': 'complete', 'conversation_id': conversation_id})}\n\n"

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )

