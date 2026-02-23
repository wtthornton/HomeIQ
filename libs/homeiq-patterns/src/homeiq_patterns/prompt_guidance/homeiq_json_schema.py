"""
HomeIQ JSON schema documentation for LLM prompts.

Provides structured documentation of HomeIQ JSON format for use in system prompts.
"""

HOMEIQ_JSON_SCHEMA_DOC = """HomeIQ JSON Automation Format

Core Structure:
- alias (required): Automation name/alias
- description: Automation description
- version: HomeIQ JSON schema version (default: "1.0.0")
- triggers (required): List of triggers (HomeIQTrigger)
- conditions (optional): List of conditions (HomeIQCondition)
- actions (required): List of actions (HomeIQAction)
- mode: Execution mode (single, restart, queued, parallel)
- initial_state: Initial state (true/false, required for 2025.10+)

HomeIQ Metadata (homeiq_metadata):
- created_by: Service that created this automation
- created_at: Creation timestamp
- pattern_id: Pattern ID (if generated from pattern)
- suggestion_id: Suggestion ID (if generated from suggestion)
- confidence_score: Confidence score (0-1)
- safety_score: Safety score (0-100)
- use_case: "energy", "comfort", "security", or "convenience"
- complexity: "low", "medium", or "high"

Device Context (device_context):
- device_ids: List of device IDs involved
- entity_ids: List of entity IDs involved
- device_types: List of device types (light, sensor, etc.)
- area_ids: List of area IDs
- device_capabilities: Device capabilities (effects, modes, ranges, etc.)

Pattern Context (pattern_context, optional):
- pattern_type: Pattern type (time_of_day, co_occurrence, etc.)
- pattern_id: Pattern ID
- pattern_metadata: Pattern-specific metadata
- confidence: Pattern confidence (0-1)
- occurrences: Number of pattern occurrences

Safety Checks (safety_checks, optional):
- requires_confirmation: Require user confirmation before deployment
- critical_devices: List of critical device IDs
- time_constraints: Time-based safety constraints
- safety_warnings: List of safety warnings

Energy Impact (energy_impact, optional):
- estimated_power_w: Estimated power consumption (watts)
- estimated_daily_kwh: Estimated daily energy (kWh)
- peak_hours: Peak consumption hours (0-23)

For complete schema, see: shared/homeiq_automation/schema.py
"""
