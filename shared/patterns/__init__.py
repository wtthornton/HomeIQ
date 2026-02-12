"""
Reusable Pattern Framework

Epic: Reusable Pattern Framework (Phase 2)
Shared abstractions for the three proven patterns from the Automation Improvements epic.

Patterns:
    - RAGContextService: Keyword-match → corpus-load → context-inject
    - RAGContextRegistry: Multi-domain context assembly
    - UnifiedValidationRouter: Orchestrated multi-backend validation
    - PostActionVerifier: Action → verify → map-warnings
"""

from .rag_context_service import RAGContextService
from .rag_context_registry import RAGContextRegistry
from .unified_validation_router import (
    UnifiedValidationRouter,
    ValidationBackend,
    ValidationRequest,
    ValidationResponse,
    ValidationSubsection,
    categorize_errors,
    get_error_domain_hints,
)
from .post_action_verifier import (
    PostActionVerifier,
    VerificationResult,
    VerificationResultStore,
    VerificationWarning,
)

__all__ = [
    "RAGContextService",
    "RAGContextRegistry",
    "UnifiedValidationRouter",
    "ValidationBackend",
    "ValidationRequest",
    "ValidationResponse",
    "ValidationSubsection",
    "categorize_errors",
    "get_error_domain_hints",
    "PostActionVerifier",
    "VerificationResult",
    "VerificationResultStore",
    "VerificationWarning",
]
