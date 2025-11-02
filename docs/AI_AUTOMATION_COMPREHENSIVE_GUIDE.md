# AI Automation System - Comprehensive Guide

**Version:** 1.1  
**Last Updated:** November 1, 2025  
**Status:** Production Ready  
**Epic:** AI1.19-22 (Enhanced)

---

## 📖 Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Features](#features)
4. [Architecture](#architecture)
5. [User Guide](#user-guide)
6. [API Reference](#api-reference)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)
9. [Cost & Performance](#cost--performance)

---

## Overview

The AI Automation System enables you to create Home Assistant automations through:

**Natural Language:** Type "Turn on kitchen light at 7 AM" → Get working automation  
**Pattern Detection:** AI analyzes usage and suggests automations automatically  
**Safety Validation:** 6-rule engine blocks dangerous automations  
**Simple Rollback:** Undo mistakes with one click

**Operational Cost:** ~$1/month  
**Setup Time:** Already deployed and running!

---

## Quick Start

### Access the Dashboard

1. **Open:** http://localhost:3001 (AI Automation UI - separate from Health Dashboard)
2. **Navigate to:** Ask AI tab
3. **See:** NL input at top, suggestions list below

### Create Your First Automation

**Type this in the blue box:**
```
Turn on kitchen light at 7 AM on weekdays
```

**Then:**
1. Click "✨ Generate Automation"
2. Wait 3-5 seconds
3. Review generated YAML (click "▶ View Automation YAML")
4. Click "✅ Approve & Deploy"
5. Check Home Assistant → Settings → Automations

**Your automation is now active!** 🎉

---

## Features

### ✨ Natural Language Generation (AI1.21)

**What:** Create automations from plain English  
**How:** Type request → AI generates YAML → You approve → Deploys to HA  
**Examples:**
- "Turn on porch light when motion detected after dark"
- "Close blinds at sunset"
- "Send notification when door left open 5 minutes"

**Behind the Scenes:**
- Fetches your actual devices from Home Assistant
- Uses OpenAI GPT-4o-mini to generate valid YAML
- Validates syntax automatically
- Retries if generation fails

---

### 🛡️ Safety Validation (AI1.19)

**What:** 6-rule engine that blocks dangerous automations  
**When:** Runs automatically before every deployment  
**Score:** 0-100 (must be ≥60 to deploy)

**Blocks:**
1. ❌ Extreme temperatures (>85°F or <55°F)
2. ❌ "Turn off all" patterns
3. ❌ Disabling security/alarm automations
4. ❌ System-level calls (restart, reload)

**Warns:**
5. ⚠️ Destructive actions without time constraints
6. ⚠️ High-frequency triggers (every minute)

**Results:**
- Safe automation → Deploys with score shown
- Unsafe automation → Blocked with detailed issues

---

### ⏪ Simple Rollback (AI1.20)

**What:** Undo automations that don't work  
**How:** One-click rollback to previous version  
**Storage:** Last 3 versions per automation

**When to Use:**
- Automation triggers too often
- Automation doesn't work as expected
- Want to test changes safely

**How It Works:**
1. Click "⏪ Rollback to Previous Version"
2. Enter reason (optional)
3. Previous version restored in HA
4. Safety validated before restore

---

### 📊 Pattern Detection (AI1.4-1.6)

**What:** Daily analysis finds automation opportunities  
**When:** Runs daily at 3 AM  
**Detects:**
- Time-of-day patterns (consistent usage times)
- Co-occurrence patterns (devices used together)
- Anomaly patterns (repeated manual interventions)

**Results:**
- 5-10 suggestions per week
- Appears in AI Automation UI (localhost:3001)
- Same approve/deploy workflow

---

## Architecture

### System Components

```
health-dashboard (3000) → ai-automation-service (8018) → Home Assistant (8123)
                                  ↓
                          data-api (8006) - Device context
                                  ↓
                          OpenAI API - YAML generation
                                  ↓
                          SQLite DB - Suggestions + versions
```

### Detailed Architecture

See: **[AI Automation System Architecture](architecture/ai-automation-system.md)**  
See: **[AI Automation Call Tree](AI_AUTOMATION_CALL_TREE.md)**

---

## User Guide

### Creating Automations with Natural Language

**Step 1: Write Your Request**

Be specific about:
- **Device:** Which device(s) to control
- **Action:** What should happen
- **Trigger:** When it should happen
- **Condition (optional):** Any special conditions

**Good Examples:**
- ✅ "Turn on kitchen light at 7 AM on weekdays"
- ✅ "Turn off heater when any window is open for 10 minutes"
- ✅ "Send notification when front door left open 5 minutes"
- ✅ "Close all blinds at sunset"

**Bad Examples:**
- ❌ "Turn on light" (which light? when?)
- ❌ "Do something with temperature" (too vague)
- ❌ "Make it comfortable" (AI needs specifics)

**Step 2: Review Generated Automation**

Check:
- ✅ Uses correct device names
- ✅ Trigger makes sense
- ✅ Action is what you want
- ✅ Safety score is high (≥80 is excellent)

**Step 3: Deploy**

- Click "✅ Approve & Deploy"
- System validates safety
- If safe: Deploys to Home Assistant
- If unsafe: Shows specific issues to fix

---

### Understanding Safety Scores

| Score | Meaning | Action |
|-------|---------|--------|
| **90-100** | ✅ Excellent - No issues | Deploy with confidence |
| **70-89** | ⚠️ Good - Minor warnings | Review warnings, usually safe to deploy |
| **60-69** | ⚠️ Acceptable - Some concerns | Review carefully before deploying |
| **40-59** | ❌ Risky - Multiple issues | Fix issues before deploying |
| **0-39** | ❌ Dangerous - Critical issues | Do not deploy, rethink automation |

**Note:** Score <60 blocks deployment (configurable)

---

### Using Rollback

**When Automation Misbehaves:**

1. Open http://localhost:3001 (AI Automation UI)
2. Navigate to the automation you want to rollback
3. Click "⏪ Rollback to Previous Version"
5. Enter reason (helps you remember why)
6. Previous version restored

**Limitations:**
- Need at least 2 versions (can't rollback first deployment)
- Previous version must pass current safety checks
- Only keeps last 3 versions

---

### Using Pattern Suggestions

**Daily at 3 AM:**
- AI analyzes last 30 days of usage
- Detects patterns in your behavior
- Generates 5-10 automation suggestions

**Review Process:**
1. Open http://localhost:3001 (AI Automation UI) in morning
2. See new "Pending" suggestions
3. Review each one
4. Approve useful ones, reject others

**Approval Rate:**
- Target: >60% approval rate
- If lower: Patterns may not be relevant
- Can adjust confidence threshold

---

## API Reference

### Generate from Natural Language

**Endpoint:** `POST /api/nl/generate`

**Request:**
```json
{
  "request_text": "Turn on kitchen light at 7 AM on weekdays",
  "user_id": "default"
}
```

**Response:**
```json
{
  "success": true,
  "suggestion_id": 42,
  "automation": {
    "yaml": "alias: Morning Kitchen Light\ntrigger:\n  - platform: time\n    at: '07:00:00'\n...",
    "title": "Morning Kitchen Light",
    "description": "Turns on kitchen light at 7 AM on weekdays",
    "explanation": "Uses time trigger with workday condition...",
    "confidence": 0.92
  },
  "safety": {
    "score": 100,
    "passed": true,
    "summary": "✅ Passed all safety checks"
  },
  "next_steps": "Review and approve suggestion #42 to deploy"
}
```

**Time:** 3-5 seconds  
**Cost:** ~$0.025 per request

---

### Deploy Automation

**Endpoint:** `POST /api/deploy/{suggestion_id}`

**Request:**
```json
{
  "force_deploy": false
}
```

**Response (Success):**
```json
{
  "success": true,
  "data": {
    "suggestion_id": 42,
    "automation_id": "automation.morning_kitchen_light",
    "status": "deployed",
    "safety_score": 95,
    "safety_warnings": []
  }
}
```

**Response (Safety Failure):**
```json
{
  "detail": {
    "error": "Safety validation failed",
    "safety_score": 40,
    "issues": [
      {
        "rule": "climate_extremes",
        "severity": "critical",
        "message": "Extreme temperature setting: 95°F",
        "suggested_fix": "Use reasonable temperature range (60-80°F)"
      }
    ],
    "can_override": true,
    "summary": "❌ 1 critical issues found (score: 40/100)"
  }
}
```

---

### Rollback Automation

**Endpoint:** `POST /api/deploy/{automation_id}/rollback`

**Response:**
```json
{
  "success": true,
  "data": {
    "automation_id": "automation.morning_kitchen_light",
    "rolled_back_to": "2025-10-16T11:00:00",
    "safety_score": 90
  }
}
```

**Time:** <1 second

---

### Get Examples

**Endpoint:** `GET /api/nl/examples`

**Response:**
```json
{
  "success": true,
  "examples": {
    "time_based": [
      "Turn on kitchen lights at 7 AM on weekdays",
      "Close all blinds at sunset"
    ],
    "condition_based": [
      "Turn off heater when window opens for 10 minutes",
      "Send notification when door left open 5 minutes"
    ]
  },
  "tips": [
    "Be specific about device names",
    "Include timing details",
    "Mention conditions if relevant"
  ]
}
```

---

## Configuration

### Environment Variables

**Located:** `infrastructure/env.ai-automation`

**Safety Validation:**
```bash
SAFETY_LEVEL=moderate              # strict, moderate, or permissive
SAFETY_ALLOW_OVERRIDE=true         # Allow force_deploy flag
SAFETY_MIN_SCORE=60                # Minimum score for deployment
```

**Natural Language:**
```bash
NL_GENERATION_ENABLED=true
NL_MODEL=gpt-4o-mini              # OpenAI model
NL_MAX_TOKENS=1500
NL_TEMPERATURE=0.3                 # 0.0-1.0 (lower = consistent)
```

**Home Assistant:**
```bash
HA_URL=http://192.168.1.86:8123
HA_TOKEN=<your-long-lived-token>
```

**OpenAI:**
```bash
OPENAI_API_KEY=sk-proj-...
```

---

### Safety Levels Explained

**Strict (score ≥80):**
- Most restrictive
- Blocks anything questionable
- Best for: Families with children, production systems

**Moderate (score ≥60) - DEFAULT:**
- Balanced approach
- Blocks critical issues, warns on concerns
- Best for: Most users

**Permissive (score ≥40):**
- Most lenient
- Allows more automations through
- Best for: Power users, testing environments

**Change Level:**
```bash
# In infrastructure/env.ai-automation
SAFETY_LEVEL=strict    # or moderate, or permissive
```

---

## Troubleshooting

### NL Generation Fails

**Symptom:** "Failed to generate automation"

**Possible Causes:**
1. OpenAI API key invalid or no credits
2. Network issues reaching OpenAI
3. data-api not responding (can't fetch devices)

**Solutions:**
```bash
# Check OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check data-api
curl http://localhost:8006/health

# Check ai-automation-service logs
docker-compose logs ai-automation-service | Select-String "error"
```

---

### Safety Validation Too Strict

**Symptom:** Safe automations getting blocked

**Solutions:**
1. **Lower safety level** to "permissive"
2. **Review specific issues** (may be legitimate concerns)
3. **Use force_deploy** for specific automation

```bash
# In env.ai-automation
SAFETY_LEVEL=permissive
SAFETY_MIN_SCORE=40
```

---

### Invalid Entity IDs in Automation

**Symptom:** "Invalid entity IDs in test YAML" or "Entity not found" errors

**What Happened:**
- Self-correction may have introduced invalid entity IDs during refinement
- Entity sanitization automatically fixes these (Nov 2025 update)

**Solutions:**
1. Check logs for sanitization activity:
```bash
docker-compose logs ai-automation-service | Select-String "Sanitized|Replaced"
```

2. Verify the fix was applied:
- Look for: `✅ Sanitized N entity IDs in refined YAML`
- Look for: `✅ Replaced {old_id} → {new_id}`

3. If still failing, check available entities:
```bash
curl http://localhost:8006/api/entities?domain=binary_sensor
curl http://localhost:8006/api/entities?domain=light
```

**New Feature (Nov 2025):** Entity sanitization automatically replaces invalid entity IDs with best matching valid ones during self-correction refinement.

---

### Can't Deploy to Home Assistant

**Symptom:** "Deployment failed" or "HA API error"

**Possible Causes:**
1. HA token expired
2. HA not accessible at configured URL
3. HA automation reload service unavailable

**Solutions:**
```bash
# Test HA connection
curl http://192.168.1.86:8123/api/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Generate new token in HA
# Profile → Long-Lived Access Tokens → Create Token

# Update in env.ai-automation
HA_TOKEN=<new-token>
```

---

### Rollback Not Working

**Symptom:** "No previous version available"

**Cause:** First deployment (no history yet)

**Solution:** Deploy automation at least twice before rollback available

---

**Symptom:** "Previous version fails safety checks"

**Cause:** Safety rules changed since original deployment

**Solution:** Edit and redeploy instead of rollback

---

## Cost & Performance

### Monthly Costs

**Pattern Analysis:**
- Frequency: Daily at 3 AM
- Cost per run: ~$0.003
- Monthly: ~$0.10 (30 runs)

**NL Generation:**
- Average request: ~$0.025
- Expected usage: 40 requests/month
- Monthly: ~$1.00

**Total:** ~$1.10/month 💰

### Performance Metrics

| Operation | Average | Target | Status |
|-----------|---------|--------|--------|
| NL Generation | 3-4s | <5s | ✅ Good |
| Safety Validation | 17ms | <500ms | ✅ Excellent |
| Deployment | 1-2s | <2s | ✅ Good |
| Rollback | <1s | <2s | ✅ Excellent |

---

## Best Practices

### Writing Good NL Requests

**Do:**
- ✅ Be specific: "Turn on **kitchen** light at **7 AM**"
- ✅ Include timing: "at 7 AM", "after sunset", "when motion detected"
- ✅ Use actual device names from your HA
- ✅ Start simple, add complexity later

**Don't:**
- ❌ Be vague: "Turn on light" (which one?)
- ❌ Use devices you don't have
- ❌ Combine too many actions in one request
- ❌ Request dangerous operations

---

### Safety Considerations

**Always Review:**
- Generated YAML before approving
- Safety score and warnings
- Devices and triggers used

**Never:**
- Override safety on critical security issues
- Deploy without reviewing YAML
- Ignore safety warnings

**Test First:**
- Create automation
- Monitor for one day
- Rollback if issues
- Adjust and redeploy

---

## Testing Checklist

### Before Production Use

- [ ] Test NL generation with 5 different requests
- [ ] Verify at least 1 deploys successfully to HA
- [ ] Confirm deployed automation actually triggers
- [ ] Test rollback functionality
- [ ] Review safety validation with unsafe request
- [ ] Check OpenAI costs after testing
- [ ] Verify mobile experience (if using phone)

### Weekly Monitoring

- [ ] Check pattern suggestions quality
- [ ] Review approval rate
- [ ] Monitor OpenAI costs
- [ ] Check for any misbehaving automations
- [ ] Review rollback frequency

---

## Example Automations

### Time-Based

**Request:** "Turn on kitchen lights at 7 AM on weekdays"

**Generated YAML:**
```yaml
alias: Morning Kitchen Lights
trigger:
  - platform: time
    at: "07:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.workday
    state: "on"
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
```

---

### Condition-Based

**Request:** "Turn off heater when any window is open for more than 10 minutes"

**Generated YAML:**
```yaml
alias: Heater Off When Window Open
trigger:
  - platform: state
    entity_id: binary_sensor.window
    to: "on"
    for: "00:10:00"
action:
  - service: climate.turn_off
    target:
      entity_id: climate.heater
```

---

### Multi-Action

**Request:** "Goodnight routine: turn off all lights, lock front door, set alarm"

**Generated YAML:**
```yaml
alias: Goodnight Routine
trigger:
  - platform: time
    at: "22:00:00"
action:
  - service: light.turn_off
    target:
      area_id: all
  - service: lock.lock
    target:
      entity_id: lock.front_door
  - service: alarm_control_panel.alarm_arm_home
    target:
      entity_id: alarm_control_panel.home
```

---

## Related Documentation

### Architecture
- [AI Automation System Architecture](architecture/ai-automation-system.md)
- [AI Automation Call Tree](AI_AUTOMATION_CALL_TREE.md)
- [Architecture Index](architecture/index.md)

### Implementation
- [Implementation Complete](../implementation/ENHANCED_EPIC_AI1_IMPLEMENTATION_COMPLETE.md)
- [Ready for Review](../implementation/READY_FOR_REVIEW.md)
- [Next Steps Roadmap](../implementation/NEXT_STEPS_ROADMAP.md)

### Stories
- [Story AI1.19: Safety Validation](stories/story-ai1-19-safety-validation-engine.md)
- [Story AI1.20: Simple Rollback](stories/story-ai1-20-simple-rollback.md)
- [Story AI1.21: Natural Language](stories/story-ai1-21-natural-language-request-generation.md)
- [Story AI1.22: Dashboard Integration](stories/story-ai1-22-simple-dashboard-integration.md)

---

## FAQ

**Q: How much does it cost to run?**  
A: ~$1.10/month (pattern analysis + NL generation)

**Q: Is it safe to use AI-generated automations?**  
A: Yes! 6-rule safety validation + rollback capability. Plus you review before deploying.

**Q: What if automation doesn't work?**  
A: One-click rollback restores previous version instantly.

**Q: Can I edit generated YAML?**  
A: Yes! Click expand YAML, copy it, edit in HA automation editor.

**Q: Does it work offline?**  
A: No, requires OpenAI API for NL generation. Pattern detection works offline.

**Q: Can I use a local LLM instead of OpenAI?**  
A: Not currently, but could be added in Phase 2 with Ollama.

**Q: How many automations can I create?**  
A: As many as Home Assistant can handle (1000s). System designed for 10-50.

---

## Changelog

### Version 1.1 (November 1, 2025)
- ✅ Post-refinement entity sanitization (prevents invalid entity IDs)
- ✅ Generic entity matching algorithm (works for all domains)
- ✅ Self-healing YAML generation

### Version 1.0 (October 16, 2025)
- ✅ Natural Language generation (AI1.21)
- ✅ Safety validation with 6 rules (AI1.19)
- ✅ Simple rollback capability (AI1.20)
- ✅ Unified dashboard integration (AI1.22)
- ✅ 41 tests, zero bugs, production ready

---

**Status:** ✅ Production Ready  
**Support:** See troubleshooting section or check logs  
**Feedback:** Welcome improvements based on real usage!

