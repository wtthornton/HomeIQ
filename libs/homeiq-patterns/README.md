# Reusable Pattern Framework

**Epic:** Reusable Pattern Framework (Phase 2) + High-Value Domain Extensions (Phase 3) + Platform-Wide Rollout (Phase 4)
**Status:** Complete (All Phases)
**PRD:** `docs/planning/automation-architecture-reusable-patterns-prd.md`

Three proven patterns extracted from the Automation Improvements epic into shared, reusable abstractions, then applied across 8 RAG domains, 5 validation endpoints, and 5 verifiers platform-wide.

### RAG Domains (8)

| Domain | Service | Keywords (sample) |
|--------|---------|-------------------|
| Automation / Sports | AutomationRAGService | team tracker, sports, game day |
| Energy | EnergyRAGService | solar, TOU, battery, kWh, EV |
| Blueprint | BlueprintRAGService | blueprint, template, input |
| Device Setup | DeviceSetupRAGService | Zigbee, Z-Wave, MQTT, Matter |
| Security | SecurityRAGService | camera, motion, lock, alarm |
| Comfort | ComfortRAGService | thermostat, HVAC, climate |
| Scene / Script | SceneScriptRAGService | scene, script, movie night |
| Device Capability | DeviceCapabilityRAGService | WLED, Hue, smart plug |

### Validation Endpoints (5)

| Endpoint | Router | Domain |
|----------|--------|--------|
| `POST /api/v1/automations/validate` | AutomationYamlValidateRouter | Automation YAML |
| `POST /api/v1/blueprints/validate` | BlueprintValidationRouter | Blueprints |
| `POST /api/v1/setup/validate` | SetupValidationRouter | Device setup |
| `POST /api/v1/scenes/validate` | SceneValidationRouter | Scenes |
| `POST /api/v1/scripts/validate` | ScriptValidationRouter | Scripts |

### Verifiers (5)

| Verifier | Domain |
|----------|--------|
| AutomationDeployVerifier | Automation deploy |
| BlueprintDeployVerifier | Blueprint deploy |
| SetupVerifier | Device setup |
| SceneVerifier | Scene creation |
| ScriptVerifier | Script creation |
| TaskExecutionVerifier | API edge task execution |

---

## Pattern A: RAGContextService

**Purpose:** Detect domain intent from user prompt via keyword matching; load domain-specific corpus; inject into LLM prompt as context.

**Module:** `libs/homeiq-patterns/rag_context_service.py`

### Quick Start

```python
from shared.patterns import RAGContextService
from pathlib import Path

class EnergyRAGService(RAGContextService):
    name = "energy"
    keywords = ("solar", "battery", "kWh", "TOU", "peak", "off-peak", "load shift")
    corpus_path = Path(__file__).parent / "data" / "energy_patterns.md"
```

### Interface

| Method | Description |
|--------|-------------|
| `detect_intent(prompt) -> bool` | Check if prompt matches domain keywords |
| `load_corpus() -> str` | Load corpus from file (cached). Override for dynamic corpus |
| `format_context(corpus) -> str` | Format corpus into prompt injection block. Override for custom formatting |
| `get_context(prompt) -> str` | Main entry point: detect + load + format. Returns empty string if no match |

### Extension Points

- **Static corpus:** Set `corpus_path` to a markdown/text file
- **Dynamic corpus:** Override `load_corpus()` to assemble content programmatically
- **Custom formatting:** Override `format_context()` to change the injection block format
- **Multiple domains:** Register multiple services in `RAGContextRegistry`

### Reference Implementation

`domains/automation-core/ha-ai-agent-service/src/services/automation_rag_service.py` — Sports/Team Tracker RAG

---

## RAGContextRegistry

**Purpose:** Manage multiple RAGContextService instances; run all domain detections for a prompt; merge results.

**Module:** `libs/homeiq-patterns/rag_context_registry.py`

### Quick Start

```python
from shared.patterns import RAGContextRegistry

registry = RAGContextRegistry()
registry.register(AutomationRAGService())
registry.register(EnergyRAGService())
registry.register(SecurityRAGService())

# Run all services, get matching contexts
contexts = await registry.get_all_context("shift laundry to off-peak hours")
# Returns: ["...energy patterns..."]

# Or get a single merged string
merged = await registry.get_merged_context("shift laundry to off-peak hours")
```

