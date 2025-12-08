# AI Automation System - Call Tree & Data Flow

**Epic:** AI1 - AI Automation Suggestion System (Enhanced)  
**Last Updated:** October 16, 2025  
**Stories:** AI1.19 (Safety), AI1.20 (Rollback), AI1.21 (NL), AI1.22 (Dashboard)

---

## System Overview

```
User Dashboard (Port 3000)
    ↓
AI Automation Service (Port 8018)
    ↓
Home Assistant API (Port 8123)
```

---

## Call Tree 1: Natural Language Automation Generation

### User Flow: "Turn on kitchen light at 7 AM"

```
1. User (health-dashboard:3000)
   └─ AIAutomationsTab.tsx → NLInput.tsx
      └─ User types request + clicks "Generate"

2. Frontend → Backend API Call
   └─ POST http://localhost:8018/api/nl/generate
      Body: { request_text: "Turn on kitchen light at 7 AM", user_id: "default" }

3. AI Automation Service (nl_generation_router.py)
   └─ generate_automation_from_nl()
      │
      ├─ NLAutomationGenerator.generate()
      │  │
      │  ├─ Step 1: Build Automation Context
      │  │  └─ _build_automation_context()
      │  │     └─ DataAPIClient.fetch_entities() [GET http://data-api:8006/api/entities]
      │  │        └─ Data API → SQLite metadata.db
      │  │           Returns: [{ entity_id: "light.kitchen", friendly_name: "Kitchen Light", ... }]
      │  │
      │  ├─ Step 2: Build OpenAI Prompt
      │  │  └─ _build_prompt(request, context)
      │  │     └─ _summarize_devices(context)
      │  │        Returns: "Available devices:\n- Lights (10): Kitchen Light, Bedroom Light, ..."
      │  │
      │  ├─ Step 3: Call OpenAI API
      │  │  └─ _call_openai(prompt)
      │  │     └─ OpenAIClient.chat.completions.create()
      │  │        Model: gpt-4o-mini
      │  │        Temperature: 0.3
      │  │        Returns: JSON with { yaml, title, description, explanation, confidence }
      │  │
      │  ├─ Step 4: Parse & Validate YAML
      │  │  └─ yaml.safe_load(automation_data['yaml'])
      │  │     └─ If invalid: _retry_generation() [retry with error feedback]
      │  │
      │  ├─ Step 5: Safety Validation
      │  │  └─ SafetyValidator.validate(yaml)
      │  │     │
      │  │     ├─ _check_climate_extremes()      [Rule 1]
      │  │     ├─ _check_bulk_device_off()       [Rule 2]
      │  │     ├─ _check_security_disable()      [Rule 3]
      │  │     ├─ _check_time_constraints()      [Rule 4]
      │  │     ├─ _check_excessive_triggers()    [Rule 5]
      │  │     ├─ _check_destructive_actions()   [Rule 6]
      │  │     │
      │  │     ├─ _calculate_safety_score(issues)
      │  │     │  Returns: 0-100 (deduct points for critical/warning/info)
      │  │     │
      │  │     └─ _determine_pass(score, issues)
      │  │        Returns: SafetyResult { passed, safety_score, issues, can_override, summary }
      │  │
      │  └─ Step 6: Calculate Confidence
      │     └─ _calculate_confidence(request, automation_data, safety_result)
      │        Factors: OpenAI confidence, request length, safety score, clarification
      │        Returns: 0.0-1.0
      │
      └─ Step 7: Store as Suggestion
         └─ Database (SQLite ai_automation.db)
            INSERT INTO suggestions (
              title, description, automation_yaml,
              status='pending', confidence, category='user_request'
            )
            Returns: suggestion_id

4. Response to Frontend
   └─ {
        success: true,
        suggestion_id: 42,
        automation: { yaml, title, description, explanation, confidence },
        safety: { score: 95, passed: true, summary: "✅ Passed" },
        next_steps: "Review and approve suggestion #42"
      }

5. Frontend Updates
   └─ NLInput.tsx
      ├─ Shows success message
      ├─ Calls onSuccess() → loadData()
      └─ New suggestion appears in list below

Total Time: 3-5 seconds
```

