# Execute Tech Stack KB Fetch - Step by Step

**Date:** November 2025  
**Status:** Ready to Execute  
**Note:** Context7 MCP API key needs verification - commands below will work once MCP is properly configured

## Prerequisites

1. Context7 MCP is running in Cursor (✅ Confirmed by user)
2. API key is properly configured (⚠️ May need verification)
3. BMAD Master agent is available

## Execution Method

Run these commands one by one using `@bmad-master`:

```
@bmad-master
```

Then execute each command below.

## Critical Stack - Execute First

### 1. SQLAlchemy (ORM)
```bash
*context7-docs sqlalchemy async-orm
*context7-docs sqlalchemy 2.0-migration
*context7-docs sqlalchemy fastapi-integration
*context7-docs sqlalchemy async-session
```

### 2. Pydantic (Data Validation)
```bash
*context7-docs pydantic v2-migration
*context7-docs pydantic fastapi-integration
*context7-docs pydantic settings
*context7-docs pydantic validation
```

### 3. aiosqlite (Async SQLite Driver)
```bash
*context7-docs aiosqlite async-patterns
*context7-docs aiosqlite sqlalchemy-integration
*context7-docs aiosqlite wal-mode
```

### 4. Zustand (State Management)
```bash
*context7-docs zustand state-management
*context7-docs zustand react-integration
*context7-docs zustand async-patterns
```

## AI/ML Stack - Execute Next

### 5. PyTorch (AI/ML Framework)
```bash
*context7-docs pytorch cpu-only
*context7-docs pytorch optimization
*context7-docs pytorch nuc-deployment
```

### 6. PEFT (Fine-tuning)
```bash
*context7-docs peft lora
*context7-docs peft fine-tuning
*context7-docs peft cpu-deployment
```

### 7. LangChain (LLM Orchestration)
```bash
*context7-docs langchain llm-orchestration
*context7-docs langchain openai-integration
*context7-docs langchain patterns
```

### 8. OpenVINO (AI Optimization)
```bash
*context7-docs openvino int8-optimization
*context7-docs openvino model-export
*context7-docs openvino cpu-deployment
```

### 9. optimum-intel (OpenVINO Integration)
```bash
*context7-docs optimum-intel transformers-integration
*context7-docs optimum-intel openvino-export
*context7-docs optimum-intel optimization
```

## Verification

After fetching all documentation, verify:

```bash
*context7-kb-status
```

Check specific libraries:
```bash
*context7-kb-search sqlalchemy
*context7-kb-search pydantic
*context7-kb-search aiosqlite
*context7-kb-search zustand
*context7-kb-search pytorch
*context7-kb-search peft
*context7-kb-search langchain
*context7-kb-search openvino
*context7-kb-search optimum-intel
```

## Expected Results

- **Total Technologies:** 25
- **Cached:** 25 (100%)
- **Cache Hit Rate:** 87%+ (target)
- **Coverage:** Complete tech stack documentation

## Troubleshooting

### If API Key Error Occurs

1. Check Context7 MCP configuration in Cursor settings
2. Verify API key starts with `ctx7sk`
3. Ensure MCP server is running
4. Try restarting Cursor if needed

### If Library Not Found

Some libraries may need to be resolved first:
```bash
*context7-resolve sqlalchemy
*context7-resolve pydantic
*context7-resolve aiosqlite
*context7-resolve zustand
```

Then fetch docs using the resolved library ID.

## Notes

- Each `*context7-docs` command will:
  1. Check KB cache first (KB-first approach)
  2. If not cached, fetch from Context7 API
  3. Automatically store in `docs/kb/context7-cache/libraries/{library}/`
  4. Update metadata in `docs/kb/context7-cache/index.yaml`

- Documentation is automatically cached for future use
- Cache hit rate will improve after all docs are fetched
- All fetched docs will be available for all BMAD agents

