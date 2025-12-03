# HomeIQ Dependency Upgrade Report

**Generated:** November 15, 2025
**Status:** 39 of 42 packages have updates available
**Recommendation:** Phased upgrade approach with testing at each stage

---

## Executive Summary

| Category | Count | Risk Level |
|----------|-------|------------|
| 🔴 **Critical - Major Version Updates** | 10 | HIGH - Breaking changes likely |
| 🟡 **Medium - Minor Version Updates** | 17 | MEDIUM - New features, minor breaking changes possible |
| 🟢 **Low - Patch Updates** | 12 | LOW - Bug fixes and security patches |
| ✅ **Up to Date** | 3 | NONE |

**Total packages reviewed:** 42

---

## 🔴 Critical Priority - Major Version Updates (Breaking Changes Expected)

### 1. **LangChain: 0.2.14 → 1.0.7** ⚠️ MAJOR UPGRADE
- **Impact:** HIGH - Major version change with breaking API changes
- **Risk:** Breaking changes to chain APIs, LCEL syntax changes
- **Recommendation:** **UPGRADE WITH CAUTION**
  - Review LangChain 1.0 migration guide
  - Test all PDL workflows and LCEL chains thoroughly
  - Update feature flags: `USE_LANGCHAIN_ASK_AI`, `USE_LANGCHAIN_PATTERNS`
  - Affected service: `ai-automation-service`
- **Priority:** HIGH (but test thoroughly first)

### 2. **OpenAI: 1.40.2 → 2.8.0** ⚠️ MAJOR UPGRADE
- **Impact:** HIGH - Major version with new API structure
- **Risk:** Breaking changes to client initialization, response formats
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Review OpenAI SDK v2 migration guide
  - Update all `openai.ChatCompletion` calls
  - Test GPT-4o-mini integrations
  - Affected service: `ai-automation-service`
- **Priority:** HIGH

### 3. **paho-mqtt: 1.6.1 → 2.1.0** ⚠️ MAJOR UPGRADE
- **Impact:** MEDIUM - Breaking changes to MQTT client API
- **Risk:** Connection handling changes
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Review paho-mqtt 2.x migration guide
  - Test MQTT connections thoroughly
  - Affected services: `ai-automation-service`, `device-intelligence-service`
- **Priority:** MEDIUM

### 4. **pytest: 8.3.3 → 9.0.1** ⚠️ MAJOR UPGRADE
- **Impact:** LOW - Test framework only
- **Risk:** Plugin compatibility issues
- **Recommendation:** **SAFE TO UPGRADE**
  - Update `pytest-asyncio` simultaneously (0.23.0 → 1.3.0)
  - Run full test suite after upgrade
- **Priority:** LOW (testing infrastructure being rebuilt)

### 5. **pytest-asyncio: 0.23.0 → 1.3.0** ⚠️ MAJOR UPGRADE
- **Impact:** LOW - Test framework only
- **Risk:** Async test fixture changes
- **Recommendation:** **SAFE TO UPGRADE** (with pytest)
- **Priority:** LOW

### 6. **pytest-cov: 5.0.0 → 7.0.0** ⚠️ MAJOR UPGRADE
- **Impact:** LOW - Coverage reporting only
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### 7. **isort: 5.12.0 → 7.0.0** ⚠️ MAJOR UPGRADE
- **Impact:** LOW - Code formatting only
- **Risk:** Import ordering changes
- **Recommendation:** **SAFE TO UPGRADE**
  - May need to reformat imports
  - Run `isort .` after upgrade
- **Priority:** LOW

### 8. **flake8: 6.1.0 → 7.3.0** ⚠️ MAJOR UPGRADE
- **Impact:** LOW - Linting only
- **Risk:** New linting rules may flag existing code
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### 9. **docker: 6.1.3 → 7.1.0** ⚠️ MAJOR UPGRADE
- **Impact:** MEDIUM - Docker SDK changes
- **Risk:** API changes for container management
- **Recommendation:** **UPGRADE WITH TESTING**
  - Test admin-api Docker management features
  - Affected service: `admin-api`
- **Priority:** MEDIUM

### 10. **tenacity: 8.2.3 → 9.1.2** ⚠️ MAJOR UPGRADE
- **Impact:** MEDIUM - Retry logic library
- **Risk:** Decorator syntax or behavior changes
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Review retry configurations
  - Test circuit breakers and infinite retry patterns