---

## Call Tree 2: Approve & Deploy Automation

### User Flow: Click "Approve & Deploy"

```
1. User (health-dashboard:3000)
   └─ AIAutomationsTab.tsx
      └─ handleApprove(suggestionId)
         └─ confirm("Deploy this automation to Home Assistant?")

2. Frontend → Backend API Call
   └─ POST http://localhost:8018/api/deploy/{suggestion_id}
      Body: { force_deploy: false }

3. AI Automation Service (deployment_router.py)
   └─ deploy_suggestion(suggestion_id, request)
      │
      ├─ Step 1: Fetch Suggestion from Database
      │  └─ SELECT * FROM suggestions WHERE id = suggestion_id
      │     └─ If status != 'approved': Allow deployment anyway (for UX)
      │
      ├─ Step 2: Safety Validation (AI1.19)
      │  └─ If NOT force_deploy:
      │     │
      │     ├─ HAClient.list_automations()
      │     │  └─ GET http://192.168.1.86:8123/api/states
      │     │     Filter: entity_id starts with "automation."
      │     │     Returns: List of existing HA automations
      │     │
      │     └─ SafetyValidator.validate(yaml, existing_automations)
      │        │
      │        ├─ Run all 6 safety rules (see Call Tree 1, Step 5)
      │        │
      │        └─ If NOT passed:
      │           └─ HTTPException(400, {
      │                error: "Safety validation failed",
      │                safety_score, issues, can_override, summary
      │              })
      │              STOP HERE - Return to user with errors
      │
      ├─ Step 3: Deploy to Home Assistant
      │  └─ HAClient.deploy_automation(yaml)
      │     └─ Parse YAML to dict
      │     └─ Extract automation_id from alias
      │     └─ POST http://192.168.1.86:8123/api/services/automation/reload
      │        Headers: Authorization: Bearer {HA_TOKEN}
      │        Returns: { success: true, automation_id: "automation.morning_kitchen_light" }
      │
      ├─ Step 4: Store Version for Rollback (AI1.20)
      │  └─ store_version(db, automation_id, yaml, safety_score)
      │     │
      │     ├─ INSERT INTO automation_versions (automation_id, yaml_content, deployed_at, safety_score)
      │     │
      │     └─ Cleanup old versions
      │        └─ SELECT * FROM automation_versions WHERE automation_id = ? ORDER BY deployed_at DESC
      │        └─ If count > 3: DELETE versions beyond last 3
      │        └─ Database now has: [v3_current, v2_previous, v1_older]
      │
      └─ Step 5: Update Suggestion Status
         └─ UPDATE suggestions SET
              status='deployed',
              ha_automation_id=automation_id,
              deployed_at=NOW()
            WHERE id=suggestion_id

4. Response to Frontend
   └─ {
        success: true,
        data: {
          suggestion_id, automation_id, status: "deployed",
          safety_score: 95,
          safety_warnings: []
        }
      }

5. Frontend Updates
   └─ Shows alert: "✅ Deployed successfully! Safety score: 95/100"
   └─ Calls loadData() → Refreshes suggestion list
   └─ Suggestion now shows status="deployed" with rollback button

Total Time: 1-2 seconds
```

---

## Call Tree 3: Rollback Automation

### User Flow: Click "Rollback to Previous Version"

