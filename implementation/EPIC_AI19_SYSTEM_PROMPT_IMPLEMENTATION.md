# Epic AI-19: System Prompt Implementation

**Date:** January 2025  
**Status:** ✅ Complete  
**Epic:** AI-19 - HA AI Agent Service Tier 1 Context Injection

---

## Summary

Implemented a comprehensive system prompt for the HA AI Agent Service following best practices for conversational AI agents. The system prompt defines the agent's role, behavior, and guidelines for creating Home Assistant automations.

---

## Implementation Details

### Files Created

1. **`services/ha-ai-agent-service/src/prompts/system_prompt.py`**
   - Contains the `SYSTEM_PROMPT` constant
   - Defines agent role, capabilities, communication style, automation guidelines, safety rules, and tool usage

2. **`services/ha-ai-agent-service/src/prompts/__init__.py`**
   - Package initialization with `SYSTEM_PROMPT` export

3. **`services/ha-ai-agent-service/docs/SYSTEM_PROMPT.md`**
   - Comprehensive documentation for the system prompt
   - Usage examples and integration guide

### Files Modified

1. **`services/ha-ai-agent-service/src/services/context_builder.py`**
   - Added import for `SYSTEM_PROMPT`
   - Added `get_system_prompt()` method
   - Added `build_complete_system_prompt()` method to combine system prompt with context

2. **`services/ha-ai-agent-service/src/main.py`**
   - Added `/api/v1/system-prompt` endpoint
   - Added `/api/v1/complete-prompt` endpoint

3. **`services/ha-ai-agent-service/README.md`**
   - Updated to include system prompt in Epic AI-19 components
   - Added API endpoint documentation

---

## System Prompt Structure

The system prompt is organized into 9 key sections:

1. **Role and Capabilities** - Defines the agent as a Home Assistant automation expert
2. **Context Awareness** - Explains Tier 1 context injection and how to use it
3. **Communication Style** - Conversational, clear, helpful, accurate, safety-first
4. **Automation Creation Guidelines** - Best practices for reliability, mode selection, organization
5. **Tool Usage** - When to use tools vs. when context is sufficient
6. **Safety and Security** - Critical safety rules and security considerations
7. **Response Format** - How to structure responses (explain, show, highlight, suggest)
8. **Error Handling** - How to handle errors and limitations
9. **Context Updates** - Understanding cached context and real-time verification

---

## Key Features

### Best Practices Followed

✅ **Clear Role Definition** - Explicitly defines agent purpose  
✅ **Specific Instructions** - Detailed automation creation guidelines  
✅ **Contextual Information** - References Tier 1 context injection  
✅ **Safety First** - Emphasizes safety and security  
✅ **Structured Design** - Organized sections for consistency  
✅ **Tool Guidance** - Clear instructions on tool usage  

### Integration Points

- **Context Builder**: System prompt can be combined with Tier 1 context
- **API Endpoints**: Three endpoints for different use cases:
  - `/api/v1/context` - Context only
  - `/api/v1/system-prompt` - System prompt only
  - `/api/v1/complete-prompt` - System prompt + context

### Token Budget

- **Base System Prompt**: ~500 tokens
- **Tier 1 Context**: ~1500 tokens
- **Complete Prompt**: ~2000 tokens

---

## API Endpoints

### Get System Prompt
```bash
GET /api/v1/system-prompt
```

Response:
```json
{
  "system_prompt": "You are a knowledgeable and helpful...",
  "token_count": 1234
}
```

### Get Complete Prompt (System + Context)
```bash
GET /api/v1/complete-prompt
```

Response:
```json
{
  "system_prompt": "You are a knowledgeable...\n\n---\n\nHOME ASSISTANT CONTEXT:\n...",
  "token_count": 2345
}
```

---

## Usage Example

```python
from src.services.context_builder import ContextBuilder

# Initialize context builder
context_builder = ContextBuilder(settings)
await context_builder.initialize()

# Get base system prompt
system_prompt = context_builder.get_system_prompt()

# Get complete prompt with context
complete_prompt = await context_builder.build_complete_system_prompt()

# Use with OpenAI
response = await openai_client.chat.completions.create(
    model="gpt-5.1",
    messages=[
        {"role": "system", "content": complete_prompt},
        {"role": "user", "content": "Turn on the office lights at 7 AM"}
    ],
    tools=[...]  # Home Assistant tools
)
```

---

## Research Basis

The system prompt was designed based on:

1. **Web Research**: Best practices for system prompt design (2024)
   - Clear role definition
   - Specific instructions and constraints
   - Contextual information inclusion
   - Avoid ambiguity and contradictions
   - Structured prompt design patterns

2. **Existing Patterns**: Referenced `unified_prompt_builder.py` from `ai-automation-service`
   - Home Assistant best practices
   - Automation reliability guidelines
   - Device capability examples

3. **Epic AI-19 Requirements**: 
   - Conversational AI agent
   - Tool-based architecture
   - Context injection system
   - Direct automation creation

---

## Testing

The system prompt can be tested via:

1. **API Endpoints**: Test `/api/v1/system-prompt` and `/api/v1/complete-prompt`
2. **Integration**: Use with OpenAI API to verify behavior
3. **Manual Review**: Review prompt structure and completeness

---

## Future Enhancements

Potential improvements for future epics:

- **Tier 2 Context**: Add entity details and existing automations summary
- **Dynamic Prompting**: Adjust prompt based on conversation context
- **Prompt Templates**: Support for different conversation styles
- **A/B Testing**: Test different prompt variations for effectiveness

---

## References

- Epic AI-19: HA AI Agent Service - Tier 1 Context Injection
- `services/ai-automation-service/src/prompt_building/unified_prompt_builder.py`
- Home Assistant Automation Best Practices
- OpenAI System Prompt Best Practices

---

## Conclusion

The system prompt implementation provides a solid foundation for the HA AI Agent Service. It follows best practices, integrates seamlessly with the context injection system, and provides clear guidelines for the agent's behavior. The prompt is ready for use with OpenAI GPT-5.1 and can be easily customized as needed.

