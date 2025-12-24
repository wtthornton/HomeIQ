# Conversational Automation UI - User Guide

**Last Updated:** October 19, 2025  
**Version:** 2.0.0 (Story AI1.24)

---

## Overview

The AI Automation system now uses a **conversational, description-first approach** to help you create Home Assistant automations. Instead of showing you YAML code immediately, it describes automation ideas in plain English that you can refine with natural language before approving.

---

## Getting Started

### Access the UI

Open your browser to: **http://localhost:3001/**

You'll see the main dashboard with suggestion cards organized by status.

---

## Understanding Status States

Suggestions move through these states:

```
📝 Draft → ✏️ Refining → ✅ Ready → 🚀 Deployed
              ↓            ↓
          ❌ Rejected   ❌ Rejected
```

### Status Definitions

| Status | Icon | Description | Actions Available |
|--------|------|-------------|-------------------|
| **Draft** | 📝 | New suggestion, description only, no YAML yet | Refine, Approve, Reject |
| **Refining** | ✏️ | You're editing the description | Continue Refining, Approve, Reject |
| **Ready** | ✅ | Approved with generated YAML, ready to deploy | Deploy, Reject |
| **Deployed** | 🚀 | Active automation in Home Assistant | View in HA |
| **Rejected** | ❌ | You rejected this suggestion | Archive |

---

## How to Use the Conversational Flow

### Step 1: View Draft Suggestions

When you first open the UI, you'll see suggestions in the **Draft** tab. Each card shows:

- **Title**: "Turn on Office Lights at 7:00am"
- **Description**: "This automation would automatically turn on your office lights at 7:00am every morning based on your consistent usage pattern over the last 30 days."
- **Category Badge**: Comfort, Energy, Security, or Convenience
- **Confidence Score**: How confident the AI is (e.g., 92%)
- **Action Buttons**: Refine, Approve, Reject

**No YAML code is shown yet!** You're just seeing the automation idea.

### Step 2: Refine (Optional)

If you want to change the suggestion, click **"Refine"**.

An input box appears where you can type changes in natural language:

**Examples:**
```
"Make it 6:30am instead"
"Change to 8am"
"Only on weekdays"
"Add a condition for when I'm home"
"Turn it off instead of on"
```

Click **"Send"** or press Enter. The AI will update the description based on your request.

**You can refine multiple times!** Each refinement is tracked, and you can see the conversation history.

### Step 3: Approve

When you're happy with the description, click **"Approve"**.

The AI will:
1. Generate Home Assistant YAML code
2. Validate the YAML for safety
3. Show you the automation code
4. Change status to **"Ready"**

**Now you can see the YAML!** It's shown in a code block with syntax highlighting.

### Step 4: Deploy

When you're ready to activate the automation, click **"Deploy"**.

The system will:
1. Push the YAML to your Home Assistant
2. Create the automation with a unique ID
3. Enable it automatically
4. Change status to **"Deployed"**

**Check Home Assistant:** Go to Settings → Automations to see your new automation!

### Alternative: Reject

At any point, you can click **"Reject"** if you don't want the suggestion.

The suggestion moves to the **Rejected** tab and won't be shown again.

---

## Example Walkthrough

### Scenario: Morning Light Automation

**1. Initial Suggestion (Draft)**
```
Title: Turn on Office Lights at 7:00am

Description: This automation would automatically turn on your office 
lights at 7:00am every morning. Based on your consistent usage pattern 
over the last 30 days, this would eliminate the need to manually turn 
them on when you start work.

Category: Comfort
Confidence: 92%
```

**2. First Refinement**
```
You type: "Make it 6:30am instead"

AI updates to:
Title: Turn on Office Lights at 6:30am

Description: This automation would automatically turn on your office 
lights at 6:30am every morning. Based on your consistent usage pattern 
over the last 30 days, this gives you lights ready earlier when you 
start work.
```

**3. Second Refinement**
```
You type: "Only on weekdays"

AI updates to:
Title: Turn on Office Lights at 6:30am on Weekdays

Description: This automation would automatically turn on your office 
lights at 6:30am on weekdays (Monday-Friday). Based on your usage 
pattern, this ensures lights are ready for work days while saving 
energy on weekends.
```

**4. Approve**
```
Click "Approve"

AI generates YAML:
```yaml
alias: "AI Suggested: Office Lights at 6:30am Weekdays"
description: "Automatically turn on office lights at 6:30am on weekdays"
trigger:
  - platform: time
    at: "06:30:00"
condition:
  - condition: time
    weekday:
      - mon
      - tue
      - wed
      - thu
      - fri
action:
  - service: light.turn_on
    target:
      entity_id: light.office
```

**5. Deploy**
```
Click "Deploy"

