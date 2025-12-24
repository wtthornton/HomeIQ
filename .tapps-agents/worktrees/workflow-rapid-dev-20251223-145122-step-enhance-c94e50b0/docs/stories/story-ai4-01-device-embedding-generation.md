# Story AI4.1: Device Embedding Generation

**Epic:** AI-4 - N-Level Synergy Detection  
**Story Points:** 8  
**Priority:** High  
**Status:** Proposed  
**Assignee:** Dev Team

---

## Story Description

As an **AI automation service**, I want to **generate semantic embeddings for all smart home devices** so that I can **discover multi-hop automation relationships using similarity search**.

### User Story

```
AS AN AI automation service
I WANT TO generate semantic embeddings for device capabilities and context
SO THAT I can find semantically similar devices for multi-hop automation chains
```

---

## Business Value

- **Foundation for N-Level Detection:** Enables semantic device relationship discovery
- **Universal Device Understanding:** Works across all device types without manual rules
- **Performance:** Cached embeddings enable fast similarity searches (<100ms)
- **Scalability:** One-time generation with 30-day refresh policy

---

## Acceptance Criteria

### Must Have

1. **✅ Embedding Generation**
   - Generate 384-dim embeddings for all devices using `sentence-transformers/all-MiniLM-L6-v2` (INT8)
   - Create device descriptors in natural language format
   - Batch process (32 devices at a time) for efficiency
   - Handle devices with incomplete metadata gracefully

2. **✅ Database Storage**
   - Create `device_embeddings` table in SQLite
   - Store embeddings as BLOB (numpy array serialized)
   - Store descriptor text for debugging/validation
   - Track model version and last_updated timestamp

3. **✅ Caching Strategy**
   - Cache embeddings for 30 days
   - Skip regeneration if fresh (<30 days old)
   - Force refresh API endpoint
   - Handle model version changes (regenerate if version mismatch)

4. **✅ Device Descriptor Quality**
   - Include device class (e.g., "motion sensor", "dimmable light")
   - Include primary action (e.g., "detects presence", "controls brightness")
   - Include area/location (e.g., "in kitchen area")
   - Include top 3 capabilities from device intelligence data

5. **✅ OpenVINO Optimization**
   - Use optimum-intel for INT8 quantization
   - Model size ≤25MB
   - Inference time <5ms per device
   - Support both CPU and GPU acceleration

### Should Have

6. **📋 Performance Monitoring**
   - Log embedding generation time per batch
   - Track cache hit rate
   - Monitor embedding quality (similarity distributions)

7. **📋 Error Handling**
   - Graceful degradation if model fails to load
   - Fallback to cached embeddings if generation fails
   - Retry logic with exponential backoff

### Nice to Have

8. **💡 Embedding Quality Metrics**
   - Calculate average similarity within same device class
   - Identify outlier embeddings (unusually low/high similarity)
   - Visualize embeddings (t-SNE) for validation

---

## Technical Implementation

### Architecture

```
┌──────────────────────────────────────────────────┐
│  DeviceEmbeddingGenerator                        │
│  (Main Orchestrator)                             │
└──────────────────────────────────────────────────┘
           ↓
    ┌──────┴────────┐
    ↓               ↓
┌─────────────┐  ┌──────────────┐
│ Descriptor  │  │ Embedding    │
│ Generator   │  │ Model        │
│             │  │ (OpenVINO)   │
└─────────────┘  └──────────────┘
           ↓               ↓
    ┌──────┴────────┬──────┘
    ↓               ↓
┌──────────┐  ┌───────────┐
│ Cache    │  │ Database  │
│ Manager  │  │ (SQLite)  │
└──────────┘  └───────────┘
```

### Database Schema

```sql
-- New table: device_embeddings
CREATE TABLE device_embeddings (
    entity_id TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,              -- Numpy array (384-dim float32)
    descriptor TEXT NOT NULL,             -- Natural language description
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    model_version TEXT DEFAULT 'all-MiniLM-L6-v2-int8',
    embedding_norm FLOAT,                 -- L2 norm for validation
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX idx_device_embeddings_updated ON device_embeddings(last_updated);
CREATE INDEX idx_device_embeddings_version ON device_embeddings(model_version);
```