```
1. User (health-dashboard:3000)
   └─ AIAutomationsTab.tsx
      └─ handleRollback(automationId)
         └─ reason = prompt("Why are you rolling back?")

2. Frontend → Backend API Call
   └─ POST http://localhost:8018/api/deploy/{automation_id}/rollback

3. AI Automation Service (deployment_router.py)
   └─ rollback_automation(automation_id)
      │
      └─ rollback_to_previous(db, automation_id, ha_client, safety_validator)
         │
         ├─ Step 1: Get Version History
         │  └─ SELECT * FROM automation_versions
         │     WHERE automation_id = ?
         │     ORDER BY deployed_at DESC
         │     LIMIT 3
         │     Returns: [v3_current, v2_previous, v1_older]
         │
         ├─ Step 2: Validate Has Previous Version
         │  └─ If count < 2: raise ValueError("No previous version available")
         │
         ├─ Step 3: Get Previous Version
         │  └─ previous_version = versions[1]  # Index 1 is previous
         │
         ├─ Step 4: Validate Safety of Previous Version
         │  └─ SafetyValidator.validate(previous_version.yaml_content)
         │     │
         │     └─ If NOT passed:
         │        └─ raise ValueError("Previous version fails current safety checks")
         │           Note: Safety standards may have changed since original deployment
         │           STOP HERE - Don't rollback unsafe automation
         │
         ├─ Step 5: Deploy Previous Version to HA
         │  └─ HAClient.deploy_automation(previous_version.yaml_content, automation_id)
         │     └─ POST http://192.168.1.86:8123/api/services/automation/reload
         │        Returns: { success: true, automation_id }
         │
         └─ Step 6: Store Rollback as New Version
            └─ store_version(db, automation_id, previous_yaml, safety_score)
               └─ Creates new version record (audit trail)
               └─ Now have: [v1_rollback, v3_old_current, v2_previous]
               └─ Cleanup keeps last 3: [v1_rollback, v3_old, v2_previous]

4. Response to Frontend
   └─ {
        success: true,
        data: {
          automation_id, rolled_back_to, rolled_back_at, safety_score
        }
      }

5. Frontend Updates
   └─ Shows alert: "✅ Rolled back successfully!"
   └─ Refreshes suggestion list
   └─ HA now running previous version

Total Time: <1 second
```

---

## Call Tree 4: Pattern-Based Suggestion Generation (Daily)

### Automated Flow: Daily at 3 AM

```
1. DailyAnalysisScheduler (scheduler/daily_analysis.py)
   └─ Cron: "0 3 * * *" triggers run_analysis()

2. Analysis Job Execution
   └─ analysis_router.py → trigger_manual_analysis()
      │
      ├─ Phase 1: Fetch Historical Events (30 days)
      │  └─ InfluxDBClient.query_events(start=-30d, end=now)
      │     └─ InfluxDB query:
      │        FROM bucket "home_assistant_events"
      │        WHERE time >= -30d
      │        Returns: DataFrame with ~10k-100k events
      │
      ├─ Phase 2: Pattern Detection (3 detectors in parallel)
      │  │
      │  ├─ TimeOfDayDetector.detect_patterns(events)
      │  │  └─ Group by device_id + hour
      │  │  └─ Find consistent usage times
      │  │  └─ Returns: [{device_id, hour, occurrences, confidence}, ...]
      │  │
      │  ├─ CoOccurrenceDetector.detect_patterns(events)
      │  │  └─ Find devices used within 5 minutes of each other
      │  │  └─ Returns: [{device1, device2, co_occurrence_rate}, ...]
      │  │
      │  └─ AnomalyDetector.detect_patterns(events)
      │     └─ Use Isolation Forest to find regular manual interventions
      │     └─ Returns: [{device_id, hour, pattern_type: "anomaly_opportunity"}, ...]
      │
      ├─ Phase 3: Store Patterns
      │  └─ For each pattern:
      │     └─ INSERT INTO patterns (pattern_type, device_id, metadata, confidence)
      │
      ├─ Phase 4: Generate Suggestions from Patterns
      │  └─ For each high-confidence pattern:
      │     │
      │     ├─ OpenAIClient.generate_automation_suggestion(pattern, device_context)
      │     │  └─ Build prompt with pattern details
      │     │  └─ Call OpenAI (gpt-4o-mini)
      │     │  └─ Returns: AutomationSuggestion { alias, description, yaml, rationale }
      │     │
      │     ├─ SafetyValidator.validate(yaml)
      │     │  └─ Run 6 safety rules
      │     │  └─ Returns: SafetyResult
      │     │
      │     └─ Store if safe
      │        └─ INSERT INTO suggestions (
      │             pattern_id, title, description, automation_yaml,
      │             status='pending', confidence, category
      │           )
      │
      └─ Phase 5: Publish MQTT Notification
         └─ MQTTClient.publish("ha-ai/events/analysis_complete", {
              patterns_detected: 12,
              suggestions_generated: 5,
              duration_seconds: 180
            })

3. Results Available
   └─ User opens AI Automations tab
   └─ Sees 5 new pattern-based suggestions
   └─ Can review, approve, deploy

Analysis Time: 3-10 minutes (depending on data volume)
```

