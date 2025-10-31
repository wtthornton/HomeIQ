# Ask AI Phase 2 Implementation Plan
**Context & Refinement Enhancement**

**Date:** January 23, 2025  
**Status:** In Progress  
**Epic:** Conversational AI Assistant for HA AutomateAI

---

## 🎯 Phase 2 Goals

### Primary Objectives
1. ✅ **Conversation History Management** - Persist messages across reloads
2. ✅ **Context Tracking** - Track mentioned devices, intents across messages
3. ✅ **Follow-up Prompts** - Generate dynamic follow-up suggestions
4. ✅ **Context Indicator** - Show active context (devices, settings, etc.)
5. ✅ **Personalized Prompts** - Suggested prompts based on user's HA setup

### Success Criteria
- Multi-turn conversations work seamlessly
- Context persists across messages (refinements like "make it 6:30am instead")
- Follow-up prompts are contextually relevant
- Context indicator shows active conversation state

---

## 📋 Current Implementation Status

### ✅ What's Already Working (MVP)
- Basic chat interface
- Single-query processing with entity extraction
- Suggestion generation and display
- Test/Approve/Reject actions on suggestions
- Typing indicator
- Sidebar with example queries

### ❌ What's Missing (Phase 2)
1. **No Conversation History** - Messages lost on page reload
2. **No Context Passing** - Each query is independent (no refinement like "make it 6:30am instead")
3. **No Follow-up Prompts** - AI doesn't suggest what to ask next
4. **No Context Indicator** - Users don't see what devices/context is active
5. **Static Example Queries** - Not personalized to user's setup

---

## 🏗️ Implementation Tasks

### Task 1: Conversation History Management

**Frontend Changes:**
```typescript
// Add to AskAI.tsx

// 1. Add conversation history state with localStorage persistence
const [conversationHistory, setConversationHistory] = useState<ChatMessage[]>(() => {
  const saved = localStorage.getItem('ask-ai-conversation');
  return saved ? JSON.parse(saved) : [welcomeMessage];
});

// 2. Save to localStorage on each update
useEffect(() => {
  localStorage.setItem('ask-ai-conversation', JSON.stringify(messages));
}, [messages]);

// 3. Add conversation management functions
const clearConversation = () => {
  localStorage.removeItem('ask-ai-conversation');
  setMessages([welcomeMessage]);
  toast.success('Conversation cleared');
};

const exportConversation = () => {
  const dataStr = JSON.stringify(messages, null, 2);
  const dataBlob = new Blob([dataStr], { type: 'application/json' });
  // Download logic...
};

const importConversation = (file: File) => {
  // Import logic...
};
```

**Backend Changes:**
```python
# Add to ask_ai_router.py

class AskAIQueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"
    context: Optional[Dict[str, Any]] = None
    conversation_history: Optional[List[Dict[str, Any]]] = None  # NEW
```

---

### Task 2: Context Tracking

**Frontend Changes:**
```typescript
// Add context state management
interface ConversationContext {
  mentioned_devices: string[];
  mentioned_intents: string[];
  active_suggestions: string[];
  last_query: string;
  last_entities: any[];
}

const [conversationContext, setConversationContext] = useState<ConversationContext>({
  mentioned_devices: [],
  mentioned_intents: [],
  active_suggestions: [],
  last_query: '',
  last_entities: []
});

// Update context after each message
const updateContextFromMessage = (message: ChatMessage) => {
  if (message.entities) {
    const devices = message.entities
      .map(e => e.name || e.entity_id)
      .filter(Boolean);
    
    setConversationContext(prev => ({
      ...prev,
      mentioned_devices: [...prev.mentioned_devices, ...devices],
      last_query: message.content,
      last_entities: message.entities
    }));
  }
};

// Send context with each query
const handleSendMessage = async () => {
  // ... existing code ...
  
  const response = await api.askAIQuery(inputValue, {
    conversation_context: conversationContext,
    conversation_history: messages.map(msg => ({
      role: msg.type,
      content: msg.content,
      timestamp: msg.timestamp.toISOString()
    }))
  });
  
  updateContextFromMessage(aiMessage);
};
```

---

### Task 3: Follow-up Prompts

