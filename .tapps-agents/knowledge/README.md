# HomeIQ RAG Knowledge Bases

This directory contains knowledge bases for all HomeIQ Industry Experts. Each expert has a dedicated directory with markdown documentation files that are automatically searched when RAG is enabled.

## Structure

```
.tapps-agents/knowledge/
├── iot-home-automation/          # IoT & Home Automation Expert
├── time-series-analytics/        # Time-Series Data & Analytics Expert
├── ai-machine-learning/          # AI & Machine Learning Expert
├── microservices-architecture/   # Microservices Architecture Expert
├── security-privacy/             # Security & Privacy Expert
├── energy-management/            # Energy Management Expert
├── frontend-ux/                  # Frontend & User Experience Expert
├── home-assistant/               # Home Assistant Expert
├── automation-strategy/          # Automation Strategy Expert (Business)
├── proactive-intelligence/       # Proactive Intelligence Expert (Business)
├── smart-home-ux/                # Smart Home UX Expert (Business)
├── energy-economics/             # Energy Economics Expert (Business)
├── pattern-analytics/            # Pattern Analytics Expert (Business)
└── device-ecosystem/             # Device Ecosystem Expert (Business)
```

## Current Status

✅ **140+ files** populated across 14 expert knowledge bases
- **Technical Experts**: 109 files (IoT, Time-Series, AI/ML, Microservices, Security, Energy Management, Frontend, Home Assistant)
- **Business Experts**: 31 files (Automation Strategy: 5, Proactive Intelligence: 5, Smart Home UX: 4, Energy Economics: 4, Pattern Analytics: 4, Device Ecosystem: 4, Energy Management: 5)
- All files updated for December 2025 standards

## Knowledge Base Types: Local KB vs Context7 KB

**IMPORTANT**: Understand when to use Local KB (domain-specific) vs Context7 KB (library documentation).

### Local KB (Domain-Specific Knowledge)

**Location**: `.tapps-agents/knowledge/{domain}/`  
**Purpose**: Domain-specific business logic, project patterns, and internal knowledge

**Use Local KB for**:
- ✅ Domain-specific business knowledge ("Automation ROI analysis patterns", "User behavior adoption rates")
- ✅ Project-specific patterns ("HomeIQ event processing patterns", "Our InfluxDB schema")
- ✅ Industry best practices and principles ("Automation strategy principles", "Energy optimization strategies")
- ✅ Internal documentation and processes

**Examples**:
- Automation strategy principles and best practices
- Energy consumption tracking patterns
- User experience design principles
- Pattern detection methodologies

### Context7 KB Cache (Library Documentation)

**Location**: `.tapps-agents/kb/context7-cache/` (auto-populated)  
**Purpose**: External library and API documentation

**Use Context7 KB for**:
- ✅ Technology/library documentation (FastAPI routing, React hooks, SQLAlchemy)
- ✅ External API documentation (Home Assistant REST API, WebSocket API)
- ✅ Framework documentation (React, FastAPI, InfluxDB)
- ✅ Any external library reference material

**Examples**:
- Home Assistant WebSocket API documentation
- FastAPI routing and dependency injection
- React component patterns and hooks
- InfluxDB query syntax

**How It Works**:
1. Agents/experts request library docs via `*context7-docs` commands
2. System checks Context7 KB cache first (instant if cached)
3. If cache miss → calls Context7 API, stores in shared cache
4. All future requests (from any expert) use cached version
5. Auto-refresh system keeps cache current

**Key Point**: Context7 KB is **SHARED** across all experts. No need to populate per-expert.

### Decision Guide

| Knowledge Type | Storage | Example |
|---|---|---|
| "How do I use FastAPI routing?" | Context7 KB | FastAPI library docs |
| "What are HomeIQ automation patterns?" | Local KB | Project-specific patterns |
| "How do I query InfluxDB?" | Context7 KB | InfluxDB query syntax |
| "What are energy optimization strategies?" | Local KB | Domain knowledge |
| "Home Assistant REST API endpoints" | Context7 KB | External API docs |
| "User behavior adoption patterns" | Local KB | Business domain knowledge |

### When Adding New Knowledge

1. **Ask**: Is this project/domain-specific or external library documentation?
2. **Project/domain-specific** → Add to Local KB (`knowledge/{domain}/`)
3. **External library/API** → Use Context7 KB (auto-populated via `*context7-docs` commands)
4. **If unsure**: Default to Local KB for business/domain knowledge, Context7 KB for technical APIs