### Code Structure

```
services/ai-automation-service/src/
├── nlevel_synergy/
│   ├── __init__.py
│   ├── device_embedding_generator.py  # Main class (NEW)
│   ├── descriptor_builder.py          # Device descriptor generation (NEW)
│   ├── embedding_model.py             # OpenVINO model wrapper (NEW)
│   └── embedding_cache.py             # Cache management (NEW)
├── database/
│   └── crud.py                         # Add embedding CRUD operations
└── models/
    └── model_manager.py                # Add OpenVINO model loading
```

### Implementation Details

#### 1. Descriptor Builder (Context7 Best Practice)

```python
# services/ai-automation-service/src/nlevel_synergy/descriptor_builder.py

class DeviceDescriptorBuilder:
    """
    Generates natural language descriptions for devices.
    
    Story AI4.1: Device Embedding Generation
    Context7 Best Practice: Clear, semantic descriptors for embedding quality
    """
    
    def __init__(self, capability_service):
        self.capability_service = capability_service
        self.action_mappings = self._load_action_mappings()
    
    def create_descriptor(self, device: Dict, entity: Dict, capabilities: Dict) -> str:
        """
        Create semantic device descriptor.
        
        Format:
        "{device_class} that {primary_action} in {area} area with {capabilities}"
        
        Examples:
        - "motion sensor that detects presence in kitchen area"
        - "dimmable light with RGB color control in living room area"
        - "smart thermostat controlling HVAC temperature in whole house"
        """
        # Extract components
        device_class = self._get_device_class(entity)
        primary_action = self._get_primary_action(entity, capabilities)
        area = entity.get('area_id', 'unknown')
        capability_features = self._get_top_capabilities(capabilities, limit=3)
        
        # Build descriptor
        descriptor = f"{device_class} that {primary_action}"
        descriptor += f" in {area} area"
        
        if capability_features:
            descriptor += f" with {', '.join(capability_features)}"
        
        return descriptor
    
    def _get_device_class(self, entity: Dict) -> str:
        """Get friendly device class name."""
        domain = entity['entity_id'].split('.')[0]
        device_class = entity.get('device_class', entity.get('original_device_class'))
        
        # Friendly name mapping
        friendly_names = {
            'binary_sensor': {
                'motion': 'motion sensor',
                'door': 'door sensor',
                'occupancy': 'occupancy sensor',
                'window': 'window sensor'
            },
            'sensor': {
                'temperature': 'temperature sensor',
                'humidity': 'humidity sensor',
                'battery': 'battery sensor'
            },
            'light': 'dimmable light',
            'switch': 'smart switch',
            'climate': 'smart thermostat',
            'lock': 'smart lock',
            'fan': 'ceiling fan',
            'cover': 'motorized cover'
        }
        
        if domain in friendly_names and isinstance(friendly_names[domain], dict):
            return friendly_names[domain].get(device_class, f"{domain} device")
        
        return friendly_names.get(domain, f"{domain} device")
    
    def _get_primary_action(self, entity: Dict, capabilities: Dict) -> str:
        """Determine primary action/purpose of device."""
        domain = entity['entity_id'].split('.')[0]
        device_class = entity.get('device_class')
        
        # Action mapping by domain + device_class
        actions = {
            'binary_sensor': {
                'motion': 'detects presence',
                'door': 'detects door state',
                'occupancy': 'detects occupancy',
                'window': 'detects window state'
            },
            'sensor': {
                'temperature': 'measures temperature',
                'humidity': 'measures humidity'
            },
            'light': 'controls lighting brightness',
            'switch': 'controls power state',
            'climate': 'controlling HVAC temperature',
            'lock': 'controls lock state',
            'fan': 'controls fan speed',
            'cover': 'controls position'
        }
        
        if domain in actions and isinstance(actions[domain], dict):
            return actions[domain].get(device_class, 'controls state')
        
        return actions.get(domain, 'controls state')
    
    def _get_top_capabilities(self, capabilities: Dict, limit: int = 3) -> List[str]:
        """Extract top N capabilities for descriptor."""
        if not capabilities or not isinstance(capabilities, dict):
            return []
        
        cap_list = capabilities.get('capabilities', {})
        if not cap_list:
            return []
        
        # Prioritize user-facing capabilities
        priority_caps = ['brightness', 'color_xy', 'color_temp', 'speed', 'position']
        
        friendly_caps = []
        for cap_name in cap_list.keys():
            if cap_name in priority_caps:
                friendly_caps.insert(0, self._friendly_cap_name(cap_name))
            else:
                friendly_caps.append(self._friendly_cap_name(cap_name))
        
        return friendly_caps[:limit]
    
    def _friendly_cap_name(self, cap_name: str) -> str:
        """Convert capability name to friendly format."""
        mappings = {
            'color_xy': 'RGB color control',
            'color_temp': 'color temperature',
            'brightness': 'brightness control',
            'speed': 'speed control',
            'position': 'position control'
        }
        return mappings.get(cap_name, cap_name.replace('_', ' '))
```