**Backend Changes:**
```python
# Add to generate_suggestions_from_query()

def generate_follow_up_prompts(
    query: str,
    entities: List[Dict[str, Any]],
    suggestions: List[Dict[str, Any]],
    conversation_history: Optional[List[Dict]] = None
) -> List[str]:
    """
    Generate contextual follow-up prompts based on current query and context.
    
    Examples:
    - "Flash office lights when VGK scores" → "Make it flash 5 times instead"
    - "Turn on bedroom lights" → "Only after sunset" or "Set brightness to 50%"
    """
    prompts = []
    
    # Extract key info
    devices = [e.get('name') for e in entities]
    actions = [s.get('action_summary') for s in suggestions]
    
    # Generate follow-ups based on context
    if conversation_history and len(conversation_history) > 0:
        # If this is a refinement, suggest applying
        prompts.append("Apply this automation")
        
    if 'flash' in query.lower():
        prompts.extend([
            "Make it flash 5 times instead",
            "Use different colors for the flash"
        ])
    
    if 'light' in query.lower():
        prompts.extend([
            "Set brightness to 50%",
            "Only after sunset",
            "Add a fade effect"
        ])
    
    # General follow-ups
    prompts.extend([
        "What else can I automate with these devices?",
        "Show me more automation ideas"
    ])
    
    return prompts[:4]  # Max 4 prompts
```

**Frontend Changes:**
```typescript
// Add follow-up prompts display in message bubbles
{message.follow_up_prompts && message.follow_up_prompts.length > 0 && (
  <div className="mt-3 space-y-1">
    <p className="text-xs text-gray-500">💡 Try asking:</p>
    {message.follow_up_prompts.map((prompt, idx) => (
      <button
        key={idx}
        onClick={() => {
          setInputValue(prompt);
          inputRef.current?.focus();
        }}
        className="block w-full text-left text-xs px-2 py-1 rounded hover:bg-gray-100"
      >
        "{prompt}"
      </button>
    ))}
  </div>
)}
```

---

### Task 4: Context Indicator Component

**Create New Component: `ContextIndicator.tsx`**
```typescript
interface ContextIndicatorProps {
  context: ConversationContext;
  darkMode: boolean;
}

export const ContextIndicator: React.FC<ContextIndicatorProps> = ({ context, darkMode }) => {
  return (
    <div className={`border-t px-4 py-2 text-xs ${darkMode ? 'bg-gray-800 border-gray-700' : 'bg-gray-100 border-gray-200'}`}>
      <div className="flex items-center gap-4 flex-wrap">
        <span className="font-medium">🎛️ Context:</span>
        
        {context.mentioned_devices.length > 0 && (
          <span>
            Devices: {context.mentioned_devices.slice(0, 3).join(', ')}
            {context.mentioned_devices.length > 3 && ` +${context.mentioned_devices.length - 3}`}
          </span>
        )}
        
        {context.active_suggestions.length > 0 && (
          <span>
            {context.active_suggestions.length} active suggestion{context.active_suggestions.length > 1 ? 's' : ''}
          </span>
        )}
        
        <span>{context.mentioned_devices.length} mentions in this conversation</span>
      </div>
    </div>
  );
};
```

**Add to AskAI.tsx:**
```typescript
// Before input area (after messages, before input)
<ContextIndicator context={conversationContext} darkMode={darkMode} />
```

---

### Task 5: Personalized Suggested Prompts

**Create New Component: `WelcomeScreen.tsx`**
```typescript
interface WelcomeScreenProps {
  context: ConversationContext;
  onPromptClick: (prompt: string) => void;
  darkMode: boolean;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ context, onPromptClick, darkMode }) => {
  // Generate personalized prompts based on user's setup
  const suggestedPrompts = generatePersonalizedPrompts(context);
  
  return (
    <div className="max-w-2xl mx-auto text-center py-12">
      <h2 className={`text-2xl font-bold mb-4 ${darkMode ? 'text-white' : 'text-gray-900'}`}>
        How can I help you automate your home?
      </h2>
      
      <div className="grid grid-cols-1 gap-3 mt-6">
        {suggestedPrompts.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => onPromptClick(prompt)}
            className={`p-4 rounded-lg text-left transition-all hover:shadow-md ${
              darkMode 
                ? 'bg-gray-800 hover:bg-gray-700 text-gray-200' 
                : 'bg-white hover:bg-gray-50 text-gray-700'
            }`}
          >
            <p className="font-medium">{prompt}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

// Helper to generate personalized prompts
function generatePersonalizedPrompts(context: ConversationContext): string[] {
  const prompts: string[] = [];
  
  // Based on context.mentioned_devices, suggest specific automations
  if (context.mentioned_devices.includes('light')) {
    prompts.push("Flash my office lights when VGK scores");
    prompts.push("Turn off all lights when I leave the house");
  }
  
  // Add general prompts
  prompts.push("What can I automate with my devices?");
  prompts.push("Show me energy-saving automations");
  
  return prompts.slice(0, 4);
}
```