### Interface

| Method | Description |
|--------|-------------|
| `register(service)` | Add a RAGContextService instance |
| `unregister(name) -> bool` | Remove a service by name |
| `services` | Read-only list of registered services |
| `get_all_context(prompt) -> list[str]` | Run all services, return matching contexts in registration order |
| `get_merged_context(prompt) -> str` | Convenience: concatenated matching contexts |

### Reference Implementation

`domains/automation-core/ha-ai-agent-service/src/services/context_builder.py` — Registry initialized in `ContextBuilder.initialize()`

---

## Pattern B: UnifiedValidationRouter

**Purpose:** Single HTTP endpoint that orchestrates one or more validation backends and returns a unified, structured response.

**Module:** `libs/homeiq-patterns/unified_validation_router.py`

### Quick Start

```python
from shared.patterns import UnifiedValidationRouter, ValidationRequest, ValidationResponse

class BlueprintValidationRouter(UnifiedValidationRouter):
    domain = "blueprint"
    error_categories = {
        "entity": ("entity", "Entity", "entity_id"),
        "device": ("device", "Device", "device_class"),
    }

    def __init__(self, blueprint_client):
        self.blueprint_client = blueprint_client

    async def run_validation(self, request: ValidationRequest, **kwargs) -> ValidationResponse:
        result = await self.blueprint_client.validate(request.content)
        return self.build_response(result, request)
```

### Models

**ValidationRequest:**
- `content: str` — Content to validate
- `normalize: bool` — Normalize content (default: True)
- `validate_entities: bool` — Validate entity references (default: True)
- `validate_services: bool` — Validate service calls (default: True)

**ValidationResponse:**
- `valid: bool` — Overall validation result
- `errors: list[str]` — All error messages
- `warnings: list[str]` — Warning messages
- `score: float` — Validation score
- `fixed_content: str | None` — Normalized/fixed content
- `fixes_applied: list[str]` — List of fixes applied
- `subsections: dict[str, ValidationSubsection]` — Per-category results

**ValidationSubsection:**
- `performed: bool` — Whether this validation was performed
- `passed: bool` — Whether validation passed
- `errors: list[str]` — Category-specific errors

### Helpers

`categorize_errors(errors, categories)` — Split error list into categories by keyword matching.

### Reference Implementation

`domains/automation-core/ai-automation-service-new/src/api/automation_yaml_validate_router.py` — Automation YAML validation

---

## Pattern C: PostActionVerifier

**Purpose:** After performing an action (deploy, apply, configure), verify the result and surface warnings to users.

**Module:** `libs/homeiq-patterns/post_action_verifier.py`

### Quick Start

```python
from shared.patterns import PostActionVerifier, VerificationResult, VerificationWarning

class BlueprintDeployVerifier(PostActionVerifier):
    def __init__(self, ha_client):
        self.ha_client = ha_client

    async def verify(self, action_result: dict) -> VerificationResult:
        entity_id = action_result["entity_id"]
        state_data = await self.ha_client.get_state(entity_id)
        warnings = self.map_warnings(state_data)
        return VerificationResult(
            success=state_data.get("state") != "unavailable",
            state=state_data.get("state"),
            warnings=warnings,
        )
```

### Models

**VerificationResult:**
- `success: bool` — Whether the action completed successfully
- `state: str | None` — Current state of the target entity
- `warnings: list[VerificationWarning]` — Warnings to surface to the user
- `metadata: dict` — Additional verification data
- `verification_warning: str | None` — (property) First warning message for backward compatibility
- `has_warnings: bool` — (property) True if any warnings exist

**VerificationWarning:**
- `message: str` — Human-readable warning message
- `entity_id: str | None` — Entity that triggered the warning
- `severity: str` — "warning" | "error" | "info"
- `guidance: str | None` — Actionable next steps

### Reference Implementation

`domains/automation-core/ai-automation-service-new/src/services/automation_deploy_verifier.py` — Automation deploy verification

---

## File Map