---

## Call Tree 5: Safety Validation (Detailed)

### Internal Flow: SafetyValidator.validate()

```
Input: automation_yaml (string), existing_automations (list)

1. Parse YAML
   └─ yaml.safe_load(automation_yaml)
      └─ If YAMLError: Return { passed: false, score: 0, issues: [yaml_syntax] }

2. Run 6 Safety Rules in Sequence

   Rule 1: Check Climate Extremes
   └─ For each action in automation.action:
      └─ If service == "climate.set_temperature":
         ├─ Check temperature in range [55°F, 85°F]
         ├─ If outside range: Issue { rule: "climate_extremes", severity: "critical" }
         └─ If no hvac_mode check: Issue { rule: "climate_extremes", severity: "warning" }

   Rule 2: Check Bulk Device Shutoff
   └─ For each action:
      └─ If service contains "turn_off":
         ├─ Check if target.area_id == "all"
         ├─ Check if entity_id contains "all"
         ├─ Check if affecting >3 areas
         └─ If yes: Issue { rule: "bulk_device_off", severity: "critical" }

   Rule 3: Check Security Disable
   └─ For each action:
      └─ If service == "automation.turn_off":
         ├─ Check entity_id for keywords: ["security", "alarm", "lock", "door", "motion", "camera"]
         └─ If found: Issue { rule: "security_disable", severity: "critical" }

   Rule 4: Check Time Constraints
   └─ has_time_condition = check automation.condition for time or state
   └─ has_destructive_action = check for turn_off, close, lock services
   └─ If destructive AND no constraints:
      └─ Issue { rule: "time_constraints", severity: "warning" }

   Rule 5: Check Excessive Triggers
   └─ For each trigger:
      ├─ If platform == "time_pattern" AND minutes == "*":
      │  └─ Issue { rule: "excessive_triggers", severity: "warning", message: "Triggers every minute" }
      └─ If platform == "state" AND entity is power/temp sensor AND no "for" duration:
         └─ Issue { rule: "excessive_triggers", severity: "info" }

   Rule 6: Check Destructive Actions
   └─ For each action:
      └─ If service in ["homeassistant.restart", "homeassistant.stop", "script.reload"]:
         └─ Issue { rule: "destructive_actions", severity: "critical" }

3. Check Conflicts (if existing_automations provided)
   └─ For each existing automation:
      └─ Compare triggers and actions
      └─ If same trigger, conflicting action:
         └─ Issue { rule: "conflicting_automation", severity: "warning" }

4. Calculate Safety Score
   └─ Start at 100
   └─ For each issue:
      ├─ critical: -30 points
      ├─ warning: -10 points
      └─ info: -5 points
   └─ Return: max(0, score)

5. Determine Pass/Fail
   └─ based on safety_level:
      ├─ strict: score >= 80 AND no critical issues
      ├─ moderate: score >= 60 AND no critical issues
      └─ permissive: score >= 40

6. Return SafetyResult
   └─ {
        passed: bool,
        safety_score: int (0-100),
        issues: [SafetyIssue],
        can_override: bool,
        summary: string
      }

Performance: ~17ms average (very fast!)
```

---

## Call Tree 6: Database Schema & Relationships

