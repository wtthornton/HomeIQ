# How to Verify the Enhancer Agent is Working

## What the Enhancer Should Do

The Enhancer Agent **enhances your prompt** - it doesn't fix code directly. It should:

1. ✅ Take your simple prompt
2. ✅ Analyze it (intent, scope, domains)
3. ✅ Consult Industry Experts
4. ✅ Retrieve knowledge from RAG bases
5. ✅ Add requirements, architecture, quality standards
6. ✅ Return an **ENHANCED PROMPT** (not fix the code)

## What You're Seeing (From Screenshot)

In your screenshot, the agent is:
- ❌ Reading code files (DebugTab.tsx, HAAgentChat.tsx)
- ❌ Planning to fix the issue directly
- ❌ Acting like a dev agent, not an enhancer

**This suggests the enhancer may not be working, OR Cursor is using the enhanced prompt to trigger a dev agent.**

## How to Verify It's Working

### Test 1: Check for Enhanced Prompt Output

After running `@enhancer *enhance-quick`, you should see:

```
# Enhanced Prompt: [Your Original Prompt]

## Metadata
- **Intent**: [detected intent]
- **Domain**: [detected domains]
- **Scope**: [estimated scope]

## Requirements
[Functional and non-functional requirements]

## Domain Context (from Industry Experts)
[Expert consultation results with sources]

## Architecture Guidance
[Design patterns and technology recommendations]

## Quality Standards
[Security, testing, quality thresholds]

## Implementation Strategy
[Task breakdown]
```

**If you DON'T see this format**, the enhancer isn't working.

### Test 2: Look for Expert Consultation

The enhanced prompt should include:

```
## Domain Context (from Industry Experts)

#### Frontend & User Experience Domain
**Primary Expert (expert-frontend, 51%):**
- [Expert recommendations]
- [Best practices from knowledge base]

**Sources:**
- [From: react-dashboard-ui-patterns.md]
- [From: tech-stack.md]
```

**If you DON'T see expert consultation**, RAG isn't working.

### Test 3: Check for Knowledge Base Sources

Look for source citations like:
```
[From: HA_WEBSOCKET_CALL_TREE.md]
[From: tech-stack.md]
[From: react-dashboard-ui-patterns.md]
```

**If you DON'T see sources**, knowledge bases aren't being retrieved.

## What's Happening in Your Screenshot

Based on your screenshot, one of these is happening:

### Scenario A: Enhancer Not Invoked
- Cursor didn't recognize `@enhancer` command
- It treated it as a regular request
- A dev agent started working instead

**Solution**: Check if `@enhancer` is recognized. Try typing `@enhancer` and see if it autocompletes.

### Scenario B: Enhancer Ran, Then Dev Agent Triggered
- Enhancer enhanced the prompt
- Cursor automatically used the enhanced prompt
- A dev agent started implementing the fix

**Solution**: Scroll up in the chat to see if there's an enhanced prompt output before the file reading started.

### Scenario C: Enhancer Working But Output Hidden
- Enhancer ran successfully
- Output is in a collapsed section
- Dev agent is using the enhanced prompt

**Solution**: Look for a collapsible section or scroll up to see the full output.

## How to Test Properly

### Step 1: Simple Test (No Code Fixing)

```
@enhancer *enhance-quick "What database should I use for time-series data?"
```

**Expected Output:**
- Enhanced prompt with InfluxDB recommendation
- Expert consultation from time-series expert
- Knowledge base sources cited
- NO code file reading
- NO implementation planning

### Step 2: Verify Expert Consultation

```
@enhancer *enhance "How do I connect to Home Assistant WebSocket?"
```

**Expected Output:**
- Home Assistant expert consulted
- Knowledge from `home-assistant/` directory
- Sources like `HA_WEBSOCKET_CALL_TREE.md` cited
- WebSocket connection patterns included

### Step 3: Check Knowledge Base Retrieval

```
@enhancer *enhance "What are React best practices for dashboards?"
```

**Expected Output:**
- Frontend expert consulted
- Knowledge from `frontend-ux/` directory
- Sources like `react-dashboard-ui-patterns.md` cited
- React/TypeScript patterns included

## Troubleshooting

### Issue: No Enhanced Prompt Output

**Check:**
1. Is `@enhancer` recognized? (Try autocomplete)
2. Is TappsCodingAgents installed?
3. Are there any error messages?

**Solution:**
```powershell
# Test from CLI
cd C:\cursor\HomeIQ
python -m tapps_agents.cli enhancer enhance-quick "test prompt"
```

### Issue: No Expert Consultation

**Check:**
1. Does `.tapps-agents/experts.yaml` exist?
2. Does `.tapps-agents/domains.md` exist?
3. Are experts configured correctly?

**Solution:**
```powershell
# Verify files exist
Get-Content .tapps-agents\experts.yaml
Get-Content .tapps-agents\domains.md
```

### Issue: No Knowledge Base Sources

**Check:**
1. Does `.tapps-agents/knowledge/` have files?
2. Are files in correct domain directories?
3. Are files `.md` format?

**Solution:**
```powershell
# Count knowledge files
Get-ChildItem .tapps-agents\knowledge -Recurse -Filter "*.md" | Measure-Object
```

## Expected vs Actual Behavior

### ✅ CORRECT: Enhancer Working

```
User: @enhancer *enhance-quick "Fix scrollbar"

Enhancer Output:
# Enhanced Prompt: Fix scrollbar
## Metadata: UI fix, frontend domain, small scope
## Requirements: Vertical scrolling, responsive design
## Expert Consultation: Frontend expert recommends...
## Sources: [From: react-dashboard-ui-patterns.md]
## Implementation Strategy: 1. Add overflow-y-auto, 2. Test...
```

### ❌ INCORRECT: Enhancer Not Working

```
User: @enhancer *enhance-quick "Fix scrollbar"

Agent: Reading DebugTab.tsx...
Agent: Planning next moves...
[Starts fixing code directly]
```

## Quick Verification Checklist

- [ ] Enhanced prompt output appears (not just code reading)
- [ ] Expert consultation section is present
- [ ] Knowledge base sources are cited
- [ ] Metadata section shows domain detection
- [ ] Architecture guidance is included
- [ ] Implementation strategy is provided
- [ ] NO direct code file reading (that's dev agent behavior)

## Next Steps

1. **Run a simple test** (see Test 1 above)
2. **Check for enhanced prompt output** (should be formatted markdown)
3. **Verify expert consultation** (should mention experts)
4. **Confirm knowledge sources** (should cite .md files)
5. **If not working**, check troubleshooting section above

## See Also

- [Testing Guide](ENHANCER_TESTING_GUIDE.md)
- [Enhancer Agent Docs](../../TappsCodingAgents/docs/ENHANCER_AGENT.md)

