---
status: Open
priority: Critical
service: ml-service
created: 2025-11-15
labels: [critical, memory-leak, security]
---

# [CRITICAL] ML Service - Memory Leaks and Security Vulnerabilities

**Use 2025 patterns, architecture and versions for decisions and ensure the Readme files are up to date.**

## Overview
The ML service has **5 CRITICAL issues** including memory leaks, DoS vulnerabilities, and blocking I/O that will cause service failures under production load.

---

## CRITICAL Issues

### 1. **MEMORY LEAK - StandardScaler State Accumulation**
**Location:** `clustering.py:20,41`, `anomaly_detection.py:20,41`
**Severity:** CRITICAL

**Issue:** `StandardScaler` instances are created once at initialization and reused across ALL requests. Each `fit_transform()` call refits the scaler.

```python
class ClusteringManager:
    def __init__(self):
        self.scaler = StandardScaler()  # SHARED across all requests

    async def kmeans_cluster(self, data: List[List[float]], ...):
        X_scaled = self.scaler.fit_transform(X)  # Contaminates future requests
```

**Impact:**
- **Privacy violation** - scaler trained on previous users' data affects current request
- **Data leakage** between requests
- **Memory accumulation** over time
- **Incorrect scaling** when data distributions change

**Fix:** Create new `StandardScaler()` instance per request.

---

### 2. **MEMORY LEAK - ML Models Never Cleaned Up**
**Location:** `clustering.py:48-49,84-85`, `anomaly_detection.py:44-50`
**Severity:** CRITICAL

**Issue:** New sklearn models (KMeans, DBSCAN, IsolationForest) created for EVERY request but never explicitly released.

```python
async def kmeans_cluster(self, data: ...):
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_scaled)
    return labels.tolist(), n_clusters  # Model stays in memory
```

**Impact:**
- Models accumulate in memory
- Each model stores fitted data (centroids, trees, etc.)
- OOM errors under sustained load

**Fix:** Explicitly delete models or rely on proper scoping. Consider model pooling for high traffic.

---

### 3. **NO INPUT VALIDATION - DoS Attack Vector**
**Location:** All endpoints in `main.py`
**Severity:** CRITICAL

**Issue:** ZERO validation on:
- Data size (attacker could send gigabytes)
- Array dimensions (could send millions of features)
- Number of clusters (could request 999999 clusters)
- Batch operations count

**Attack Example:**
```json
POST /cluster
{
  "data": [[1.0] * 10000] * 100000,  // 100k points × 10k dimensions = 8GB
  "n_clusters": 999999
}
```

**Impact:**
- Service DoS
- Container crash
- Resource exhaustion

**Fix:** Add input validation:
- Max data size: 10MB
- Max dimensions: 1000
- Max clusters: 100
- Max batch size: 100 (as documented in README but NOT enforced)

---

### 4. **UNBOUNDED BATCH PROCESSING**
**Location:** `main.py:188-257`
**Severity:** CRITICAL

**Issue:** Batch endpoint has NO limits on number of operations.

```python
async def batch_process(request: BatchProcessRequest):
    for operation in request.operations:  # Could be unlimited!
        # Process each synchronously...
```

**Impact:**
- Complete service lockup
- Request timeouts for other users
- Could tie up all resources for minutes

**Fix:** Enforce `MAX_BATCH_SIZE=100` as documented.

---

### 5. **BLOCKING EVENT LOOP - False Async**
**Location:** All `async def` methods in `clustering.py` and `anomaly_detection.py`
**Severity:** CRITICAL

**Issue:** Methods declared `async` but perform **blocking CPU-bound operations** with NO `await`.

```python
async def kmeans_cluster(self, data: ...):  # Async declaration
    X = np.array(data)                      # BLOCKING
    X_scaled = self.scaler.fit_transform(X) # BLOCKING (could take seconds)
    kmeans = KMeans(...)                    # BLOCKING
    labels = kmeans.fit_predict(X_scaled)   # BLOCKING (heavy computation)
    # NO await anywhere - blocks entire event loop!
```

**Impact:**
- Under load, ALL requests timeout because event loop is blocked by ML computation
- Service becomes unresponsive
- Violates async best practices from CLAUDE.md

**Fix:** Move CPU-bound work to executor pool:
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, self._fit_kmeans, X_scaled)
```

---

## HIGH Severity Issues

### 6. **INFORMATION DISCLOSURE**
**Location:** `main.py:158, 186, 257`
**Severity:** HIGH

**Issue:** Raw exception messages exposed to clients.

**Impact:** Attackers learn system internals.

---

### 7. **UNRESTRICTED CORS**
**Location:** `main.py:61-67`
**Severity:** HIGH

**Issue:** Accepts requests from ANY origin.

**Impact:** CSRF attacks, unauthorized access.

---

## Risk Assessment

| Issue | Severity | Likelihood | Impact |
|-------|----------|------------|---------|
| StandardScaler leak | CRITICAL | High | Data contamination, memory leak |
| Model accumulation | CRITICAL | High | OOM crashes |
| No input validation | CRITICAL | Medium | DoS attacks |
| Unbounded batching | CRITICAL | Medium | Resource exhaustion |
| Blocking event loop | CRITICAL | High | Performance degradation |

---

## Recommended Actions

### Immediate (Critical)
1. Create new `StandardScaler()` instance per request
2. Add input validation (max data size: 10MB, max dimensions: 1000, max clusters: 100)
3. Enforce batch size limit (MAX_BATCH_SIZE=100)
4. Add timeouts to all operations
5. Move CPU-bound work to executor pool

### High Priority
6. Generic error messages (don't expose internal details)
7. Restrict CORS origins

**This service is vulnerable to multiple attack vectors and will experience memory/performance issues under production load.**

---

## References
- CLAUDE.md - Async Best Practices & Performance Patterns
- Service location: `/services/ml-service/`
- Port: 8025 → 8020
