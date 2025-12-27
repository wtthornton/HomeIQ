# Story AI4.6: Performance Optimization & OpenVINO Integration

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 5  
**Priority:** High  
**Dependencies:** Stories AI4.1-AI4.5

---

## Story Description

AS AN AI automation service  
I WANT TO optimize n-level synergy detection for edge deployment  
SO THAT detection completes in <5s with <500MB memory footprint

---

## Acceptance Criteria

### Must Have

1. **✅ OpenVINO INT8 Optimization**
   - Quantize all models to INT8 using optimum-cli
   - Verify model sizes: embedding (20MB), reranker (280MB), classifier (80MB)
   - Test inference speed on CPU (target baseline)
   - Optional GPU acceleration if available

2. **✅ Embedding Cache Optimization**
   - In-memory cache during detection run
   - Lazy loading (load embeddings only when needed)
   - Batch load common areas (kitchen, living room)
   - Memory limit: 200MB for embeddings

3. **✅ Batch Processing**
   - Batch descriptor generation (32 devices at a time)
   - Batch embedding encoding (32 descriptors)
   - Batch re-ranking (32 pairs per batch)
   - Minimize model I/O calls

4. **✅ Performance Benchmarking**
   - Benchmark suite: 10, 20, 50, 100 devices
   - Depth variations: 2, 3, 4, 5 hops
   - Memory profiling (peak usage tracking)
   - Latency breakdown (per phase timing)

5. **✅ Resource Management**
   - Graceful degradation if memory limited
   - Model preloading on service startup
   - Clean model unloading if needed
   - Thread-safe model access

### Should Have

6. **📋 GPU Acceleration (Optional)**
   - Detect GPU availability (CUDA, OpenVINO GPU plugin)
   - Move embeddings to GPU if available
   - Benchmark CPU vs GPU performance
   - Fallback to CPU if GPU fails

7. **📋 Caching Strategy**
   - Cache frequent path patterns
   - Cache re-ranking results (24 hour TTL)
   - LRU eviction for memory management

---

## Technical Implementation

### Model Quantization Script

```bash
#!/bin/bash
# scripts/quantize-nlevel-models.sh

# Create models directory
mkdir -p ./models/nlevel-synergy

echo "🔧 Quantizing models for N-Level Synergy Detection..."

# 1. Quantize embedding model (sentence-transformers/all-MiniLM-L6-v2)
echo "📦 Quantizing embedding model..."
optimum-cli export openvino \
  --model sentence-transformers/all-MiniLM-L6-v2 \
  --task feature-extraction \
  --weight-format int8 \
  ./models/nlevel-synergy/embedding-int8

# 2. Download pre-quantized re-ranker (already INT8)
echo "📦 Downloading pre-quantized re-ranker..."
python -c "
from optimum.intel.openvino import OVModelForSequenceClassification
model = OVModelForSequenceClassification.from_pretrained('OpenVINO/bge-reranker-base-int8-ov')
model.save_pretrained('./models/nlevel-synergy/reranker-int8')
"

# 3. Quantize classifier model (google/flan-t5-small)
echo "📦 Quantizing classifier model..."
optimum-cli export openvino \
  --model google/flan-t5-small \
  --task text2text-generation \
  --weight-format int8 \
  ./models/nlevel-synergy/classifier-int8

echo "✅ Model quantization complete!"
echo "📊 Model sizes:"
du -sh ./models/nlevel-synergy/*
```

### Performance Benchmarking Script

