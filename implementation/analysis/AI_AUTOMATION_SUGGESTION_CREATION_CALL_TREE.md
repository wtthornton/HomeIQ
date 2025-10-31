# AI Automation Service - Suggestion Creation Call Tree

**Focus:** Only the creation of suggestions in ai-automation-service  
**Last Updated:** January 2025

## Call Tree Overview

```
POST /query (ask_ai_router.py)
    │
    ├─ extract_entities_with_ha() → List[Dict[str, Any]]  # Entity extraction
    │
    └─ generate_suggestions_from_query() → List[Dict[str, Any]]
        │
        ├─ Entity Resolution & Enrichment
        │   │
        │   ├─ HomeAssistantClient()  # Initialize HA client
        │   ├─ EntityValidator()  # Entity validation service
        │   │   ├─ _extract_location_from_query() → str
        │   │   ├─ _extract_domain_from_query() → str
        │   │   └─ _get_available_entities() → List[Dict]
        │   │
        │   ├─ expand_group_entities_to_members() → List[str]
        │   │   └─ ha_client.get_entity_state() → Dict
        │   │
        │   ├─ EntityAttributeService()  # Entity enrichment
        │   │   └─ enrich_multiple_entities() → Dict[str, Dict[str, Any]]
        │   │       └─ enrich_entity_with_attributes() → Dict[str, Any]
        │   │           └─ ha_client.get_entity_state() → Dict
        │   │
        │   └─ EntityContextBuilder()  # Build context JSON
        │       └─ build_entity_context_json() → str (JSON)
        │           ├─ _extract_capabilities() → List[str]
        │           ├─ _determine_type() → str
        │           └─ _generate_human_readable_description() → str
        │
        ├─ Prompt Building
        │   │
        │   └─ UnifiedPromptBuilder.build_query_prompt() → Dict[str, str]
        │       ├─ _build_entity_context_section() → str
        │       └─ _generate_capability_examples() → str
        │
        ├─ LLM Generation
        │   │
        │   └─ OpenAIClient.generate_with_unified_prompt() → Dict | List[Dict]
        │       └─ client.chat.completions.create()  # OpenAI API call
        │           └─ Response parsing (JSON format)
        │
        └─ Response Processing
            │
            └─ Parse OpenAI response → List[Dict[str, Any]]
                ├─ suggestion_id: str
                ├─ description: str
                ├─ trigger_summary: str
                ├─ action_summary: str
                ├─ devices_involved: List[str]
                ├─ capabilities_used: List[str]
                ├─ confidence: float
                ├─ status: str
                └─ created_at: str
```

## Detailed Function Signatures & Data Types

### Entry Point

#### `POST /query` (ask_ai_router.py:1040)
```python
async def process_query(
    request: AskAIQueryRequest,
    db: AsyncSession = Depends(get_db)
) -> AskAIQueryResponse
```

**Input:**
```python
AskAIQueryRequest:
    query: str              # Natural language query from user
    user_id: str           # User identifier
```

**Output:**
```python
AskAIQueryResponse:
    query_id: str          # Generated query ID (e.g., "query-abc123")
    query: str             # Original query
    entities: List[Dict]   # Extracted entities
    suggestions: List[Dict[str, Any]]  # Generated suggestions
    confidence: float      # Confidence score (0.0-1.0)
    intent: str            # Parsed intent
    timestamp: str         # ISO timestamp
```

---

### Main Suggestion Generation Function

#### `generate_suggestions_from_query()` (ask_ai_router.py:835)
```python
async def generate_suggestions_from_query(
    query: str,
    entities: List[Dict[str, Any]],
    user_id: str
) -> List[Dict[str, Any]]
```

**Input:**
```python
query: str                    # Natural language query
entities: List[Dict[str, Any]]  # Extracted entities from HA
    - entity_id: str
    - name: str
    - domain: str
    - capabilities: List[Dict]  # Optional
    - extraction_method: str    # Optional
user_id: str                   # User identifier
```

**Output:**
```python
List[Dict[str, Any]]  # List of suggestion dictionaries
    - suggestion_id: str           # "ask-ai-{uuid8}"
    - description: str             # Full description of automation
    - trigger_summary: str         # What triggers the automation
    - action_summary: str          # What actions will be performed
    - devices_involved: List[str]  # Device friendly names
    - capabilities_used: List[str] # Capability names
    - confidence: float            # 0.0-1.0
    - status: str                  # "draft"
    - created_at: str              # ISO timestamp
```