- **Priority:** MEDIUM

---

## 🟡 Medium Priority - Minor Version Updates

### AI/ML Ecosystem

#### **sentence-transformers: 3.3.1 → 5.1.2** 📈 2 MAJOR VERSIONS
- **Impact:** HIGH - Significant API and performance improvements
- **Risk:** Model loading changes, embedding dimension changes
- **Recommendation:** **UPGRADE WITH CAUTION**
  - Test all-MiniLM-L6-v2 embeddings for consistency
  - Verify embedding dimensions haven't changed
  - Re-index any stored embeddings if needed
  - Affected services: `ai-automation-service`, `openvino-service`
- **Priority:** HIGH

#### **transformers: 4.46.1 → 4.57.1** 📈 MINOR
- **Impact:** MEDIUM - New model support, bug fixes
- **Risk:** Tokenizer changes possible
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Verify compatibility with `optimum-intel==1.26.1`
  - Test T5 and other models
  - Affected services: `ai-automation-service`, `openvino-service`
- **Priority:** MEDIUM

#### **torch: 2.3.1 → 2.9.1** 📈 MINOR
- **Impact:** MEDIUM - Performance improvements
- **Risk:** CPU-only build compatibility
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Use `torch==2.9.1+cpu` from PyTorch CPU index
  - Test model inference performance
  - Affected services: `ai-automation-service`, `openvino-service`
- **Priority:** MEDIUM

#### **openvino: 2024.6.0 → 2025.3.0** 📈 YEARLY RELEASE
- **Impact:** MEDIUM - New optimizations
- **Risk:** Model compatibility
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Update with `optimum-intel==1.26.1`
  - Test INT8 quantization
  - Verify NER and embedding performance
- **Priority:** MEDIUM

#### **optimum-intel: 1.21.0 → 1.26.1** 📈 MINOR
- **Impact:** MEDIUM - Better OpenVINO integration
- **Risk:** Transformer version compatibility
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Ensure `transformers>=4.36,<4.58` compatibility
  - Test with updated OpenVINO
- **Priority:** MEDIUM

#### **scikit-learn: 1.4.2 → 1.7.2** 📈 MINOR
- **Impact:** MEDIUM - New algorithms, performance
- **Risk:** Serialized model compatibility
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Re-train/re-save any pickled models
  - Test clustering algorithms
  - Affected services: `ml-service`, `ai-automation-service`, `device-intelligence-service`
- **Priority:** MEDIUM

#### **spacy: 3.7.2 → 3.8.9** 📈 MINOR
- **Impact:** LOW - NER improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
  - May need to re-download language models
  - Affected service: `ai-automation-service`
- **Priority:** LOW

### Data Processing

#### **pandas: 2.2.3 → 2.3.3** 📈 MINOR
- **Impact:** MEDIUM - Performance improvements
- **Risk:** Deprecation warnings possible
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Test data processing pipelines
  - Multiple services affected
- **Priority:** MEDIUM

#### **numpy: 2.0.1 → 2.3.4** 📈 MINOR
- **Impact:** LOW - Bug fixes and performance
- **Risk:** Minimal (already on 2.x)
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

#### **scipy: 1.12.0 → 1.16.3** 📈 MINOR
- **Impact:** LOW - Scientific computing improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
  - Affected service: `ml-service`
- **Priority:** LOW

### Database & ORM

#### **sqlalchemy: 2.0.25 → 2.0.44** 📈 PATCH
- **Impact:** MEDIUM - Many bug fixes and improvements
- **Risk:** Low (within 2.0.x)
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Multiple services use SQLAlchemy
  - Test async ORM operations
- **Priority:** MEDIUM

#### **alembic: 1.13.1 → 1.17.2** 📈 MINOR
- **Impact:** LOW - Migration improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

#### **aiosqlite: 0.20.0 → 0.21.0** 📈 MINOR
- **Impact:** LOW - Async SQLite improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

#### **influxdb-client: 1.44.0 → 1.49.0** 📈 MINOR
- **Impact:** MEDIUM - Performance and bug fixes
- **Risk:** Low
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Test batch writes and queries
  - Multiple services affected
- **Priority:** MEDIUM

### Web Framework & HTTP

#### **fastapi: 0.121.0 → 0.121.2** 📈 PATCH
- **Impact:** LOW - Bug fixes
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
  - All backend services use FastAPI
