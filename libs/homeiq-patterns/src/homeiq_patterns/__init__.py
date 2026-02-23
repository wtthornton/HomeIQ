"""
Reusable Pattern Framework — homeiq-patterns

Epic: Reusable Pattern Framework (Phase 2)
Shared abstractions for the three proven patterns from the Automation Improvements epic.

Patterns:
    - RAGContextService: Keyword-match -> corpus-load -> context-inject
    - RAGContextRegistry: Multi-domain context assembly
    - UnifiedValidationRouter: Orchestrated multi-backend validation
    - PostActionVerifier: Action -> verify -> map-warnings

Install (editable, for development):
    pip install -e shared/patterns/

Install (from git):
    pip install git+https://github.com/<org>/HomeIQ#subdirectory=shared/patterns
"""

try:
    from importlib.metadata import version as _version

    __version__ = _version("homeiq-patterns")
except Exception:
    __version__ = "0.0.0.dev0"

from .post_action_verifier import (
    PostActionVerifier,
    VerificationResult,
    VerificationResultStore,
    VerificationWarning,
)
from .rag_context_registry import RAGContextRegistry
from .rag_context_service import RAGContextService
from .unified_validation_router import (
    UnifiedValidationRouter,
    ValidationBackend,
    ValidationRequest,
    ValidationResponse,
    ValidationSubsection,
    categorize_errors,
    get_error_domain_hints,
)

__all__ = [
    "__version__",
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
