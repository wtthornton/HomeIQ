"""
Service Container for Dependency Injection

Centralized container for all services used in the conversation system.
Replaces global variables with proper dependency injection pattern.

Created: Phase 1 - Architecture & Database Design
"""

import logging
from typing import Any, Optional

from ..clients.device_intelligence_client import DeviceIntelligenceClient
from ..clients.ha_client import HomeAssistantClient
from ..config import settings
from ..llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Centralized dependency injection container.
    
    Provides lazy-loaded singleton instances of all services.
    Thread-safe singleton pattern.
    """

    _instance: Optional['ServiceContainer'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Lazy-loaded services (initialized on first access)
        self._ha_client: HomeAssistantClient | None = None
        self._openai_client: OpenAIClient | None = None
        self._device_intelligence: DeviceIntelligenceClient | None = None

        # Entity services (will be initialized when entity module is created)
        self._entity_extractor: Any | None = None
        self._entity_validator: Any | None = None
        self._entity_enricher: Any | None = None
        self._entity_resolver: Any | None = None

        # Automation services (will be initialized when automation module is created)
        self._yaml_generator: Any | None = None
        self._yaml_validator: Any | None = None
        self._yaml_corrector: Any | None = None
        self._test_executor: Any | None = None
        self._deployer: Any | None = None
        self._action_executor: Any | None = None

        # Conversation services (will be initialized when conversation module is created)
        self._context_manager: Any | None = None
        self._intent_matcher: Any | None = None
        self._response_builder: Any | None = None
        self._history_manager: Any | None = None

        # Confidence and error handling
        self._confidence_calculator: Any | None = None
        self._error_recovery: Any | None = None

        # Function calling
        self._function_registry: Any | None = None

        # Device context
        self._device_context_service: Any | None = None

        # In-memory stores (could move to Redis later)
        self._conversation_contexts: dict[str, Any] = {}

        self._initialized = True
        logger.info("✅ ServiceContainer initialized")

    @property
    def ha_client(self) -> HomeAssistantClient:
        """Get or create Home Assistant client"""
        if self._ha_client is None:
            if not settings.ha_url or not settings.ha_token:
                raise ValueError("HA URL and token must be configured")
            self._ha_client = HomeAssistantClient(
                ha_url=settings.ha_url,
                access_token=settings.ha_token,
                max_retries=settings.ha_max_retries,
                retry_delay=settings.ha_retry_delay,
                timeout=settings.ha_timeout
            )
            logger.info("✅ HomeAssistantClient initialized")
        return self._ha_client

    @property
    def openai_client(self) -> OpenAIClient:
        """Get or create OpenAI client"""
        if self._openai_client is None:
            if not settings.openai_api_key:
                raise ValueError("OpenAI API key must be configured")
            self._openai_client = OpenAIClient(
                api_key=settings.openai_api_key,
                model=settings.openai_model
            )
            logger.info("✅ OpenAIClient initialized")
        return self._openai_client

    @property
    def device_intelligence(self) -> DeviceIntelligenceClient | None:
        """Get or create Device Intelligence client"""
        if self._device_intelligence is None:
            if settings.device_intelligence_enabled:
                try:
                    self._device_intelligence = DeviceIntelligenceClient(
                        base_url=settings.device_intelligence_url
                    )
                    logger.info("✅ DeviceIntelligenceClient initialized")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to initialize DeviceIntelligenceClient: {e}")
                    return None
        return self._device_intelligence

    # Entity services properties
    @property
    def entity_extractor(self):
        """Get or create entity extractor"""
        if self._entity_extractor is None:
            from .entity.extractor import EntityExtractor
            self._entity_extractor = EntityExtractor(
                device_intelligence_client=self.device_intelligence,
                ha_client=self.ha_client,
                openai_client=self.openai_client,
                # Keep deprecated params for backward compatibility
                openai_api_key=settings.openai_api_key,
                ner_model=settings.ner_model,
                openai_model=settings.openai_model
            )
            logger.info("✅ EntityExtractor initialized (using UnifiedExtractionPipeline)")
        return self._entity_extractor

    @property
    def entity_validator(self):
        """Get or create entity validator"""
        if self._entity_validator is None:
            from ..clients.data_api_client import DataAPIClient
            from .entity.validator import EntityValidator
            self._entity_validator = EntityValidator(
                ha_client=self.ha_client,
                data_api_client=DataAPIClient()
            )
            logger.info("✅ EntityValidator initialized")
        return self._entity_validator

    @property
    def entity_enricher(self):
        """Get or create entity enricher"""
        if self._entity_enricher is None:
            from ..clients.data_api_client import DataAPIClient
            from .entity.enricher import EntityEnricher
            self._entity_enricher = EntityEnricher(
                ha_client=self.ha_client,
                device_intelligence_client=self.device_intelligence,
                data_api_client=DataAPIClient()
            )
            logger.info("✅ EntityEnricher initialized")
        return self._entity_enricher

    @property
    def entity_resolver(self):
        """Get or create entity resolver"""
        if self._entity_resolver is None:
            from ..clients.data_api_client import DataAPIClient
            from .entity.resolver import EntityResolver

            # Try to get RAG client if available (optional)
            rag_client = None
            try:
                # RAG client requires database session, so we'll get it on-demand
                # For now, pass None and let EntityResolver work without RAG
                # RAG can be added later when database session is available
                pass
            except Exception:
                pass

            self._entity_resolver = EntityResolver(
                ha_client=self.ha_client,
                data_api_client=DataAPIClient(),
                rag_client=rag_client  # None for now, can be set later
            )
            logger.info("✅ EntityResolver initialized")
        return self._entity_resolver

    # Automation services properties
    @property
    def yaml_generator(self):
        """Get or create YAML generator"""
        if self._yaml_generator is None:
            from .automation.yaml_generator import AutomationYAMLGenerator
            self._yaml_generator = AutomationYAMLGenerator(
                openai_client=self.openai_client,
                ha_client=self.ha_client
            )
            logger.info("✅ AutomationYAMLGenerator initialized")
        return self._yaml_generator

    @property
    def yaml_validator(self):
        """Get or create YAML validator"""
        if self._yaml_validator is None:
            from .automation.yaml_validator import AutomationYAMLValidator
            self._yaml_validator = AutomationYAMLValidator(
                ha_client=self.ha_client
            )
            logger.info("✅ AutomationYAMLValidator initialized")
        return self._yaml_validator

    @property
    def yaml_corrector(self):
        """Get or create YAML corrector"""
        if self._yaml_corrector is None:

            from .automation.yaml_corrector import AutomationYAMLCorrector
            # Get AsyncOpenAI client from OpenAIClient wrapper
            async_openai = self.openai_client.client if hasattr(self.openai_client, 'client') else None
            if async_openai is None:
                raise ValueError("OpenAI client not properly initialized")
            self._yaml_corrector = AutomationYAMLCorrector(
                openai_client=async_openai,
                ha_client=self.ha_client,
                device_intelligence_client=self.device_intelligence
            )
            logger.info("✅ AutomationYAMLCorrector initialized")
        return self._yaml_corrector

    @property
    def test_executor(self):
        """Get or create test executor"""
        if self._test_executor is None:
            from .automation.test_executor import AutomationTestExecutor
            # Pass action_executor to test_executor for direct action execution
            action_executor = self.action_executor
            self._test_executor = AutomationTestExecutor(
                ha_client=self.ha_client,
                action_executor=action_executor
            )
            logger.info("✅ AutomationTestExecutor initialized")
        return self._test_executor

    @property
    def deployer(self):
        """Get or create deployer"""
        if self._deployer is None:
            from .automation.deployer import AutomationDeployer
            self._deployer = AutomationDeployer(
                ha_client=self.ha_client
            )
            logger.info("✅ AutomationDeployer initialized")
        return self._deployer

    @property
    def action_executor(self):
        """Get or create action executor"""
        if self._action_executor is None:
            from ..config import settings
            from ..template_engine import TemplateEngine
            from .automation.action_executor import ActionExecutor

            # Create template engine for action executor
            template_engine = TemplateEngine(ha_client=self.ha_client)

            # Initialize action executor
            self._action_executor = ActionExecutor(
                ha_client=self.ha_client,
                template_engine=template_engine,
                num_workers=getattr(settings, 'action_executor_workers', 2),
                max_retries=getattr(settings, 'action_executor_max_retries', 3),
                retry_delay=getattr(settings, 'action_executor_retry_delay', 1.0)
            )
            logger.info("✅ ActionExecutor initialized")
        return self._action_executor

    # Conversation services properties
    @property
    def context_manager(self):
        """Get or create conversation context manager"""
        if self._context_manager is None:
            from .conversation.context_manager import ConversationContextManager
            self._context_manager = ConversationContextManager()
            logger.info("✅ ConversationContextManager initialized")
        return self._context_manager

    @property
    def intent_matcher(self):
        """Get or create intent matcher"""
        if self._intent_matcher is None:
            from .conversation.intent_matcher import IntentMatcher
            self._intent_matcher = IntentMatcher()
            logger.info("✅ IntentMatcher initialized")
        return self._intent_matcher

    @property
    def response_builder(self):
        """Get or create response builder"""
        if self._response_builder is None:
            from .conversation.response_builder import ResponseBuilder
            self._response_builder = ResponseBuilder()
            logger.info("✅ ResponseBuilder initialized")
        return self._response_builder

    @property
    def history_manager(self):
        """Get or create history manager"""
        if self._history_manager is None:
            from .conversation.history_manager import HistoryManager
            self._history_manager = HistoryManager()
            logger.info("✅ HistoryManager initialized")
        return self._history_manager

    # Confidence and error handling
    @property
    def confidence_calculator(self):
        """Get or create confidence calculator"""
        if self._confidence_calculator is None:
            from .confidence.calculator import EnhancedConfidenceCalculator
            self._confidence_calculator = EnhancedConfidenceCalculator()
            logger.info("✅ EnhancedConfidenceCalculator initialized")
        return self._confidence_calculator

    @property
    def error_recovery(self):
        """Get or create error recovery service"""
        if self._error_recovery is None:
            from .error_recovery import ErrorRecoveryService
            self._error_recovery = ErrorRecoveryService()
            logger.info("✅ ErrorRecoveryService initialized")
        return self._error_recovery

    # Function calling
    @property
    def function_registry(self):
        """Get or create function registry"""
        if self._function_registry is None:
            from .function_calling.registry import FunctionRegistry
            self._function_registry = FunctionRegistry(ha_client=self.ha_client)
            logger.info("✅ FunctionRegistry initialized")
        return self._function_registry

    # Device context
    @property
    def device_context_service(self):
        """Get or create device context service"""
        if self._device_context_service is None:
            from .device.context_service import DeviceContextService
            self._device_context_service = DeviceContextService(ha_client=self.ha_client)
            logger.info("✅ DeviceContextService initialized")
        return self._device_context_service

    # Conversation context management
    def get_conversation_context(self, conversation_id: str) -> Any | None:
        """Get conversation context from in-memory store"""
        return self._conversation_contexts.get(conversation_id)

    def store_conversation_context(self, conversation_id: str, context: Any):
        """Store conversation context in memory"""
        self._conversation_contexts[conversation_id] = context
        logger.debug(f"Stored context for conversation: {conversation_id}")

    def clear_conversation_context(self, conversation_id: str):
        """Clear conversation context"""
        if conversation_id in self._conversation_contexts:
            del self._conversation_contexts[conversation_id]
            logger.debug(f"Cleared context for conversation: {conversation_id}")

    def reset(self):
        """Reset all services (useful for testing)"""
        self._ha_client = None
        self._openai_client = None
        self._device_intelligence = None
        self._conversation_contexts.clear()
        logger.info("ServiceContainer reset")


def get_service_container() -> ServiceContainer:
    """Dependency function for FastAPI routes"""
    return ServiceContainer()