---

### Entity Resolution & Enrichment

#### `EntityValidator._extract_location_from_query()` (entity_validator.py)
```python
def _extract_location_from_query(query: str) -> str
```
**Returns:** Location/area name extracted from query (e.g., "office", "kitchen")

#### `EntityValidator._extract_domain_from_query()` (entity_validator.py)
```python
def _extract_domain_from_query(query: str) -> str
```
**Returns:** Domain extracted from query (e.g., "light", "switch", "climate")

#### `EntityValidator._get_available_entities()` (entity_validator.py)
```python
async def _get_available_entities(
    domain: str,
    area_id: str
) -> List[Dict]
```

**Output:**
```python
List[Dict]:
    - entity_id: str
    - friendly_name: str
    - domain: str
    - area: str
    - state: str
    # Additional metadata
```

#### `expand_group_entities_to_members()` (ask_ai_router.py:191)
```python
async def expand_group_entities_to_members(
    entity_ids: List[str],
    ha_client: Optional[HomeAssistantClient],
    entity_validator: Optional[Any] = None
) -> List[str]
```

**Input:** List of entity IDs (may include group entities)  
**Output:** Expanded list with group entities replaced by member entity IDs

---

### Entity Enrichment

#### `EntityAttributeService.enrich_multiple_entities()` (entity_attribute_service.py:113)
```python
async def enrich_multiple_entities(
    entity_ids: List[str]
) -> Dict[str, Dict[str, Any]]
```

**Input:**
```python
entity_ids: List[str]  # e.g., ["light.office_1", "light.office_2"]
```

**Output:**
```python
Dict[str, Dict[str, Any]]  # Mapping entity_id → enriched data
    {
        "light.office_1": {
            "entity_id": "light.office_1",
            "friendly_name": "Office light 1",
            "state": "on" | "off",
            "attributes": Dict[str, Any],  # Full HA attributes
            "is_group": bool,
            "integration": str,  # "hue", "zigbee", etc.
            "device_id": str,
            # ... additional enriched fields
        },
        "light.office_2": { ... }
    }
```

#### `EntityAttributeService.enrich_entity_with_attributes()` (entity_attribute_service.py)
```python
async def enrich_entity_with_attributes(
    entity_id: str
) -> Dict[str, Any]
```

**Calls:** `ha_client.get_entity_state(entity_id)` to fetch full entity state and attributes

**Output:**
```python
Dict[str, Any]:
    - entity_id: str
    - friendly_name: str
    - state: str
    - attributes: Dict[str, Any]  # Complete HA attributes dict
        - supported_features: int  # Bitmask for capabilities
        - brightness: int | None
        - color_temp: int | None
        - rgb_color: List[int] | None
        - device_id: str
        - is_hue_group: bool | None
        # ... all other HA attributes
    - is_group: bool
    - integration: str
    - device_id: str
```

---

### Entity Context Building

#### `EntityContextBuilder.build_entity_context_json()` (entity_context_builder.py:121)
```python
async def build_entity_context_json(
    entities: List[Dict[str, Any]],
    enriched_data: Dict[str, Dict[str, Any]]
) -> str  # JSON string
```

**Input:**
```python
entities: List[Dict[str, Any]]  # Base entity list from validator
    - entity_id: str
    - friendly_name: str
    - name: str

enriched_data: Dict[str, Dict[str, Any]]  # From EntityAttributeService
```

**Output:**
```python
str  # JSON string with structure:
{
    "entities": [
        {
            "entity_id": "light.office_1",
            "friendly_name": "Office light 1",
            "domain": "light",
            "type": "individual" | "group" | "scene",
            "state": "on" | "off",
            "description": str,  # Human-readable description
            "capabilities": List[str],  # ["brightness", "color_temp", ...]
            "attributes": Dict[str, Any],  # Full attributes passthrough
            "is_group": bool,
            "integration": str,
            "brightness": int | None,  # If available
            "color_temp": int | None,  # If available
            "rgb_color": List[int] | None,  # If available
            "temperature": float | None,  # If available
            "humidity": float | None  # If available
        },
        ...
    ],
    "summary": {
        "total_entities": int,
        "group_entities": int,
        "individual_entities": int
    }
}
```

