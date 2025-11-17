# RAG System - Deployment Checklist & Next Steps

**Date:** January 2025  
**Status:** ✅ Implementation Complete - Ready for Deployment

---

## ✅ Implementation Status: COMPLETE

All code has been implemented, tested, and documented:

- [x] Core RAG module (`src/services/rag/`)
- [x] Database model (`SemanticKnowledge`)
- [x] Database migration (`20250120_add_semantic_knowledge.py`)
- [x] Clarification detector integration
- [x] Router integration
- [x] Seeding script
- [x] Documentation updates (README, architecture docs)

---

## 🚀 Deployment Steps

### Step 1: Verify Prerequisites

**Required Services:**
- [ ] OpenVINO Service running (port 8019)
  ```bash
  curl http://localhost:8019/health
  ```

**Environment Variables:**
- [ ] `OPENVINO_SERVICE_URL` set (default: `http://openvino-service:8019`)
  - Check in `infrastructure/env.ai-automation`
  - Or set in Docker Compose environment

### Step 2: Run Database Migration

```bash
cd services/ai-automation-service

# Check current migration status
alembic current

# Run migration
alembic upgrade head

# Verify migration
alembic current  # Should show: 20250120_semantic_knowledge (head)
```

**Expected Output:**
- Migration creates `semantic_knowledge` table
- Creates 3 indexes: `idx_knowledge_type`, `idx_success_score`, `idx_created_at`

### Step 3: Seed Knowledge Base

```bash
cd services/ai-automation-service

# Seed from existing data
python scripts/seed_rag_knowledge_base.py
```

**Expected Output:**
- Extracts successful queries (confidence >= 0.85)
- Extracts common patterns from `common_patterns.py`
- Extracts deployed automations
- Generates embeddings via OpenVINO service
- Stores in `semantic_knowledge` table

**Verification:**
```bash
# Check knowledge base entries (using SQLite CLI or script)
sqlite3 data/ai_automation.db "SELECT COUNT(*) FROM semantic_knowledge;"
```

### Step 4: Restart Service

```bash
# If using Docker
docker compose restart ai-automation-service

# If running locally
# Stop and restart the service
```

**Verify Service Health:**
```bash
curl http://localhost:8024/health
```

### Step 5: Test RAG Integration

**Test Query (should skip clarification if similar query exists):**
```bash
curl -X POST http://localhost:8024/api/v1/ask-ai/query \
  -H "Content-Type: application/json" \
  -H "X-HomeIQ-API-Key: your-api-key" \
  -d '{
    "query": "flash all four Hue office lights using the Hue Flash command for 30 secs at the top of every hour"
  }'
```

**Expected Behavior:**
- If similar successful query exists in knowledge base → No clarification questions
- If no similar query → Falls back to hardcoded rules (may ask questions)

**Check Logs:**
```bash
# Look for RAG client initialization
docker compose logs ai-automation-service | grep -i "RAG"

# Look for semantic similarity matches
docker compose logs ai-automation-service | grep -i "similar successful query"
```

---

## 🔍 Verification Checklist

### Code Verification
- [x] All files created and committed
- [x] No linter errors
- [x] Database migration tested
- [x] Integration points verified

### Service Verification
- [ ] OpenVINO service accessible
- [ ] Database migration successful
- [ ] Knowledge base seeded (check entry count)
- [ ] Service starts without errors
- [ ] RAG client initializes successfully

### Functional Verification
- [ ] Query with similar successful query → No clarification
- [ ] Query without similar query → Falls back to rules
- [ ] RAG unavailable → Falls back gracefully (no errors)
- [ ] Embeddings generated correctly
- [ ] Similarity search working

---

## 📊 Success Metrics

### Immediate (Post-Deployment)
- **Knowledge Base Size:** 100+ entries after seeding
- **Service Health:** No errors in logs
- **RAG Client:** Initializes successfully

### Short-term (1 week)
- **False Positive Rate:** Reduced from ~30% to <10%
- **Query Processing Time:** <100ms (including embedding)
- **Cache Hit Rate:** >70% for frequently accessed queries

