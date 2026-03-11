# Ask AI API Response Schema (Epic 53.2)

Expected response shapes for ai-automation-service Ask AI endpoints (base: `http://localhost:8024/api/v1/ask-ai`).

## POST /query

**Request:** `{"query": string, "user_id": string}`

**Response (200/201):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query_id` | string | Yes | Unique query identifier |
| `original_query` | string | Yes | User's input text |
| `suggestions` | array | Yes | List of suggestion objects |
| `confidence` | number | No | Overall confidence (0–1) |

**Suggestion object (inside `suggestions[]`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `suggestion_id` | string | Yes | Unique suggestion ID (e.g. `ask-ai-8bdbe1b5`) |
| `description` | string | Yes | Human-readable description |
| `trigger_summary` | string | No | Summary of trigger(s) |
| `action_summary` | string | No | Summary of action(s) |
| `confidence` | number | No | Suggestion confidence (0–1) |

---

## GET /query/{query_id}/suggestions

**Response (200):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `suggestions` | array | Yes | Same suggestion objects as in POST /query |

---

## POST /query/{query_id}/suggestions/{suggestion_id}/test

**Response (200):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `suggestion_id` | string | Yes | Echo of suggestion ID |
| `query_id` | string | Yes | Echo of query ID |
| `executed` | boolean | Yes | Whether the quick test ran successfully |
| `command` | string | Yes | Simplified command sent to HA |
| `original_description` | string | Yes | Original suggestion description |
| `response` | string | No | Raw response from HA Conversation API |
| `message` | string | No | User-facing message (e.g. success toast text) |
| `automation_id` | string | No | If backend creates a [TEST] automation and returns it |
| `validation_details` | object | No | Debug: validation result |
| `quality_report` | object | No | Debug: quality metrics |

---

## POST /query/{query_id}/suggestions/{suggestion_id}/approve

**Response (200):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `suggestion_id` | string | Yes | Echo of suggestion ID |
| `automation_id` | string | No | Created HA automation entity ID (e.g. `automation.xyz`) |
| `automation_yaml` | string | No | Generated YAML for the automation |
| `message` | string | No | User-facing message |

---

## Assertion rules (integration tests)

- **Required:** Assert presence of all "Required" fields; test fails if missing.
- **Optional:** If an optional field is present, assert type and (where useful) non-empty.
- **Debug:** When `validation_details` or `quality_report` are present, assert they are dict-like (e.g. `isinstance(..., dict)`).
