# Phase 1 Model Stack - Docker Deployment

**Stack:** all-MiniLM-L6-v2 (INT8) → bge-reranker-base (INT8) → flan-t5-small (INT8)  
**Size:** 380MB (INT8) or 1.5GB (standard)  
**Deployment:** Docker container with persistent model volume  
**Location:** `/app/models/` inside container

---

## 🐳 Docker Setup

### **What Changed**

1. **requirements.txt** - Added OpenVINO stack:
   - sentence-transformers==3.3.1
   - transformers==4.46.3
   - torch==2.5.1
   - openvino==2024.5.0
   - optimum-intel==1.20.0

2. **Dockerfile** - Added libgomp1 for OpenVINO threading

3. **docker-compose.yml** - Added models volume and increased memory:
   - Volume: `ai_automation_models:/app/models`
   - Memory: 1G → 2G (for model loading)

4. **New Files:**
   - `src/models/model_manager.py` - Model management
   - `scripts/download-models.py` - Pre-download script

---

## 🚀 Deployment Options

### **Option A: Lazy Loading (Recommended for MVP)**

Models download automatically on first use (inside Docker).

**Pros:**
- ✅ Faster initial build
- ✅ No build-time downloads
- ✅ Works immediately

**Cons:**
- ⚠️ First pattern detection run is slower (~5-10 min for downloads)
- ⚠️ Requires internet connection on first run

**How it works:**
```python
# In src/models/model_manager.py
model = OVModelForFeatureExtraction.from_pretrained(
    "sentence-transformers/all-MiniLM-L6-v2",
    export=True,  # Downloads and converts on first use
    cache_dir="/app/models"  # Persists in Docker volume
)
```

**Deploy:**
```bash
docker-compose up --build ai-automation-service
# Models download on first API call
# Cached in ai_automation_models volume
# Subsequent restarts: models already cached
```

---

### **Option B: Pre-download During Build (Production)**

Download models during Docker build.

**Pros:**
- ✅ First run is fast (models already cached)
- ✅ Predictable build
- ✅ No internet needed after build

**Cons:**
- ⚠️ Slower build time (+10-15 minutes)
- ⚠️ Requires internet during build

**Enable:**
```dockerfile
# Uncomment in Dockerfile (lines 50-51):
COPY services/ai-automation-service/scripts/download-models.py ./scripts/
RUN python scripts/download-models.py || echo "Model download failed, will retry on startup"
```

**Deploy:**
```bash
docker-compose build ai-automation-service  # Downloads models
docker-compose up ai-automation-service      # Ready immediately
```

---

## 💾 Model Volume Persistence

### **Models Cached in Docker Volume**

```bash
# Volume defined in docker-compose.yml
volumes:
  ai_automation_models:  # Persistent model cache

# Mounted in container:
/app/models/
  ├── models--sentence-transformers--all-MiniLM-L6-v2/
  ├── models--OpenVINO--bge-reranker-base-int8-ov/
  └── models--google--flan-t5-small/
```

**Benefits:**
- Models download once, persist across container restarts
- Survives `docker-compose down` and `up`
- Shared if multiple containers need models (future)

**Clear cache:**
```bash
# Only if you need to re-download
docker volume rm homeiq_ai_automation_models
```

---

## 🔧 Usage in Code

### **In Your Pattern Detection Code**

```python
from src.models.model_manager import get_model_manager

# Get singleton instance
model_mgr = get_model_manager()

# Generate embeddings (auto-loads model on first call)
pattern_texts = ["Light turns on at 7 AM", "Lock door at 11 PM"]
embeddings = model_mgr.generate_embeddings(pattern_texts)  # (2, 384) array

# Re-rank patterns (auto-loads re-ranker on first call)
query = "morning routine pattern"
top_100 = similarity_search(query_embedding, all_patterns, top_k=100)
top_10 = model_mgr.rerank(query, top_100, top_k=10)

# Classify pattern (auto-loads classifier on first call)
classification = model_mgr.classify_pattern("Turn on lights at 7:15 AM on weekdays")
# Returns: {'category': 'convenience', 'priority': 'medium'}
```

---

## 🚀 Quick Start

### **Build and Run**

```bash
# Option 1: Lazy loading (models download on first use)
docker-compose up --build ai-automation-service

# Option 2: Pre-download during build
# 1. Edit Dockerfile, uncomment lines 50-51
# 2. Build:
docker-compose build ai-automation-service
# 3. Run:
docker-compose up ai-automation-service
```

### **Test Models Inside Container**

```bash
# Exec into running container
docker exec -it ai-automation-service bash

# Test models
python scripts/download-models.py

# Check model cache
ls -lh /app/models/
```

### **View Logs**

```bash
# Watch model download logs
docker-compose logs -f ai-automation-service

# Look for:
# "Loading embedding model: all-MiniLM-L6-v2..."
# "✅ Loaded OpenVINO optimized embedding model (20MB)"
```

---

## 📊 Memory Requirements

### **Updated Container Limits**

| Phase | Memory Limit | Reason |
|-------|--------------|--------|
| **Before** | 1GB | Small models or no models |
| **After** | 2GB | OpenVINO models need headroom |

**Breakdown:**
- Base service: 256MB
- Model loading: 380MB (INT8) or 1.5GB (standard)
- Inference working memory: 200-400MB
- Buffer: 500MB
- **Total:** 2GB (safe for INT8 stack)

**If using standard models (not INT8):**
- Increase to 3GB: `memory: 3G`

---

## 🎯 First Run Behavior

### **What Happens on First Run**

```bash
docker-compose up ai-automation-service

# Container starts:
# 1. FastAPI initializes
# 2. Routes load
# 3. Models NOT loaded yet (lazy)

# First pattern detection API call or 3 AM job:
# 1. ModelManager.get_embedding_model() called
# 2. Downloads all-MiniLM-L6-v2 (~80MB)
# 3. Converts to OpenVINO INT8 (~20MB)
# 4. Caches in /app/models/ (Docker volume)
# 5. Returns model instance

# Same for re-ranker and classifier
# Total first-run download: 5-10 minutes (one-time)

# Subsequent runs:
# Models load from cache (< 30 seconds)
```

---

## 🔍 Verify Installation

### **Check Models After First Run**

```bash
# Exec into container
docker exec -it ai-automation-service bash

# Check model cache size
du -sh /app/models/
# Should show: ~380MB (INT8) or ~1.5GB (standard)

# List cached models
ls -la /app/models/

# Test model manager
python -c "from src.models.model_manager import get_model_manager; mgr = get_model_manager(); print(mgr.get_model_info())"
```

---

## ✅ Next Steps

**Since you want everything in Docker:**

1. ✅ **Build updated container:**
   ```bash
   docker-compose build ai-automation-service
   ```

2. ✅ **Start container:**
   ```bash
   docker-compose up ai-automation-service
   ```

3. ✅ **Models download on first use** (or pre-download if enabled)

4. ✅ **Start Week 1 development** - Build preprocessing pipeline

**Ready to build the container?**

