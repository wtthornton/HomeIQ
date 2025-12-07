# Enhancer Agent Testing Guide

**Date**: December 6, 2025  
**Status**: Ready for Testing

## Quick Test (In Cursor Chat)

### Test 1: Basic Enhancement

In Cursor chat, type:

```
@enhancer *enhance-quick "Add real-time performance monitoring dashboard"
```

**What to verify:**
- ✅ Enhancer responds without errors
- ✅ Enhanced prompt includes HomeIQ-specific context
- ✅ Mentions relevant technologies (React, TypeScript, InfluxDB)

### Test 2: Home Assistant Expert

```
@enhancer *enhance "How do I connect to Home Assistant WebSocket API?"
```

**What to verify:**
- ✅ Home Assistant expert is consulted
- ✅ Knowledge from `home-assistant/` directory is retrieved
- ✅ Includes WebSocket connection patterns
- ✅ References HomeIQ architecture (192.168.1.86:8123)

### Test 3: Technology Stack Query

```
@enhancer *enhance "What database should I use for time-series data?"
```

**What to verify:**
- ✅ References tech-stack.md content
- ✅ Recommends InfluxDB (from knowledge base)
- ✅ Mentions hybrid architecture (InfluxDB + SQLite)
- ✅ Includes version information (InfluxDB 2.7)

### Test 4: Full Enhancement Pipeline

```
@enhancer *enhance "Create a new service for weather data aggregation"
```

**What to verify:**
- ✅ All 7 stages execute
- ✅ Expert consultation happens
- ✅ Codebase context is injected
- ✅ Implementation strategy is provided
- ✅ Sources are cited

## CLI Testing

### Test from Terminal

```powershell
# Navigate to HomeIQ
cd C:\cursor\HomeIQ

# Quick enhancement test
python -m tapps_agents.cli enhancer enhance-quick "Add device health monitoring" --format markdown

# Full enhancement test
python -m tapps_agents.cli enhancer enhance "Create new InfluxDB query endpoint" --output test-enhanced.md
```

### Verify Output

Check that the enhanced prompt includes:
- ✅ Domain detection (IoT, time-series, etc.)
- ✅ Expert consultation results
- ✅ Knowledge base sources
- ✅ HomeIQ-specific patterns
- ✅ Technology recommendations

## Testing RAG Knowledge Bases

### Test Knowledge Base Retrieval

1. **Check Knowledge Base Files Exist**:
```powershell
Get-ChildItem .tapps-agents\knowledge -Recurse -Filter "*.md" | Measure-Object
# Should show 114+ files
```

2. **Test Specific Domain**:
```
@enhancer *enhance "What are the best practices for Home Assistant WebSocket connections?"
```

**Expected**: Should retrieve content from:
- `home-assistant/HA_WEBSOCKET_CALL_TREE.md`
- `home-assistant/tech-stack.md`
- `home-assistant/WEBSOCKET_TROUBLESHOOTING.md`

3. **Verify Sources in Output**:
The enhanced prompt should include source citations like:
```
[From: HA_WEBSOCKET_CALL_TREE.md]
[From: tech-stack.md]
```

## Testing Expert Consultation

### Verify Experts Are Loaded

The enhancer should automatically:
1. Load experts from `.tapps-agents/experts.yaml`
2. Match domains from prompt to experts
3. Consult relevant experts with weighted aggregation
4. Include expert knowledge in enhanced prompt

### Test Expert Consultation

```
@enhancer *enhance "How should I structure microservices for HomeIQ?"
```

**Expected**:
- ✅ Microservices expert is consulted
- ✅ Knowledge from `microservices-architecture/` is used
- ✅ References HomeIQ's 26 microservices
- ✅ Includes architecture patterns

## Verification Checklist

### Setup Verification