**API Endpoint for Personalized Prompts:**
```python
# Add to ask_ai_router.py

@router.get("/suggested-prompts")
async def get_suggested_prompts(
    user_id: str = "anonymous",
    db: AsyncSession = Depends(get_db)
) -> Dict[str, List[str]]:
    """
    Get personalized suggested prompts based on user's HA setup.
    
    Fetches:
    - Available devices
    - Active integrations (sports, energy, weather)
    - Existing automations
    
    Returns prompts tailored to user's setup.
    """
    # Fetch user's devices
    devices = await device_intelligence_client.get_devices(limit=100)
    
    # Detect integrations
    has_sports = await detect_sports_tracking()
    has_energy = await detect_energy_pricing()
    has_weather = await detect_weather()
    
    prompts = []
    
    # Sports-based prompts
    if has_sports:
        prompts.append("Flash my lights when VGK scores")
        prompts.append("Notify me when Golden Knights win")
    
    # Energy-based prompts
    if has_energy:
        prompts.append("Turn off devices when electricity is expensive")
        prompts.append("Run dishwasher during cheap electricity hours")
    
    # Device-based prompts
    light_devices = [d for d in devices if 'light' in d.get('domain', '')]
    if light_devices:
        prompts.append(f"Dim the {light_devices[0].get('name')} at sunset")
    
    # General prompts (always)
    prompts.extend([
        "What can I automate with my devices?",
        "Show me energy-saving automations"
    ])
    
    return {"suggested_prompts": prompts[:5]}
```

---

## 🧪 Testing Plan

### Manual Testing Checklist
- [ ] Send a message → reload page → verify conversation persists
- [ ] Send "Flash office lights" → respond "Make it 5 times" → verify context is used
- [ ] Check that follow-up prompts appear after AI responses
- [ ] Verify context indicator shows active devices/intents
- [ ] Test personalized prompts on welcome screen
- [ ] Export/import conversation history

### Integration Testing
- [ ] Test context passing to backend API
- [ ] Verify conversation_history parameter is processed
- [ ] Test follow-up prompt generation accuracy
- [ ] Verify localStorage persistence across sessions

---

## 📝 Implementation Order

### Week 1: Core Context Features
1. ✅ Conversation history localStorage persistence (Day 1)
2. ✅ Context state management (Day 2)
3. ✅ Context passing to API (Day 3)
4. ✅ ContextIndicator component (Day 4)
5. ✅ Testing and bug fixes (Day 5)

### Week 2: Enhanced Features
1. ⬜ Follow-up prompt generation (Day 1)
2. ⬜ Follow-up prompt display (Day 2)
3. ⬜ Personalized suggested prompts API (Day 3)
4. ⬜ WelcomeScreen component (Day 4)
5. ⬜ Testing and polish (Day 5)

---

## 🎨 UI/UX Enhancements

### Context Indicator Design
```
┌──────────────────────────────────────────────────────────┐
│ 🎛️ Context: 3 devices • 2 active suggestions • 8 total  │
│    mentions in this conversation                         │
└──────────────────────────────────────────────────────────┘
```

### Follow-up Prompts Design
```
AI Response: "I found 3 automation suggestions..."

💡 Try asking:
  "Make it flash 5 times instead"
  "Use different colors"
  "What else can I automate?"
  "Show me more ideas"
```

### Welcome Screen Design
```
┌─────────────────────────────────────────────┐
│                                             │
│  How can I help you automate your home?    │
│                                             │
│  ┌───────────────────────────────────────┐ │
│  │ Flash my office lights when VGK       │ │
│  │ scores                                │ │
│  └───────────────────────────────────────┘ │
│  ┌───────────────────────────────────────┐ │
│  │ Turn off devices when electricity     │ │
│  │ is expensive                          │ │
│  └───────────────────────────────────────┘ │
│  ┌───────────────────────────────────────┐ │
│  │ What can I automate with my devices?  │ │
│  └───────────────────────────────────────┘ │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🚀 Deployment Checklist

- [ ] All Phase 2 features implemented
- [ ] Manual testing complete
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] UI/UX approved
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production

---

**Document Status:** Implementation Guide  
**Last Updated:** January 23, 2025  
**Next:** Start implementing Task 1 (Conversation History)