#### `EntityContextBuilder._extract_capabilities()` (entity_context_builder.py:22)
```python
def _extract_capabilities(
    attributes: Dict[str, không Any],
    domain: str
) -> List[str]
```

**Returns:** List of capability strings based on domain and supported_features bitmask  
**Examples:**
- Light: `["brightness", "color_temp", "rgb_color", "transition", "flash", "effect"]`
- Climate: `["target_temperature", "fan_mode", "preset_mode", "swing_mode"]`
- Cover: `["open", "close", "set_position", "stop"]`

---

### Prompt Building

#### `UnifiedPromptBuilder.build_query_prompt()` (unified_prompt_builder.py:118)
```python
async def build_query_prompt(
    query: str,
    entities: List[Dict],
    output_mode: str = "suggestions",  # "suggestions" | "yaml"
    entity_context_json: Optional[str] = None  # JSON string from EntityContextBuilder
) -> Dict[str, str]
```

**Input:**
```python
query: str  # User's natural language query
entities: List[Dict]  # Entity list with capabilities
    - entity_id: str
    - name: str
    - capabilities: List[Dict]  # Optional
    - health_score: float | None  # Optional
    - area: str | None  # Optional

entity_context_json: str | None  # JSON string from EntityContextBuilder
```

**Output:**
```python
Dict[str, str]:
    {
        "system_prompt": str,  # UNIFIED_SYSTEM_PROMPT constant
        "user_prompt": str     # Generated user prompt with:
                                # - Query
                                # - Available devices section
                                # - Enriched entity context JSON (if provided)
                                # - Capability examples
                                # - Instructions for generating 3-5 suggestions
    }
```

#### `UnifiedPromptBuilder._build_entity_context_section()` (unified_prompt_builder.py:411)
```python
async def _build_entity_context_section(
    entities: List[Dict]
) -> str
```

**Returns:** Formatted text section listing entities with capabilities, health scores, and areas

**Format:**
```
- {name} ({manufacturer} {model}) [Capabilities: ...] [Health: {score} ({status})] [Area: ...]
```

#### `UnifiedPromptBuilder._generate_capability_examples()` (unified_prompt_builder.py:457)
```python
def _generate_capability_examples(
    entities: List[Dict]
) -> str
```

**Returns:** Text section with capability-specific automation examples based on detected device capabilities

---

### LLM Generation

#### `OpenAIClient.generate_with_unified_prompt()` (openai_client.py:844)
```python
async def generate_with_unified_prompt(
    prompt_dict: Dict[str, str],
    temperature: float = 0.7,
    max_tokens: int = 600,
    output_format: str = "yaml"  # "yaml" | "description" | "json"
) -> Dict | List[Dict]
```

**Input:**
```python
prompt_dict: Dict[str, str]
    - "system_prompt": str
    - "user_prompt": str

temperature: float = 0.7  # Creativity level
max_tokens: int = 600     # Response limit
output_format: str = "json"  # For suggestions, uses "json"
```

**Output (for suggestions, output_format="json"):**
```python
List[Dict]  # Parsed JSON array from OpenAI response
    [
        {
            "description": str,
            "trigger_summary": str,
            "action_summary": str,
            "devices_involved": List[str],  # Device friendly names
            "capabilities_used": List[str],
            "confidence": float  # 0.0-1.0
        },
        ...  # 3-5 suggestions
    ]
```

**Process:**
1. Calls `client.chat.completions.create()` with prompt_dict
2. Extracts `response.choices[0].message.content`
3. Removes markdown code blocks (```json, ```)
4. Parses JSON string with `json.loads()`
5. Returns parsed list/dict

---

### Response Processing & Final Suggestion Structure

#### Final Suggestion Object (ask_ai_router.py:1001)
```python
{
    'suggestion_id': str,           # "ask-ai-{uuid8}" (8 hex chars)
    'description': str,             # Full automation description
    'trigger_summary': str,         # When automation triggers
    'action_summary': str,          # What automation does
    'devices_involved': List[str],  # Device friendly names (exact from entity context)
    'capabilities_used': List[str], # Capability names
    'confidence': float,            # 0.0-1.0 (from LLM)
    'status': str,                  # "draft"
    'created_at': str               # ISO timestamp (datetime.now().isoformat())
}
```

