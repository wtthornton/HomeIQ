# System Prompt Documentation

**Epic AI-19:** System prompt foundation  
**Epic AI-20:** Full conversational AI agent integration

## Overview

The HA AI Agent Service includes a comprehensive system prompt that defines the agent's role, behavior, and guidelines for interacting with users and creating Home Assistant automations. This system prompt is automatically injected into every conversation along with Tier 1 context, enabling the agent to provide accurate, context-aware responses.

## System Prompt Location

The system prompt is defined in:
- **File**: `src/prompts/system_prompt.py`
- **Constant**: `SYSTEM_PROMPT`

## System Prompt Structure

The system prompt is organized into the following sections:

### 1. Role and Capabilities
- Defines the agent as a knowledgeable Home Assistant automation assistant
- Lists expertise areas (automation creation, device capabilities, safety, YAML syntax)

### 2. Context Awareness
- Explains that the agent receives Tier 1 context at the start of each conversation
- Lists the context components (Entity Inventory, Areas, Services, Capabilities, Helpers & Scenes)
- Instructs the agent to use context and tools appropriately

### 3. Communication Style
- Conversational and natural
- Clear and concise
- Helpful and proactive
- Accurate and safety-first

### 4. Automation Creation Guidelines
- **Reliability**: initial_state, availability checks, error handling, max_exceeded
- **Mode Selection**: single, restart, queued, parallel
- **Target Optimization**: area_id/device_id preferences
- **Organization**: descriptions, tags, friendly names
- **Device Capabilities**: numeric ranges, enum values, health scores

### 5. Tool Usage
- When to use tools (query states, verify IDs, create automations)
- When NOT to use tools (context already available, general knowledge)

### 6. Safety and Security
- Critical safety rules (never disable guardrails, warn about implications)
- Security considerations (critical systems, time constraints, fallbacks)

### 7. Response Format
- Explain, show, highlight, suggest pattern for automation creation
- Clear answers with context references for questions

### 8. Error Handling
- Acknowledge issues, suggest alternatives, offer troubleshooting

### 9. Context Updates
- Context is cached, use tools for real-time verification

## Usage

### Get Base System Prompt

```python
from src.prompts.system_prompt import SYSTEM_PROMPT

# Use directly
system_prompt = SYSTEM_PROMPT
```

### Get System Prompt via ContextBuilder

```python
from src.services.context_builder import ContextBuilder

# Get base system prompt
system_prompt = context_builder.get_system_prompt()

# Get complete prompt with context injected
complete_prompt = await context_builder.build_complete_system_prompt()
```

### API Endpoints

#### Get System Prompt Only
```bash
GET /api/v1/system-prompt
```

Response:
```json
{
  "system_prompt": "...",
  "token_count": 1234
}
```

#### Get Complete Prompt (System + Context)
```bash
GET /api/v1/complete-prompt
```

Response:
```json
{
  "system_prompt": "...\n\n---\n\nHOME ASSISTANT CONTEXT:\n...",
  "token_count": 2345
}
```

## Integration with OpenAI

When using the system prompt with OpenAI API:

```python
import openai
from src.services.context_builder import ContextBuilder

# Build complete system prompt
context_builder = ContextBuilder(settings)
await context_builder.initialize()

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

## Best Practices

The system prompt follows these best practices:

1. **Clear Role Definition**: Explicitly defines the agent's purpose
2. **Specific Instructions**: Detailed guidelines for automation creation
3. **Contextual Information**: References the Tier 1 context injection
4. **Safety First**: Emphasizes safety and security considerations
5. **Structured Design**: Organized sections for consistency
6. **Tool Guidance**: Clear instructions on when to use tools

## Token Budget

- **Base System Prompt**: ~500 tokens
- **Tier 1 Context**: ~1500 tokens
- **Complete Prompt**: ~2000 tokens

The system prompt is designed to be cached (90% discount on repeated calls) and the context is cached with TTL-based expiration.

## Customization

To customize the system prompt:

1. Edit `src/prompts/system_prompt.py`
2. Modify the `SYSTEM_PROMPT` constant
3. Follow the existing structure and best practices
4. Test with real conversations to ensure effectiveness

## References

- Epic AI-19: HA AI Agent Service - Tier 1 Context Injection (system prompt foundation)
- Epic AI-20: HA AI Agent Service - Full Conversational AI Agent (system prompt integration)
- Home Assistant Automation Best Practices
- OpenAI System Prompt Best Practices

