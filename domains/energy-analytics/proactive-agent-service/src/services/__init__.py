"""Services for Proactive Agent Service.

Lazy imports: some submodules depend on relative imports (e.g.
``..clients.breakers``) that only resolve when the full package tree
is available (inside the Docker container).  Guard with try/except so
that individual submodules (e.g. ``confidence_scorer``) remain
importable from integration tests that add ``src/`` to sys.path.
"""

try:
    from .ai_prompt_generation_service import AIPromptGenerationService
    from .context_analysis_service import ContextAnalysisService
    from .device_validation_service import DeviceValidationService, ValidationResult
    from .prompt_generation_service import PromptGenerationService
    from .suggestion_pipeline_service import SuggestionPipelineService
    from .suggestion_storage_service import SuggestionStorageService
except ImportError:
    pass

__all__ = [
    "DeviceValidationService",
    "ValidationResult",
    "AIPromptGenerationService",
    "ContextAnalysisService",
    "PromptGenerationService",
    "SuggestionStorageService",
    "SuggestionPipelineService",
]