```
libs/homeiq-patterns/
├── __init__.py                    # Package exports
├── rag_context_service.py         # Pattern A: RAGContextService base class
├── rag_context_registry.py        # RAGContextRegistry for multi-domain assembly
├── unified_validation_router.py   # Pattern B: UnifiedValidationRouter template
├── post_action_verifier.py        # Pattern C: PostActionVerifier interface
├── README.md                      # This file
└── tests/
    ├── __init__.py
    ├── test_rag_context_service.py          # 21 tests (Phase 2)
    ├── test_unified_validation_router.py    # 13 tests (Phase 2)
    ├── test_post_action_verifier.py         # 11 tests (Phase 2)
    ├── test_epic2_rag_services.py           # 30 tests (Phase 3 — Energy, Blueprint, DeviceSetup RAG)
    ├── test_epic2_validation_verifiers.py   # 23 tests (Phase 3 — Validation routers, Verifiers)
    ├── test_epic3_rag_services.py           # 30 tests (Phase 4 — Security, Comfort, SceneScript, DeviceCapability RAG)
    └── test_epic3_validation_verifiers.py   # 24 tests (Phase 4 — Scene/Script validation, Verifiers, Sports blueprint)

Total: 152 tests across all phases

Phase 3 implementations (Epic: High-Value Domain Extensions):
  domains/automation-core/ha-ai-agent-service/src/services/
    ├── energy_rag_service.py          # EnergyRAGService
    ├── blueprint_rag_service.py       # BlueprintRAGService
    └── device_setup_rag_service.py    # DeviceSetupRAGService
  domains/automation-core/ha-ai-agent-service/src/data/
    ├── energy_automation_patterns.md  # Energy corpus
    ├── blueprint_patterns.md          # Blueprint corpus
    └── device_setup_patterns.md       # Device setup corpus
  domains/automation-core/ai-automation-service-new/src/api/
    ├── blueprint_validate_router.py   # POST /api/v1/blueprints/validate
    └── setup_validate_router.py       # POST /api/v1/setup/validate
  domains/automation-core/ai-automation-service-new/src/services/
    ├── blueprint_deploy_verifier.py   # BlueprintDeployVerifier
    └── setup_verifier.py              # SetupVerifier

Phase 4 implementations (Epic: Platform-Wide Pattern Rollout):
  domains/automation-core/ha-ai-agent-service/src/services/
    ├── security_rag_service.py        # SecurityRAGService
    ├── comfort_rag_service.py         # ComfortRAGService
    ├── scene_script_rag_service.py    # SceneScriptRAGService
    └── device_capability_rag_service.py # DeviceCapabilityRAGService
  domains/automation-core/ha-ai-agent-service/src/data/
    ├── security_automation_patterns.md  # Security corpus
    ├── comfort_automation_patterns.md   # Comfort corpus
    ├── scene_script_patterns.md         # Scene/script corpus
    ├── device_capability_patterns.md    # Device capability corpus
    └── sport_specific_patterns.md       # Sport-specific corpus (MLB, MLS, Tennis, NHL)
  domains/automation-core/ai-automation-service-new/src/api/
    ├── scene_validate_router.py       # POST /api/v1/scenes/validate
    └── script_validate_router.py      # POST /api/v1/scripts/validate
  domains/automation-core/ai-automation-service-new/src/services/
    ├── scene_verifier.py              # SceneVerifier
    ├── script_verifier.py             # ScriptVerifier
    ├── task_execution_verifier.py     # TaskExecutionVerifier
    └── sports_blueprint_generator.py  # Parameterized sports-lights blueprint generator
```

## Running Tests

```bash
cd c:\cursor\HomeIQ
python -m pytest libs/homeiq-patterns/tests/ -v
```

## Adding a New Domain

1. **RAG Context:** Create a `*RAGService` class extending `RAGContextService`. Set `name`, `keywords`, `corpus_path`. Register in `ContextBuilder._rag_registry`.
2. **Validation:** Create a `*ValidationRouter` extending `UnifiedValidationRouter`. Set `domain`, `error_categories`. Implement `run_validation()`. Wire to a FastAPI route.
3. **Post-Action Verification:** Create a `*Verifier` extending `PostActionVerifier`. Implement `verify()`. Call after the action in your service layer.