```
SQLite: ai_automation.db
│
├─ patterns (Pattern detection results)
│  ├─ id (PK)
│  ├─ pattern_type (time_of_day, co_occurrence, anomaly)
│  ├─ device_id
│  ├─ pattern_metadata (JSON)
│  ├─ confidence (0-1)
│  ├─ occurrences
│  └─ created_at
│
├─ suggestions (Automation suggestions)
│  ├─ id (PK)
│  ├─ pattern_id (FK → patterns.id, nullable)
│  ├─ title
│  ├─ description
│  ├─ automation_yaml (TEXT)
│  ├─ status (pending, approved, deployed, rejected)
│  ├─ confidence (0-1)
│  ├─ category (user_request, energy, comfort, security, convenience)
│  ├─ priority (high, medium, low)
│  ├─ created_at
│  ├─ updated_at
│  ├─ deployed_at
│  └─ ha_automation_id (for rollback)
│
└─ automation_versions (Rollback history - AI1.20)
   ├─ id (PK)
   ├─ automation_id (INDEX)
   ├─ yaml_content (TEXT)
   ├─ deployed_at
   └─ safety_score (0-100)
   
   Constraint: Keep only last 3 per automation_id (auto-cleanup)

SQLite: metadata.db (data-api)
│
├─ devices (HA device registry)
│  └─ Used for device context in NL generation
│
└─ entities (HA entity registry)
   └─ Fetched by NL generator for available device list
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Types: "Turn on kitchen light at 7 AM"                     │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
      ┌──────────────────────────────┐
      │   health-dashboard (3000)    │
      │   - AIAutomationsTab         │
      │   - NLInput component         │
      └──────────────┬───────────────┘
                     │ POST /api/nl/generate
                     ▼
      ┌──────────────────────────────┐
      │ ai-automation-service (8018) │
      │ - NLAutomationGenerator      │
      └──────────────┬───────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌────────┐  ┌─────────┐  ┌──────────┐
   │data-api│  │ OpenAI  │  │  Safety  │
   │ (8006) │  │   API   │  │Validator │
   └────┬───┘  └────┬────┘  └─────┬────┘
        │           │             │
        │ Entities  │ YAML        │ SafetyResult
        │           │             │
        └───────────┴─────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │ SQLite Database  │
           │ - suggestions    │
           └─────────┬────────┘
                     │ suggestion_id
                     ▼
      ┌──────────────────────────────┐
      │ User Clicks "Approve"        │
      └──────────────┬───────────────┘
                     │ POST /api/deploy/{id}
                     ▼
      ┌──────────────────────────────┐
      │ ai-automation-service        │
      │ - SafetyValidator (validate) │
      └──────────────┬───────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌──────────┐
   │   HA    │ │ SQLite  │ │  Store   │
   │   API   │ │versions │ │ Version  │
   └────┬────┘ └────┬────┘ └─────┬────┘
        │           │            │
        │ Deploy    │ Last 3     │ Auto-cleanup
        │           │            │
        └───────────┴────────────┘
                     │
                     ▼
           ┌──────────────────┐
           │ Automation in HA │
           │ Ready to trigger │
           └──────────────────┘
```

---

## API Endpoint Reference

### Natural Language Generation (AI1.21)
```
POST /api/nl/generate
Request:  { request_text: string, user_id: string }
Response: { success, suggestion_id, automation: {yaml, title, ...}, safety: {...} }
Time: 3-5s

POST /api/nl/clarify/{suggestion_id}
Request:  { clarification_text: string }
Response: { success, automation: {...}, safety: {...} }
Time: 3-5s

GET /api/nl/examples
Response: { examples: {...}, tips: [...] }
Time: <10ms

GET /api/nl/stats
Response: { total_requests, approval_rate, openai_usage: {...} }
Time: <100ms
```

### Deployment with Safety (AI1.19)
```
POST /api/deploy/{suggestion_id}
Request:  { force_deploy: bool }
Response: { success, data: { automation_id, safety_score, safety_warnings } }
Time: 1-2s
Validation: Runs 6 safety rules before deployment
```

### Rollback (AI1.20)
```
POST /api/deploy/{automation_id}/rollback
Response: { success, data: { rolled_back_to, safety_score } }
Time: <1s
Validation: Previous version must pass current safety checks

GET /api/deploy/{automation_id}/versions
Response: { versions: [{id, deployed_at, safety_score, is_current}], can_rollback }
Time: <50ms
```

---

## Performance Metrics

| Operation | Average Time | Target | Status |
|-----------|-------------|--------|--------|
| Safety Validation | 17ms | <500ms | ✅ 34x faster |
| Version Storage | <50ms | <100ms | ✅ Fast |
| Version Retrieval | <10ms | <100ms | ✅ Very fast |
| NL Generation | 3-4s | <5s | ✅ Acceptable |
| Deployment to HA | 500ms-1s | <2s | ✅ Fast |
| Rollback | <1s | <2s | ✅ Fast |
| Pattern Analysis | 7-15min | <30min | ✅ Good |