```python
# scripts/benchmark_nlevel_synergy.py
"""
Benchmark n-level synergy detection performance.

Story AI4.6: Performance Optimization
"""

import asyncio
import time
import psutil
import tracemalloc
from typing import Dict, List
import statistics

class NLevelSynergyBenchmark:
    """Benchmark suite for n-level synergy detection."""
    
    def __init__(self, detector):
        self.detector = detector
        self.results = []
    
    async def run_benchmarks(self):
        """Run comprehensive benchmark suite."""
        print("🔬 N-Level Synergy Detection Benchmark Suite\n")
        
        # Test configurations
        configs = [
            {"devices": 10, "depth": 2, "name": "Small home, 2-hop"},
            {"devices": 20, "depth": 3, "name": "Medium home, 3-hop"},
            {"devices": 50, "depth": 3, "name": "Large home, 3-hop"},
            {"devices": 100, "depth": 4, "name": "Very large home, 4-hop"},
        ]
        
        for config in configs:
            result = await self._benchmark_config(config)
            self.results.append(result)
            self._print_result(result)
        
        # Summary
        self._print_summary()
    
    async def _benchmark_config(self, config: Dict) -> Dict:
        """Benchmark single configuration."""
        num_devices = config['devices']
        max_depth = config['depth']
        
        # Setup test data
        devices = self._generate_test_devices(num_devices)
        
        # Memory tracking
        tracemalloc.start()
        process = psutil.Process()
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run detection (3 iterations)
        times = []
        for i in range(3):
            start = time.time()
            synergies = await self.detector.detect_nlevel_synergies(
                devices,
                max_depth=max_depth
            )
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)
        
        # Memory tracking
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024 / 1024  # MB
        tracemalloc.stop()
        
        return {
            "name": config['name'],
            "devices": num_devices,
            "depth": max_depth,
            "synergies_found": len(synergies),
            "time_p50_ms": statistics.median(times),
            "time_p95_ms": max(times),
            "time_avg_ms": statistics.mean(times),
            "mem_used_mb": mem_after - mem_before,
            "mem_peak_mb": peak_mem
        }
    
    def _print_result(self, result: Dict):
        """Print benchmark result."""
        print(f"\n{'='*60}")
        print(f"Config: {result['name']}")
        print(f"  Devices: {result['devices']}, Depth: {result['depth']}")
        print(f"  Synergies Found: {result['synergies_found']}")
        print(f"  Performance:")
        print(f"    P50: {result['time_p50_ms']:.0f}ms")
        print(f"    P95: {result['time_p95_ms']:.0f}ms")
        print(f"    Avg: {result['time_avg_ms']:.0f}ms")
        print(f"  Memory:")
        print(f"    Used: {result['mem_used_mb']:.0f}MB")
        print(f"    Peak: {result['mem_peak_mb']:.0f}MB")
        
        # Check targets
        target_time = 5000  # 5s
        target_mem = 500    # 500MB
        
        time_status = "✅" if result['time_p95_ms'] < target_time else "❌"
        mem_status = "✅" if result['mem_peak_mb'] < target_mem else "❌"
        
        print(f"  Status: {time_status} Time, {mem_status} Memory")
    
    def _print_summary(self):
        """Print benchmark summary."""
        print(f"\n{'='*60}")
        print("📊 Benchmark Summary\n")
        
        print(f"{'Config':<30} {'P50 (ms)':<12} {'P95 (ms)':<12} {'Peak Mem (MB)':<15}")
        print(f"{'-'*70}")
        
        for result in self.results:
            print(f"{result['name']:<30} {result['time_p50_ms']:<12.0f} {result['time_p95_ms']:<12.0f} {result['mem_peak_mb']:<15.0f}")
        
        # Overall pass/fail
        all_pass = all(
            r['time_p95_ms'] < 5000 and r['mem_peak_mb'] < 500
            for r in self.results[:2]  # Check first 2 configs (realistic scenarios)
        )
        
        print(f"\n{'✅ All targets met!' if all_pass else '❌ Some targets missed'}")

if __name__ == "__main__":
    # Run benchmark
    from nlevel_synergy.detector import NLevelSynergyDetector
    
    detector = NLevelSynergyDetector()
    benchmark = NLevelSynergyBenchmark(detector)
    
    asyncio.run(benchmark.run_benchmarks())
```

### Optimized Embedding Cache

