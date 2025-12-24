# Expert Mode Implementation Guide

**Feature:** Expert Mode for Suggestion API
**Date:** November 5, 2025
**Status:** Implementation Complete
**Version:** 1.0.0

---

## Executive Summary

Expert Mode provides advanced users with granular control over every step of the automation creation process. Unlike Standard Mode (auto-draft), which automatically generates YAML and streamlines the flow, Expert Mode allows users to:

1. **Generate description only** (no automatic YAML generation)
2. **Refine description multiple times** with natural language edits
3. **Generate YAML on-demand** when satisfied with description
4. **Edit YAML manually** in a code editor with syntax highlighting
5. **Deploy with full control** over validation and safety checks

**Key Benefits:**
- **Full control** - Users control every step (no automation)
- **Learning tool** - See how descriptions translate to YAML
- **Advanced customization** - Manual YAML editing for power users
- **Iterative refinement** - Refine description before generating YAML
- **Non-linear navigation** - Jump back to previous steps anytime

---

## Table of Contents

1. [Architecture](#1-architecture)
2. [API Endpoints](#2-api-endpoints)
3. [Request/Response Models](#3-requestresponse-models)
4. [User Flows](#4-user-flows)
5. [Security & Safety](#5-security--safety)
6. [Configuration](#6-configuration)
7. [Database Schema](#7-database-schema)
8. [Frontend Integration](#8-frontend-integration)
9. [Testing](#9-testing)
10. [Monitoring](#10-monitoring)

---

## 1. Architecture

### 1.1 Mode Comparison

| Feature | Standard Mode (Auto-Draft) | Expert Mode |
|---------|---------------------------|-------------|
| **YAML Generation** | Automatic (with description) | On-demand (manual trigger) |
| **Description Refinement** | Optional (skip to approval) | Full control (multiple iterations) |
| **YAML Editing** | Not available | Manual code editor |
| **Steps** | 2 clicks (Generate → Approve) | 3-10+ clicks (full control) |
| **Time to Deploy** | ~1.7s (automated) | 30s - 5min (user-paced) |
| **Target Users** | General users | Power users, developers |
| **Use Cases** | Quick automation, common patterns | Custom logic, learning, complex automations |

### 1.2 Expert Mode Flow

```
Step 1: Generate Description Only
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/suggestions/generate                          │
│ { "mode": "expert" }                                        │
│                                                             │
│ Response: { description, no YAML }                          │
│ Status: "draft"                                             │
└─────────────────────────────────────────────────────────────┘
                         ↓
Step 2: Refine Description (Optional, Repeatable)
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/suggestions/{id}/refine                        │
│ { "user_input": "Make it 75% brightness and weekdays" }    │
│                                                             │
│ Response: { updated_description }                           │
│ Status: "refining"                                          │
└─────────────────────────────────────────────────────────────┘
                         ↓
Step 3: Generate YAML (On-Demand)
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/suggestions/{id}/generate-yaml (NEW)          │
│ { "validate_syntax": true }                                 │
│                                                             │
│ Response: { automation_yaml, yaml_validation }              │
│ Status: "yaml_generated"                                    │
└─────────────────────────────────────────────────────────────┘
                         ↓
Step 4: Edit YAML (Optional, Repeatable)
┌─────────────────────────────────────────────────────────────┐
│ PATCH /api/v1/suggestions/{id}/yaml (NEW)                  │
│ { "automation_yaml": "..." }                                │
│                                                             │
│ Response: { automation_yaml, changes: { diff } }            │
│ Status: "yaml_edited"                                       │
└─────────────────────────────────────────────────────────────┘
                         ↓
Step 5: Deploy to Home Assistant
┌─────────────────────────────────────────────────────────────┐
│ POST /api/v1/suggestions/{id}/approve                       │
│ { "deploy_immediately": true }                              │
│                                                             │
│ Response: { automation_id, deployment_status }              │
│ Status: "deployed"                                          │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 Non-Linear Navigation

Expert Mode allows users to go back to previous steps:

```
   Step 1 (Generate) ←─────┐
       ↓                   │
   Step 2 (Refine) ←───────┼─────┐
       ↓                   │     │
   Step 3 (Generate YAML) ←┼─────┤
       ↓                   │     │
   Step 4 (Edit YAML) ─────┘     │
       ↓                         │
   Step 5 (Deploy) ──────────────┘

Users can:
- Refine description after seeing YAML (Step 3 → Step 2)
- Regenerate YAML after editing description (Step 2 → Step 3)
- Edit YAML multiple times (Step 4 loop)
- Go back to description from any step
```

---

## 2. API Endpoints

### 2.1 Generate Description (Updated)

**Endpoint:** `POST /api/v1/suggestions/generate`

**Request:**
```json
{
  "pattern_id": 123,
  "pattern_type": "time_of_day",
  "device_id": "light.living_room",
  "metadata": {
    "hour": 18,
    "confidence": 0.92
  },
  "mode": "expert"  // NEW: "auto_draft" or "expert"
}
```

**Response (Expert Mode):**
```json
{
  "suggestion_id": "suggestion-42",
  "description": "Every evening at 6 PM, your living room light turns on...",
  "trigger_summary": "At 18:00 daily",
  "action_summary": "Turn on living room light",
  "devices_involved": [...],
  "confidence": 0.92,
  "status": "draft",
  "mode": "expert",  // NEW
  "created_at": "2025-11-05T14:30:00Z",

  // YAML fields are NULL in expert mode
  "draft_id": "suggestion-42",
  "automation_yaml": null,
  "yaml_validation": null,
  "yaml_generated_at": null,
  "yaml_generation_status": "not_requested",

  // Expert mode fields
  "yaml_edited_at": null,
  "yaml_edit_count": 0
}
```

---

### 2.2 Generate YAML (NEW - Expert Mode)

**Endpoint:** `POST /api/v1/suggestions/{id}/generate-yaml`

**Purpose:** Manually trigger YAML generation after user is satisfied with description.

**Request:**
```json
{
  "description": null,  // Optional: override description
  "validate_syntax": true,
  "run_safety_check": false  // Optional: defer to approval
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-42",
  "automation_yaml": "alias: Living Room Evening Light\nmode: single\ntrigger:\n  - platform: time\n    at: '18:00:00'\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.living_room\n    data:\n      brightness_pct: 75\n",
  "yaml_validation": {
    "syntax_valid": true,
    "safety_score": null,
    "issues": [],
    "services_used": ["light.turn_on"],
    "entities_referenced": ["light.living_room"],
    "advanced_features_used": []
  },
  "status": "yaml_generated",
  "yaml_generated_at": "2025-11-05T14:35:00Z",
  "yaml_generation_method": "expert_manual"
}
```

**Error Responses:**

```json
// 404 - Suggestion not found
{
  "detail": "Suggestion not found"
}

// 400 - No description available
{
  "detail": "No description available for YAML generation"
}

// 500 - YAML generation failed
{
  "detail": "YAML generation returned empty result"
}
```

---

### 2.3 Edit YAML (NEW - Expert Mode)

**Endpoint:** `PATCH /api/v1/suggestions/{id}/yaml`

**Purpose:** Allow manual YAML editing by expert users.

**Request:**
```json
{
  "automation_yaml": "alias: Living Room Evening Light\nmode: single\ntrigger:\n  - platform: time\n    at: '18:00:00'\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.living_room\n    data:\n      brightness_pct: 80  // Changed from 75
      transition: 2  // NEW field added
\n",
  "validate_on_save": true,
  "user_notes": "Adjusted brightness to 80% and added 2s transition"
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-42",
  "automation_yaml": "... updated YAML ...",
  "yaml_validation": {
    "syntax_valid": true,
    "safety_score": null,
    "issues": [],
    "services_used": ["light.turn_on"],
    "entities_referenced": ["light.living_room"],
    "advanced_features_used": []
  },
  "changes": {
    "modified_fields": ["data"],
    "diff": "--- \n+++ \n@@ -8,5 +8,6 @@\n       entity_id: light.living_room\n     data:\n-      brightness_pct: 75\n+      brightness_pct: 80\n+      transition: 2\n"
  },
  "status": "yaml_edited",
  "yaml_edited_at": "2025-11-05T14:40:00Z",
  "edit_count": 1
}
```

**Error Responses:**

```json
// 400 - YAML syntax error
{
  "detail": "YAML syntax error: while parsing a block mapping\n  in \"<unicode string>\", line 3, column 1\nexpected <block end>, but found '<block mapping start>'"
}

// 400 - Dangerous service detected
{
  "detail": "Dangerous services not allowed: shell_command. Contact admin to enable expert_mode_allow_dangerous_operations."
}

// 400 - Edit limit reached
{
  "detail": "Maximum YAML edit limit reached (10 edits). Create a new suggestion to continue editing."
}
```

---

### 2.4 Approve & Deploy (Updated)

**Endpoint:** `POST /api/v1/suggestions/{id}/approve`

**Request:**
```json
{
  "final_description": null,
  "user_notes": "Perfect!",
  "regenerate_yaml": false,
  "deploy_immediately": true  // NEW: Allow staging without deployment
}
```

**Response:**
```json
{
  "suggestion_id": "suggestion-42",
  "status": "deployed",
  "automation_yaml": "...",
  "yaml_validation": {
    "syntax_valid": true,
    "safety_score": 95,
    "issues": []
  },
  "ready_to_deploy": true,
  "automation_id": "automation.living_room_evening_light",
  "deployment_status": "success",
  "safe": true,
  "safety_report": {...},

  // Expert mode tracking
  "mode": "expert",
  "yaml_source": "expert_manual_edited",
  "yaml_generated_at": "2025-11-05T14:35:00Z",
  "yaml_edited_at": "2025-11-05T14:40:00Z"
}
```

---

## 3. Request/Response Models

### 3.1 GenerateRequest (Updated)

```python
class GenerateRequest(BaseModel):
    pattern_id: Optional[int] = None
    pattern_type: str
    device_id: str
    metadata: Dict[str, Any]

    # NEW: Mode selection
    mode: Literal["auto_draft", "expert"] = "auto_draft"

    # Explicit control (overrides mode)
    auto_generate_yaml: Optional[bool] = None
```

### 3.2 GenerateYAMLRequest (NEW)

```python
class GenerateYAMLRequest(BaseModel):
    """Request to manually generate YAML (expert mode)"""
    description: Optional[str] = None
    validate_syntax: bool = True
    run_safety_check: bool = False
```

### 3.3 EditYAMLRequest (NEW)

```python
class EditYAMLRequest(BaseModel):
    """Request to manually edit YAML (expert mode)"""
    automation_yaml: str
    validate_on_save: bool = True
    user_notes: Optional[str] = None
```

### 3.4 SuggestionResponse (Updated)

```python
class SuggestionResponse(BaseModel):
    suggestion_id: str
    description: str
    trigger_summary: str
    action_summary: str
    devices_involved: List[Dict[str, Any]]
    confidence: float
    status: str
    created_at: str

    # NEW: Mode tracking
    mode: Literal["auto_draft", "expert"] = "auto_draft"

    # Auto-draft fields
    draft_id: Optional[str] = None
    automation_yaml: Optional[str] = None
    yaml_validation: Optional[YAMLValidationReport] = None
    yaml_generation_error: Optional[str] = None
    yaml_generated_at: Optional[str] = None
    yaml_generation_status: Optional[str] = None

    # NEW: Expert mode fields
    yaml_edited_at: Optional[str] = None
    yaml_edit_count: int = 0
```

---

## 4. User Flows

### 4.1 Complete Expert Mode Flow (Example)

**Scenario:** User wants to create a motion light automation with custom brightness and schedule.

**Step 1: Generate Description**

```bash
curl -X POST http://localhost:8018/api/v1/suggestions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "pattern_type": "co_occurrence",
    "device_id": "binary_sensor.kitchen_motion+light.kitchen",
    "metadata": {"confidence": 0.85},
    "mode": "expert"
  }'
```

Response:
```json
{
  "suggestion_id": "suggestion-789",
  "description": "When motion is detected in the kitchen, the kitchen light turns on.",
  "status": "draft",
  "mode": "expert",
  "automation_yaml": null  // No YAML yet
}
```

**Step 2: Refine Description**

```bash
curl -X POST http://localhost:8018/api/v1/suggestions/789/refine \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Make it 75% brightness and only between 6 PM and midnight"
  }'
```

Response:
```json
{
  "suggestion_id": "suggestion-789",
  "updated_description": "When motion is detected in the kitchen between 6 PM and midnight, the kitchen light turns on at 75% brightness.",
  "changes_detected": ["Added brightness: 75%", "Added time constraint: 6 PM - midnight"],
  "status": "refining"
}
```

**Step 3: Generate YAML**

```bash
curl -X POST http://localhost:8018/api/v1/suggestions/789/generate-yaml \
  -H "Content-Type: application/json" \
  -d '{
    "validate_syntax": true,
    "run_safety_check": false
  }'
```

Response:
```json
{
  "suggestion_id": "suggestion-789",
  "automation_yaml": "alias: Kitchen Motion Light\nmode: restart\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.kitchen_motion\n    to: 'on'\ncondition:\n  - condition: time\n    after: '18:00:00'\n    before: '00:00:00'\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.kitchen\n    data:\n      brightness_pct: 75\n",
  "yaml_validation": {
    "syntax_valid": true,
    "issues": []
  },
  "status": "yaml_generated"
}
```

**Step 4: Edit YAML (Add Transition)**

```bash
curl -X PATCH http://localhost:8018/api/v1/suggestions/789/yaml \
  -H "Content-Type: application/json" \
  -d '{
    "automation_yaml": "alias: Kitchen Motion Light\nmode: restart\ntrigger:\n  - platform: state\n    entity_id: binary_sensor.kitchen_motion\n    to: '\''on'\''\ncondition:\n  - condition: time\n    after: '\''18:00:00'\''\n    before: '\''00:00:00'\''\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.kitchen\n    data:\n      brightness_pct: 80\n      transition: 2\n",
    "validate_on_save": true,
    "user_notes": "Increased brightness to 80% and added 2s transition"
  }'
```

Response:
```json
{
  "suggestion_id": "suggestion-789",
  "automation_yaml": "... updated YAML ...",
  "changes": {
    "modified_fields": ["data"],
    "diff": "...\n+      brightness_pct: 80\n+      transition: 2"
  },
  "status": "yaml_edited",
  "edit_count": 1
}
```

**Step 5: Deploy**

```bash
curl -X POST http://localhost:8018/api/v1/suggestions/789/approve \
  -H "Content-Type: application/json" \
  -d '{
    "deploy_immediately": true
  }'
```

Response:
```json
{
  "suggestion_id": "suggestion-789",
  "status": "deployed",
  "automation_id": "automation.kitchen_motion_light",
  "deployment_status": "success",
  "mode": "expert",
  "yaml_source": "expert_manual_edited"
}
```

---

## 5. Security & Safety

### 5.1 Dangerous Service Blocking

**Configuration:**
```python
expert_mode_allow_dangerous_operations: bool = False  # Default
expert_mode_blocked_services: List[str] = [
    "shell_command",
    "python_script",
    "script.turn_on",
    "automation.reload",
    "homeassistant.restart",
    "homeassistant.stop"
]
```

**Behavior:**
- If user edits YAML to include `shell_command.*`, API returns 400 error
- Error message: "Dangerous services not allowed: shell_command. Contact admin to enable expert_mode_allow_dangerous_operations."
- Prevents arbitrary code execution

### 5.2 YAML Edit Limits

**Configuration:**
```python
expert_mode_max_yaml_edits: int = 10
```

**Rationale:**
- Prevents abuse (infinite edit loops)
- Encourages creating new suggestions for major changes
- Tracks edit history for debugging

### 5.3 Safety Validation (Always Required)

**Behavior:**
- YAML syntax validation: Always runs on save (unless `validate_on_save=false`)
- Safety validation: Always runs before deployment (cannot be skipped)
- Dangerous services: Blocked unless admin override

**Safety Checks:**
- YAML syntax validation
- Entity ID format validation
- Service call structure validation
- Dangerous service detection
- Entity existence validation (optional)

---

## 6. Configuration

### 6.1 Expert Mode Settings

```python
# Enable/disable expert mode
expert_mode_enabled: bool = True

# Default mode for new suggestions
expert_mode_default: bool = False  # Standard mode is default

# Allow mode switching mid-flow
expert_mode_allow_mode_switching: bool = True

# Validation settings
expert_mode_yaml_validation_strict: bool = True
expert_mode_validate_on_save: bool = True
expert_mode_show_yaml_diff: bool = True

# Limits
expert_mode_max_yaml_edits: int = 10

# Security settings
expert_mode_allow_dangerous_operations: bool = False
expert_mode_blocked_services: List[str] = [
    "shell_command",
    "python_script",
    "script.turn_on",
    "automation.reload",
    "homeassistant.restart",
    "homeassistant.stop"
]

# Services requiring explicit approval
expert_mode_require_approval_services: List[str] = [
    "notify",
    "camera",
    "lock",
    "cover",
    "climate"
]
```

### 6.2 Environment Variables

```bash
# infrastructure/env.ai-automation

# Expert Mode
EXPERT_MODE_ENABLED=true
EXPERT_MODE_DEFAULT=false
EXPERT_MODE_ALLOW_MODE_SWITCHING=true
EXPERT_MODE_YAML_VALIDATION_STRICT=true
EXPERT_MODE_VALIDATE_ON_SAVE=true
EXPERT_MODE_SHOW_YAML_DIFF=true
EXPERT_MODE_MAX_YAML_EDITS=10
EXPERT_MODE_ALLOW_DANGEROUS_OPERATIONS=false
```

---

## 7. Database Schema

### 7.1 New Columns

```sql
-- Mode tracking
ALTER TABLE suggestions ADD COLUMN mode VARCHAR(20) DEFAULT 'auto_draft';
-- Values: 'auto_draft', 'expert'

-- Expert mode tracking
ALTER TABLE suggestions ADD COLUMN yaml_edited_at DATETIME NULL;
ALTER TABLE suggestions ADD COLUMN yaml_edit_count INT DEFAULT 0;

-- Indexes
CREATE INDEX ix_suggestions_mode ON suggestions(mode);
CREATE INDEX ix_suggestions_yaml_edited_at ON suggestions(yaml_edited_at);
```

### 7.2 Status Transitions

```
Standard Mode:
draft → yaml_generated → approved → deployed

Expert Mode:
draft → refining → yaml_generated → yaml_edited → approved → deployed
```

### 7.3 YAML Generation Methods

```
auto_draft            - Auto-generated during suggestion creation
auto_draft_async      - Background job generation
on_approval           - Generated during approval (legacy)
on_approval_regenerated - Regenerated during approval
expert_manual         - Generated via /generate-yaml endpoint
expert_manual_edited  - Manually edited via /yaml endpoint
```

---

## 8. Frontend Integration

### 8.1 Mode Selector Component

```typescript
interface ModeSelectorProps {
  mode: 'auto_draft' | 'expert';
  onChange: (mode: 'auto_draft' | 'expert') => void;
}

const ModeSelector: React.FC<ModeSelectorProps> = ({ mode, onChange }) => {
  return (
    <div className="mode-selector">
      <h3>Generate Automation</h3>

      <div className="mode-options">
        <RadioButton
          checked={mode === 'auto_draft'}
          onChange={() => onChange('auto_draft')}
          label="Standard (Fast)"
        />
        <p>• Automatically generates YAML</p>
        <p>• Fast approval (1 click)</p>
        <p>• Best for most users</p>

        <RadioButton
          checked={mode === 'expert'}
          onChange={() => onChange('expert')}
          label="Expert (Full Control)"
        />
        <p>• Step-by-step control</p>
        <p>• Edit description & YAML</p>
        <p>• Full customization</p>
      </div>

      <Button onClick={handleGenerate}>Generate</Button>
    </div>
  );
};
```

### 8.2 Expert Mode Wizard

```typescript
interface ExpertModeWizardProps {
  suggestionId: string;
}

const ExpertModeWizard: React.FC<ExpertModeWizardProps> = ({ suggestionId }) => {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3 | 4 | 5>(1);
  const [description, setDescription] = useState<string>('');
  const [yaml, setYaml] = useState<string>('');

  return (
    <div className="expert-wizard">
      {/* Progress Indicator */}
      <ProgressBar currentStep={currentStep} totalSteps={5} />

      {/* Step 1: Description */}
      {currentStep === 1 && (
        <DescriptionStep
          description={description}
          onNext={() => setCurrentStep(2)}
          onSkip={() => setCurrentStep(3)}
        />
      )}

      {/* Step 2: Refine */}
      {currentStep === 2 && (
        <RefineStep
          description={description}
          onUpdate={(newDesc) => setDescription(newDesc)}
          onBack={() => setCurrentStep(1)}
          onNext={() => setCurrentStep(3)}
        />
      )}

      {/* Step 3: Generate YAML */}
      {currentStep === 3 && (
        <GenerateYAMLStep
          suggestionId={suggestionId}
          onGenerated={(yamlContent) => {
            setYaml(yamlContent);
            setCurrentStep(4);
          }}
          onBack={() => setCurrentStep(2)}
        />
      )}

      {/* Step 4: Edit YAML */}
      {currentStep === 4 && (
        <EditYAMLStep
          yaml={yaml}
          onUpdate={(newYaml) => setYaml(newYaml)}
          onBack={() => setCurrentStep(3)}
          onNext={() => setCurrentStep(5)}
          onSkip={() => setCurrentStep(5)}
        />
      )}

      {/* Step 5: Deploy */}
      {currentStep === 5 && (
        <DeployStep
          suggestionId={suggestionId}
          yaml={yaml}
          onDeploy={handleDeploy}
          onBack={() => setCurrentStep(4)}
        />
      )}
    </div>
  );
};
```

### 8.3 YAML Editor Component

```typescript
import MonacoEditor from '@monaco-editor/react';

interface YAMLEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave: () => void;
}

const YAMLEditor: React.FC<YAMLEditorProps> = ({ value, onChange, onSave }) => {
  return (
    <div className="yaml-editor">
      <h3>Edit YAML</h3>

      <MonacoEditor
        height="400px"
        language="yaml"
        value={value}
        onChange={onChange}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          formatOnPaste: true,
          formatOnType: true
        }}
      />

      <div className="editor-actions">
        <Button onClick={onSave} variant="primary">
          Save Changes
        </Button>
        <Button onClick={() => onChange(value)} variant="secondary">
          Reset
        </Button>
      </div>
    </div>
  );
};
```

---

## 9. Testing

### 9.1 Unit Tests

```python
import pytest
from src.api.conversational_router import (
    generate_description_only,
    generate_yaml_expert_mode,
    edit_yaml_expert_mode
)

@pytest.mark.asyncio
async def test_expert_mode_description_only():
    """Test expert mode generates description without YAML"""
    request = GenerateRequest(
        pattern_type="time_of_day",
        device_id="light.bedroom",
        metadata={"confidence": 0.85},
        mode="expert"
    )

    response = await generate_description_only(request, db_session)

    assert response.mode == "expert"
    assert response.automation_yaml is None
    assert response.yaml_generation_status == "not_requested"
    assert response.status == "draft"


@pytest.mark.asyncio
async def test_generate_yaml_endpoint():
    """Test manual YAML generation in expert mode"""
    # Create suggestion in expert mode
    suggestion = await create_suggestion(mode="expert")

    # Generate YAML manually
    yaml_request = GenerateYAMLRequest(validate_syntax=True)
    response = await generate_yaml_expert_mode(
        suggestion.id, yaml_request, db_session
    )

    assert response["automation_yaml"] is not None
    assert response["yaml_validation"]["syntax_valid"] is True
    assert response["status"] == "yaml_generated"


@pytest.mark.asyncio
async def test_edit_yaml_endpoint():
    """Test manual YAML editing"""
    # Create suggestion with YAML
    suggestion = await create_suggestion_with_yaml()

    # Edit YAML
    edit_request = EditYAMLRequest(
        automation_yaml="... modified YAML ...",
        validate_on_save=True,
        user_notes="Changed brightness"
    )
    response = await edit_yaml_expert_mode(
        suggestion.id, edit_request, db_session
    )

    assert response["status"] == "yaml_edited"
    assert response["edit_count"] == 1
    assert response["changes"]["diff"] is not None


@pytest.mark.asyncio
async def test_dangerous_service_blocking():
    """Test that dangerous services are blocked"""
    suggestion = await create_suggestion_with_yaml()

    # Try to edit with shell_command
    edit_request = EditYAMLRequest(
        automation_yaml="...\nservice: shell_command.test\n...",
        validate_on_save=True
    )

    with pytest.raises(HTTPException) as exc_info:
        await edit_yaml_expert_mode(suggestion.id, edit_request, db_session)

    assert exc_info.value.status_code == 400
    assert "Dangerous services" in exc_info.value.detail


@pytest.mark.asyncio
async def test_yaml_edit_limit():
    """Test that edit limit is enforced"""
    suggestion = await create_suggestion_with_yaml()
    suggestion.yaml_edit_count = 10  # At limit

    edit_request = EditYAMLRequest(automation_yaml="...")

    with pytest.raises(HTTPException) as exc_info:
        await edit_yaml_expert_mode(suggestion.id, edit_request, db_session)

    assert exc_info.value.status_code == 400
    assert "Maximum YAML edit limit" in exc_info.value.detail
```

### 9.2 Integration Tests

```bash
# Test complete expert mode flow
curl -X POST http://localhost:8018/api/v1/suggestions/generate \
  -d '{"mode": "expert", ...}'

# Verify response
assert_json '.mode == "expert"'
assert_json '.automation_yaml == null'

# Refine description
curl -X POST http://localhost:8018/api/v1/suggestions/42/refine \
  -d '{"user_input": "Make it brighter"}'

# Generate YAML
curl -X POST http://localhost:8018/api/v1/suggestions/42/generate-yaml \
  -d '{}'

assert_json '.automation_yaml != null'
assert_json '.status == "yaml_generated"'

# Edit YAML
curl -X PATCH http://localhost:8018/api/v1/suggestions/42/yaml \
  -d '{"automation_yaml": "...", "validate_on_save": true}'

assert_json '.status == "yaml_edited"'
assert_json '.edit_count == 1'

# Deploy
curl -X POST http://localhost:8018/api/v1/suggestions/42/approve

assert_json '.status == "deployed"'
assert_json '.yaml_source == "expert_manual_edited"'
```

---

## 10. Monitoring

### 10.1 Key Metrics

```python
# Track mode usage
metrics.increment_counter("suggestion_generated", tags={"mode": "expert"})
metrics.increment_counter("yaml_generated_manual")  # Expert mode
metrics.increment_counter("yaml_edited", tags={"edit_count": edit_count})

# Track edit patterns
metrics.set_gauge("yaml_edit_count_avg", avg_edit_count)
metrics.increment_counter("dangerous_service_blocked")

# Track deployment success
metrics.increment_counter("expert_mode_deployed", tags={"success": True})
```

### 10.2 Grafana Dashboard

**Panels:**
1. **Mode Distribution** - Pie chart (Standard vs Expert)
2. **Expert Mode Adoption** - Time series (% of suggestions in expert mode)
3. **YAML Edit Count** - Histogram (distribution of edit counts)
4. **Dangerous Service Blocks** - Counter (security incidents)
5. **Expert Mode Success Rate** - Gauge (% of expert suggestions deployed)

### 10.3 Alerting

```yaml
# Alert if dangerous services frequently blocked (potential attack)
- alert: DangerousServiceBlocksHigh
  expr: rate(dangerous_service_blocked[5m]) > 5
  for: 5m
  annotations:
    summary: "High rate of dangerous service blocks"

# Alert if YAML edit count unusually high (UX issue?)
- alert: YAMLEditCountHigh
  expr: avg(yaml_edit_count_avg) > 5
  for: 10m
  annotations:
    summary: "Users editing YAML many times (avg > 5)"
```

---

## 11. Future Enhancements

### 11.1 YAML Templates

Allow users to start from templates:

```python
POST /api/v1/suggestions/generate
{
  "mode": "expert",
  "template": "motion_light",  # Pre-defined template
  "device_id": "binary_sensor.kitchen_motion+light.kitchen"
}
```

### 11.2 YAML Validation on Keystroke

Real-time syntax highlighting in frontend:

```typescript
const [yamlErrors, setYamlErrors] = useState<YAMLError[]>([]);

useEffect(() => {
  const errors = validateYAMLSyntax(yaml);
  setYamlErrors(errors);
}, [yaml]);
```

### 11.3 YAML Diff Viewer

Visual diff viewer for changes:

```typescript
import DiffViewer from 'react-diff-viewer';

<DiffViewer
  oldValue={originalYAML}
  newValue={editedYAML}
  splitView={true}
  showDiffOnly={false}
/>
```

### 11.4 Collaboration Features

Allow multiple users to review/edit:

```python
POST /api/v1/suggestions/{id}/yaml/comment
{
  "line_number": 12,
  "comment": "Should this be 80% brightness?",
  "user_id": "user-123"
}
```

---

## Appendix A: Complete API Reference

See full API documentation:
- [Suggestion API Spec](../api/suggestion-api.md)
- [Expert Mode Endpoints](../api/expert-mode-endpoints.md)

## Appendix B: Configuration Reference

See full configuration documentation:
- [Config Settings](../configuration/expert-mode-config.md)
- [Environment Variables](../configuration/env-variables.md)

---

**Document Version:** 1.0.0
**Last Updated:** November 5, 2025
**Next Review:** December 5, 2025 (post-rollout)