#### 2. Embedding Model (OpenVINO Optimization)

```python
# services/ai-automation-service/src/nlevel_synergy/embedding_model.py

from optimum.intel.openvino import OVModelForFeatureExtraction
from sentence_transformers import util
from transformers import AutoTokenizer
import torch
import numpy as np
import logging

logger = logging.getLogger(__name__)

class DeviceEmbeddingModel:
    """
    OpenVINO-optimized embedding model for device descriptions.
    
    Story AI4.1: Device Embedding Generation
    Context7 Best Practice: OpenVINO INT8 quantization for edge deployment
    """
    
    MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
    MODEL_VERSION = "all-MiniLM-L6-v2-int8"
    
    def __init__(self, model_cache_dir: str = "./models/cache"):
        self.model_cache_dir = model_cache_dir
        self.model = None
        self.tokenizer = None
        self.device = "CPU"  # OpenVINO device (CPU, GPU, etc.)
    
    def load_model(self):
        """
        Load OpenVINO-optimized model.
        
        Context7 Best Practice: Auto-export to OpenVINO with INT8 quantization
        """
        try:
            logger.info(f"Loading {self.MODEL_NAME} with OpenVINO optimization...")
            
            # Load with OpenVINO optimization (auto-export if needed)
            self.model = OVModelForFeatureExtraction.from_pretrained(
                self.MODEL_NAME,
                export=True,  # Auto-convert to OpenVINO if not cached
                cache_dir=self.model_cache_dir,
                device=self.device
            )
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.MODEL_NAME,
                cache_dir=self.model_cache_dir
            )
            
            logger.info(f"✅ Model loaded successfully (device: {self.device})")
            
        except Exception as e:
            logger.error(f"Failed to load OpenVINO model: {e}")
            raise
    
    def encode(
        self,
        texts: List[str],
        batch_size: int = 32,
        normalize: bool = True,
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Generate embeddings for text descriptions.
        
        Args:
            texts: List of device descriptors
            batch_size: Batch size for processing (Context7: 32 optimal)
            normalize: Normalize embeddings for dot-product scoring
            show_progress: Show progress bar
        
        Returns:
            Numpy array of embeddings (N x 384)
        
        Context7 Best Practice:
        - Batch processing for efficiency
        - Normalize for dot-product scoring (faster than cosine)
        """
        if not self.model:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        all_embeddings = []
        
        # Batch processing
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            
            # Tokenize batch
            inputs = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors='pt'
            )
            
            # Generate embeddings
            with torch.no_grad():
                outputs = self.model(**inputs)
                embeddings = outputs.last_hidden_state[:, 0, :]  # CLS token
            
            all_embeddings.append(embeddings)
        
        # Concatenate batches
        embeddings = torch.cat(all_embeddings, dim=0)
        
        # Normalize for dot-product scoring (Context7 best practice)
        if normalize:
            embeddings = util.normalize_embeddings(embeddings)
        
        return embeddings.cpu().numpy()
    
    def get_model_info(self) -> Dict:
        """Get model metadata."""
        return {
            'model_name': self.MODEL_NAME,
            'model_version': self.MODEL_VERSION,
            'device': self.device,
            'embedding_dim': 384,
            'max_seq_length': 512
        }
```