## Adding 2025 Best Practices

### Method 1: Manual Addition

1. Navigate to the appropriate domain directory
2. Create a new markdown file (e.g., `2025-best-practices.md`)
3. Use clear headers and keywords for better searchability
4. Follow the format below

### Method 2: Using the Population Script

Run the population script to add new documentation:

```bash
python scripts/populate_rag_knowledge.py
```

Edit `scripts/populate_rag_knowledge.py` to add new file patterns.

## Knowledge File Format

### Best Practices for Knowledge Files

1. **Use Clear Headers**: Headers (`#`, `##`, `###`) are weighted higher in search
2. **Include Keywords**: Important terms in first paragraph improve matching
3. **One Topic Per File**: Keep files focused for better retrieval
4. **Code Examples**: Include code/configuration examples when relevant
5. **Cross-References**: Mention related topics for context

### Example Knowledge File

```markdown
# Home Assistant WebSocket API Best Practices (2025)

## Connection Management

Always use connection pooling for WebSocket connections.

### Best Practices

- **Reconnection Strategy**: Implement exponential backoff
- **Heartbeat**: Send ping every 30 seconds
- **Error Handling**: Handle connection drops gracefully

## Event Processing

Process events in batches for better performance.

### 2025 Updates

- New: Support for event filtering
- Improved: Reduced latency with async processing
- Deprecated: Old event format (use v2)

## Code Example

```python
async def connect_websocket():
    # 2025 best practice: Use connection pool
    async with WebSocketClient() as ws:
        await ws.subscribe_events()
        async for event in ws:
            await process_event(event)
```
```

## Updating Knowledge Bases

### Adding New Documentation

1. **From HomeIQ Docs**: Files are automatically mapped from `docs/` directory
2. **External Sources**: Manually add markdown files with 2025 best practices
3. **Web Scraping**: Use tools to fetch and format documentation (see below)

### Fetching 2025 Best Practices

For Home Assistant:
- Official HA docs: https://www.home-assistant.io/docs/
- API reference: https://developers.home-assistant.io/docs/api/rest/
- WebSocket API: https://developers.home-assistant.io/docs/api/websocket/

For other technologies:
- InfluxDB: https://docs.influxdata.com/
- FastAPI: https://fastapi.tiangolo.com/
- React: https://react.dev/

## Search Behavior

The RAG system uses keyword matching:
- **Headers** are weighted 1.5x higher
- **Exact matches** score higher than partial matches
- **Context lines** around matches are included
- **Top 5 chunks** are returned by default

## Testing Knowledge Bases

Test your knowledge base with the enhancer:

```bash
# In Cursor chat
@enhancer *enhance "How do I connect to Home Assistant WebSocket?"
```

The enhancer will:
1. Detect relevant domains
2. Search knowledge bases for matching content
3. Include retrieved context in the enhanced prompt
4. Show sources in the output

## Maintenance

### Regular Updates

- **Monthly**: Review and update outdated information
- **Quarterly**: Add new best practices and patterns
- **After Major Updates**: Update knowledge when HomeIQ architecture changes

### File Organization

- Keep files under 100KB each
- Use descriptive filenames
- Group related topics in subdirectories if needed
- Update README.md in each domain directory

## Troubleshooting

### No Results Found

- Check file encoding (must be UTF-8)
- Verify keywords match your query
- Ensure files are in correct domain directory
- Check file extensions (.md only)

### Poor Relevance

- Add more headers to knowledge files
- Include keywords in first paragraph
- Use more specific search terms
- Organize knowledge better

## Related Documentation

- [Knowledge Base Recommendations](KNOWLEDGE_BASE_RECOMMENDATIONS.md) - Comprehensive recommendations and next steps
- [Next Steps Summary](NEXT_STEPS_SUMMARY.md) - Quick reference for immediate actions
- [2025 Knowledge Base Verification](2025_KNOWLEDGE_BASE_VERIFICATION.md) - Verification results

## See Also

- [Knowledge Base Guide](../../TappsCodingAgents/docs/KNOWLEDGE_BASE_GUIDE.md)
- [Expert Configuration Guide](../../TappsCodingAgents/docs/EXPERT_CONFIG_GUIDE.md)
- [Enhancer Agent Guide](../../TappsCodingAgents/docs/ENHANCER_AGENT.md)

