"""
Dependency Injection Helpers (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Following 2025 FastAPI dependency injection patterns with Annotated types.
"""

import logging
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.ha_client import HomeAssistantClient
from ..clients.openai_client import OpenAIClient
from ..clients.yaml_validation_client import YAMLValidationClient
from ..config import settings
from ..database import get_db
from ..services.automation_combiner import AutomationCombiner
from ..services.deployment_service import DeploymentService
from ..services.ha_version_service import HAVersionService
from ..services.json_query_service import JSONQueryService
from ..services.json_rebuilder import JSONRebuilder
from ..services.json_verification_service import JSONVerificationService
from ..services.suggestion_service import SuggestionService
from ..services.yaml_generation_service import YAMLGenerationService

logger = logging.getLogger(__name__)

# Type aliases for cleaner dependency injection (2025 pattern)
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


def get_api_key(request: Request) -> str:
    """
    Extract API key from request state (set by AuthenticationMiddleware).
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(api_key: str = Depends(get_api_key)):
            ...
    """
    if not hasattr(request.state, "api_key"):
        raise ValueError("API key not found in request state. Ensure AuthenticationMiddleware is configured.")
    return request.state.api_key


def get_authenticated_user(request: Request) -> dict:
    """
    Get authenticated user information from request state.
    
    Usage:
        @router.get("/endpoint")
        async def endpoint(user: dict = Depends(get_authenticated_user)):
            ...
    """
    return {
        "api_key": get_api_key(request),
        "authenticated": getattr(request.state, "authenticated", False)
    }


# Type alias for authenticated user dependency
AuthenticatedUser = Annotated[dict, Depends(get_authenticated_user)]


# Client dependencies
def get_data_api_client() -> DataAPIClient:
    """Get Data API client instance."""
    return DataAPIClient(base_url=settings.data_api_url)


def get_ha_client() -> HomeAssistantClient:
    """Get Home Assistant client instance."""
    return HomeAssistantClient(
        ha_url=settings.ha_url,
        access_token=settings.ha_token
    )


def get_openai_client() -> OpenAIClient:
    """Get OpenAI client instance."""
    return OpenAIClient(
        api_key=settings.openai_api_key,
        model=settings.openai_model
    )


def get_yaml_validation_client() -> YAMLValidationClient:
    """Get YAML Validation Service client instance (Epic 51)."""
    return YAMLValidationClient(
        base_url=settings.yaml_validation_service_url,
        api_key=settings.yaml_validation_api_key
    )


# Service dependencies
def get_yaml_generation_service(
    db: DatabaseSession,
    openai_client: Annotated[OpenAIClient, Depends(get_openai_client)],
    data_api_client: Annotated[DataAPIClient, Depends(get_data_api_client)],
    yaml_validation_client: Annotated[YAMLValidationClient, Depends(get_yaml_validation_client)]
) -> YAMLGenerationService:
    """Get YAML generation service instance (Epic 51: integrated with validation service)."""
    return YAMLGenerationService(
        openai_client=openai_client,
        data_api_client=data_api_client,
        yaml_validation_client=yaml_validation_client
    )


def get_suggestion_service(
    db: DatabaseSession,
    data_api_client: Annotated[DataAPIClient, Depends(get_data_api_client)],
    openai_client: Annotated[OpenAIClient, Depends(get_openai_client)]
) -> SuggestionService:
    """Get suggestion service instance."""
    return SuggestionService(
        db=db,
        data_api_client=data_api_client,
        openai_client=openai_client
    )


def get_deployment_service(
    db: DatabaseSession,
    ha_client: Annotated[HomeAssistantClient, Depends(get_ha_client)],
    yaml_service: Annotated[YAMLGenerationService, Depends(get_yaml_generation_service)]
) -> DeploymentService:
    """Get deployment service instance."""
    return DeploymentService(
        db=db,
        ha_client=ha_client,
        yaml_service=yaml_service
    )


# JSON service dependencies (Epic 51: HomeIQ JSON Automation layer)
def get_json_rebuilder(
    openai_client: Annotated[OpenAIClient, Depends(get_openai_client)]
) -> JSONRebuilder:
    """Get JSON rebuilder service instance."""
    return JSONRebuilder(openai_client=openai_client)


def get_json_verification_service(
    data_api_client: Annotated[DataAPIClient, Depends(get_data_api_client)]
) -> JSONVerificationService:
    """Get JSON verification service instance."""
    return JSONVerificationService(data_api_client=data_api_client)


def get_json_query_service() -> JSONQueryService:
    """Get JSON query service instance."""
    return JSONQueryService()


def get_automation_combiner() -> AutomationCombiner:
    """Get automation combiner service instance."""
    return AutomationCombiner()


def get_ha_version_service() -> HAVersionService:
    """Get HA version service instance."""
    return HAVersionService()