#### 3. Main Generator Class

```python
# services/ai-automation-service/src/nlevel_synergy/device_embedding_generator.py

from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DeviceEmbeddingGenerator:
    """
    Generates and manages device embeddings for n-level synergy detection.
    
    Story AI4.1: Device Embedding Generation
    """
    
    def __init__(
        self,
        db_session,
        data_api_client,
        capability_service,
        cache_days: int = 30
    ):
        self.db = db_session
        self.data_api = data_api_client
        self.capability_service = capability_service
        self.cache_days = cache_days
        
        # Initialize components
        self.descriptor_builder = DeviceDescriptorBuilder(capability_service)
        self.embedding_model = DeviceEmbeddingModel()
        
        # Load model
        self.embedding_model.load_model()
    
    async def generate_all_embeddings(self, force_refresh: bool = False) -> Dict:
        """
        Generate embeddings for all devices.
        
        Args:
            force_refresh: Regenerate even if cached
        
        Returns:
            Statistics dict
        """
        logger.info("🔧 Starting device embedding generation...")
        start_time = datetime.utcnow()
        
        stats = {
            'total_devices': 0,
            'generated': 0,
            'cached': 0,
            'errors': 0,
            'generation_time_ms': 0
        }
        
        try:
            # Step 1: Get all devices and entities
            devices = await self.data_api.fetch_devices()
            entities = await self.data_api.fetch_entities()
            stats['total_devices'] = len(entities)
            
            # Create entity lookup
            entity_map = {e['entity_id']: e for e in entities}
            
            # Step 2: Prepare device descriptors
            descriptors_to_generate = []
            entity_ids_to_generate = []
            
            for entity in entities:
                entity_id = entity['entity_id']
                
                # Check cache (skip if fresh and not force_refresh)
                if not force_refresh and self._is_cached(entity_id):
                    stats['cached'] += 1
                    continue
                
                # Get device capabilities
                device = next((d for d in devices if d.get('device_id') == entity.get('device_id')), None)
                capabilities = await self.capability_service.get_capabilities(entity.get('device_id')) if device else {}
                
                # Generate descriptor
                try:
                    descriptor = self.descriptor_builder.create_descriptor(device, entity, capabilities)
                    descriptors_to_generate.append(descriptor)
                    entity_ids_to_generate.append(entity_id)
                except Exception as e:
                    logger.error(f"Failed to create descriptor for {entity_id}: {e}")
                    stats['errors'] += 1
            
            # Step 3: Batch generate embeddings
            if descriptors_to_generate:
                logger.info(f"Generating embeddings for {len(descriptors_to_generate)} devices...")
                
                embeddings = self.embedding_model.encode(
                    descriptors_to_generate,
                    batch_size=32,
                    normalize=True
                )
                
                # Step 4: Store in database
                model_info = self.embedding_model.get_model_info()
                
                for entity_id, descriptor, embedding in zip(entity_ids_to_generate, descriptors_to_generate, embeddings):
                    try:
                        self._store_embedding(
                            entity_id=entity_id,
                            embedding=embedding,
                            descriptor=descriptor,
                            model_version=model_info['model_version']
                        )
                        stats['generated'] += 1
                    except Exception as e:
                        logger.error(f"Failed to store embedding for {entity_id}: {e}")
                        stats['errors'] += 1
            
            # Calculate stats
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            stats['generation_time_ms'] = int(duration)
            
            logger.info(
                f"✅ Embedding generation complete:\n"
                f"   Total devices: {stats['total_devices']}\n"
                f"   Generated: {stats['generated']}\n"
                f"   Cached: {stats['cached']}\n"
                f"   Errors: {stats['errors']}\n"
                f"   Time: {stats['generation_time_ms']}ms"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Embedding generation failed: {e}", exc_info=True)
            raise
    
    def _is_cached(self, entity_id: str) -> bool:
        """Check if embedding is cached and fresh."""
        result = self.db.execute(
            "SELECT last_updated, model_version FROM device_embeddings WHERE entity_id = ?",
            (entity_id,)
        ).fetchone()
        
        if not result:
            return False
        
        last_updated, model_version = result
        
        # Check version match
        current_version = self.embedding_model.get_model_info()['model_version']
        if model_version != current_version:
            return False
        
        # Check freshness
        age = datetime.utcnow() - datetime.fromisoformat(last_updated)
        return age < timedelta(days=self.cache_days)
    
    def _store_embedding(
        self,
        entity_id: str,
        embedding: np.ndarray,
        descriptor: str,
        model_version: str
    ):
        """Store embedding in database."""
        # Calculate L2 norm for validation
        embedding_norm = float(np.linalg.norm(embedding))
        
        # Serialize embedding
        embedding_bytes = embedding.tobytes()
        
        # Upsert
        self.db.execute(
            """
            INSERT INTO device_embeddings (entity_id, embedding, descriptor, model_version, embedding_norm, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                embedding = excluded.embedding,
                descriptor = excluded.descriptor,
                model_version = excluded.model_version,
                embedding_norm = excluded.embedding_norm,
                last_updated = excluded.last_updated
            """,
            (entity_id, embedding_bytes, descriptor, model_version, embedding_norm, datetime.utcnow())
        )
        self.db.commit()
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_device_embedding_generation.py

import pytest
import numpy as np
from nlevel_synergy.device_embedding_generator import DeviceEmbeddingGenerator
from nlevel_synergy.descriptor_builder import DeviceDescriptorBuilder
from nlevel_synergy.embedding_model import DeviceEmbeddingModel

class TestDescriptorBuilder:
    def test_motion_sensor_descriptor(self):
        """Test motion sensor descriptor generation."""
        builder = DeviceDescriptorBuilder(mock_capability_service)
        
        entity = {
            'entity_id': 'binary_sensor.kitchen_motion',
            'device_class': 'motion',
            'area_id': 'kitchen'
        }
        
        descriptor = builder.create_descriptor(device={}, entity=entity, capabilities={})
        
        assert "motion sensor" in descriptor
        assert "detects presence" in descriptor
        assert "kitchen area" in descriptor
    
    def test_light_descriptor_with_capabilities(self):
        """Test light descriptor with capabilities."""
        builder = DeviceDescriptorBuilder(mock_capability_service)
        
        entity = {
            'entity_id': 'light.living_room',
            'area_id': 'living_room'
        }
        
        capabilities = {
            'capabilities': {
                'brightness': {},
                'color_xy': {},
                'color_temp': {}
            }
        }
        
        descriptor = builder.create_descriptor(device={}, entity=entity, capabilities=capabilities)
        
        assert "dimmable light" in descriptor
        assert "RGB color control" in descriptor
        assert "living room area" in descriptor

class TestEmbeddingModel:
    def test_model_loading(self):
        """Test OpenVINO model loads successfully."""
        model = DeviceEmbeddingModel()
        model.load_model()
        
        assert model.model is not None
        assert model.tokenizer is not None
    
    def test_embedding_generation(self):
        """Test embedding generation."""
        model = DeviceEmbeddingModel()
        model.load_model()
        
        texts = [
            "motion sensor that detects presence in kitchen area",
            "dimmable light with RGB color in living room area"
        ]
        
        embeddings = model.encode(texts, normalize=True)
        
        assert embeddings.shape == (2, 384)
        assert np.allclose(np.linalg.norm(embeddings, axis=1), 1.0, atol=1e-5)  # Normalized
    
    def test_batch_processing(self):
        """Test batch processing with large dataset."""
        model = DeviceEmbeddingModel()
        model.load_model()
        
        texts = [f"device {i}" for i in range(100)]
        embeddings = model.encode(texts, batch_size=32)
        
        assert embeddings.shape == (100, 384)

class TestDeviceEmbeddingGenerator:
    @pytest.mark.asyncio
    async def test_generate_all_embeddings(self, mock_db, mock_data_api):
        """Test full embedding generation pipeline."""
        generator = DeviceEmbeddingGenerator(mock_db, mock_data_api, mock_capability_service)
        
        stats = await generator.generate_all_embeddings()
        
        assert stats['total_devices'] > 0
        assert stats['generated'] + stats['cached'] == stats['total_devices']
        assert stats['errors'] == 0
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, mock_db, mock_data_api):
        """Test embedding caching."""
        generator = DeviceEmbeddingGenerator(mock_db, mock_data_api, mock_capability_service)
        
        # First run
        stats1 = await generator.generate_all_embeddings()
        generated_first = stats1['generated']
        
        # Second run (should be cached)
        stats2 = await generator.generate_all_embeddings()
        
        assert stats2['cached'] >= generated_first
        assert stats2['generated'] == 0  # Nothing new to generate
```

