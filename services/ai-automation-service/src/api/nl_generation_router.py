"""
Natural Language Generation API Router
Story AI1.21: Natural Language Request Generation

API endpoints for generating automations from natural language requests.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.clients.data_api_client import DataAPIClient
from src.config import settings
from src.database.models import Suggestion, get_db_session
from src.llm.openai_client import OpenAIClient
from src.nl_automation_generator import NLAutomationRequest, get_nl_generator
from src.safety_validator import get_safety_validator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nl", tags=["natural-language"])

# Initialize clients
data_api_client = DataAPIClient(
    base_url=settings.data_api_url,
    influxdb_url=settings.influxdb_url,
    influxdb_token=settings.influxdb_token,
    influxdb_org=settings.influxdb_org,
    influxdb_bucket=settings.influxdb_bucket,
)

openai_client = OpenAIClient(
    api_key=settings.openai_api_key,
    model=getattr(settings, "nl_model", "gpt-5.1"),
)

safety_validator = get_safety_validator(getattr(settings, "safety_level", "moderate"))

nl_generator = get_nl_generator(data_api_client, openai_client, safety_validator)


class NLGenerationRequest(BaseModel):
    """Request body for NL automation generation"""
    request_text: str = Field(..., min_length=10, description="Natural language automation request")
    user_id: str = Field(default="default", description="User ID making the request")
    context: dict = Field(default={}, description="Additional context")


class ClarificationRequest(BaseModel):
    """Request body for providing clarification"""
    clarification_text: str = Field(..., min_length=5, description="Clarification details")


@router.post("/generate")
async def generate_automation_from_nl(request: NLGenerationRequest):
    """
    Generate automation from natural language request.

    Example request:
    ```json
    {
        "request_text": "Turn off the heater when any window is open for more than 10 minutes",
        "user_id": "user123"
    }
    ```

    Returns:
        Generated automation with YAML, explanation, and safety validation
    """
    logger.info(f"📝 NL generation request: '{request.request_text}'")

    # Generate automation
    try:
        nl_request = NLAutomationRequest(
            request_text=request.request_text,
            user_id=request.user_id,
            context=request.context,
        )

        generated = await nl_generator.generate(nl_request)

    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate automation: {e!s}",
        )

    # Store as suggestion (if generation succeeded)
    suggestion_id = None
    if generated.automation_yaml:
        try:
            async with get_db_session() as db:
                suggestion = Suggestion(
                    pattern_id=None,  # No pattern, it's from NL request
                    title=generated.title,
                    description=generated.description,
                    automation_yaml=generated.automation_yaml,
                    status="pending",
                    confidence=generated.confidence,
                    category="user_request",
                    priority="medium",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )

                db.add(suggestion)
                await db.commit()
                await db.refresh(suggestion)

                suggestion_id = suggestion.id
                logger.info(f"✅ Suggestion {suggestion_id} created from NL request")

        except Exception as e:
            logger.exception(f"Failed to store suggestion: {e}")
            # Don't fail the request, just log the error

    # Build response
    response = {
        "success": generated.automation_yaml != "",
        "suggestion_id": suggestion_id,
        "automation": {
            "yaml": generated.automation_yaml,
            "title": generated.title,
            "description": generated.description,
            "explanation": generated.explanation,
            "confidence": generated.confidence,
        },
    }

    # Add safety information
    if generated.safety_result:
        response["safety"] = {
            "score": generated.safety_result.safety_score,
            "passed": generated.safety_result.passed,
            "summary": generated.safety_result.summary,
        }

    # Add clarification if needed
    if generated.clarification_needed:
        response["clarification_needed"] = generated.clarification_needed
        response["next_steps"] = "Please provide clarification using the /api/nl/clarify endpoint"
    else:
        response["next_steps"] = f"Review and approve suggestion #{suggestion_id} to deploy" if suggestion_id else "Generation failed"

    # Add warnings
    if generated.warnings:
        response["warnings"] = generated.warnings

    logger.info(
        f"NL generation complete: success={response['success']}, "
        f"confidence={generated.confidence:.0%}, "
        f"suggestion_id={suggestion_id}",
    )

    return response


@router.post("/clarify/{suggestion_id}")
async def clarify_automation_request(
    suggestion_id: int,
    request: ClarificationRequest,
):
    """
    Provide clarification for ambiguous automation request.
    Regenerates automation with additional context.

    Args:
        suggestion_id: ID of suggestion needing clarification
        request: Clarification details

    Returns:
        Regenerated automation with clarification incorporated
    """
    logger.info(f"Clarification provided for suggestion {suggestion_id}")

    try:
        async with get_db_session() as db:
            # Get original suggestion
            result = await db.execute(
                select(Suggestion).where(Suggestion.id == suggestion_id),
            )
            suggestion = result.scalar_one_or_none()

            if not suggestion:
                raise HTTPException(status_code=404, detail="Suggestion not found")

            # Extract original request from description (or use description as fallback)
            original_request = suggestion.description

            # Regenerate with clarification
            generated = await nl_generator.regenerate_with_clarification(
                original_request=original_request,
                clarification=request.clarification_text,
            )

            # Update suggestion with regenerated automation
            if generated.automation_yaml:
                suggestion.automation_yaml = generated.automation_yaml
                suggestion.title = generated.title
                suggestion.description = generated.description
                suggestion.confidence = generated.confidence
                suggestion.updated_at = datetime.now(timezone.utc)
                await db.commit()

                logger.info(f"✅ Suggestion {suggestion_id} updated with clarification")

            # Build response
            response = {
                "success": generated.automation_yaml != "",
                "suggestion_id": suggestion_id,
                "automation": {
                    "yaml": generated.automation_yaml,
                    "title": generated.title,
                    "description": generated.description,
                    "explanation": generated.explanation,
                    "confidence": generated.confidence,
                },
            }

            # Add safety information
            if generated.safety_result:
                response["safety"] = {
                    "score": generated.safety_result.safety_score,
                    "passed": generated.safety_result.passed,
                    "summary": generated.safety_result.summary,
                }

            # Add warnings
            if generated.warnings:
                response["warnings"] = generated.warnings

            return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Clarification failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/examples")
async def get_example_requests():
    """
    Get example natural language requests for user guidance.

    Returns:
        List of example requests organized by category
    """
    examples = {
        "time_based": [
            "Turn on kitchen lights at 7 AM on weekdays",
            "Close all blinds at sunset",
            "Set thermostat to 68 degrees at 10 PM",
        ],
        "condition_based": [
            "Turn off heater when any window is open for more than 10 minutes",
            "Send notification when front door is left open for 5 minutes",
            "Turn on porch light when motion detected after dark",
        ],
        "automation": [
            "When I leave home, turn off all lights and lock doors",
            "Morning routine: turn on coffee maker, set temperature to 70, open blinds",
            "Goodnight routine: turn off all lights, lock doors, set alarm",
        ],
        "energy": [
            "Turn off AC when electricity price is above 30 cents per kWh",
            "Charge EV when solar production is high",
            "Reduce heating when carbon intensity is very high",
        ],
    }

    return {
        "success": True,
        "examples": examples,
        "tips": [
            "Be specific about device names (use actual device names from your system)",
            "Include timing details (when should it trigger?)",
            "Mention conditions if relevant (only when someone is home, etc.)",
            "Start simple - you can always make it more complex later",
        ],
    }


@router.get("/stats")
async def get_nl_generation_stats():
    """
    Get statistics about NL generation usage.

    Returns:
        Usage statistics (requests, success rate, etc.)
    """
    try:
        async with get_db_session() as db:
            # Count NL-generated suggestions
            result = await db.execute(
                select(Suggestion).where(Suggestion.category == "user_request"),
            )
            nl_suggestions = result.scalars().all()

            total_requests = len(nl_suggestions)
            approved_count = sum(1 for s in nl_suggestions if s.status in ["approved", "deployed"])
            deployed_count = sum(1 for s in nl_suggestions if s.status == "deployed")

            approval_rate = (approved_count / total_requests * 100) if total_requests > 0 else 0
            deployment_rate = (deployed_count / total_requests * 100) if total_requests > 0 else 0

            avg_confidence = sum(s.confidence for s in nl_suggestions) / total_requests if total_requests > 0 else 0

            return {
                "success": True,
                "stats": {
                    "total_requests": total_requests,
                    "approved_count": approved_count,
                    "deployed_count": deployed_count,
                    "approval_rate": round(approval_rate, 1),
                    "deployment_rate": round(deployment_rate, 1),
                    "average_confidence": round(avg_confidence, 2),
                },
                "openai_usage": {
                    "total_tokens": openai_client.total_tokens_used,
                    "input_tokens": openai_client.total_input_tokens,
                    "output_tokens": openai_client.total_output_tokens,
                },
            }

    except Exception as e:
        logger.exception(f"Failed to get NL stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

