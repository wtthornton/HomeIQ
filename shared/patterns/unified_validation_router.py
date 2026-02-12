"""
UnifiedValidationRouter - Reusable Pattern B: Unified Validation API

Epic: Reusable Pattern Framework, Story 3
Base class/template for orchestrated multi-backend validation endpoints
with standardized response shape.

Pattern: Single HTTP endpoint that orchestrates one or more validation
backends and returns a unified, structured response.

Usage:
    class BlueprintValidationRouter(UnifiedValidationRouter):
        domain = "blueprint"

        async def run_validation(self, request, **kwargs):
            result = await self.blueprint_client.validate(request.content)
            return self.build_response(result)
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Standard Request / Response Models ---

class ValidationRequest(BaseModel):
    """Standard validation request model. Extend for domain-specific fields."""
    content: str = Field(..., description="Content to validate (YAML, JSON, etc.)")
    normalize: bool = Field(True, description="Normalize content to canonical format")
    validate_entities: bool = Field(True, description="Validate entity references exist")
    validate_services: bool = Field(True, description="Validate service calls")


class ValidationSubsection(BaseModel):
    """Validation subsection for a specific category (entity, service, device, etc.)."""
    performed: bool = True
    passed: bool = True
    errors: list[str] = Field(default_factory=list)


class ValidationResponse(BaseModel):
    """
    Standard unified validation response.

    All validation endpoints return this shape for consistency.
    Domain-specific subsections are added via the `subsections` dict.
    """
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    score: float = 0.0
    fixed_content: str | None = None
    fixes_applied: list[str] = Field(default_factory=list)
    # Domain-specific subsections keyed by category name
    subsections: dict[str, ValidationSubsection] = Field(default_factory=dict)


# --- Pluggable Validation Backend ---

class ValidationBackend(ABC):
    """
    Interface for a pluggable validation backend.

    Each backend performs one type of validation (schema, entity, service, etc.)
    and returns a ValidationResult dict.
    """

    name: str = ""

    @abstractmethod
    async def validate(self, content: str, **kwargs: Any) -> dict[str, Any]:
        """
        Validate content and return results.

        Args:
            content: Content to validate
            **kwargs: Additional validation options

        Returns:
            Dict with at least: valid (bool), errors (list[str]), warnings (list[str])
        """
        ...


# --- Error Categorization ---

def categorize_errors(
    errors: list[str],
    categories: dict[str, tuple[str, ...]],
) -> dict[str, list[str]]:
    """
    Categorize errors by keyword matching.

    Args:
        errors: List of error messages
        categories: Dict mapping category name to keyword tuples.
            Example: {"entity": ("entity", "Entity", "entity_id"),
                      "service": ("service", "Service")}

    Returns:
        Dict mapping category name to list of matching errors.
        Errors that match no category are placed under "other".
    """
    result: dict[str, list[str]] = {name: [] for name in categories}
    result["other"] = []

    for error in errors:
        matched = False
        for category_name, keywords in categories.items():
            if any(kw in error for kw in keywords):
                result[category_name].append(error)
                matched = True
                break
        if not matched:
            result["other"].append(error)

    return result


# --- Error-to-Domain Mapping for RAG Feedback ---

# Maps error patterns to RAG domain names for corpus selection
ERROR_DOMAIN_MAP: dict[str, list[tuple[str, ...]]] = {
    "device_capability": (
        ("entity_id", "not found", "unknown entity", "invalid entity",
         "entity does not exist", "no such entity"),
    ),
    "automation": (
        ("service", "invalid service", "service not found",
         "unknown service", "service call"),
    ),
    "comfort": (
        ("brightness", "color_temp", "temperature", "hvac",
         "climate", "thermostat"),
    ),
    "energy": (
        ("power", "energy", "kwh", "battery", "solar", "charge"),
    ),
    "security": (
        ("alarm", "lock", "camera", "motion sensor", "arm", "disarm"),
    ),
}


def get_error_domain_hints(errors: list[str]) -> list[str]:
    """
    Map validation error patterns to RAG domain names.

    When validation fails, this identifies which RAG domains are relevant
    so their corpus can be proactively injected on retry.

    Args:
        errors: List of validation error messages

    Returns:
        List of RAG domain names that should be injected
    """
    if not errors:
        return []

    domains: set[str] = set()
    error_text = " ".join(errors).lower()

    for domain, keyword_groups in ERROR_DOMAIN_MAP.items():
        for keywords in keyword_groups:
            if any(kw.lower() in error_text for kw in keywords):
                domains.add(domain)
                break

    return sorted(domains)


# --- Base Router Template ---

class UnifiedValidationRouter(ABC):
    """
    Base class for unified validation endpoints.

    Provides:
        - Standard request/response models
        - Error categorization logic
        - Response building helpers

    Subclasses must implement:
        - domain: str (e.g. "automation", "blueprint", "scene")
        - run_validation(): Core validation orchestration
    """

    domain: str = ""

    # Default error categories - override in subclass for domain-specific categories
    error_categories: dict[str, tuple[str, ...]] = {
        "entity": ("entity", "Entity", "invalid entity", "entity_id"),
        "service": ("service", "Service", "invalid service"),
    }

    @abstractmethod
    async def run_validation(
        self,
        request: ValidationRequest,
        **kwargs: Any,
    ) -> ValidationResponse:
        """
        Run validation and return unified response.

        Subclasses implement this to orchestrate their specific
        validation backends.

        Args:
            request: Standard validation request
            **kwargs: Additional context (e.g. injected dependencies)

        Returns:
            Unified ValidationResponse
        """
        ...

    def build_response(
        self,
        backend_result: dict[str, Any],
        request: ValidationRequest | None = None,
    ) -> ValidationResponse:
        """
        Build a ValidationResponse from a raw backend result dict.

        Automatically categorizes errors into subsections.

        Args:
            backend_result: Dict from validation backend with
                valid, errors, warnings, score, fixed_yaml/fixed_content, fixes_applied
            request: Original request (for setting performed flags)

        Returns:
            Structured ValidationResponse
        """
        errors = backend_result.get("errors", [])
        categorized = categorize_errors(errors, self.error_categories)

        subsections: dict[str, ValidationSubsection] = {}
        for category_name in self.error_categories:
            cat_errors = categorized.get(category_name, [])
            performed = True
            if request:
                if category_name == "entity":
                    performed = request.validate_entities
                elif category_name == "service":
                    performed = request.validate_services
            subsections[f"{category_name}_validation"] = ValidationSubsection(
                performed=performed,
                passed=len(cat_errors) == 0,
                errors=cat_errors,
            )

        return ValidationResponse(
            valid=backend_result.get("valid", False),
            errors=errors,
            warnings=backend_result.get("warnings", []),
            score=backend_result.get("score", 0.0),
            fixed_content=backend_result.get("fixed_yaml")
            or backend_result.get("fixed_content"),
            fixes_applied=backend_result.get("fixes_applied", []),
            subsections=subsections,
        )
