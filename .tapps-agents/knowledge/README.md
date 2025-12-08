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
└── home-assistant/               # Home Assistant Expert
```

## Current Status

✅ **109 files** populated from existing HomeIQ documentation
- IoT & Home Automation: 5 files
- Time-Series Analytics: 16 files
- AI & Machine Learning: 5 files
- Microservices Architecture: 68 files
- Security & Privacy: 1 file
- Frontend & UX: 4 files
- Home Assistant: 10 files

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

## See Also

- [Knowledge Base Guide](../../TappsCodingAgents/docs/KNOWLEDGE_BASE_GUIDE.md)
- [Expert Configuration Guide](../../TappsCodingAgents/docs/EXPERT_CONFIG_GUIDE.md)
- [Enhancer Agent Guide](../../TappsCodingAgents/docs/ENHANCER_AGENT.md)

