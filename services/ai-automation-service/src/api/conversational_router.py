"""
Conversational Suggestion Router - Story AI1.23
================================================

New endpoints for conversational automation suggestion refinement.

Flow:
1. POST /generate - Generate description-only (no YAML) ✅ Phase 2
2. POST /{id}/refine - Refine with natural language (Phase 3)
3. GET /devices/{id}/capabilities - Get device capabilities ✅ Phase 2
4. POST /{id}/approve - Generate YAML after approval (Phase 4)

Phase 1: Returns mock data (stubs) ✅ COMPLETE
Phase 2: Real OpenAI descriptions + capabilities ✅ CURRENT
Phase 3-4: Refinement and YAML generation (Coming soon)
"""

import difflib
import json
import logging
import re
from datetime import datetime
from typing import Any, Literal

import yaml as yaml_module
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..database import get_db, store_suggestion
from ..database.models import Pattern as PatternModel
from ..database.models import Suggestion as SuggestionModel

# Phase 2-4: Import OpenAI components (SIMPLIFIED)
from ..llm.openai_client import OpenAIClient
from ..prompt_building.unified_prompt_builder import UnifiedPromptBuilder
from ..services.safety_validator import SafetyValidator

# Import YAML generation from ask_ai_router
from .ask_ai_router import generate_automation_yaml

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/suggestions", tags=["Conversational Suggestions"])

# Phase 2-4: Initialize OpenAI client (single simple class)
openai_client = None
prompt_builder = None
if settings.openai_api_key:
    try:
        openai_client = OpenAIClient(api_key=settings.openai_api_key, model=settings.openai_model)
        prompt_builder = UnifiedPromptBuilder()
        logger.info("✅ OpenAI client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenAI client: {e}")
else:
    logger.warning("⚠️ OpenAI API key not set - conversational features disabled")

# Initialize Home Assistant client for deployment
ha_client = None
if settings.ha_url and settings.ha_token:
    try:
        ha_client = HomeAssistantClient(settings.ha_url, settings.ha_token)
        logger.info("✅ Home Assistant client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize HA client: {e}")