- **Priority:** HIGH (patch update, widely used)

#### **aiohttp: 3.9.5 → 3.13.2** 📈 MINOR
- **Impact:** MEDIUM - Security fixes and improvements
- **Risk:** Low
- **Recommendation:** **UPGRADE RECOMMENDED**
  - Multiple services use aiohttp
  - Check for security advisories
- **Priority:** HIGH (potential security fixes)

#### **pydantic: 2.8.2 → 2.12.4** 📈 MINOR
- **Impact:** MEDIUM - Validation improvements
- **Risk:** Low (within 2.x)
- **Recommendation:** **UPGRADE RECOMMENDED**
  - All services use Pydantic
  - Test data validation
- **Priority:** MEDIUM

#### **pydantic-settings: 2.4.0 → 2.12.0** 📈 MINOR
- **Impact:** LOW - Settings management
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### Utilities

#### **apscheduler: 3.10.4 → 3.11.1** 📈 MINOR
- **Impact:** LOW - Scheduler improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
  - Affected services: `ai-automation-service`, `automation-miner`
- **Priority:** LOW

#### **rapidfuzz: 3.0.0 → 3.14.3** 📈 MINOR
- **Impact:** LOW - Performance improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

#### **beautifulsoup4: 4.12.0 → 4.14.2** 📈 MINOR
- **Impact:** LOW - HTML parsing improvements
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
  - Affected service: `automation-miner`
- **Priority:** LOW

#### **lxml: 5.0.0 → 6.0.2** 📈 MINOR
- **Impact:** LOW - XML/HTML parsing
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

---

## 🟢 Low Priority - Patch Updates (Safe to Upgrade)

### **python-dotenv: 1.0.1 → 1.2.1** 📈 PATCH
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### **pyyaml: 6.0.1 → 6.0.3** 📈 PATCH
- **Risk:** Minimal (security fixes likely)
- **Recommendation:** **UPGRADE RECOMMENDED**
- **Priority:** MEDIUM (potential security fixes)

### **requests: 2.32.3 → 2.32.5** 📈 PATCH
- **Risk:** Minimal
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### **psutil: 6.0.0 → 7.1.3** 📈 MINOR
- **Risk:** Low
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

### **python-jose: 3.3.0 → 3.5.0** 📈 PATCH
- **Risk:** Low (authentication library)
- **Recommendation:** **UPGRADE RECOMMENDED**
- **Priority:** MEDIUM (security-related)

### **black: 23.11.0 → 25.11.0** 📈 YEARLY
- **Risk:** Code formatting changes only
- **Recommendation:** **SAFE TO UPGRADE**
  - May reformat code
- **Priority:** LOW

### **mypy: 1.7.1 → 1.18.2** 📈 MINOR
- **Risk:** New type checking rules
- **Recommendation:** **SAFE TO UPGRADE**
- **Priority:** LOW

---

## ✅ Up to Date

1. **uvicorn: 0.38.0** ✓
2. **httpx: 0.28.1** ✓
3. **passlib: 1.7.4** ✓

---

## 📋 Phased Upgrade Strategy

### Phase 1: Security & Patch Updates (Low Risk) - Week 1

**Goal:** Apply security patches and bug fixes

```bash
# Update these packages across all services
fastapi==0.121.2              # Patch update
pyyaml==6.0.3                 # Security fixes
aiohttp==3.13.2               # Security + bug fixes
python-jose==3.5.0            # Security-related
requests==2.32.5              # Patch update
python-dotenv==1.2.1          # Patch update
influxdb-client==1.49.0       # Bug fixes
sqlalchemy==2.0.44            # Bug fixes (19 versions!)
```

**Testing:**
- Run health checks across all services
- Verify database operations
- Test HTTP clients
- Check authentication flows

**Risk:** MINIMAL

---

### Phase 2: Framework & Core Updates (Medium Risk) - Week 2-3

**Goal:** Update core frameworks and dependencies

```bash
# Update web framework stack
pydantic==2.12.4
pydantic-settings==2.12.0
alembic==1.17.2
aiosqlite==0.21.0

# Update utilities
apscheduler==3.11.1
rapidfuzz==3.14.3
beautifulsoup4==4.14.2
lxml==6.0.2
psutil==7.1.3

# Update data processing
pandas==2.3.3
numpy==2.3.4
scipy==1.16.3
```