### Integration Tests

```python
# tests/integration/test_embedding_integration.py

@pytest.mark.integration
class TestEmbeddingIntegration:
    @pytest.mark.asyncio
    async def test_end_to_end_generation(self, test_db, real_data_api):
        """Test complete embedding generation with real data."""
        generator = DeviceEmbeddingGenerator(test_db, real_data_api, capability_service)
        
        stats = await generator.generate_all_embeddings(force_refresh=True)
        
        # Verify database
        result = test_db.execute("SELECT COUNT(*) FROM device_embeddings").fetchone()
        assert result[0] == stats['generated']
        
        # Verify embedding quality
        embeddings = test_db.execute("SELECT embedding, embedding_norm FROM device_embeddings").fetchall()
        for emb_bytes, norm in embeddings:
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            assert emb.shape == (384,)
            assert 0.99 <= norm <= 1.01  # Normalized
```

---

## Dependencies

### Python Packages (New)

```txt
sentence-transformers==3.0.0
optimum[openvino,intel]==1.19.0
openvino==2024.0.0
transformers==4.40.0
torch==2.2.0
numpy==1.26.4
```

### System Requirements

- Python 3.11+
- 2GB free disk space (model cache)
- 1GB RAM (model loading)
- CPU with AVX2 support (OpenVINO)