**Example:**
```python
{
    'suggestion_id': 'ask-ai-a1b2c3d4',
    'description': 'Automatically turn on all office lights when motion is detected in the morning',
    'trigger_summary': 'Motion sensor detects movement between 6:00 AM and 9:00 AM',
    'action_summary': 'Turn on Office light 1, Office light 2, and Office light 3 with 80% brightness',
    'devices_involved': ['Office light 1', 'Office light 2', 'Office light 3'],
    'capabilities_used': ['brightness', 'transition'],
    'confidence': 0.85,
    'status': 'draft',
    'created_at': '2025-01-20T10:30:45.123456'
}
```

---

## Data Flow Summary

### 1. Entity Extraction → List[Dict]
- Raw entities from Home Assistant Conversation API
- Basic structure: `entity_id`, `name`, `domain`

### 2. Entity Resolution → List[str]
- Extract location and domain from query
- Fetch ALL matching entities (not just one per term)
- Expand group entities to individual members
- Result: List of entity IDs

### 3. Entity Enrichment → Dict[str, Dict]
- Fetch full entity state and attributes from HA
- Extract capabilities, integration info, group status
- Result: Enriched data per entity ID

### 4. Context Building → str (JSON)
- Build comprehensive JSON context
- Include capabilities, attributes, type information
- Result: JSON string for LLM prompt

### 5. Prompt Building → Dict[str, str]
- Combine query, entities, and enriched context
- Generate capability examples
- Result: System and user prompts

### 6. LLM Generation → List[Dict]
- Send prompts to OpenAI
- Parse JSON response
- Result: Raw suggestion objects from LLM

### 7. Final Processing → List[Dict]
- Add suggestion_id (UUID)
- Add status and timestamp
- Result: Final suggestion objects ready for storage/display

---

## Key Design Patterns

### Entity Resolution Strategy
1. **Primary:** Location + Domain matching (finds ALL matching entities)
2. **Fallback 1:** Device name mapping (may return only one per term)
3. **Fallback 2:** Direct entity ID extraction from entities list

### Group Entity Expansion
- Detects group entities via `is_hue_group` attribute or group patterns
- Fetches member entity IDs from `attributes.entity_id`
- Expands to individual entities for more granular control

### Enrichment Pipeline
- **EntityAttributeService:** Fetches raw HA state/attributes
- **EntityContextBuilder:** Transforms to structured JSON with capabilities
- Result: Complete entity information for LLM understanding

### Prompt Structure
- **System Prompt:** Fixed, defines AI role and capabilities
- **User Prompt:** Dynamic, includes:
  - User query
  - Available devices (from entity extraction)
  - Enriched entity context JSON (complete information)
  - Capability-specific examples
  - Generation instructions

### Suggestion Progression
LLM is instructed to generate 3-5 suggestions that progress:
1. **First:** Direct, straightforward (high confidence 0.9+)
2. **Middle:** Enhanced variations (0.8-0.9)
3. **Last:** Creative, outside-the-box (0.7-0.8)

---

## Error Handling & Fallbacks

### Entity Resolution Failure
- Falls back to device name mapping
- If that fails, uses entity IDs directly from entities list
- If no entities found, enrichment is skipped (empty context)

### Entity Enrichment Failure
- Logs warning and continues with empty enriched_data
- Entity context JSON will be empty
- Suggestions still generated but with less device information

### LLM Generation Failure
- Raises exception (retried 3 times with exponential backoff)
- If parsing fails, creates fallback suggestion with basic info

### JSON Parsing Failure
- Creates single fallback suggestion:
  ```python
  {
      'suggestion_id': 'ask-ai-{uuid}',
      'description': f"Automation suggestion for: {query}",
      'trigger_summary': "Based on your query",
      'action_summary': "Device control",
      'devices_involved': [entity['name'] for entity in entities[:3]],
      'confidence': 0.7,
      'status': 'draft',
      'created_at': datetime.now().isoformat()
  }
  ```

---

## File Locations

- **Entry Point:** `services/ai-automation-service/src/api/ask_ai_router.py`
- **Suggestion Generation:** `ask_ai_router.py:835` (`generate_suggestions_from_query`)
- **Prompt Building:** `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- **Entity Enrichment:** `services/ai-automation-service/src/services/entity_attribute_service.py`
- **Context Building:** `services/ai-automation-service/src/prompt_building/entity_context_builder.py`
- **LLM Client:** `services/ai-automation-service/src/llm/openai_client.py`
- **Entity Validation:** `services/ai-automation-service/src/services/entity_validator.py`

