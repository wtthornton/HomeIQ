# Test Button Call Tree Analysis

## Overview

**Question**: What is the call tree for the test button and how many AI models are used?

## Two Distinct Flows

### Flow 1: Initial Query (POST /query)

Creates suggestions from user query:

```
POST /api/v1/ask-ai/query
├── Step 1: Extract entities (extract_entities_with_ha)
│   ├── Multi-Model Extractor (if enabled)
│   │   ├── NER Extraction (can use OpenAI)
│   │   ├── OpenAI for entity mapping
│   │   └── Pattern matching fallback
│   ├── Enhanced Extractor (fallback)
│   │   └── Device Intelligence API (no AI)
│   └── Basic Pattern Matching (fallback)
│       └── Regex patterns (no AI)
│
└── Step 2: Generate suggestions (generate_suggestions_from_query)
    ├── Build unified prompt (UnifiedPromptBuilder)
    │   └── Uses device intelligence data (no AI)
    └── Call OpenAI to generate suggestions
        ├── Model: gpt-4o-mini
        ├── Temperature: creative_temperature (0.7)
        ├── Max tokens: 1200
        ├── Output: JSON array of suggestions
        └── Returns: Multiple creative automation suggestions
```

**AI Calls in Flow 1:**
- **Entity Extraction (optional)**: 1 OpenAI call (if Multi-Model Extractor enabled)
- **Suggestions Generation**: 1 OpenAI call (always)

**Total AI calls**: 1-2 (depending on entity extraction method)

---

### Flow 2: Test Button (POST /test)

Tests a specific suggestion:

```
POST /api/v1/ask-ai/query/{query_id}/suggestions/{suggestion_id}/test
├── Step 1: Retrieve query from database (already exists)
│   └── No AI involved
│
├── Step 2: Find suggestion from query.suggestions array
│   └── No AI involved
│
├── Step 3: Generate YAML (generate_automation_yaml)
│   ├── Entity validation (EntityValidator)
│   │   ├── Uses DataAPIClient to query SQLite
│   │   ├── Map devices to entities (database lookup)
│   │   └── No AI involved
│   │
│   ├── Build YAML generation prompt
│   │   ├── Include suggestion details
│   │   ├── Include validated entities
│   │   └── Include advanced YAML examples
│   │
│   └── Call OpenAI to generate YAML
│       ├── Model: gpt-4o-mini
│       ├── Temperature: 0.3 (lower for consistency)
│       ├── Max tokens: 1000
│       ├── Output: YAML string
│       └── Returns: Valid Home Assistant automation YAML
│
├── Step 4: Validate YAML (ha_client.validate_automation)
│   └── Home Assistant API call (no AI)
│
├── Step 5: Modify YAML for testing
│   ├── Add "test_" prefix to ID
│   ├── Add "[TEST]" to alias
│   ├── Set mode: 'single'
│   └── No AI involved
│
├── Step 6: Create automation in HA
│   └── Home Assistant API call (no AI)
│
├── Step 7: Trigger automation
│   └── Home Assistant API call (no AI)
│
└── Step 8: Disable automation
    └── Home Assistant API call (no AI)
```

**AI Calls in Flow 2:**
- **YAML Generation**: 1 OpenAI call (always)

**Total AI calls**: 1

---

## Key Differences

| Aspect | Initial Query Flow | Test Button Flow |
|--------|-------------------|------------------|
| **Purpose** | Generate creative automation ideas | Generate valid YAML from idea |
| **Input** | Natural language query | Pre-existing suggestion |
| **Output** | Multiple creative suggestions | One valid YAML automation |
| **AI Temperature** | 0.7 (creative) | 0.3 (consistent) |
| **AI Max Tokens** | 1200 | 1000 |
| **AI Calls** | 1-2 | 1 |
| **Uses Suggestions?** | NO (creates them) | YES (one exists already) |
| **HA API Calls** | 0 | 5+ (validate, create, trigger, disable) |
| **Database Calls** | Write query + suggestions | Read query + suggestion |

---

## Complete Flow Diagram