---

## Rollout Plan

### Week 1: Setup & Model Integration
- Day 1-2: Create database schema, implement descriptor builder
- Day 3-4: Integrate OpenVINO model, test loading
- Day 5: Initial testing with sample devices

### Week 2: Implementation & Testing
- Day 1-3: Implement main generator class, caching logic
- Day 4-5: Unit tests, integration tests, performance benchmarks

### Week 3: Refinement & Documentation
- Day 1-2: Bug fixes, edge case handling
- Day 3-4: API endpoint, monitoring integration
- Day 5: Code review, documentation

---

## Success Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| **Model Size** | ≤25MB | ___ MB |
| **Inference Time** | <5ms/device | ___ ms |
| **Cache Hit Rate** | >90% (after initial run) | ___ % |
| **Embedding Quality** | Same-class similarity >0.7 | ___ |
| **Error Rate** | <1% | ___ % |

---

## Related Stories

- **Story AI4.2:** Multi-Hop Path Discovery (depends on this)
- **Story AI4.3:** Path Re-Ranking (uses embeddings)
- **Story AI2.1:** Device Capability Discovery (provides capability data)

---

**Document Version:** 1.0  
**Last Updated:** October 19, 2025  
**Created By:** BMad Master (AI Agent)  
**Story Status:** Proposed - Ready for Development

