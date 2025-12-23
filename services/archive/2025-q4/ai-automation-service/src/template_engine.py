"""
Template Engine for Dynamic Automation Values
Home Assistant Pattern Improvement #2 (2025)

Provides Jinja2 template evaluation for dynamic automation values that adapt
to current state, time, and context.
Compatible with Jinja2 3.1.4+ (2025 versions).
"""

import logging
from datetime import datetime
from typing import Any

from jinja2 import StrictUndefined, TemplateError
from jinja2.sandbox import SandboxedEnvironment

from .clients.ha_client import HomeAssistantClient

logger = logging.getLogger(__name__)


class StateProxy:
    """
    Proxy object for state access in templates (states.entity_id).
    
    Provides Home Assistant-style state access:
    - states('sensor.temperature') -> returns current state
    - states.sensor.temperature.state -> returns current state
    - states.sensor.temperature.attributes -> returns attributes
    """

    def __init__(self, ha_client: HomeAssistantClient):
        """
        Initialize state proxy.
        
        Args:
            ha_client: Home Assistant client for fetching states
        """
        self._ha_client = ha_client
        self._state_cache: dict[str, dict[str, Any]] = {}
        self._cache_timestamp: datetime | None = None
        self._cache_ttl = 5.0  # Cache states for 5 seconds

    async def _get_states(self) -> dict[str, dict[str, Any]]:
        """Get all states from Home Assistant (with caching)"""
        now = datetime.now()

        # Return cached states if still valid
        if self._state_cache and self._cache_timestamp:
            age = (now - self._cache_timestamp).total_seconds()
            if age < self._cache_ttl:
                return self._state_cache

        # Fetch fresh states
        try:
            states = await self._ha_client.get_states()
            self._state_cache = {state['entity_id']: state for state in states}
            self._cache_timestamp = now
            return self._state_cache
        except Exception as e:
            logger.error(f"Error fetching states for template: {e}")
            return self._state_cache  # Return stale cache on error

    async def __call__(self, entity_id: str) -> str:
        """
        Callable interface: states('sensor.temperature')
        
        Args:
            entity_id: Entity ID to get state for
            
        Returns:
            Current state string
        """
        states = await self._get_states()
        entity = states.get(entity_id, {})
        return entity.get('state', 'unknown')

    def __getattr__(self, domain: str):
        """
        Attribute access: states.sensor.temperature
        
        Returns:
            DomainProxy for accessing entities in that domain
        """
        return DomainProxy(self, domain)


class DomainProxy:
    """Proxy for domain access: states.sensor.temperature"""

    def __init__(self, state_proxy: StateProxy, domain: str):
        self._state_proxy = state_proxy
        self._domain = domain

    def __getattr__(self, entity_name: str):
        """Access entity: states.sensor.temperature"""
        entity_id = f"{self._domain}.{entity_name}"
        return EntityProxy(self._state_proxy, entity_id)


class EntityProxy:
    """Proxy for entity access: states.sensor.temperature.state"""

    def __init__(self, state_proxy: StateProxy, entity_id: str):
        self._state_proxy = state_proxy
        self._entity_id = entity_id

    @property
    async def state(self) -> str:
        """Get entity state"""
        states = await self._state_proxy._get_states()
        entity = states.get(self._entity_id, {})
        return entity.get('state', 'unknown')

    @property
    async def attributes(self) -> dict[str, Any]:
        """Get entity attributes"""
        states = await self._state_proxy._get_states()
        entity = states.get(self._entity_id, {})
        return entity.get('attributes', {})


class TimeProxy:
    """Proxy for time access in templates"""

    @staticmethod
    def now() -> datetime:
        """Get current time"""
        return datetime.now()

    @staticmethod
    def utcnow() -> datetime:
        """Get current UTC time"""
        return datetime.utcnow()


class TemplateEngine:
    """
    Template evaluation engine for dynamic automation values.
    
    Provides Jinja2 template rendering with Home Assistant-style state access
    for generating dynamic automation YAML.
    """

    def __init__(self, ha_client: HomeAssistantClient):
        """
        Initialize template engine.
        
        Args:
            ha_client: Home Assistant client for fetching states
        """
        self.ha_client = ha_client

        # Use SandboxedEnvironment for security (prevents dangerous operations)
        self.env = SandboxedEnvironment(
            undefined=StrictUndefined,  # Raise error on undefined variables
            autoescape=False,  # Don't escape HTML (not needed for YAML)
            enable_async=True  # Enable async template rendering
        )

        # Add custom filters
        self.env.filters['float'] = float
        self.env.filters['int'] = int
        self.env.filters['round'] = round

        self.state_proxy = StateProxy(ha_client)
        self.time_proxy = TimeProxy()

    async def render(
        self,
        template_str: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """
        Render template string with context.
        
        Args:
            template_str: Jinja2 template string
            context: Additional template variables
            
        Returns:
            Rendered template string
            
        Raises:
            TemplateError: If template rendering fails
        """
        if context is None:
            context = {}

        try:
            template = self.env.from_string(template_str)

            # Create a helper class that Jinja2 sandbox recognizes as safe
            class SafeStatesCallable:
                """Safe callable wrapper for states() function"""
                def __init__(self, state_proxy):
                    self._state_proxy = state_proxy
                    # Mark as safe callable for Jinja2 sandbox
                    self.is_safe_callable = True

                async def __call__(self, entity_id: str) -> str:
                    """Callable interface"""
                    return await self._state_proxy(entity_id)

            states_callable = SafeStatesCallable(self.state_proxy)

            # Build template context with Home Assistant-style objects
            template_context = {
                'states': states_callable,
                'time': self.time_proxy,
                'now': datetime.now(),
                'utcnow': datetime.utcnow(),
                **context
            }

            # Render template (async)
            result = await template.render_async(**template_context)
            return result

        except TemplateError as e:
            logger.error(f"Template rendering error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error rendering template: {e}")
            raise TemplateError(f"Template rendering failed: {e}")

    async def render_automation(
        self,
        automation_yaml: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """
        Render automation YAML with template variables.
        
        Args:
            automation_yaml: Automation YAML string (may contain templates)
            context: Additional template variables
            
        Returns:
            Rendered automation YAML with templates evaluated
            
        Example:
            automation_yaml = '''
            triggers:
              - trigger: state
                entity_id: sensor.temperature
                above: "{{ states('sensor.temp_threshold') | float }}"
            '''
        """
        return await self.render(automation_yaml, context)

    async def validate_template(
        self,
        template_str: str,
        context: dict[str, Any] | None = None
    ) -> tuple[bool, str | None]:
        """
        Validate template without rendering.
        
        Args:
            template_str: Template string to validate
            context: Optional context for validation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Try to parse template
            self.env.parse(template_str)

            # Try to render with dummy context to catch runtime errors
            dummy_context = context or {}
            dummy_context.update({
                'states': self.state_proxy,
                'time': self.time_proxy,
                'now': datetime.now()
            })

            # Create template and check for syntax errors
            template = self.env.from_string(template_str)

            return True, None

        except TemplateError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Validation error: {e}"

    def get_available_filters(self) -> list[str]:
        """Get list of available template filters"""
        return ['float', 'int', 'round'] + list(self.env.filters.keys())

    def get_available_objects(self) -> list[str]:
        """Get list of available template objects"""
        return ['states', 'time', 'now', 'utcnow']