---

## Security & Safety Features

### Safety Validation Rules
1. ✅ **Climate Extremes** - Prevents dangerous temperature settings
2. ✅ **Bulk Shutoff** - Blocks "turn off all" patterns
3. ✅ **Security Disable** - Never disables security systems
4. ✅ **Time Constraints** - Requires conditions for destructive actions
5. ✅ **Excessive Triggers** - Warns on high-frequency triggers
6. ✅ **Destructive Actions** - Blocks system-level service calls

### Safety Levels
- **Strict:** score >=80, no critical issues
- **Moderate:** score >=60, no critical issues (default)
- **Permissive:** score >=40

### Override Mechanism
- `force_deploy=true` bypasses non-critical checks
- **Cannot override:** security_disable, destructive_actions (critical rules)

---

## Error Handling & Recovery

### NL Generation Failures
```
OpenAI API Error
    └─ Automatic retry (up to 3 attempts via tenacity)
    └─ If all retries fail: Return error with clarification_needed
    └─ User can rephrase and try again

Invalid YAML Generated
    └─ Detected by yaml.safe_load()
    └─ Automatic retry with error feedback to OpenAI
    └─ If retry fails: Return error, ask user to rephrase

Safety Validation Failure
    └─ Deployment blocked
    └─ Detailed issues returned to user
    └─ User can fix automation or use force_deploy (if allowed)
```

### Rollback Failures
```
No Previous Version
    └─ Error: "Need at least 2 versions to rollback"
    └─ User informed, no action taken

Previous Version Unsafe
    └─ Validate with current safety rules
    └─ If fails: Block rollback with reason
    └─ User must fix current version instead

HA Deployment Error
    └─ Rollback transaction fails
    └─ No changes made to database
    └─ Error returned to user
```

---

## Integration Points

### With Existing Services

**data-api (8006):**
- Provides device/entity context for NL generation
- SQLite metadata.db queried for available devices
- Used in prompt building

**Home Assistant (8123):**
- Target for automation deployment
- REST API: /api/services/automation/reload
- State API: /api/states (for existing automations)

**InfluxDB (8086):**
- Historical events for pattern detection
- Not used by NL generation (only pattern analysis)

---

## Configuration Flow

```
infrastructure/env.ai-automation
    ↓
services/ai-automation-service/src/config.py
    ↓ (Settings class with defaults)
services/ai-automation-service/src/main.py
    ↓ (Initialize clients)
API Routers (nl_generation_router, deployment_router)
    ↓ (Use configured clients)
Runtime Operations
```

**Key Settings:**
- `SAFETY_LEVEL`: strict/moderate/permissive (default: moderate)
- `NL_MODEL`: gpt-4o-mini (cost-effective)
- `NL_TEMPERATURE`: 0.3 (consistent output)
- `SAFETY_ALLOW_OVERRIDE`: true (allow force_deploy)

---

## Testing & Validation

### Automated Tests (41 total)
- **Safety Validation:** 22 tests (0.38s)
- **Rollback:** 7 tests (3.70s)
- **NL Generation:** 12 tests (2.60s)
- **Total:** 41 tests in 6.68s ✅

### Manual Testing Required
- [ ] Real OpenAI API calls
- [ ] Actual HA deployment
- [ ] Live rollback testing
- [ ] Mobile device testing

---

## Monitoring & Observability

### Logs to Watch
```bash
# AI service logs
docker-compose logs -f ai-automation-service

# Look for:
- "🤖 Generating automation from NL"
- "🛡️ Running safety validation"
- "✅ Safety validation passed: score=X"
- "📝 Version stored for rollback"
- "⏪ Rolling back X to version from Y"
```

### Metrics to Track
- NL generation success rate
- Safety validation block rate
- Rollback frequency
- OpenAI API costs
- Average confidence scores

---

**Document Status:** Complete Call Tree & Data Flow  
**Last Updated:** October 16, 2025  
**Related Docs:** See implementation/ folder for detailed summaries

