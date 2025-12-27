# Top 10 Improvements from Home Assistant Patterns

**Created:** December 2025  
**Source:** Home Assistant Core (https://github.com/home-assistant/core)  
**Focus:** Suggestions, Automation, and Code Logic Improvements

---

## Overview

After reviewing Home Assistant's codebase architecture, patterns, and implementation practices, here are ten key improvements that could enhance HomeIQ's automation system, code quality, and architectural patterns.

---

## 1. **Formal State Machine Pattern for Connection & Service Management**

### Home Assistant Pattern
Home Assistant uses explicit state machines for entity states, connection management, and service lifecycle. States are clearly defined with transition rules.

### Current HomeIQ State
- Connection managers use basic state tracking (connected/disconnected/running)
- No formal state machine validation or transition rules
- States are implicit in boolean flags

### Improvement
Implement explicit state machines using Python `enum` and state transition validation:

```python
from enum import Enum
from typing import Optional, Callable

class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    AUTHENTICATING = "authenticating"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"

class StateMachine:
    """Enforces valid state transitions"""
    
    VALID_TRANSITIONS = {
        ConnectionState.DISCONNECTED: [ConnectionState.CONNECTING],
        ConnectionState.CONNECTING: [ConnectionState.AUTHENTICATING, ConnectionState.FAILED],
        ConnectionState.AUTHENTICATING: [ConnectionState.CONNECTED, ConnectionState.FAILED],
        ConnectionState.CONNECTED: [ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED],
        ConnectionState.RECONNECTING: [ConnectionState.CONNECTING, ConnectionState.FAILED],
        ConnectionState.FAILED: [ConnectionState.RECONNECTING]
    }
    
    def transition(self, from_state: ConnectionState, to_state: ConnectionState) -> bool:
        if to_state not in self.VALID_TRANSITIONS.get(from_state, []):
            raise InvalidStateTransition(f"Cannot transition from {from_state} to {to_state}")
        return True
```

**Benefits:**
- Prevents invalid state transitions
- Makes state management explicit and testable
- Easier debugging and monitoring
- Can be applied to automation execution states, entity states, service lifecycle

**Application:**
- `ConnectionManager` state transitions
- `BatchProcessor` processing states
- `AsyncEventProcessor` worker states
- Automation execution states (idle/running/paused/error)

---

## 2. **Template System for Dynamic Automation Values**

### Home Assistant Pattern
Home Assistant uses Jinja2 templates extensively for dynamic values in automations, scripts, and conditions. Templates can access entity states, time, context, etc.

### Current HomeIQ State
- Automation YAML is static (generated once)
- No dynamic template evaluation in generated automations
- Limited ability to use real-time values

### Improvement
Implement a template evaluation engine for automation generation and runtime:

```python
from jinja2 import Environment, Template, StrictUndefined

class TemplateEngine:
    """Template evaluation engine for dynamic automation values"""
    
    def __init__(self, ha_client: HomeAssistantClient):
        self.ha_client = ha_client
        self.env = Environment(
            undefined=StrictUndefined,
            autoescape=False
        )
        
    async def render_automation(self, automation_yaml: str, context: Dict[str, Any]) -> str:
        """Render automation YAML with template variables"""
        template = self.env.from_string(automation_yaml)
        return template.render(
            states=self._get_states_proxy(),
            time=self._get_time_proxy(),
            now=self._get_now_proxy(),
            **context
        )
    
    def _get_states_proxy(self):
        """Return proxy object for state access (states.entity_id)"""
        return StateProxy(self.ha_client)
```

**Example Usage:**
```yaml
# Generate automation with template
triggers:
  - trigger: state
    entity_id: sensor.temperature
    above: "{{ states('sensor.temp_threshold') | float }}"
    
actions:
  - action: climate.set_temperature
    target:
      entity_id: climate.living_room
    data:
      temperature: "{{ states('sensor.temperature') | float + 2 }}"
```

**Benefits:**
- Dynamic automations that adapt to current state
- More intelligent automation generation
- Better user experience (automations work with current context)
- Enables advanced patterns like adaptive thresholds

**Application:**
- AI automation generation (add template support to generated YAML)
- Automation refinement (suggest template improvements)
- Runtime automation validation (pre-validate templates)

---

## 3. **Enhanced Entity Registry with Relationship Tracking**

### Home Assistant Pattern
Home Assistant maintains a comprehensive entity registry with:
- Device → Entity relationships (one device, multiple entities)
- Entity → Area relationships (spatial organization)
- Entity → Config Entry relationships (source tracking)
- Metadata: manufacturer, model, sw_version, via_device

### Current HomeIQ State
- Basic entity storage in SQLite
- Device/entity relationships exist but not fully utilized
- Limited metadata tracking
- No config entry tracking

### Improvement
Extend entity registry with full relationship graph:

```python
@dataclass
class EntityRegistryEntry:
    """Comprehensive entity registry entry"""
    entity_id: str
    unique_id: str
    name: Optional[str]
    device_id: Optional[str]  # Links to device
    area_id: Optional[str]    # Links to area
    config_entry_id: Optional[str]  # Source tracking
    
    # Metadata
    platform: str
    domain: str
    manufacturer: Optional[str]
    model: Optional[str]
    sw_version: Optional[str]
    via_device: Optional[str]  # Parent device
    
    # Relationships
    related_entities: List[str]  # Siblings from same device
    capabilities: Dict[str, Any]
    
class EntityRegistry:
    """Entity registry with relationship queries"""
    
    async def get_entities_by_device(self, device_id: str) -> List[EntityRegistryEntry]:
        """Get all entities for a device"""
        
    async def get_device_for_entity(self, entity_id: str) -> Optional[DeviceEntry]:
        """Get device for an entity"""
        
    async def get_sibling_entities(self, entity_id: str) -> List[EntityRegistryEntry]:
        """Get entities from same device"""
        
    async def get_entities_in_area(self, area_id: str) -> List[EntityRegistryEntry]:
        """Get all entities in an area"""
```

**Benefits:**
- Better automation suggestions (understand device capabilities)
- Richer entity resolution (suggest related entities)
- Improved pattern detection (device-level patterns)
- Better debugging (track entity source/config)

**Application:**
- Device intelligence service
- AI automation generation (better entity suggestions)
- Pattern detection (device-level patterns)
- Discovery service enhancement

---

## 4. **Event Bus/Dispatcher Pattern for Decoupled Communication**

### Home Assistant Pattern
Home Assistant uses a central event bus (`homeassistant.bus.EventBus`) where all events are dispatched. Components subscribe to specific event types.

### Current HomeIQ State
- Direct event processing in `AsyncEventProcessor`
- Handlers registered directly
- Tight coupling between event producer and consumer

### Improvement
Implement an event bus for decoupled event communication:

```python
from typing import Dict, List, Callable, Any
from collections import defaultdict
import asyncio

class EventBus:
    """Central event bus for decoupled event communication"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._async_listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._event_history: deque = deque(maxlen=1000)
    
    def fire(self, event_type: str, event_data: Dict[str, Any]):
        """Fire a synchronous event"""
        self._event_history.append({
            'time': datetime.now(),
            'event_type': event_type,
            'event_data': event_data
        })
        for listener in self._listeners.get(event_type, []):
            try:
                listener(event_data)
            except Exception as e:
                logger.error(f"Error in event listener: {e}")
    
    async def async_fire(self, event_type: str, event_data: Dict[str, Any]):
        """Fire an asynchronous event"""
        self._event_history.append({
            'time': datetime.now(),
            'event_type': event_type,
            'event_data': event_data
        })
        tasks = [
            listener(event_data)
            for listener in self._async_listeners.get(event_type, [])
        ]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def listen(self, event_type: str, listener: Callable):
        """Subscribe to event type"""
        self._listeners[event_type].append(listener)
    
    def async_listen(self, event_type: str, listener: Callable):
        """Subscribe to event type (async)"""
        self._async_listeners[event_type].append(listener)
```

**Benefits:**
- Decoupled components (services don't need direct references)
- Easier testing (mock event bus)
- Better observability (all events in one place)
- Plugin/extensibility support (add new listeners without changing core)

**Application:**
- WebSocket ingestion → Event bus → Multiple consumers
- Service-to-service communication (replace direct HTTP calls)
- Plugin system (external services can subscribe)
- Testing (capture all events)

---

## 5. **Condition Evaluation Engine with AND/OR/NOT Logic**

### Home Assistant Pattern
Home Assistant has a sophisticated condition system with:
- AND/OR/NOT logic operators
- Nested conditions
- Template conditions
- State conditions with time-based evaluation
- Numeric state conditions

### Current HomeIQ State
- Basic condition validation in automation YAML
- Limited condition evaluation
- No runtime condition checking

### Improvement
Implement a condition evaluation engine:

```python
class ConditionEvaluator:
    """Evaluates automation conditions with AND/OR/NOT logic"""
    
    async def evaluate(
        self,
        condition: Union[Dict, List[Dict]],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate condition(s) with AND/OR/NOT logic"""
        
        if isinstance(condition, list):
            # Default to AND logic for list
            return all(await self.evaluate(c, context) for c in condition)
        
        if isinstance(condition, dict):
            # Check for logic operator
            if 'condition' in condition:
                op = condition['condition']
                
                if op == 'and':
                    conditions = condition.get('conditions', [])
                    return all(await self.evaluate(c, context) for c in conditions)
                
                elif op == 'or':
                    conditions = condition.get('conditions', [])
                    return any(await self.evaluate(c, context) for c in conditions)
                
                elif op == 'not':
                    sub_condition = condition.get('conditions', [])
                    result = await self.evaluate(sub_condition, context)
                    return not result
                
                else:
                    # Specific condition type
                    return await self._evaluate_specific_condition(condition, context)
        
        return False
    
    async def _evaluate_specific_condition(
        self,
        condition: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Evaluate specific condition type"""
        condition_type = condition.get('condition')
        
        if condition_type == 'state':
            return await self._evaluate_state_condition(condition, context)
        elif condition_type == 'numeric_state':
            return await self._evaluate_numeric_state_condition(condition, context)
        elif condition_type == 'time':
            return await self._evaluate_time_condition(condition, context)
        elif condition_type == 'template':
            return await self._evaluate_template_condition(condition, context)
        # ... more condition types
        
        return False
```

**Benefits:**
- More sophisticated automation conditions
- Better automation suggestions (suggest complex conditions)
- Runtime condition validation
- Test automation conditions without deploying

**Application:**
- AI automation generation (generate complex conditions)
- Automation testing (validate conditions)
- Automation refinement (improve condition logic)

---

## 6. **Action Queuing and Execution Engine with Retry Logic**

### Home Assistant Pattern
Home Assistant queues actions and executes them with:
- Retry logic for failed actions
- Delay support (time-based and wait-for-trigger)
- Parallel action execution
- Action sequences with error handling

### Current HomeIQ State
- Actions are generated as YAML but not executed/tested by HomeIQ
- No action queuing system
- Limited retry logic in external API calls

### Improvement
Implement an action execution engine with queuing and retry:

```python
class ActionExecutor:
    """Executes automation actions with queuing and retry"""
    
    def __init__(self, ha_client: HomeAssistantClient):
        self.ha_client = ha_client
        self.action_queue: asyncio.Queue = asyncio.Queue()
        self.executor_workers: List[asyncio.Task] = []
        self.max_retries = 3
        self.retry_delay = 1.0
    
    async def queue_action(
        self,
        action: Dict[str, Any],
        context: Dict[str, Any],
        retry_on_failure: bool = True
    ):
        """Queue an action for execution"""
        action_item = {
            'action': action,
            'context': context,
            'retry_on_failure': retry_on_failure,
            'attempts': 0,
            'queued_at': datetime.now()
        }
        await self.action_queue.put(action_item)
    
    async def _execute_worker(self):
        """Worker that executes actions from queue"""
        while True:
            try:
                action_item = await self.action_queue.get()
                success = await self._execute_action_with_retry(action_item)
                if not success and action_item['retry_on_failure']:
                    # Re-queue for retry
                    if action_item['attempts'] < self.max_retries:
                        action_item['attempts'] += 1
                        await asyncio.sleep(self.retry_delay * action_item['attempts'])
                        await self.action_queue.put(action_item)
                self.action_queue.task_done()
            except asyncio.CancelledError:
                break
    
    async def _execute_action_with_retry(self, action_item: Dict[str, Any]) -> bool:
        """Execute action with retry logic"""
        action = action_item['action']
        
        try:
            # Handle delay action
            if 'delay' in action:
                delay = self._parse_delay(action['delay'])
                await asyncio.sleep(delay)
            
            # Handle parallel actions
            if 'parallel' in action:
                tasks = [
                    self._execute_single_action(a, action_item['context'])
                    for a in action['parallel']
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                return all(not isinstance(r, Exception) for r in results)
            
            # Handle sequence
            if 'sequence' in action:
                for a in action['sequence']:
                    success = await self._execute_single_action(a, action_item['context'])
                    if not success:
                        return False
                return True
            
            # Single action
            return await self._execute_single_action(action, action_item['context'])
            
        except Exception as e:
            logger.error(f"Action execution failed: {e}")
            return False
```

**Benefits:**
- Test automation actions before deployment
- Better error handling and retry logic
- Support for complex action patterns (parallel, sequence, delay)
- Action execution metrics

**Application:**
- Automation testing (test actions without deploying to HA)
- AI automation service (validate actions)
- Automation refinement (suggest action improvements)

---

## 7. **Configuration Schema Validation with Pydantic**

### Home Assistant Pattern
Home Assistant uses comprehensive configuration validation:
- Platform config schemas
- Integration config schemas
- Automation config schemas
- Runtime validation with clear error messages

### Current HomeIQ State
- Basic YAML validation
- Pydantic models for some contracts (AutomationPlan)
- Limited runtime configuration validation
- Error messages could be clearer

### Improvement
Extend Pydantic-based validation with comprehensive schemas:

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Union, List

class TriggerConfig(BaseModel):
    """Trigger configuration with validation"""
    platform: Literal[
        "state", "time", "time_pattern", "numeric_state", 
        "sun", "event", "mqtt", "webhook", "zone"
    ]
    entity_id: Optional[Union[str, List[str]]] = None
    to: Optional[Union[str, List[str]]] = None
    from_: Optional[Union[str, List[str]]] = Field(None, alias="from")
    
    @field_validator('entity_id')
    @classmethod
    def validate_entity_id(cls, v):
        if isinstance(v, str):
            # Validate entity ID format
            if '.' not in v:
                raise ValueError(f"Invalid entity_id format: {v}")
        return v
    
    @model_validator(mode='after')
    def validate_trigger_fields(self):
        """Validate platform-specific required fields"""
        if self.platform == 'state' and not self.entity_id:
            raise ValueError("state trigger requires entity_id")
        if self.platform == 'time' and 'at' not in self.model_dump(exclude_unset=True):
            raise ValueError("time trigger requires 'at' field")
        return self

class AutomationConfig(BaseModel):
    """Complete automation configuration with validation"""
    id: Optional[str] = None
    alias: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    mode: Literal["single", "restart", "queued", "parallel"] = "single"
    triggers: List[TriggerConfig] = Field(..., min_length=1)
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(..., min_length=1)
    
    @field_validator('triggers')
    @classmethod
    def validate_triggers(cls, v):
        if not v:
            raise ValueError("Automation must have at least one trigger")
        return v
    
    @model_validator(mode='after')
    def validate_automation(self):
        """Cross-field validation"""
        # Check for circular dependencies
        # Validate entity references
        # Check for unsafe patterns
        return self
```

**Benefits:**
- Catch configuration errors early
- Clear error messages
- Type safety
- Better IDE support
- Validation can be reused in multiple places

**Application:**
- Automation generation (validate before sending to HA)
- Configuration files (validate service configs)
- API endpoints (validate request payloads)

---

## 8. **Integration Quality Scale for Services**

### Home Assistant Pattern
Home Assistant uses an Integration Quality Scale:
- Bronze, Silver, Gold, Platinum tiers
- Criteria: code quality, documentation, tests, user experience
- Encourages continuous improvement

### Current HomeIQ State
- Services are developed independently
- No formal quality metrics
- Limited documentation standards enforcement
- Testing coverage varies

### Improvement
Implement a service quality scale:

```python
from dataclasses import dataclass
from typing import List
from enum import Enum

class QualityTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"

@dataclass
class QualityMetrics:
    """Service quality metrics"""
    service_name: str
    
    # Code Quality
    test_coverage: float  # 0-100
    type_hints_coverage: float  # 0-100
    docstring_coverage: float  # 0-100
    
    # Documentation
    has_readme: bool
    has_api_docs: bool
    has_examples: bool
    
    # User Experience
    has_health_endpoint: bool
    has_metrics_endpoint: bool
    error_handling_quality: float  # 0-100
    
    # Testing
    has_unit_tests: bool
    has_integration_tests: bool
    has_performance_tests: bool
    
    def calculate_tier(self) -> QualityTier:
        """Calculate quality tier based on metrics"""
        score = 0
        
        # Bronze requirements (minimum)
        if self.test_coverage >= 50 and self.has_readme:
            score = 1  # Bronze
        
        # Silver requirements
        if (self.test_coverage >= 70 and 
            self.type_hints_coverage >= 80 and 
            self.has_api_docs and
            self.has_health_endpoint):
            score = 2  # Silver
        
        # Gold requirements
        if (self.test_coverage >= 85 and
            self.type_hints_coverage >= 90 and
            self.docstring_coverage >= 80 and
            self.has_integration_tests and
            self.error_handling_quality >= 80):
            score = 3  # Gold
        
        # Platinum requirements
        if (self.test_coverage >= 95 and
            self.type_hints_coverage >= 100 and
            self.docstring_coverage >= 90 and
            self.has_performance_tests and
            self.error_handling_quality >= 95):
            score = 4  # Platinum
        
        tiers = [
            QualityTier.BRONZE,
            QualityTier.SILVER,
            QualityTier.GOLD,
            QualityTier.PLATINUM
        ]
        return tiers[min(score, 3)]

class QualityAuditor:
    """Audits service quality and suggests improvements"""
    
    async def audit_service(self, service_name: str) -> QualityMetrics:
        """Audit service and return metrics"""
        # Run code analysis
        # Check documentation
        # Analyze tests
        # Review error handling
        pass
    
    def suggest_improvements(self, metrics: QualityMetrics) -> List[str]:
        """Suggest improvements to reach next tier"""
        suggestions = []
        tier = metrics.calculate_tier()
        
        if tier == QualityTier.BRONZE:
            if metrics.test_coverage < 70:
                suggestions.append(f"Increase test coverage to 70% (currently {metrics.test_coverage}%)")
            if metrics.type_hints_coverage < 80:
                suggestions.append(f"Add type hints to {100 - metrics.type_hints_coverage}% of functions")
        # ... more suggestions
        
        return suggestions
```

**Benefits:**
- Encourage continuous improvement
- Standardize service quality
- Better code quality across all services
- Clear goals for developers

**Application:**
- CI/CD pipeline (quality checks)
- Service documentation (show quality tier)
- Code review (suggest improvements based on tier)

---

## 9. **Supervisor Pattern for Service Lifecycle Management**

### Home Assistant Pattern
Home Assistant Supervisor manages integration lifecycle:
- Start/stop services
- Restart on failure
- Health monitoring
- Dependency management
- Configuration reload

### Current HomeIQ State
- Docker Compose manages service lifecycle
- No programmatic service supervision
- Limited health monitoring
- No automatic restart logic (except Docker restart policies)

### Improvement
Implement a service supervisor for better lifecycle management:

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict
import asyncio

class ServiceState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    FAILED = "failed"
    RESTARTING = "restarting"

@dataclass
class ServiceConfig:
    """Service configuration"""
    name: str
    port: int
    health_check_url: str
    health_check_interval: float = 30.0
    restart_on_failure: bool = True
    max_restart_attempts: int = 3
    restart_delay: float = 5.0
    dependencies: List[str] = None

class ServiceSupervisor:
    """Supervises service lifecycle and health"""
    
    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.service_states: Dict[str, ServiceState] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self.restart_counts: Dict[str, int] = {}
    
    async def register_service(self, config: ServiceConfig):
        """Register a service for supervision"""
        self.services[config.name] = config
        self.service_states[config.name] = ServiceState.STOPPED
        self.restart_counts[config.name] = 0
    
    async def start_service(self, service_name: str):
        """Start a service"""
        config = self.services.get(service_name)
        if not config:
            raise ValueError(f"Service not found: {service_name}")
        
        # Check dependencies
        for dep in config.dependencies or []:
            if self.service_states.get(dep) != ServiceState.RUNNING:
                raise ValueError(f"Service {service_name} depends on {dep} which is not running")
        
        self.service_states[service_name] = ServiceState.STARTING
        
        # Start health check
        self.health_check_tasks[service_name] = asyncio.create_task(
            self._health_check_loop(service_name)
        )
        
        self.service_states[service_name] = ServiceState.RUNNING
    
    async def _health_check_loop(self, service_name: str):
        """Continuously check service health"""
        config = self.services[service_name]
        
        while self.service_states[service_name] in [
            ServiceState.RUNNING,
            ServiceState.STARTING
        ]:
            try:
                healthy = await self._check_health(config)
                
                if not healthy and self.service_states[service_name] == ServiceState.RUNNING:
                    logger.warning(f"Service {service_name} unhealthy")
                    
                    if config.restart_on_failure:
                        if self.restart_counts[service_name] < config.max_restart_attempts:
                            await self._restart_service(service_name)
                        else:
                            self.service_states[service_name] = ServiceState.FAILED
                            logger.error(
                                f"Service {service_name} failed after "
                                f"{config.max_restart_attempts} restart attempts"
                            )
                
                await asyncio.sleep(config.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error for {service_name}: {e}")
                await asyncio.sleep(config.health_check_interval)
    
    async def _restart_service(self, service_name: str):
        """Restart a service"""
        config = self.services[service_name]
        self.restart_counts[service_name] += 1
        
        logger.info(f"Restarting service {service_name} (attempt {self.restart_counts[service_name]})")
        
        self.service_states[service_name] = ServiceState.RESTARTING
        
        # Stop health check
        if service_name in self.health_check_tasks:
            self.health_check_tasks[service_name].cancel()
        
        await asyncio.sleep(config.restart_delay)
        
        # Restart
        await self.start_service(service_name)
```

**Benefits:**
- Better service reliability
- Automatic recovery from failures
- Dependency management
- Health monitoring
- Can be used alongside Docker Compose

**Application:**
- Service orchestration (manage service lifecycle)
- Health monitoring (continuous health checks)
- Failure recovery (automatic restart)

---

## 10. **Enhanced Context Tracking with Full Event History**

### Home Assistant Pattern
Home Assistant tracks context for all events:
- `context_id`: Unique ID for each event chain
- `context_parent_id`: Parent context for nested events
- `context_user_id`: User who triggered the event
- Context is preserved through automation execution

### Current HomeIQ State
- Basic context tracking (context_id, context_parent_id, context_user_id)
- Context stored in InfluxDB
- Limited context querying capabilities
- No context-based event replay

### Improvement
Enhance context tracking with event history and replay:

```python
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
from collections import deque

@dataclass
class EventContext:
    """Enhanced event context with history"""
    context_id: str
    context_parent_id: Optional[str]
    context_user_id: Optional[str]
    events: List[Dict[str, Any]]  # All events in this context
    started_at: datetime
    last_event_at: datetime
    automation_ids: List[str]  # Automations triggered in this context

class ContextTracker:
    """Tracks event contexts with history"""
    
    def __init__(self):
        self.contexts: Dict[str, EventContext] = {}
        self.context_history: deque = deque(maxlen=10000)  # Last 10k contexts
    
    def track_event(
        self,
        event: Dict[str, Any],
        context_id: Optional[str] = None
    ) -> str:
        """Track an event in a context"""
        # Extract context from event
        event_context_id = event.get('context', {}).get('id')
        if context_id:
            event_context_id = context_id
        
        if not event_context_id:
            # Generate new context
            event_context_id = self._generate_context_id()
        
        # Get or create context
        if event_context_id not in self.contexts:
            self.contexts[event_context_id] = EventContext(
                context_id=event_context_id,
                context_parent_id=event.get('context', {}).get('parent_id'),
                context_user_id=event.get('context', {}).get('user_id'),
                events=[],
                started_at=datetime.now(),
                last_event_at=datetime.now(),
                automation_ids=[]
            )
        
        # Add event to context
        context = self.contexts[event_context_id]
        context.events.append(event)
        context.last_event_at = datetime.now()
        
        # Track automation triggers
        if event.get('event_type') == 'automation_triggered':
            automation_id = event.get('data', {}).get('entity_id')
            if automation_id and automation_id not in context.automation_ids:
                context.automation_ids.append(automation_id)
        
        # Archive old contexts
        if len(self.contexts) > 1000:
            oldest = min(self.contexts.values(), key=lambda c: c.last_event_at)
            self.context_history.append(oldest)
            del self.contexts[oldest.context_id]
        
        return event_context_id
    
    def get_context_chain(self, context_id: str) -> List[EventContext]:
        """Get full context chain (parent contexts)"""
        chain = []
        current_id = context_id
        
        while current_id:
            context = self.contexts.get(current_id)
            if not context:
                # Try history
                context = next(
                    (c for c in self.context_history if c.context_id == current_id),
                    None
                )
            
            if context:
                chain.append(context)
                current_id = context.context_parent_id
            else:
                break
        
        return chain
    
    def replay_context(self, context_id: str) -> List[Dict[str, Any]]:
        """Replay all events in a context (for debugging)"""
        chain = self.get_context_chain(context_id)
        events = []
        
        for context in reversed(chain):  # Start from root
            events.extend(context.events)
        
        return events
```

**Benefits:**
- Better debugging (see full event chain)
- Automation testing (replay contexts)
- Better pattern detection (context-aware patterns)
- Audit trail (full event history per context)

**Application:**
- Debugging (replay event chains)
- Automation testing (test with real event contexts)
- Pattern detection (context-aware patterns)
- Analytics (analyze event chains)

---

## Summary

These ten improvements, inspired by Home Assistant's architecture, would significantly enhance HomeIQ's:

1. **Reliability**: State machines, supervisor pattern, enhanced retry logic
2. **Flexibility**: Template system, event bus, condition engine
3. **Maintainability**: Quality scale, schema validation, enhanced registry
4. **Debugging**: Context tracking, event replay, better error messages
5. **User Experience**: Dynamic automations, better suggestions, template support

**Priority Recommendations:**

**High Priority:** ✅ **IMPLEMENTED (November 2025)**
1. ✅ **State Machine Pattern (#1)** - Core reliability improvement
   - **Status:** Implemented and deployed
   - **Location:** `services/websocket-ingestion/src/state_machine.py`
   - **Integration:** ConnectionManager, BatchProcessor, AsyncEventProcessor
   - **Features:** State transition validation, history tracking, force transitions
   - **Test Coverage:** 15/15 tests passing (100%)

2. ✅ **Template System (#2)** - Major UX improvement
   - **Status:** Implemented and deployed
   - **Location:** `services/ai-automation-service/src/template_engine.py`
   - **Features:** Jinja2-based template rendering, Home Assistant-style state access, time functions
   - **Test Coverage:** 17/17 tests passing (100%)

3. ✅ **Condition Evaluation Engine (#5)** - Essential for advanced automations
   - **Status:** Implemented and deployed
   - **Location:** `services/ai-automation-service/src/condition_evaluator.py`
   - **Features:** AND/OR/NOT logic, nested conditions, multiple condition types
   - **Test Coverage:** 25/25 tests passing (100%)

**Medium Priority:**
4. Entity Registry Enhancement (#3) - Better automation suggestions
5. Event Bus Pattern (#4) - Architectural improvement
6. Action Execution Engine (#6) - Better testing capabilities

**Lower Priority (but valuable):**
7. Configuration Schema Validation (#7) - Code quality
8. Quality Scale (#8) - Long-term quality improvement
9. Service Supervisor (#9) - Operational improvement
10. Enhanced Context Tracking (#10) - Debugging improvement

---

**Implementation Summary (November 2025):**

All three high-priority improvements have been successfully implemented, tested, and deployed:

- **Total Tests:** 57 tests across 3 modules
- **Test Results:** 57/57 passing (100% pass rate)
- **Code Coverage:** State Machine (95%), Template Engine (81%), Condition Evaluator (64%)
- **Dependencies:** Updated to 2025-compatible versions
- **Deployment Status:** ✅ Deployed to local Docker, services healthy
- **Documentation:** Architecture documentation updated

**Next Steps:**
1. ✅ ~~Prioritize improvements based on current needs~~ - COMPLETE
2. ✅ ~~Create implementation stories/epics for selected improvements~~ - COMPLETE
3. ✅ ~~Start with high-priority items that provide immediate value~~ - COMPLETE
4. Consider medium-priority items for future enhancements

