# Step 4: Component Design Specifications

## 1. DeviceValidationService

### Class Definition

```python
@dataclass
class ValidationResult:
    """Result of device validation."""
    is_valid: bool
    suggestion_text: str
    mentioned_devices: list[str]
    invalid_devices: list[str]
    reason: str | None = None


class DeviceValidationService:
    """
    Validates that suggestions reference only existing devices.
    
    Fetches device inventory from ha-ai-agent-service and validates
    suggestion text against actual devices in Home Assistant.
    """
    
    def __init__(
        self,
        ha_agent_url: str = "http://ha-ai-agent-service:8030",
        cache_ttl_seconds: int = 300,  # 5 minutes
    ):
        """Initialize with HA Agent URL and cache TTL."""
        
    async def get_device_inventory(self) -> list[dict[str, Any]]:
        """
        Fetch all devices from Home Assistant.
        
        Returns:
            List of device dicts with keys: entity_id, friendly_name, domain
        """
        
    async def validate_suggestion(
        self, 
        suggestion_text: str
    ) -> ValidationResult:
        """
        Validate that a suggestion only references existing devices.
        
        Args:
            suggestion_text: The suggestion prompt text
            
        Returns:
            ValidationResult with validation status and details
        """
        
    def extract_device_mentions(self, text: str) -> list[str]:
        """
        Extract potential device mentions from suggestion text.
        
        Uses regex patterns to find device-like phrases:
        - "Smart X" patterns (Smart Humidifier, Smart Thermostat)
        - "X Lights" patterns (Living Room Lights)
        - Quoted device names ("Kitchen Light")
        
        Returns:
            List of potential device name mentions
        """
        
    async def has_device_type(self, device_type: str) -> bool:
        """
        Check if a device type/domain exists.
        
        Args:
            device_type: Domain like 'humidifier', 'climate', 'light'
            
        Returns:
            True if at least one device of this type exists
        """
        
    async def get_device_list_for_llm(self) -> str:
        """
        Get formatted device list for LLM context.
        
        Returns:
            JSON-formatted string of all device friendly names
        """
```

### Device Extraction Patterns

```python
DEVICE_PATTERNS = [
    # "Smart X" pattern
    r'\bSmart\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
    
    # "your X" pattern  
    r'\byour\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b',
    
    # "the X" with device keywords
    r'\bthe\s+([\w\s]+(?:light|switch|sensor|thermostat|fan|lock|camera|speaker|humidifier|dehumidifier)s?)\b',
    
    # Quoted names
    r'"([^"]+)"',
    r"'([^']+)'",
]
```

---

## 2. Enhanced System Prompt

### Updated SUGGESTION_SYSTEM_PROMPT

```python
SUGGESTION_SYSTEM_PROMPT = """You are HomeIQ's Proactive Automation Intelligence.

Your role is to analyze the current home context and generate 1-3 highly personalized, 
actionable automation suggestions that would genuinely help this specific homeowner.

## CRITICAL: Device Constraints

⚠️ CRITICAL RULE: You may ONLY suggest automations for devices that exist in the AVAILABLE DEVICES list below.
- If no device exists for a suggestion type, DO NOT suggest it
- NEVER invent, assume, or hallucinate device names
- If uncertain whether a device exists, DO NOT mention it
- Return an empty array [] rather than suggesting non-existent devices

## Your Capabilities
- You understand smart home devices, their states, and capabilities
- You know about weather patterns and their impact on home comfort
- You understand energy pricing and carbon intensity for cost/eco optimization
- You recognize behavioral patterns from historical data
- You can correlate multiple data sources to find synergies

## What Makes a Great Suggestion
1. **Device-Verified**: ONLY reference devices from the AVAILABLE DEVICES list
2. **Specific**: Reference actual devices/areas by their exact friendly name
3. **Timely**: Based on current conditions, not generic advice
4. **Actionable**: Something that can become an automation
5. **Valuable**: Saves money, increases comfort, or improves safety
6. **Novel**: Not something they're already doing

## Bad Suggestions (AVOID)
- ❌ Generic tips like "turn off lights when not in use"
- ❌ Things already covered by existing automations
- ❌ Suggestions for devices NOT in the AVAILABLE DEVICES list
- ❌ Temperature advice without climate/thermostat device
- ❌ Humidity advice without humidifier/dehumidifier device
- ❌ Any device name you invented or assumed

## Response Format
Return a JSON array of suggestions. Each suggestion:
{
    "prompt": "Natural language suggestion to show the user (1-2 sentences)",
    "context_type": "weather|sports|energy|pattern|device|synergy",
    "trigger": "unique_identifier_for_deduplication",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of why this suggestion is valuable",
    "referenced_devices": ["exact_device_name_from_list"]
}

Return 1-3 suggestions, or empty array [] if no good suggestions available.
Quality over quantity - only suggest things that are genuinely useful AND for devices that exist."""
```