- [ ] `.tapps-agents/experts.yaml` exists with 8 experts
- [ ] `.tapps-agents/domains.md` exists with 8 domains
- [ ] `.tapps-agents/enhancement-config.yaml` exists
- [ ] `.tapps-agents/knowledge/` has 8 domain directories
- [ ] Each domain directory has knowledge files
- [ ] `tech-stack.md` is in relevant domains

### Functionality Verification

- [ ] Enhancer command executes without errors
- [ ] Enhanced prompts include domain-specific context
- [ ] Expert consultation happens automatically
- [ ] Knowledge base content is retrieved
- [ ] Sources are cited in output
- [ ] HomeIQ-specific patterns are included

## Troubleshooting

### Issue: "Expert not found"

**Solution**: Verify `.tapps-agents/experts.yaml` exists and expert IDs match `domains.md`

### Issue: "No knowledge found"

**Solution**: 
1. Check `.tapps-agents/knowledge/{domain}/` has files
2. Verify files are `.md` format
3. Check file encoding is UTF-8

### Issue: "Enhancer command not found"

**Solution**: 
1. Verify TappsCodingAgents is installed
2. Check Python path includes TappsCodingAgents
3. Try: `python -m tapps_agents.cli enhancer help`

### Issue: "No domain detected"

**Solution**: 
1. Use more specific prompts with domain keywords
2. Check `domains.md` has correct domain definitions
3. Verify expert primary_domain matches

## Next Steps After Testing

### 1. Review Enhanced Prompts

- Check if enhanced prompts are useful
- Verify knowledge base content is relevant
- Identify gaps in knowledge bases

### 2. Add Missing Knowledge

If certain topics aren't covered:
1. Identify missing knowledge
2. Add markdown files to appropriate domain
3. Re-run population script if needed

### 3. Refine Expert Configuration

- Adjust `min_expert_confidence` in `enhancement-config.yaml`
- Add more experts if needed
- Update domain mappings

### 4. Optimize Knowledge Bases

- Remove outdated information
- Add 2025 best practices
- Organize knowledge files better
- Add more cross-references

### 5. Create Custom Knowledge

For HomeIQ-specific patterns:
1. Document patterns in markdown
2. Add to appropriate domain directory
3. Use clear headers and keywords

## Example Test Scenarios

### Scenario 1: New Feature Request

**Prompt**: "Add device health monitoring dashboard"

**Expected Enhancement**:
- Detects: IoT, frontend, time-series domains
- Consults: IoT expert, Frontend expert, Time-Series expert
- Retrieves: Dashboard patterns, device monitoring docs, InfluxDB query patterns
- Includes: React/TypeScript patterns, HomeIQ architecture, implementation tasks

### Scenario 2: Architecture Question

**Prompt**: "How should I structure a new microservice?"

**Expected Enhancement**:
- Detects: microservices-architecture domain
- Consults: Microservices expert
- Retrieves: Architecture docs, service patterns, tech-stack.md
- Includes: HomeIQ's 26-service architecture, FastAPI patterns, Docker setup

### Scenario 3: Integration Question

**Prompt**: "How do I integrate with Home Assistant REST API?"

**Expected Enhancement**:
- Detects: home-assistant, iot-home-automation domains
- Consults: Home Assistant expert, IoT expert
- Retrieves: HA API docs, WebSocket patterns, tech-stack.md
- Includes: Connection patterns, authentication, error handling

## Success Criteria

✅ **Enhancer works**: Commands execute without errors  
✅ **Experts consulted**: Enhanced prompts show expert input  
✅ **Knowledge retrieved**: Sources are cited in output  
✅ **Context relevant**: Enhanced prompts are HomeIQ-specific  
✅ **Useful output**: Enhanced prompts improve original prompts  

## See Also

- [Enhancer Agent Guide](../../TappsCodingAgents/docs/ENHANCER_AGENT.md)
- [Knowledge Base Guide](.tapps-agents/knowledge/README.md)
- [RAG Setup Summary](RAG_KNOWLEDGE_BASE_SETUP.md)