```python
# services/ai-automation-service/src/nlevel_synergy/embedding_cache.py

from typing import Dict, Optional
import torch
import numpy as np
import logging

logger = logging.getLogger(__name__)

class EmbeddingCache:
    """
    In-memory embedding cache for fast access during detection.
    
    Story AI4.6: Performance Optimization
    Context7: Minimize I/O, maximize cache hits
    """
    
    def __init__(self, db_session, max_cache_mb: int = 200):
        self.db = db_session
        self.max_cache_mb = max_cache_mb
        self._cache: Dict[str, torch.Tensor] = {}
        self._loaded_areas = set()
    
    def load_embeddings(self, entity_ids: List[str]) -> Dict[str, torch.Tensor]:
        """
        Load embeddings with intelligent caching.
        
        Strategy:
        1. Check in-memory cache first
        2. Load from database if miss
        3. Convert to tensors for GPU compatibility
        4. LRU eviction if cache full
        """
        embeddings = {}
        to_load = []
        
        # Check cache first
        for entity_id in entity_ids:
            if entity_id in self._cache:
                embeddings[entity_id] = self._cache[entity_id]
            else:
                to_load.append(entity_id)
        
        # Load missing embeddings
        if to_load:
            loaded = self._load_from_db(to_load)
            
            for entity_id, embedding_bytes in loaded.items():
                # Convert to tensor
                embedding_np = np.frombuffer(embedding_bytes, dtype=np.float32)
                embedding_tensor = torch.from_numpy(embedding_np)
                
                # Cache if space available
                if self._check_cache_space():
                    self._cache[entity_id] = embedding_tensor
                
                embeddings[entity_id] = embedding_tensor
        
        logger.debug(
            f"Embedding cache: {len(self._cache)} cached, "
            f"{len(to_load)} loaded from DB"
        )
        
        return embeddings
    
    def load_area(self, area_id: str):
        """Batch load all embeddings for an area."""
        if area_id in self._loaded_areas:
            return
        
        # Get all entity_ids in area
        results = self.db.execute(
            """
            SELECT de.entity_id, de.embedding
            FROM device_embeddings de
            JOIN entities e ON de.entity_id = e.entity_id
            WHERE e.area_id = ?
            """,
            (area_id,)
        ).fetchall()
        
        # Cache all
        for entity_id, embedding_bytes in results:
            if entity_id not in self._cache:
                embedding_np = np.frombuffer(embedding_bytes, dtype=np.float32)
                self._cache[entity_id] = torch.from_numpy(embedding_np)
        
        self._loaded_areas.add(area_id)
        logger.info(f"Loaded {len(results)} embeddings for area '{area_id}'")
    
    def _load_from_db(self, entity_ids: List[str]) -> Dict[str, bytes]:
        """Load embeddings from database."""
        placeholders = ','.join(['?' for _ in entity_ids])
        results = self.db.execute(
            f"SELECT entity_id, embedding FROM device_embeddings WHERE entity_id IN ({placeholders})",
            entity_ids
        ).fetchall()
        
        return {entity_id: embedding for entity_id, embedding in results}
    
    def _check_cache_space(self) -> bool:
        """Check if cache has space for more embeddings."""
        # Estimate: 384 floats * 4 bytes = 1536 bytes per embedding
        current_mb = len(self._cache) * 1536 / 1024 / 1024
        return current_mb < self.max_cache_mb
    
    def clear(self):
        """Clear cache."""
        self._cache.clear()
        self._loaded_areas.clear()
        logger.debug("Embedding cache cleared")
```

---

## Performance Targets

| Configuration | Time Target | Memory Target | Status |
|--------------|-------------|---------------|--------|
| 20 devices, depth 3 | <5s | <500MB | Primary |
| 50 devices, depth 3 | <12s | <600MB | Secondary |
| 100 devices, depth 4 | <30s | <800MB | Stretch |

---

## Testing Strategy

### Benchmark Tests
- Run on various hardware (Intel i5, i7, ARM)
- Test with/without GPU
- Memory stress tests
- Long-running stability tests

### Optimization Tests
- Cache hit rate monitoring
- Model loading time
- Batch processing efficiency
- GPU vs CPU comparison

---

## Success Metrics

| Metric | Target | Measured |
|--------|--------|----------|
| **P95 Latency (20 devices)** | <5s | ___ s |
| **Peak Memory** | <500MB | ___ MB |
| **Model Load Time** | <2s | ___ s |
| **Cache Hit Rate** | >80% | ___ % |

---

**Created:** October 19, 2025  
**Status:** Proposed