---

## 3. Updated Context Analysis Insights

### Remove Generic Insights

**Before (line 131-133):**
```python
if humidity and humidity > 70:
    insights.append("High humidity - consider dehumidifier automation")
```

**After:**
```python
# Humidity insights removed - device-specific insights 
# are generated based on actual device inventory
# See: _generate_device_aware_insights()
```

### New Device-Aware Insights Method

```python
async def _generate_device_aware_insights(
    self,
    weather: dict[str, Any],
    device_types: set[str],
) -> list[str]:
    """
    Generate insights only for device types that exist.
    
    Args:
        weather: Weather analysis results
        device_types: Set of device domains that exist
        
    Returns:
        List of device-aware insight strings
    """
    insights = []
    
    humidity = weather.get("current", {}).get("humidity")
    temperature = weather.get("current", {}).get("temperature")
    
    # Only suggest dehumidifier if user has one
    if humidity and humidity > 70 and "humidifier" in device_types:
        insights.append("High humidity detected - your humidifier can help")
    
    # Only suggest climate control if user has thermostat
    if temperature:
        if temperature > 85 and "climate" in device_types:
            insights.append("High temperature - consider cooling automation")
        elif temperature < 50 and "climate" in device_types:
            insights.append("Low temperature - consider heating automation")
    
    return insights
```

---

## 4. API Endpoint: Report Invalid Suggestion

### Endpoint Specification

```yaml
openapi: 3.0.0
paths:
  /api/v1/suggestions/{suggestion_id}/report:
    post:
      summary: Report an invalid suggestion
      description: |
        Allows users to report suggestions that are invalid,
        such as those referencing non-existent devices.
      parameters:
        - name: suggestion_id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                reason:
                  type: string
                  enum: [device_not_found, not_relevant, already_automated, other]
                feedback:
                  type: string
                  maxLength: 500
              required:
                - reason
      responses:
        '200':
          description: Report submitted successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                  report_id:
                    type: integer
        '404':
          description: Suggestion not found
```

### Pydantic Models

```python
from pydantic import BaseModel, Field
from enum import Enum

class InvalidReportReason(str, Enum):
    DEVICE_NOT_FOUND = "device_not_found"
    NOT_RELEVANT = "not_relevant"
    ALREADY_AUTOMATED = "already_automated"
    OTHER = "other"

class InvalidSuggestionReportRequest(BaseModel):
    """Request body for reporting invalid suggestion."""
    reason: InvalidReportReason
    feedback: str | None = Field(None, max_length=500)

class InvalidSuggestionReportResponse(BaseModel):
    """Response for invalid suggestion report."""
    success: bool
    report_id: int
```

---

## 5. Database Model: InvalidSuggestionReport

```python
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from .database import Base

class InvalidSuggestionReport(Base):
    """Model for tracking invalid suggestion reports."""
    
    __tablename__ = "invalid_suggestion_reports"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    suggestion_id = Column(Integer, ForeignKey("suggestions.id"), nullable=False)
    reason = Column(String(50), nullable=False)
    feedback = Column(Text, nullable=True)
    reported_at = Column(DateTime, server_default=func.now())
    
    def __repr__(self) -> str:
        return f"<InvalidSuggestionReport(id={self.id}, suggestion_id={self.suggestion_id})>"
```

---

## 6. LLM Context Format

### Device List Format for LLM

```json
{
    "available_devices": {
        "lights": [
            "Living Room Lights",
            "Kitchen Light",
            "Bedroom Lamp"
        ],
        "climate": [
            "Main Thermostat"
        ],
        "switches": [
            "Garage Door",
            "Porch Light Switch"
        ],
        "sensors": [
            "Front Door Sensor",
            "Motion Sensor - Hallway"
        ]
    },
    "total_devices": 8,
    "device_domains_available": ["light", "climate", "switch", "binary_sensor"]
}
```

### Context Injection Point

```python
def _build_llm_context(self, context_analysis, home_context, device_inventory):
    """Build context with explicit device list."""
    
    parts = ["## Current Home State\n"]
    
    # ... weather, sports, energy context ...
    
    # NEW: Explicit device list (not truncated)
    parts.append(f"""### AVAILABLE DEVICES (You may ONLY suggest for these)
{json.dumps(device_inventory, indent=2)}

⚠️ REMINDER: Only suggest automations for devices in this list.
""")
    
    return "\n".join(parts)
```

---
*Generated by TappsCodingAgents Simple Mode - Step 4: @designer *design-api*