```
USER INPUT: "Flash the office lights every 30 seconds"

┌─────────────────────────────────────────────────────────────┐
│ FLOW 1: Initial Query POST /query                           │
└─────────────────────────────────────────────────────────────┘

  [Step 1: Entity Extraction]
  ┌──────────────────────────────────┐
  │ extract_entities_with_ha()      │
  │ - Query: "Flash the office..."   │
  │ - Method: Multi-Model or Enhanced│
  │ - Uses AI: Maybe (optional)     │
  │ - Returns: Entities list         │
  └──────────────────────────────────┘
            │
            ▼
  [Step 2: Generate Suggestions]
  ┌──────────────────────────────────┐
  │ generate_suggestions_from_query()│
  │ - Prompt includes:                │
  │   * User query                   │
  │   * Available entities           │
  │   * Creative examples             │
  │ - OpenAI Model: gpt-4o-mini      │
  │ - Temperature: 0.7 (creative)   │
  │ - Max tokens: 1200              │
  │ - Output: JSON array             │
  │                                   │
  │ Returns:                         │
  │ [                                │
  │   {                              │
  │     description: "Flash...",     │
  │     trigger_summary: "...",      │
  │     action_summary: "...",       │
  │     confidence: 0.9             │
  │   },                             │
  │   {                              │
  │     description: "Strobe...",    │
  │     trigger_summary: "...",      │
  │     action_summary: "...",       │
  │     confidence: 0.85            │
  │   },                             │
  │   ...                            │
  │ ]                                │
  └──────────────────────────────────┘
            │
            ▼
  [Step 3: Save to Database]
  ┌──────────────────────────────────┐
  │ AskAIQueryModel                  │
  │ - query_id: "query-abc123"       │
  │ - suggestions: [array of 3-4]    │
  │ - Saved to SQLite                │
  └──────────────────────────────────┘


┌─────────────────────────────────────────────────────────────┐
│ FLOW 2: Test Button POST /test                             │
└─────────────────────────────────────────────────────────────┘

  [Step 1: Retrieve Query from DB]
  ┌──────────────────────────────────┐
  │ db.get(AskAIQueryModel, query_id)│
  │ - Reads query with suggestions    │
  │ - No AI involved                 │
  └──────────────────────────────────┘
            │
            ▼
  [Step 2: Find Specific Suggestion]
  ┌──────────────────────────────────┐
  │ query.suggestions.find(suggestion_│
  │     id)                           │
  │ - Gets suggestion #3             │
  │ - No AI involved                 │
  └──────────────────────────────────┘
            │
            ▼
  [Step 3: Generate YAML]
  ┌──────────────────────────────────┐
  │ generate_automation_yaml()        │
  │                                   │
  │  [3a: Validate Entities]         │
  │  ┌────────────────────────────┐  │
  │  │ EntityValidator             │  │
  │  │ - Query data-api           │  │
  │  │ - Map devices to entities  │  │
  │  │ - No AI                    │  │
  │  └────────────────────────────┘  │
  │                                   │
  │  [3b: Build Prompt]              │
  │  ┌────────────────────────────┐  │
  │  │ Prompt includes:            │  │
  │  │ - Original query            │  │
  │  │ - Suggestion details        │  │
  │  │ - Validated entities        │  │
  │  │ - YAML examples             │  │
  │  └────────────────────────────┘  │
  │                                   │
  │  [3c: Call OpenAI]               │
  │  ┌────────────────────────────┐  │
  │  │ OpenAI API Call:            │  │
  │  │ - Model: gpt-4o-mini       │  │
  │  │ - Temperature: 0.3        │  │
  │  │ - Max tokens: 1000         │  │
  │  │ - Returns: YAML string      │  │
  │  └────────────────────────────┘  │
  └──────────────────────────────────┘
            │
            ▼
  [Step 4: Validate YAML]
  ┌──────────────────────────────────┐
  │ ha_client.validate_automation()  │
  │ - Calls Home Assistant API       │
  │ - Checks entity existence        │
  │ - No AI involved                │
  └──────────────────────────────────┘
            │
            ▼
  [Step 5: Create Test Automation]
  ┌──────────────────────────────────┐
  │ Modify YAML:                      │
  │ - ID: "test_office_lights_..."   │
  │ - Alias: "[TEST] Office Lights..."│
  │ - Mode: 'single'                 │
  │                                   │
  │ Create in HA:                     │
  │ - ha_client.create_automation()   │
  │ - No AI involved                 │
  └──────────────────────────────────┘
            │
            ▼
  [Step 6: Trigger & Disable]
  ┌──────────────────────────────────┐
  │ ha_client.trigger_automation()   │
  │ ha_client.disable_automation()   │
  │ - No AI involved                │
  └──────────────────────────────────┘
```

---

## Answer to User's Question

**Q: Does the test button flow go through the suggestions flow?**

**A: NO** - It bypasses it entirely:

- The test button uses suggestions that were already created during the initial query
- It retrieves a pre-existing suggestion from the database
- It only needs to generate YAML from that suggestion

**Q: How many AI models are used?**

**A: 1-2 AI calls total:**

### In Initial Query Flow:
- **0-1 AI call** for entity extraction (optional, only if Multi-Model Extractor enabled)
- **1 AI call** for generating suggestions

### In Test Button Flow:
- **1 AI call** for generating YAML from the suggestion

### Combined (both flows):
- **Total: 2-3 AI calls** for the complete end-to-end flow
- **All use the same model**: gpt-4o-mini
- **Different temperatures**: 
  - Suggestions: 0.7 (creative)
  - YAML Generation: 0.3 (consistent)

---

## Key Insight

The test button flow is **simpler and more focused** than the initial query flow:

1. **No entity extraction needed** - entities already validated when query was created
2. **No suggestion generation needed** - suggestion already exists in database
3. **Only needs YAML generation** - converts suggestion → valid Home Assistant YAML
4. **Uses lower temperature** (0.3 vs 0.7) for more consistent, reliable YAML output
5. **Followed by HA validation** - ensures entities exist before creating automation

This design separates concerns:
- **Query flow**: Creative brainstorming (temperature 0.7, multiple ideas)
- **Test flow**: Precise implementation (temperature 0.3, one valid YAML)
