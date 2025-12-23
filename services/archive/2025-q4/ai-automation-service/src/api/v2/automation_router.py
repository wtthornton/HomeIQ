"""
Automation Router v2

Automation management endpoints.
Consolidates automation generation, testing, and deployment.

Created: Phase 3 - New API Routers
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...services.service_container import ServiceContainer, get_service_container
from .models import (
    AutomationGenerationRequest,
    AutomationGenerationResponse,
    AutomationSummary,
    DeploymentRequest,
    DeploymentResult,
    TestRequest,
    TestResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/automations", tags=["Automations v2"])


@router.post("/generate", response_model=AutomationGenerationResponse)
async def generate_automation(
    request: AutomationGenerationRequest,
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db)
) -> AutomationGenerationResponse:
    """Generate automation YAML from suggestion"""
    # Get suggestion from database
    result = await db.execute(text("""
        SELECT suggestion_id, title, description, validated_entities, confidence
        FROM automation_suggestions
        WHERE suggestion_id = :suggestion_id
    """), {"suggestion_id": request.suggestion_id})

    suggestion_row = result.fetchone()
    if not suggestion_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Suggestion {request.suggestion_id} not found"
        )

    # Generate YAML
    yaml_generator = container.yaml_generator

    # Parse validated_entities JSON
    import json
    validated_entities = {}
    if suggestion_row[3]:  # validated_entities column
        if isinstance(suggestion_row[3], str):
            validated_entities = json.loads(suggestion_row[3])
        elif isinstance(suggestion_row[3], dict):
            validated_entities = suggestion_row[3]

    suggestion_dict = {
        "title": suggestion_row[1],  # title
        "description": suggestion_row[2],  # description
        "validated_entities": validated_entities
    }

    automation_yaml = await yaml_generator.generate(
        suggestion=suggestion_dict,
        original_query=suggestion_row[2],  # description
        validated_entities=validated_entities
    )

    # Validate YAML
    yaml_validator = container.yaml_validator
    validation_result = await yaml_validator.validate(automation_yaml)

    # Update suggestion with YAML
    await db.execute(text("""
        UPDATE automation_suggestions
        SET automation_yaml = :yaml, status = 'yaml_generated', updated_at = :updated_at
        WHERE suggestion_id = :suggestion_id
    """), {
        "suggestion_id": request.suggestion_id,
        "yaml": automation_yaml,
        "updated_at": datetime.utcnow().isoformat()
    })

    await db.commit()

    return AutomationGenerationResponse(
        suggestion_id=request.suggestion_id,
        automation_yaml=automation_yaml,
        validation_result={
            "valid": validation_result.valid,
            "stages": [{"name": s.name, "valid": s.valid} for s in validation_result.stages]
        },
        confidence=suggestion_row[4] if len(suggestion_row) > 4 else 0.5  # confidence
    )


@router.post("/{suggestion_id}/test", response_model=TestResult)
async def test_automation(
    suggestion_id: str,
    request: TestRequest,
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db)
) -> TestResult:
    """Test automation before deployment"""
    test_executor = container.test_executor

    start_time = datetime.utcnow()
    result = await test_executor.execute_test(
        automation_yaml=request.automation_yaml
    )

    execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

    return TestResult(
        success=result.get("success", False),
        state_changes=result.get("state_changes", {}),
        errors=result.get("errors", []),
        warnings=result.get("warnings", []),
        execution_time_ms=execution_time
    )


@router.post("/{suggestion_id}/deploy", response_model=DeploymentResult)
async def deploy_automation(
    suggestion_id: str,
    request: DeploymentRequest,
    container: ServiceContainer = Depends(get_service_container),
    db: AsyncSession = Depends(get_db)
) -> DeploymentResult:
    """Deploy automation to Home Assistant"""
    deployer = container.deployer

    result = await deployer.deploy(
        automation_yaml=request.automation_yaml,
        automation_id=request.automation_id
    )

    # Update suggestion status
    await db.execute(text("""
        UPDATE automation_suggestions
        SET status = 'deployed', updated_at = :updated_at
        WHERE suggestion_id = :suggestion_id
    """), {
        "suggestion_id": suggestion_id,
        "updated_at": datetime.utcnow().isoformat()
    })

    await db.commit()

    return DeploymentResult(
        success=result.get("success", False),
        automation_id=result.get("automation_id", ""),
        message=result.get("message", "Deployment completed"),
        deployed_at=datetime.utcnow().isoformat()
    )


@router.get("", response_model=list[AutomationSummary])
async def list_automations(
    conversation_id: str | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db)
) -> list[AutomationSummary]:
    """List automations with optional filters"""
    query = "SELECT * FROM automation_suggestions WHERE 1=1"
    params = {}

    if conversation_id:
        query += " AND conversation_id = :conversation_id"
        params["conversation_id"] = conversation_id

    if status:
        query += " AND status = :status"
        params["status"] = status

    query += " ORDER BY created_at DESC LIMIT 100"

    result = await db.execute(text(query), params)

    summaries = []
    for row in result:
        summaries.append(AutomationSummary(
            suggestion_id=row[1] if len(row) > 1 else "",  # suggestion_id
            conversation_id=row[2] if len(row) > 2 else "",  # conversation_id
            title=row[4] if len(row) > 4 else "",  # title
            description=row[5] if len(row) > 5 else "",  # description
            status=row[10] if len(row) > 10 else "draft",  # status
            confidence=row[8] if len(row) > 8 else 0.5,  # confidence
            created_at=row[11].isoformat() if len(row) > 11 and row[11] else datetime.utcnow().isoformat(),  # created_at
            updated_at=row[12].isoformat() if len(row) > 12 and row[12] else datetime.utcnow().isoformat()  # updated_at
        ))

    return summaries