✅ Automation deployed to Home Assistant!
Automation ID: automation.ai_suggested_office_lights_weekdays
```

**6. Check Home Assistant**
```
Settings → Automations → "AI Suggested: Office Lights at 6:30am Weekdays"
Status: Enabled ✅
```

---

## Tips & Best Practices

### Refinement Tips

**Be Specific:**
- ✅ "Change to 6:30am"
- ❌ "Earlier"

**Use Natural Language:**
- ✅ "Only when I'm home"
- ✅ "Turn off instead of on"
- ✅ "Add a 10 minute delay"

**One Change at a Time:**
- Better to refine multiple times than make complex requests
- Each refinement is tracked in conversation history

### Review Before Deploying

**Check the YAML:**
- Verify entity IDs are correct
- Confirm times and conditions match your intent
- Look for any safety warnings

**Test First:**
- You can manually test the automation in Home Assistant
- Go to Settings → Automations → Run Actions

### Managing Suggestions

**Filter by Status:**
- Use tabs to see suggestions at different stages
- Draft = need review
- Ready = approved, not yet deployed
- Deployed = active in HA

**Sort by Confidence:**
- Higher confidence = more reliable pattern detected
- Focus on 80%+ confidence suggestions first

**Categories:**
- **Energy**: Power saving, electricity optimization
- **Comfort**: Temperature, lighting, ambiance
- **Security**: Safety, locks, monitoring
- **Convenience**: Time-saving, routine automation

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + A` | Select all pending suggestions |
| `Ctrl/Cmd + Enter` | Approve selected suggestion |
| `Delete/Backspace` | Reject selected suggestion |
| `R` | Refine selected suggestion |
| `Esc` | Clear selection |

---

## Frequently Asked Questions

### Why don't I see any suggestions?

**New installation:** Trigger the first analysis run:
- Click "Run Analysis" button in the UI
- Or wait for the automatic 3 AM daily job

**Old data:** Existing suggestions from before the update might not display correctly. Delete them and trigger a new analysis.

### Can I edit the YAML directly?

Not in this UI. The YAML is generated from your approved description.

If you need custom YAML, you can:
1. Deploy the automation
2. Edit it directly in Home Assistant (Settings → Automations)

### What happens if I reject a suggestion?

It's moved to the Rejected tab and won't be shown again in the main feed. The pattern that generated it is still tracked, so future analysis might create a similar (but refined) suggestion.

### How often are new suggestions generated?

The system runs automatically at **3 AM daily**. It analyzes the last 30 days of usage patterns and generates 8-10 new suggestions.

You can also trigger manual analysis anytime by clicking **"Run Analysis"**.

### Can I undo a deployment?

Yes! In Home Assistant:
1. Go to Settings → Automations
2. Find the automation (starts with "AI Suggested:")
3. Click the three dots → Delete

Or just disable it without deleting.

### How much does this cost?

**OpenAI Usage:**
- ~$0.00005-0.00008 per description (initial generation)
- ~$0.00010-0.00015 per refinement (optional)
- ~$0.00015-0.00020 per YAML generation (on approval)

**Monthly estimate:** ~$0.50-$1.00 for daily suggestions

**Cost savings:** 60% savings on rejected suggestions (no YAML generated)

### Is my data sent to OpenAI?

**What's sent:**
- Device usage patterns (e.g., "light.office activated at 7am")
- Device names and types
- Your refinement requests

**What's NOT sent:**
- Your personal information
- Raw event data
- Specific sensor readings
- Your Home Assistant configuration

---

## Troubleshooting

### "No draft suggestions" message

**Cause:** No new suggestions generated yet

**Fix:**
1. Click "Run Analysis" button
2. Wait 2-4 minutes for analysis to complete
3. Refresh the page

### "API connection failed" error

**Cause:** Backend service not running

**Fix:**
```bash
docker ps | grep ai-automation-service
# If not running:
docker-compose up -d ai-automation-service
```

### Refinement doesn't work

**Cause:** OpenAI API key not configured or invalid

**Fix:**
1. Check `infrastructure/env.ai-automation`
2. Verify `OPENAI_API_KEY` is set
3. Restart service: `docker-compose restart ai-automation-service`

### YAML appears in draft suggestions

**Cause:** Old suggestions created before Story AI1.24

**Fix:** Delete old suggestions and trigger new analysis

---

## Related Resources

- **Backend API Documentation:** http://localhost:8018/docs
- **Main System Dashboard:** http://localhost:3000
- **Home Assistant:** http://192.168.1.86:8123
- **Technical Documentation:** `services/ai-automation-ui/README.md`

---

## Feedback & Support

This is Story AI1.24 (Conversational UI Cleanup). The conversational refinement system is production-ready but continues to evolve.

**Known limitations:**
- Feature-based and synergy-based suggestions still use old flow (will be updated)
- Some complex refinements might require multiple iterations
- YAML generation cannot create custom services (only standard HA services)

**Planned improvements:**
- Voice input for refinements
- Suggested refinements based on common patterns
- Multi-language support
- Mobile app integration

---

**Enjoy your conversational automation experience!** 🤖✨