**Testing:**
- Test data validation with Pydantic
- Verify database migrations
- Test scheduled jobs
- Check data processing pipelines

**Risk:** LOW-MEDIUM

---

### Phase 3: AI/ML Stack Updates (High Risk) - Week 4-5

**Goal:** Update AI/ML libraries with careful testing

```bash
# Update ML libraries (test thoroughly!)
scikit-learn==1.7.2           # Re-train models
spacy==3.8.9                  # Re-download language models

# Update PyTorch ecosystem
torch==2.9.1+cpu              # Use CPU-only wheel
transformers==4.57.1          # Test model loading
sentence-transformers==5.1.2  # TEST EMBEDDINGS CAREFULLY!
openvino==2025.3.0            # Test INT8 quantization
optimum-intel==1.26.1         # Update with OpenVINO
```

**Testing:**
- ⚠️ **CRITICAL:** Test embedding consistency (sentence-transformers)
- Verify model loading and inference
- Test NER performance
- Benchmark clustering algorithms
- Verify INT8 quantization works
- Check embedding dimensions

**Risk:** HIGH - May require model retraining or re-indexing

---

### Phase 4: Breaking Changes (High Risk) - Week 6-8

**Goal:** Handle major version updates with breaking changes

#### 4A: OpenAI SDK v2 Migration

```bash
openai==2.8.0
```