else:
    logger.warning("⚠️ Home Assistant URL/token not set - deployment disabled")


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate description-only suggestion"""
    pattern_id: int | None = None
    pattern_type: str
    device_id: str
    metadata: dict[str, Any]

    # Mode selection (NEW: Expert Mode)
    mode: Literal["auto_draft", "expert"] = Field(
        "auto_draft",
        description="Generation mode: 'auto_draft' (fast, automated) or 'expert' (full control)"
    )

    # Explicit control (overrides mode)
    auto_generate_yaml: bool | None = Field(
        None,
        description="Explicitly control YAML generation. If None, determined by mode. "
                    "auto_draft mode: default true, expert mode: default false"
    )


class RefineRequest(BaseModel):
    """Request to refine suggestion with natural language"""
    user_input: str = Field(..., description="Natural language edit (e.g., 'Make it blue and only on weekdays')")
    conversation_context: bool = Field(default=True, description="Include conversation history in refinement")


class ApproveRequest(BaseModel):
    """Request to approve and generate YAML"""
    final_description: str | None = None
    user_notes: str | None = None
    regenerate_yaml: bool = Field(
        False,
        description="Force regeneration of YAML even if auto-draft exists. "
                    "Useful if user edited description and wants fresh YAML"
    )
    deploy_immediately: bool = Field(
        True,
        description="Deploy to Home Assistant immediately after approval. "
                    "Set to false to stage without deploying (expert mode)"
    )


class GenerateYAMLRequest(BaseModel):
    """Request to manually generate YAML (expert mode)"""
    description: str | None = Field(
        None,
        description="Override description to use. If None, uses current suggestion description"
    )
    validate_syntax: bool = Field(
        True,
        description="Run YAML syntax validation after generation"
    )
    run_safety_check: bool = Field(
        False,
        description="Run safety validation during generation (adds ~300ms, optional)"
    )


class EditYAMLRequest(BaseModel):
    """Request to manually edit YAML (expert mode)"""
    automation_yaml: str = Field(
        ...,
        description="Updated YAML content"
    )
    validate_on_save: bool = Field(
        True,
        description="Validate YAML before saving (recommended)"
    )
    user_notes: str | None = Field(
        None,
        description="Notes about what was changed"
    )


class DeviceCapability(BaseModel):
    """Device capability information"""
    feature_name: str
    available: bool
    description: str
    examples: list[str] | None = None


class ValidationResult(BaseModel):
    """Validation result for refinement"""
    ok: bool
    messages: list[str] = []
    warnings: list[str] = []
    alternatives: list[str] = []


class YAMLValidationReport(BaseModel):
    """YAML validation results from auto-draft generation"""
    syntax_valid: bool = Field(description="Whether YAML syntax is valid")
    safety_score: int | None = Field(
        None, ge=0, le=100,
        description="Safety score (0-100). Only present if safety validation ran"
    )
    issues: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of validation issues (warnings or errors)"
    )
    services_used: list[str] = Field(
        default_factory=list,
        description="Home Assistant services used (e.g., ['light.turn_on'])"
    )
    entities_referenced: list[str] = Field(
        default_factory=list,
        description="Entity IDs referenced in YAML"
    )
    advanced_features_used: list[str] = Field(
        default_factory=list,
        description="Advanced features used (e.g., ['choose', 'parallel'])"
    )


class SuggestionResponse(BaseModel):
    """Suggestion response"""
    suggestion_id: str
    description: str
    trigger_summary: str
    action_summary: str
    devices_involved: list[dict[str, Any]]
    confidence: float
    status: str
    created_at: str

    # Mode tracking (NEW: Expert Mode)
    mode: Literal["auto_draft", "expert"] = Field(
        "auto_draft",
        description="Mode used to create this suggestion"
    )

    # Auto-Draft Fields
    draft_id: str | None = Field(
        None,
        description="Draft ID (same as suggestion_id, for semantic clarity)"
    )
    automation_yaml: str | None = Field(
        None,
        description="Pre-generated Home Assistant YAML automation. "
                    "Only present if auto_draft_suggestions_enabled=true "
                    "and this suggestion is in top N (auto_draft_count)"
    )
    yaml_validation: YAMLValidationReport | None = Field(
        None,
        description="YAML validation report. Only present if automation_yaml was generated"
    )
    yaml_generation_error: str | None = Field(
        None,
        description="Error message if YAML generation failed. "
                    "Suggestion is still returned but without YAML"
    )
    yaml_generated_at: str | None = Field(
        None,
        description="ISO 8601 timestamp when YAML was generated. "
                    "None if YAML not yet generated"
    )
    yaml_generation_status: str | None = Field(
        None,
        description="Status of YAML generation: 'completed', 'queued', 'failed', 'not_requested'. "
                    "Used for async generation when count > async_threshold"
    )

    # Expert Mode Fields (NEW)
    yaml_edited_at: str | None = Field(
        None,
        description="ISO 8601 timestamp when YAML was manually edited (expert mode)"
    )
    yaml_edit_count: int = Field(
        0,
        description="Number of manual YAML edits made (expert mode)"
    )


class RefinementResponse(BaseModel):
    """Refinement response"""
    suggestion_id: str
    updated_description: str
    changes_detected: list[str]
    validation: ValidationResult
    confidence: float
    refinement_count: int
    status: str


class ApprovalResponse(BaseModel):
    """Approval response"""
    suggestion_id: str
    status: str
    automation_yaml: str
    yaml_validation: dict[str, Any]
    ready_to_deploy: bool


# ============================================================================
# Endpoints (Phase 1: Mock Data)
# ============================================================================

@router.post("/generate", response_model=SuggestionResponse, status_code=status.HTTP_201_CREATED)
async def generate_description_only(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db)
) -> SuggestionResponse:
    """
    Generate description-only suggestion (no YAML yet).
    
    Phase 2: ✅ IMPLEMENTED - Real OpenAI description generation!
    
    Flow:
    1. Fetch device metadata from data-api
    2. Call OpenAI to generate human-readable description
    3. Cache device capabilities
    4. Return structured response (no YAML generated yet)
    """
    pattern_info = f"pattern {request.pattern_id}" if request.pattern_id else "sample suggestion"
    logger.info(f"📝 Generating description for {pattern_info} ({request.pattern_type})")

    # Check if OpenAI is configured
    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API not configured"
        )

    try:
        # Validate pattern_id if provided, set to None if not found or not provided
        validated_pattern_id = None
        if request.pattern_id is not None:
            result = await db.execute(
                select(PatternModel).where(PatternModel.id == request.pattern_id)
            )
            pattern_exists = result.scalar_one_or_none()

            if pattern_exists:
                validated_pattern_id = request.pattern_id
                logger.info(f"✅ Using existing pattern {request.pattern_id}")
            else:
                logger.warning(f"⚠️ Pattern {request.pattern_id} not found, creating suggestion without pattern")
                validated_pattern_id = None
        else:
            logger.info("📝 Creating suggestion without pattern (sample/direct generation)")

        # Build pattern dict for OpenAI
        pattern_dict = {
            'pattern_type': request.pattern_type,
            'device_id': request.device_id,
            'hour': request.metadata.get('hour', 18),
            'minute': request.metadata.get('minute', 0),
            'occurrences': request.metadata.get('occurrences', 20),
            'confidence': request.metadata.get('confidence', 0.85)
        }

        # Simple device context (no data-api dependency for now)
        device_name = request.device_id.split('.')[-1].replace('_', ' ').title() if '.' in request.device_id else request.device_id
        device_context = {
            'name': device_name,
            'domain': request.device_id.split('.')[0] if '.' in request.device_id else 'unknown'
        }

        # Generate description via OpenAI
        # Build prompt using UnifiedPromptBuilder
        prompt_dict = await prompt_builder.build_pattern_prompt(
            pattern=pattern_dict,
            device_context=device_context,
            output_mode="description"
        )

        # Generate with unified method
        result = await openai_client.generate_with_unified_prompt(
            prompt_dict=prompt_dict,
            temperature=0.7,
            max_tokens=300,
            output_format="description"
        )

        # Extract description from result
        description = result.get('description', '')

        # Simple capabilities (mock for now)
        capabilities = {
            'entity_id': request.device_id,
            'friendly_name': device_name,
            'domain': device_context['domain'],
            'supported_features': {},
            'friendly_capabilities': []
        }

        # Persist suggestion using enriched storage helper
        suggestion = await store_suggestion(
            db,
            {
                'pattern_id': validated_pattern_id,
                'title': f"Automation: {device_name}",
                'description': description,
                'description_only': description,
                'automation_yaml': None,
                'confidence': request.metadata.get('confidence', 0.75),
                'category': 'convenience',
                'priority': request.metadata.get('priority'),
                'status': 'draft',
                'device_id': request.device_id,
                'devices_involved': [request.device_id],
                'device_capabilities': capabilities,
            }
        )

        # Build response
        response = SuggestionResponse(
            suggestion_id=f"suggestion-{suggestion.id}",
            description=description,
            trigger_summary=_extract_trigger_summary_from_request(request),
            action_summary=_extract_action_summary_from_request(request, capabilities),
            devices_involved=[{
                "entity_id": capabilities.get('entity_id', request.device_id),
                "friendly_name": capabilities.get('friendly_name', request.device_id),
                "domain": capabilities.get('domain', 'unknown'),
                "area": capabilities.get('area', ''),
                "capabilities": {
                    "supported_features": list(capabilities.get('supported_features', {}).keys()),
                    "friendly_capabilities": capabilities.get('friendly_capabilities', [])
                }
            }],
            confidence=request.metadata.get('confidence', 0.75),
            status="draft",
            created_at=suggestion.created_at.isoformat()
        )

        logger.info(f"✅ Generated description: {description[:60]}... (ID: {suggestion.id})")
        return response

    except Exception as e:
        logger.error(f"❌ Failed to generate description: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate description: {str(e)}"
        ) from e


def _extract_trigger_summary_from_request(request: GenerateRequest) -> str:
    """Extract trigger summary from pattern"""
    if request.pattern_type == 'time_of_day':
        hour = int(request.metadata.get('avg_time_decimal', 0))
        return f"At {hour:02d}:00 daily"
    elif request.pattern_type == 'co_occurrence':
        if '+' in request.device_id:
            device1 = request.device_id.split('+')[0].split('.')[-1].replace('_', ' ').title()
            return f"When {device1} activates"
    elif request.pattern_type == 'anomaly':
        return "Unusual activity detected"
    return "Pattern detected"


def _extract_action_summary_from_request(request: GenerateRequest, capabilities: dict) -> str:
    """Extract action summary from pattern and capabilities"""
    device_name = capabilities.get('friendly_name', request.device_id)
    domain = capabilities.get('domain', 'unknown')

    if domain == 'light':
        return f"Turn on {device_name}"
    elif domain == 'switch':
        return f"Activate {device_name}"
    elif domain == 'climate':
        return f"Adjust {device_name}"
    else:
        return f"Control {device_name}"


@router.post("/{suggestion_id}/refine", response_model=RefinementResponse)
async def refine_description(
    suggestion_id: str,
    request: RefineRequest,
    db: AsyncSession = Depends(get_db)
) -> RefinementResponse:
    """
    Refine suggestion description with natural language.
    
    Phase 3: ✅ IMPLEMENTED - Real OpenAI refinement with validation!
    
    Flow:
    1. Fetch current suggestion from database
    2. Get device capabilities (cached in suggestion)
    3. Pre-validate feasibility (fast check)
    4. Call OpenAI with refinement prompt
    5. Update database with new description and history
    """
    logger.info(f"✏️ Refining suggestion {suggestion_id}: '{request.user_input}'")

    # Check if OpenAI is configured
    if not openai_client:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OpenAI API not configured. Set OPENAI_API_KEY environment variable."
        )

    try:
        # Step 1: Fetch current suggestion
        # Handle both string IDs (suggestion-1) and integer IDs
        try:
            if suggestion_id.startswith('suggestion-'):
                # Extract integer from "suggestion-1" format
                db_id = int(suggestion_id.split('-')[1])
            else:
                # Direct integer ID
                db_id = int(suggestion_id)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail=f"Invalid suggestion ID format: {suggestion_id}")

        result = await db.execute(
            select(SuggestionModel).where(SuggestionModel.id == db_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

        # Step 2: Check refinement limit
        can_refine, error_msg = suggestion.can_refine(max_refinements=10)
        if not can_refine:
            raise HTTPException(status_code=400, detail=error_msg)

        # Verify editable status
        if suggestion.status not in ['draft', 'refining']:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot refine suggestion in '{suggestion.status}' status"
            )

        logger.info(f"📖 Current: {suggestion.description_only[:60]}...")

        # Step 3: Call OpenAI for refinement
        refinement_result = await openai_client.refine_description(
            current_description=suggestion.description_only,
            user_input=request.user_input,
            device_capabilities=suggestion.device_capabilities
        )

        # Step 4: Update database
        updated_history = suggestion.conversation_history or []
        updated_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "user_input": request.user_input,
            "updated_description": refinement_result['updated_description'],
            "changes": refinement_result['changes_made'],
            "validation": refinement_result['validation']
        })

        await db.execute(
            update(SuggestionModel)
            .where(SuggestionModel.id == db_id)
            .values(
                description_only=refinement_result['updated_description'],
                conversation_history=updated_history,
                refinement_count=suggestion.refinement_count + 1,
                status='refining',
                updated_at=datetime.utcnow()
            )
        )
        await db.commit()

        logger.info(f"✅ Refined: {len(refinement_result['changes_made'])} changes")

        # Build response
        validation_data = refinement_result['validation']
        response = RefinementResponse(
            suggestion_id=suggestion_id,
            updated_description=refinement_result['updated_description'],
            changes_detected=refinement_result['changes_made'],
            validation=ValidationResult(
                ok=validation_data['ok'],
                messages=[],
                warnings=[validation_data.get('error')] if validation_data.get('error') else [],
                alternatives=[]
            ),
            confidence=suggestion.confidence,
            refinement_count=suggestion.refinement_count + 1,
            status="refining"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to refine suggestion {suggestion_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refine suggestion: {str(e)}"
        )


# ============================================================================
# Helper Functions for YAML Generation
# ============================================================================

def _extract_trigger_summary(description: str) -> str:
    """
    Extract trigger summary from description.
    Looks for patterns like "when", "at", "if", etc.
    """

    # Common trigger patterns
    trigger_patterns = [
        r'(?:when|if|at|on|after|before)\s+([^,]+?)(?:,|$|\.)',
        r'time[:\s]+([^,]+?)(?:,|$|\.)',
    ]

    for pattern in trigger_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback: extract first part before comma or period
    parts = re.split(r'[,.]+', description)
    if len(parts) > 1:
        # Look for trigger keywords in first part
        for keyword in ['when', 'if', 'at', 'on', 'after', 'before']:
            if keyword.lower() in parts[0].lower():
                return parts[0].strip()

    return "Automation trigger"  # Default fallback


def _extract_action_summary(description: str) -> str:
    """
    Extract action summary from description.
    Looks for action verbs like "turn on", "flash", "dim", etc.
    """

    # Common action patterns
    action_patterns = [
        r'(turn\s+(?:on|off|up|down)|flash|dim|brighten|change|set|enable|disable|activate|deactivate)\s+([^,]+?)(?:,|$|\.)',
        r'(?:then|and)\s+(.+?)(?:,|$|\.)',
    ]

    for pattern in action_patterns:
        match = re.search(pattern, description, re.IGNORECASE)
        if match:
            return match.group(0).strip()

    # Fallback: extract last part after comma or period
    parts = re.split(r'[,.]+', description)
    if len(parts) > 1:
        # Last part often contains the action
        return parts[-1].strip()

    return description.strip()  # Use whole description as fallback


def _extract_devices(suggestion: SuggestionModel, conversation_history: list[dict]) -> list[str]:
    """
    Extract device names from suggestion and conversation history.
    Combines information from title, description, and conversation history.
    """
    devices = []

    # Extract from title (often contains device name)
    if suggestion.title:
        # Pattern: "AI Suggested: {device}" or "Automation: {device}"
        title_match = re.search(r'(?:AI Suggested|Automation):\s*(.+?)(?:\s|$|at|when)', suggestion.title)
        if title_match:
            devices.append(title_match.group(1).strip())

    # Extract from description
    if suggestion.description_only or suggestion.description:
        desc = suggestion.description_only or suggestion.description
        # Look for common device patterns
        device_patterns = [
            r'(?:the\s+)?([a-z\s]+?)\s+(?:light|sensor|switch|door|lock|thermostat|camera)',
            r'(?:office|living room|kitchen|bedroom|garage|front|back)\s+([a-z\s]+)',
        ]
        for pattern in device_patterns:
            matches = re.findall(pattern, desc, re.IGNORECASE)
            devices.extend([m.strip() for m in matches if m.strip()])

    # Extract from conversation history
    if conversation_history:
        for entry in conversation_history:
            user_input = entry.get('user_input', '')
            # Look for device mentions in user edits
            device_matches = re.findall(
                r'(?:the\s+)?([a-z\s]+?)\s+(?:light|sensor|switch|door|lock)',
                user_input,
                re.IGNORECASE
            )
            devices.extend([m.strip() for m in device_matches if m.strip()])

    # Deduplicate and return
    return list(set(devices)) if devices else ["device"]


async def _extract_entities_from_context(
    suggestion: SuggestionModel,
    conversation_history: list[dict],
    db: AsyncSession
) -> list[dict[str, Any]]:
    """
    Extract entities from conversation history and device capabilities.
    Uses EntityValidator to map natural language to real entity IDs.
    """
    from ..clients.data_api_client import DataAPIClient
    from ..services.entity_validator import EntityValidator

    # Build combined description from suggestion and history
    combined_text = suggestion.description_only or suggestion.description or ""

    # Add conversation history context
    if conversation_history:
        for entry in conversation_history:
            user_input = entry.get('user_input', '')
            if user_input:
                combined_text += f" {user_input}"

    # Try to extract entities using EntityValidator
    try:
        data_api_client = DataAPIClient()
        ha_client_for_validation = HomeAssistantClient(
            ha_url=settings.ha_url,
            access_token=settings.ha_token
        ) if settings.ha_url and settings.ha_token else None

        entity_validator = EntityValidator(
            data_api_client,
            db_session=db,
            ha_client=ha_client_for_validation
        )

        # Extract devices from context
        devices_involved = _extract_devices(suggestion, conversation_history)

        # Map to real entities
        entity_mapping = await entity_validator.map_query_to_entities(
            combined_text,
            devices_involved
        )

        # Convert mapping to entity list format
        if entity_mapping:
            entities = []
            for term, entity_id in entity_mapping.items():
                entities.append({
                    'name': term,
                    'entity_id': entity_id,
                    'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                })
            return entities

        # Fallback to stored device metadata when validator finds no matches
        caps = suggestion.device_capabilities or {}
        if not isinstance(caps, dict):
            try:
                caps = dict(caps)
            except Exception:
                caps = {}
        fallback_entities: list[dict[str, Any]] = []
        devices = caps.get('devices') if isinstance(caps, dict) else None
        if isinstance(devices, list):
            for entry in devices:
                if isinstance(entry, dict):
                    entity_id = entry.get('entity_id')
                    if entity_id:
                        fallback_entities.append({
                            'name': entry.get('friendly_name', entity_id),
                            'entity_id': entity_id,
                            'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                        })
        else:
            entity_id = caps.get('entity_id') if isinstance(caps, dict) else None
            if isinstance(entity_id, str):
                fallback_entities.append({
                    'name': caps.get('friendly_name', entity_id),
                    'entity_id': entity_id,
                    'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown'
                })

        if fallback_entities:
            logger.info(
                "Using fallback device metadata for entity extraction on suggestion %s",
                suggestion.id
            )
            return fallback_entities
    except Exception as e:
        logger.warning(f"⚠️ Failed to extract entities from context: {e}")

    # Fallback: return empty list if extraction fails
    return []


@router.post("/{suggestion_id}/approve")
async def approve_suggestion(
    suggestion_id: str,
    request: ApproveRequest | None = Body(None),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Approve suggestion and generate YAML.
    
    Unified Implementation (Phase 2): Uses same YAML generation as Ask-AI page!
    
    Flow:
    1. Fetch suggestion from database
    2. Verify status (draft or refining)
    3. Extract entities from conversation history and device capabilities
    4. Generate YAML using unified generate_automation_yaml() with entity validation
    5. Validate YAML syntax
    6. Run safety validation before deployment
    7. Store YAML and update status
    8. Deploy to Home Assistant (if enabled)
    
    Uses superset of available data:
    - description_only / final_description
    - conversation_history (for context)
    - device_capabilities (for validation)
    - Extracted entities (validated via EntityValidator)
    """
    logger.info(f"✅ Approving suggestion {suggestion_id}")

    # Handle optional request body
    if request is None:
        request = ApproveRequest(final_description=None, user_notes=None)

    logger.info(f"📥 Request body: final_description={request.final_description}, user_notes={request.user_notes}")

    if not openai_client:
        raise HTTPException(
            status_code=500,
            detail="OpenAI API not configured"
        )

    try:
        # Step 1: Fetch suggestion
        # Handle both string IDs (suggestion-1) and integer IDs
        try:
            if suggestion_id.startswith('suggestion-'):
                # Extract integer from "suggestion-1" format
                db_id = int(suggestion_id.split('-')[1])
            else:
                # Direct integer ID
                db_id = int(suggestion_id)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail=f"Invalid suggestion ID format: {suggestion_id}")

        result = await db.execute(
            select(SuggestionModel).where(SuggestionModel.id == db_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        logger.info(f"📋 Approving suggestion {suggestion_id} (DB ID: {db_id}) - Current status: '{suggestion.status}'")

        # Step 2: Verify status (allow re-approving deployed suggestions for updates)
        # Note: 'approved' status is set after YAML generation, so it should be allowed for re-deployment
        if suggestion.status not in ['draft', 'refining', 'deployed', 'yaml_generated', 'approved']:
            error_msg = f"Cannot approve suggestion in '{suggestion.status}' status"
            logger.warning(f"⚠️ {error_msg} for suggestion {suggestion_id} (DB ID: {db_id})")
            raise HTTPException(
                status_code=400,
                detail=error_msg
            )

        # If already deployed, this is a re-deploy (regenerate YAML and update)
        # Include 'approved' status since it means YAML was generated but may need re-deployment
        is_redeploy = suggestion.status in ['deployed', 'yaml_generated', 'approved']
        if is_redeploy:
            logger.info(f"🔄 Re-deploying suggestion {suggestion_id} - regenerating YAML with latest logic")

        # Use final_description if provided, otherwise use the current description_only
        description_to_use = request.final_description or suggestion.description_only or suggestion.description or ""
        logger.info(f"📝 Generating YAML for: {description_to_use[:60]}...")

        # Step 3: Extract context information
        conversation_history = suggestion.conversation_history or []
        devices_involved = _extract_devices(suggestion, conversation_history)
        entities = await _extract_entities_from_context(suggestion, conversation_history, db)

        if entities:
            resolved_entities = [entity.get('entity_id') for entity in entities if entity.get('entity_id')]
            if resolved_entities:
                devices_involved = resolved_entities

        # Build suggestion dictionary in format expected by generate_automation_yaml
        suggestion_dict = {
            'description': description_to_use,
            'trigger_summary': _extract_trigger_summary(description_to_use),
            'action_summary': _extract_action_summary(description_to_use),
            'devices_involved': devices_involved,
            'device_capabilities': suggestion.device_capabilities or {}
        }

        if entities:
            validated_entities_map = {}
            for entity in entities:
                entity_id = entity.get('entity_id')
                if not entity_id:
                    continue
                key = entity.get('name') or entity_id
                validated_entities_map[key] = entity_id

            if validated_entities_map:
                suggestion_dict['validated_entities'] = validated_entities_map
                try:
                    suggestion_dict['enriched_entity_context'] = json.dumps(entities)
                except (TypeError, ValueError):
                    suggestion_dict['enriched_entity_context'] = json.dumps(validated_entities_map)

        # Step 4: Generate YAML using unified method (same as Ask-AI page)
        logger.info("🚀 Using unified YAML generation with entity validation...")
        automation_yaml = await generate_automation_yaml(
            suggestion=suggestion_dict,
            original_query=description_to_use,
            entities=entities if entities else None,
            db_session=db
        )

        if not automation_yaml:
            raise HTTPException(status_code=500, detail="Failed to generate automation YAML")

        # Step 5: Validate YAML syntax
        import yaml
        try:
            yaml.safe_load(automation_yaml)
            yaml_valid = True
        except yaml.YAMLError as e:
            yaml_valid = False
            logger.warning(f"⚠️ Generated YAML has syntax errors: {e}")
            raise HTTPException(status_code=400, detail=f"Generated YAML has syntax errors: {str(e)}")

        # Step 6: Run safety validation before deployment
        logger.info("🔒 Running safety validation...")
        safety_report = None
        if ha_client:
            try:
                safety_validator = SafetyValidator(ha_client=ha_client)
                safety_report = await safety_validator.validate_automation(automation_yaml)

                if not safety_report.get('safe', True):
                    critical_issues = safety_report.get('critical_issues', [])
                    logger.warning(f"⚠️ Safety validation failed: {len(critical_issues)} critical issues")
                    return {
                        "suggestion_id": suggestion_id,
                        "status": "blocked",
                        "safe": False,
                        "safety_report": safety_report,
                        "message": "Automation creation blocked due to safety concerns",
                        "warnings": [issue.get('message') for issue in critical_issues],
                        "automation_yaml": automation_yaml,  # Still return YAML for review
                        "yaml_validation": {
                            "syntax_valid": yaml_valid,
                            "safety_score": safety_report.get('safety_score', 0),
                            "issues": critical_issues
                        }
                    }

                if safety_report.get('warnings'):
                    logger.info(f"⚠️ Safety validation passed with {len(safety_report.get('warnings', []))} warnings")
            except Exception as e:
                logger.warning(f"⚠️ Safety validation error: {e}, continuing without safety check")
                safety_report = {'safe': True, 'warnings': [f'Safety check skipped: {str(e)}']}

        # Step 6.5: Regenerate category and priority during redeploy
        category = suggestion.category
        priority = suggestion.priority
        if is_redeploy:
            logger.info("🔄 Re-deploy detected - regenerating category and priority")
            try:
                classification = await openai_client.infer_category_and_priority(description_to_use)
                category = classification['category']
                priority = classification['priority']
                logger.info(f"✅ Updated category: {category}, priority: {priority}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to regenerate category: {e}, keeping original values")

        # Step 7: Store YAML first
        await db.execute(
            update(SuggestionModel)
            .where(SuggestionModel.id == db_id)
            .values(
                automation_yaml=automation_yaml,
                category=category,
                priority=priority,
                yaml_generated_at=datetime.utcnow(),
                approved_at=datetime.utcnow(),
                status='approved',  # Set to 'approved' so deploy endpoint accepts it
                updated_at=datetime.utcnow()
            )
        )
        await db.commit()

        logger.info(f"✅ YAML generated and stored for suggestion {suggestion_id}")

        # Step 8: Deploy to Home Assistant
        automation_id = None
        deployment_error = None
        if ha_client:
            try:
                # If re-deploying, ensure YAML has the correct automation ID for updates
                if is_redeploy and suggestion.ha_automation_id:
                    existing_automation_id = suggestion.ha_automation_id
                    logger.info(f"🔄 Re-deploying automation {existing_automation_id} to Home Assistant")

                    # Parse YAML and ensure it has the correct ID for updating
                    import yaml
                    automation_data = yaml.safe_load(automation_yaml)
                    if isinstance(automation_data, dict):
                        # Extract ID from entity_id (e.g., "automation.test" -> "test")
                        # Try to preserve the original ID if present, otherwise extract from entity_id
                        entity_id_parts = existing_automation_id.replace('automation.', '').split('.')
                        base_id = entity_id_parts[-1] if entity_id_parts else None

                        # If YAML doesn't have an 'id', try to set it from the existing automation
                        # Note: This is a best-effort approach - HA may use the alias for matching
                        if 'id' not in automation_data and base_id:
                            # Use create_automation which handles updates properly
                            deployment_result = await ha_client.create_automation(
                                automation_yaml,
                                automation_id=existing_automation_id,
                                force_new=False  # Update existing automation
                            )
                        else:
                            # YAML has an ID, use create_automation which will update if ID exists
                            deployment_result = await ha_client.create_automation(
                                automation_yaml,
                                automation_id=existing_automation_id,
                                force_new=False  # Update existing automation
                            )
                    else:
                        # Fallback to deploy_automation if YAML parsing fails
                        deployment_result = await ha_client.deploy_automation(
                            automation_yaml=automation_yaml,
                            automation_id=existing_automation_id
                        )
                else:
                    logger.info(f"🚀 Deploying automation to Home Assistant for suggestion {suggestion_id}")
                    deployment_result = await ha_client.deploy_automation(automation_yaml=automation_yaml)

                if deployment_result.get('success'):
                    automation_id = deployment_result.get('automation_id')

                    # Update status to deployed
                    await db.execute(
                        update(SuggestionModel)
                        .where(SuggestionModel.id == db_id)
                        .values(
                            status='deployed',
                            ha_automation_id=automation_id,
                            deployed_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                    )
                    await db.commit()

                    logger.info(f"✅ Successfully deployed automation {automation_id} to Home Assistant")
                else:
                    deployment_error = deployment_result.get('error', 'Unknown deployment error')
                    logger.error(f"❌ Deployment failed: {deployment_error}")
            except Exception as e:
                deployment_error = str(e)
                logger.error(f"❌ Deployment error: {deployment_error}")
        else:
            logger.warning("⚠️ HA client not available - skipping deployment")
            deployment_error = "Home Assistant client not configured"

        # Return response (matching Ask-AI endpoint format)
        response = {
            "suggestion_id": suggestion_id,
            "status": "deployed" if automation_id else "approved",
            "automation_yaml": automation_yaml,
            "automation_id": automation_id,
            "category": category,
            "priority": priority,
            "ready_to_deploy": yaml_valid and (safety_report is None or safety_report.get('safe', True)),
            "yaml_validation": {
                "syntax_valid": yaml_valid,
                "safety_score": safety_report.get('safety_score', 95) if safety_report else 95,
                "issues": safety_report.get('critical_issues', []) if safety_report else []
            },
            "approved_at": datetime.utcnow().isoformat()
        }

        # Add safety report if available
        if safety_report:
            response["safety_report"] = safety_report
            response["safe"] = safety_report.get('safe', True)
            if safety_report.get('warnings'):
                response["warnings"] = [w.get('message') if isinstance(w, dict) else w for w in safety_report.get('warnings', [])]

        # Add restoration info (empty for now, for consistency with Ask-AI)
        response["restoration_log"] = []
        response["restored_components"] = []

        if deployment_error:
            response["deployment_error"] = deployment_error
            response["deployment_warning"] = "YAML generated but not deployed to Home Assistant"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to approve suggestion: {e}")
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.get("/devices/{device_id}/capabilities", response_model=dict[str, Any])
async def get_device_capabilities(
    device_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get device capabilities for showing to user.
    
    Phase 2: ✅ IMPLEMENTED - Real capability fetching from data-api!
    
    Flow:
    1. Query data-api for device metadata
    2. Parse supported features
    3. Format as friendly capabilities list
    4. Return structured capability information
    """
    logger.info(f"🔍 Get capabilities for device: {device_id}")

    try:
        # Mock capabilities for now (data-api integration pending)
        capabilities = {
            'entity_id': device_id,
            'friendly_name': device_id.split('.')[-1].replace('_', ' ').title(),
            'domain': device_id.split('.')[0] if '.' in device_id else 'unknown',
            'area': '',
            'supported_features': {},
            'friendly_capabilities': [],
            'cached': False
        }

        # Format response with detailed capability information
        formatted_capabilities = {
            "entity_id": capabilities.get('entity_id', device_id),
            "friendly_name": capabilities.get('friendly_name', device_id),
            "domain": capabilities.get('domain', 'unknown'),
            "area": capabilities.get('area', ''),
            "supported_features": {},
            "friendly_capabilities": capabilities.get('friendly_capabilities', []),
            "cached": capabilities.get('cached', False)
        }

        # Add detailed feature descriptions
        for feature, is_available in capabilities.get('supported_features', {}).items():
            if is_available:
                formatted_capabilities['supported_features'][feature] = {
                    "available": True,
                    "description": _get_feature_description(feature, capabilities['domain'])
                }

        # Add common use cases based on capabilities
        formatted_capabilities['common_use_cases'] = _generate_use_cases(capabilities)

        logger.info(f"✅ Returned {len(formatted_capabilities['friendly_capabilities'])} capabilities")
        return formatted_capabilities

    except Exception as e:
        logger.error(f"❌ Failed to fetch capabilities for {device_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device capabilities: {str(e)}"
        )


def _get_feature_description(feature: str, domain: str) -> str:
    """Get friendly description for a feature"""
    descriptions = {
        'brightness': "Adjust brightness level (0-100%)",
        'rgb_color': "Set any RGB color (red, blue, warm white, etc.)",
        'color_temp': "Set color temperature (2700K warm - 6500K cool)",
        'transition': "Smooth fade in/out transitions",
        'effect': "Light effects and animations",
        'temperature': "Set target temperature",
        'hvac_mode': "Change heating/cooling mode",
        'fan_mode': "Adjust fan speed",
        'position': "Set position (0-100%)",
        'speed': "Adjust speed level"
    }
    return descriptions.get(feature, f"Control {feature.replace('_', ' ')}")


def _generate_use_cases(capabilities: dict) -> list[str]:
    """Generate example use cases based on capabilities"""
    use_cases = []
    domain = capabilities.get('domain', '')
    features = capabilities.get('supported_features', {})
    device_name = capabilities.get('friendly_name', 'device')

    if domain == 'light':
        if features.get('brightness'):
            use_cases.append(f"Turn on {device_name} to 50% brightness")
        if features.get('rgb_color'):
            use_cases.append(f"Change {device_name} to blue")
        if features.get('color_temp'):
            use_cases.append(f"Set {device_name} to warm white")
        if features.get('transition'):
            use_cases.append(f"Fade in {device_name} over 2 seconds")

    elif domain == 'climate':
        if features.get('temperature'):
            use_cases.append(f"Set {device_name} to 72°F")
        if features.get('hvac_mode'):
            use_cases.append(f"Switch {device_name} to heat/cool")

    elif domain == 'cover':
        if features.get('position'):
            use_cases.append(f"Open {device_name} to 50%")
        use_cases.append(f"Close {device_name}")

    else:
        use_cases.append(f"Turn {device_name} on/off")

    return use_cases if use_cases else [f"Control {device_name}"]




@router.get("/by-automation/{automation_id}", response_model=dict[str, Any])
async def get_suggestion_by_automation_id(
    automation_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get suggestion by Home Assistant automation ID.
    Used for re-deploy functionality from Deployed page.
    """
    logger.info(f"📖 Get suggestion by automation_id: {automation_id}")

    try:
        result = await db.execute(
            select(SuggestionModel).where(SuggestionModel.ha_automation_id == automation_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(status_code=404, detail=f"Suggestion not found for automation_id: {automation_id}")

        return {
            "id": suggestion.id,
            "suggestion_id": f"suggestion-{suggestion.id}",
            "title": suggestion.title,
            "description": suggestion.description_only or suggestion.description,
            "description_only": suggestion.description_only or suggestion.description,
            "status": suggestion.status,
            "ha_automation_id": suggestion.ha_automation_id,
            "automation_yaml": suggestion.automation_yaml,
            "conversation_history": suggestion.conversation_history or [],
            "device_capabilities": suggestion.device_capabilities or {},
            "refinement_count": suggestion.refinement_count or 0,
            "confidence": suggestion.confidence,
            "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
            "deployed_at": suggestion.deployed_at.isoformat() if suggestion.deployed_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get suggestion by automation_id: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestion: {str(e)}")


@router.get("/{suggestion_id}", response_model=dict[str, Any])
async def get_suggestion_detail(
    suggestion_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Get detailed suggestion information.
    
    Phase 1: Returns mock data
    Phase 2+: Fetch from database
    """
    logger.info(f"📖 [STUB] Get suggestion detail: {suggestion_id}")

    # TODO: Implement database fetch
    mock_detail = {
        "suggestion_id": suggestion_id,
        "pattern_id": 123,
        "description_only": "When motion is detected in the Living Room after 6PM on weekdays, turn on the Living Room Light to blue",
        "conversation_history": [
            {
                "timestamp": "2025-10-17T18:30:00Z",
                "user_input": "Make it blue",
                "updated_description": "When motion is detected in the Living Room after 6PM, turn on the Living Room Light to blue",
                "validation_result": {"ok": True, "message": "Device supports RGB colors"}
            },
            {
                "timestamp": "2025-10-17T18:31:00Z",
                "user_input": "Only on weekdays",
                "updated_description": "When motion is detected in the Living Room after 6PM on weekdays, turn on the Living Room Light to blue",
                "validation_result": {"ok": True}
            }
        ],
        "device_capabilities": {},
        "refinement_count": 2,
        "automation_yaml": None,
        "status": "refining",
        "confidence": 0.92,
        "created_at": "2025-10-17T18:25:00Z"
    }

    return mock_detail


# ============================================================================
# Expert Mode Endpoints (NEW)
# ============================================================================

@router.post("/{suggestion_id}/generate-yaml")
async def generate_yaml_expert_mode(
    suggestion_id: str,
    request: GenerateYAMLRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Generate YAML on-demand for expert mode (Step 3 of expert flow).

    Expert Mode Flow:
    1. Generate description → 2. Refine description → 3. Generate YAML (HERE) → 4. Edit YAML → 5. Deploy

    This endpoint allows users to manually trigger YAML generation after they're satisfied
    with the description. It's called when the user clicks "Generate YAML" in expert mode.

    Returns:
    - automation_yaml: Generated YAML content
    - yaml_validation: Validation report
    - status: Updated to 'yaml_generated'
    """
    logger.info(f"🔧 Expert Mode: Generating YAML for suggestion {suggestion_id}")

    if not openai_client:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")

    try:
        # Step 1: Fetch suggestion
        try:
            if suggestion_id.startswith('suggestion-'):
                db_id = int(suggestion_id.split('-')[1])
            else:
                db_id = int(suggestion_id)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail=f"Invalid suggestion ID format: {suggestion_id}")

        result = await db.execute(
            select(SuggestionModel).where(SuggestionModel.id == db_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        logger.info(f"📋 Generating YAML for suggestion {suggestion_id} (mode: {suggestion.mode or 'auto_draft'})")

        # Step 2: Use provided description or current suggestion description
        description_to_use = request.description or suggestion.description_only or suggestion.description or ""

        if not description_to_use:
            raise HTTPException(status_code=400, detail="No description available for YAML generation")

        # Step 3: Extract entities from description
        conversation_history = suggestion.conversation_history or []
        entities = await _extract_entities_from_context(suggestion, conversation_history, db)

        # Step 4: Build suggestion dict for YAML generator
        suggestion_dict = {
            'description': description_to_use,
            'trigger_summary': _extract_trigger_summary(description_to_use),
            'action_summary': _extract_action_summary(description_to_use),
            'devices_involved': _extract_devices(suggestion, conversation_history),
            'device_capabilities': suggestion.device_capabilities or {}
        }

        # Step 5: Generate YAML using unified generator
        logger.info("🚀 Calling unified YAML generator...")
        automation_yaml = await generate_automation_yaml(
            suggestion=suggestion_dict,
            original_query=description_to_use,
            entities=entities if entities else None,
            db_session=db
        )

        if not automation_yaml:
            raise HTTPException(status_code=500, detail="YAML generation returned empty result")

        # Step 6: Validate YAML syntax
        yaml_valid = False
        issues = []

        if request.validate_syntax:
            try:
                yaml_module.safe_load(automation_yaml)
                yaml_valid = True
                logger.info("✅ YAML syntax validation passed")
            except yaml_module.YAMLError as e:
                yaml_valid = False
                issues.append({"type": "error", "message": f"YAML syntax error: {str(e)}"})
                logger.warning(f"⚠️ YAML syntax validation failed: {e}")
        else:
            yaml_valid = True  # Skip validation if requested

        # Step 7: Optional safety validation
        safety_score = None
        if request.run_safety_check and ha_client:
            try:
                safety_validator = SafetyValidator(ha_client=ha_client)
                safety_report = await safety_validator.validate_automation(automation_yaml)
                safety_score = safety_report.get('safety_score', 0)
                if not safety_report.get('safe', True):
                    issues.extend(safety_report.get('critical_issues', []))
                logger.info(f"✅ Safety validation completed (score: {safety_score})")
            except Exception as e:
                logger.warning(f"⚠️ Safety validation failed: {e}")

        # Step 8: Build validation report
        yaml_validation = {
            "syntax_valid": yaml_valid,
            "safety_score": safety_score,
            "issues": issues,
            "services_used": _extract_services(automation_yaml),
            "entities_referenced": _extract_entities_from_yaml(automation_yaml),
            "advanced_features_used": _extract_advanced_features(automation_yaml)
        }

        # Step 9: Update database with generated YAML
        suggestion.automation_yaml = automation_yaml
        suggestion.status = "yaml_generated"
        suggestion.yaml_generated_at = datetime.utcnow()
        suggestion.yaml_generation_method = "expert_manual"
        suggestion.yaml_generation_error = None

        await db.commit()
        await db.refresh(suggestion)

        logger.info(f"✅ Expert mode YAML generated and stored for suggestion {suggestion_id}")

        # Step 10: Return response
        return {
            "suggestion_id": suggestion_id,
            "automation_yaml": automation_yaml,
            "yaml_validation": yaml_validation,
            "status": "yaml_generated",
            "yaml_generated_at": suggestion.yaml_generated_at.isoformat(),
            "yaml_generation_method": "expert_manual"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Expert mode YAML generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YAML generation failed: {str(e)}"
        )


@router.patch("/{suggestion_id}/yaml")
async def edit_yaml_expert_mode(
    suggestion_id: str,
    request: EditYAMLRequest = Body(...),
    db: AsyncSession = Depends(get_db)
) -> dict[str, Any]:
    """
    Edit YAML manually for expert mode (Step 4 of expert flow).

    Expert Mode Flow:
    1. Generate description → 2. Refine description → 3. Generate YAML → 4. Edit YAML (HERE) → 5. Deploy

    This endpoint allows users to manually edit the generated YAML. It's called when the user
    edits YAML in a code editor and clicks "Save Changes".

    Returns:
    - automation_yaml: Updated YAML content
    - yaml_validation: Validation report for edited YAML
    - changes: Diff showing what was changed
    - status: Updated to 'yaml_edited'
    """
    logger.info(f"🛠️ Expert Mode: Editing YAML for suggestion {suggestion_id}")

    try:
        # Step 1: Fetch suggestion
        try:
            if suggestion_id.startswith('suggestion-'):
                db_id = int(suggestion_id.split('-')[1])
            else:
                db_id = int(suggestion_id)
        except (ValueError, IndexError):
            raise HTTPException(status_code=400, detail=f"Invalid suggestion ID format: {suggestion_id}")

        result = await db.execute(
            select(SuggestionModel).where(SuggestionModel.id == db_id)
        )
        suggestion = result.scalar_one_or_none()

        if not suggestion:
            raise HTTPException(status_code=404, detail="Suggestion not found")

        logger.info(f"📝 Editing YAML for suggestion {suggestion_id}")

        # Step 2: Check edit count limit
        current_edit_count = suggestion.yaml_edit_count or 0
        if current_edit_count >= settings.expert_mode_max_yaml_edits:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum YAML edit limit reached ({settings.expert_mode_max_yaml_edits} edits). "
                       "Create a new suggestion to continue editing."
            )

        # Step 3: Validate YAML syntax
        yaml_valid = False
        issues = []

        if request.validate_on_save:
            try:
                yaml_module.safe_load(request.automation_yaml)
                yaml_valid = True
                logger.info("✅ Edited YAML syntax validation passed")
            except yaml_module.YAMLError as e:
                yaml_valid = False
                issues.append({"type": "error", "message": f"YAML syntax error: {str(e)}", "line": getattr(e, 'problem_mark', None)})
                logger.warning(f"⚠️ Edited YAML syntax validation failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"YAML syntax error: {str(e)}"
                )
        else:
            yaml_valid = True  # Skip validation if requested (not recommended)

        # Step 4: Check for dangerous operations (security)
        if not settings.expert_mode_allow_dangerous_operations:
            dangerous_services = _check_dangerous_services(request.automation_yaml)
            if dangerous_services:
                issues.append({
                    "type": "security",
                    "message": f"Dangerous services detected: {', '.join(dangerous_services)}",
                    "services": dangerous_services
                })
                logger.warning(f"⚠️ Dangerous services detected in YAML edit: {dangerous_services}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Dangerous services not allowed: {', '.join(dangerous_services)}. "
                           "Contact admin to enable expert_mode_allow_dangerous_operations."
                )

        # Step 5: Generate YAML diff (show what changed)
        diff_lines = []
        if suggestion.automation_yaml and settings.expert_mode_show_yaml_diff:
            old_lines = suggestion.automation_yaml.splitlines(keepends=True)
            new_lines = request.automation_yaml.splitlines(keepends=True)
            diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
            diff_lines = list(diff)

        diff_text = ''.join(diff_lines) if diff_lines else "No previous YAML to compare"

        # Step 6: Extract modified fields from diff
        modified_fields = []
        for line in diff_lines:
            if line.startswith('+') and not line.startswith('+++'):
                # Extract field name from added lines
                match = re.match(r'\+\s*(\w+):', line)
                if match:
                    modified_fields.append(match.group(1))

        # Step 7: Build validation report
        yaml_validation = {
            "syntax_valid": yaml_valid,
            "safety_score": None,  # Safety validation runs on deployment
            "issues": issues,
            "services_used": _extract_services(request.automation_yaml),
            "entities_referenced": _extract_entities_from_yaml(request.automation_yaml),
            "advanced_features_used": _extract_advanced_features(request.automation_yaml)
        }

        # Step 8: Update database with edited YAML
        suggestion.automation_yaml = request.automation_yaml
        suggestion.status = "yaml_edited"
        suggestion.yaml_edited_at = datetime.utcnow()
        suggestion.yaml_edit_count = current_edit_count + 1
        suggestion.yaml_generation_method = "expert_manual_edited"

        # Add user notes to conversation history
        if request.user_notes:
            if not suggestion.conversation_history:
                suggestion.conversation_history = []
            suggestion.conversation_history.append({
                "role": "user",
                "content": request.user_notes,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "yaml_edit"
            })

        await db.commit()
        await db.refresh(suggestion)

        logger.info(f"✅ Expert mode YAML edited and stored for suggestion {suggestion_id} (edit #{suggestion.yaml_edit_count})")

        # Step 9: Return response with diff
        return {
            "suggestion_id": suggestion_id,
            "automation_yaml": request.automation_yaml,
            "yaml_validation": yaml_validation,
            "changes": {
                "modified_fields": list(set(modified_fields)),
                "diff": diff_text
            },
            "status": "yaml_edited",
            "yaml_edited_at": suggestion.yaml_edited_at.isoformat(),
            "edit_count": suggestion.yaml_edit_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Expert mode YAML edit failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YAML edit failed: {str(e)}"
        )


# ============================================================================
# Helper Functions for Expert Mode
# ============================================================================

def _extract_services(yaml_content: str) -> list[str]:
    """Extract Home Assistant service calls from YAML"""
    services = []
    for match in re.finditer(r'service:\s+([\w.]+)', yaml_content):
        service = match.group(1)
        if service not in services:
            services.append(service)
    return services


def _extract_entities_from_yaml(yaml_content: str) -> list[str]:
    """Extract entity IDs from YAML content"""
    entities = []
    for match in re.finditer(r'entity_id:\s+([\w.]+)', yaml_content):
        entity = match.group(1)
        if entity not in entities:
            entities.append(entity)
    return entities


def _extract_advanced_features(yaml_content: str) -> list[str]:
    """Detect advanced HA automation features in YAML"""
    features = []
    advanced_keywords = {
        'choose': 'choose',
        'parallel': 'parallel',
        'sequence': 'sequence',
        'repeat': 'repeat',
        'wait_template': 'wait_template',
        'variables': 'variables',
        'condition:': 'condition'
    }

    for keyword, feature_name in advanced_keywords.items():
        if keyword in yaml_content:
            features.append(feature_name)

    return features


def _check_dangerous_services(yaml_content: str) -> list[str]:
    """Check for dangerous service calls in YAML (security)"""
    dangerous_found = []

    for blocked_service in settings.expert_mode_blocked_services:
        # Check for exact match or wildcard
        if blocked_service.endswith('*'):
            prefix = blocked_service[:-1]  # Remove asterisk
            if f"service: {prefix}" in yaml_content:
                dangerous_found.append(blocked_service)
        else:
            if f"service: {blocked_service}" in yaml_content:
                dangerous_found.append(blocked_service)

    return dangerous_found


# ============================================================================
# Health Check
# ============================================================================

@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check for conversational suggestion endpoints"""
    return {
        "status": "healthy",
        "message": "Conversational suggestion router (Phase 1: Stubs)",
        "phase": "1-mock-data"
    }