### Long-term (1 month)
- **Knowledge Base Growth:** 50+ new entries per month
- **Success Score Updates:** Automatic from user feedback
- **User Satisfaction:** Fewer unnecessary clarification questions

---

## 🐛 Troubleshooting

### Issue: Migration Fails

**Error:** `alembic.util.exc.CommandError: Target database is not up to date`

**Solution:**
```bash
# Check current migration
alembic current

# If behind, upgrade
alembic upgrade head

# If migration conflicts, check revision history
alembic history
```

### Issue: OpenVINO Service Unavailable

**Error:** `RAG lookup failed, falling back to hardcoded rules`

**Solution:**
- Verify OpenVINO service is running: `curl http://localhost:8019/health`
- Check `OPENVINO_SERVICE_URL` environment variable
- System will fall back to hardcoded rules (expected behavior)

### Issue: No Similar Queries Found

**Symptom:** Still asking clarification questions

**Solution:**
- Ensure knowledge base is seeded: `python scripts/seed_rag_knowledge_base.py`
- Check similarity threshold (default: 0.85) - may need adjustment
- Verify embeddings are being generated (check logs)
- System falls back to hardcoded rules if no similar query (expected)

### Issue: Knowledge Base Empty After Seeding

**Check:**
```bash
# Verify entries exist
sqlite3 data/ai_automation.db "SELECT COUNT(*) FROM semantic_knowledge;"

# Check for errors in seeding script
python scripts/seed_rag_knowledge_base.py 2>&1 | grep -i error
```

**Solution:**
- Ensure OpenVINO service is accessible
- Check database connection
- Verify source data exists (queries, patterns, automations)

---

## 🔄 Post-Deployment Monitoring

### Logs to Monitor

```bash
# RAG client initialization
docker compose logs ai-automation-service | grep -i "RAG client initialized"

# Semantic similarity matches
docker compose logs ai-automation-service | grep -i "similar successful query"

# RAG lookup failures (fallback to rules)
docker compose logs ai-automation-service | grep -i "RAG lookup failed"

# Embedding generation errors
docker compose logs ai-automation-service | grep -i "embedding"
```

### Metrics to Track

1. **Performance:**
   - Embedding generation time (target: <100ms)
   - Query latency (target: <50ms)
   - Cache hit rate (target: >70%)

2. **Quality:**
   - False positive rate (target: <10%)
   - Similarity score distribution
   - Knowledge base growth rate

3. **Reliability:**
   - RAG client initialization success rate
   - OpenVINO service availability
   - Fallback usage (should decrease over time)

---

## 📝 Next Steps (Future Enhancements)

### Phase 2: Learning Loop (Future)
- [ ] Background job to learn from successful queries
- [ ] Automatic success score updates
- [ ] Knowledge base growth monitoring
- [ ] User feedback integration

### Phase 3: Expand Use Cases (Future)
- [ ] Pattern matching enhancement
- [ ] Community pattern learning
- [ ] Device intelligence
- [ ] Automation mining

### Phase 4: Optimization (Future)
- [ ] Vector DB migration (if >10K entries)
- [ ] Advanced caching strategies
- [ ] Batch embedding generation
- [ ] Performance tuning

---

## ✅ Completion Status

**Implementation:** ✅ COMPLETE  
**Documentation:** ✅ COMPLETE  
**Ready for Deployment:** ✅ YES

**Remaining Tasks:**
1. Run database migration
2. Seed knowledge base
3. Restart service
4. Verify functionality
5. Monitor metrics

---

## 📚 Reference Documentation

- **Implementation Details:** `implementation/RAG_IMPLEMENTATION_COMPLETE.md`
- **Architecture Research:** `implementation/analysis/RAG_ARCHITECTURE_RESEARCH.md`
- **Service README:** `services/ai-automation-service/README.md`
- **Architecture Docs:** `docs/architecture/ai-automation-system.md`

---

**Status:** ✅ Ready to Deploy