**Migration steps:**
1. Review [OpenAI Python SDK v2 migration guide](https://github.com/openai/openai-python/discussions/742)
2. Update client initialization:
   ```python
   # Old (v1)
   import openai
   openai.api_key = "..."
   response = openai.ChatCompletion.create(...)

   # New (v2)
   from openai import OpenAI
   client = OpenAI(api_key="...")
   response = client.chat.completions.create(...)
   ```
3. Update all GPT-4o-mini calls in `ai-automation-service`
4. Test natural language generation
5. Test Ask AI feature

**Risk:** HIGH - Breaking API changes

#### 4B: LangChain 1.0 Migration

```bash
langchain==1.0.7
```

**Migration steps:**
1. Review [LangChain 1.0 migration guide](https://python.langchain.com/docs/versions/v0_2/)
2. Update LCEL chain syntax
3. Test PDL workflows
4. Test feature flags: `USE_LANGCHAIN_ASK_AI`, `USE_LANGCHAIN_PATTERNS`
5. Update any custom chains

**Risk:** HIGH - Major API changes

#### 4C: Other Major Updates

```bash
paho-mqtt==2.1.0              # Update MQTT connection handling
docker==7.1.0                 # Update Docker SDK usage
tenacity==9.1.2               # Update retry decorators
```

**Testing:**
- Test MQTT connections
- Test Docker container management (admin-api)
- Test retry logic and circuit breakers

**Risk:** MEDIUM-HIGH

---

### Phase 5: Development Tools (Low Priority) - Anytime

```bash
# Code quality tools (won't affect production)
pytest==9.0.1
pytest-asyncio==1.3.0
pytest-cov==7.0.0
black==25.11.0
isort==7.0.0
flake8==7.3.0
mypy==1.18.2
```

**Testing:**
- Run test suite
- Reformat code if needed
- Update CI/CD if needed

**Risk:** MINIMAL

---

## 🚨 Special Considerations

### 1. **sentence-transformers (3.3.1 → 5.1.2)**

⚠️ **CRITICAL DECISION REQUIRED**

This is a **2 major version jump** that may affect:
- Embedding dimensions
- Model loading APIs
- Stored embeddings compatibility

**Options:**

**Option A: Upgrade (Recommended)**
- Test embedding consistency first
- May need to re-generate stored embeddings
- Better performance and features

**Option B: Stay on 3.x**
- Pin to `sentence-transformers>=3.3.1,<4.0.0`
- Avoid re-indexing work
- Miss out on improvements

**Recommendation:** **Upgrade to 5.1.2** but test thoroughly first. Run a comparison:

```python
# Test embedding consistency
from sentence_transformers import SentenceTransformer

# Old version embeddings
model_old = SentenceTransformer('all-MiniLM-L6-v2')
emb_old = model_old.encode("test sentence")

# New version embeddings (after upgrade)
model_new = SentenceTransformer('all-MiniLM-L6-v2')
emb_new = model_new.encode("test sentence")

# Compare
import numpy as np
similarity = np.dot(emb_old, emb_new) / (np.linalg.norm(emb_old) * np.linalg.norm(emb_new))
print(f"Similarity: {similarity}")  # Should be very close to 1.0
```

---

### 2. **numpy Version Inconsistency**

**Issue:** Different services use different numpy versions:
- `ai-automation-service`: numpy==1.26.4
- `openvino-service`: numpy==2.0.1
- `ml-service`: numpy==1.26.4
- `device-intelligence-service`: numpy==2.0.1

**Recommendation:** **Standardize on numpy==2.3.4** across all services for consistency.

---

### 3. **httpx Version Inconsistency**

**Issue:** Different services use different httpx versions:
- Most services: httpx==0.27.2
- `data-api`, `automation-miner`: httpx==0.28.1

**Recommendation:** **Standardize on httpx==0.28.1** (already latest).

---

### 4. **Transformers + optimum-intel Compatibility**

**Current constraint:** `optimum-intel==1.21.0` requires `transformers<4.46`
**Your version:** `transformers==4.46.1` (exceeds constraint!)

**Recommendation:**
1. Update to `optimum-intel==1.26.1` (supports transformers>=4.36,<4.58)
2. Then update `transformers==4.57.1`
3. Test INT8 quantization works

---

## 📊 Summary Recommendation

### Immediate Actions (This Week)

1. ✅ **Apply security patches** (Phase 1) - Low risk, high value
   - aiohttp, pyyaml, python-jose, requests

2. ✅ **Standardize versions** across services
   - numpy → 2.3.4
   - httpx → 0.28.1

3. ✅ **Update core frameworks** (Phase 2) - Low risk
   - FastAPI, Pydantic, SQLAlchemy, InfluxDB client

### Medium Term (Next Month)

4. 🔄 **Test AI/ML updates** (Phase 3) - High impact
   - sentence-transformers (TEST CAREFULLY!)
   - transformers + optimum-intel
   - scikit-learn
   - torch, openvino

5. 🔄 **Plan breaking changes** (Phase 4)
   - OpenAI SDK v2 migration
   - LangChain 1.0 migration
   - paho-mqtt 2.x migration

### Long Term (When Convenient)

6. 📝 **Update development tools** (Phase 5)
   - pytest, black, mypy, flake8

---

## 🎯 Final Recommendations

### ✅ **UPGRADE NOW** (Low Risk, High Value)

- fastapi==0.121.2
- aiohttp==3.13.2 (security)
- pyyaml==6.0.3 (security)
- python-jose==3.5.0 (security)
- sqlalchemy==2.0.44 (bug fixes)
- influxdb-client==1.49.0
- pydantic==2.12.4
- pandas==2.3.3

### 🔄 **UPGRADE SOON** (Medium Risk, Good Value)

- scikit-learn==1.7.2
- transformers==4.57.1
- openvino==2025.3.0
- optimum-intel==1.26.1
- torch==2.9.1+cpu

### ⚠️ **UPGRADE WITH CAUTION** (High Risk, Test Thoroughly)

- sentence-transformers==5.1.2 (**TEST EMBEDDINGS FIRST!**)
- openai==2.8.0 (breaking changes - plan migration)
- langchain==1.0.7 (breaking changes - plan migration)
- paho-mqtt==2.1.0 (breaking changes)

### ❌ **DEFER** (Low Priority)

- Development tools (pytest, black, mypy, etc.) - upgrade anytime
- Minor utilities - upgrade when convenient

---

## 📝 Next Steps

1. **Review this report** with the team
2. **Decide on sentence-transformers strategy** (upgrade vs pin)
3. **Create upgrade branches** for each phase
4. **Test phase by phase** - don't upgrade everything at once
5. **Monitor for issues** after each phase
6. **Update CI/CD** to catch version drift

---

## 🔗 Resources

- [LangChain 1.0 Migration Guide](https://python.langchain.com/docs/versions/v0_2/)
- [OpenAI Python SDK v2 Migration](https://github.com/openai/openai-python/discussions/742)
- [paho-mqtt 2.0 Migration](https://github.com/eclipse/paho.mqtt.python/blob/master/ChangeLog.txt)
- [PyPI Security Advisories](https://pypi.org/security/)

---

**Report Generated By:** HomeIQ Dependency Analyzer
**Last Updated:** November 15, 2025
**Next Review:** December 15, 2025 (monthly)
