# Entity Resolution: Current Logic, Models, and Device Attributes

**Date:** October 29, 2025  
**Purpose:** Comprehensive summary of entity resolution logic, ML models, and available device attributes

---

## 1. Current Logic Flow

### High-Level Pipeline

```
User Query: "Turn on Office light 1"
    ↓
map_query_to_entities(query, entities)
    ↓
1. Extract location context ("office")
    ↓
2. Fetch available entities from Data API
    ↓
3. Filter by location (area_id) if available
    ↓
4. Full Chain Matching (if enabled)
    ├─ Entity Enrichment (device metadata)
    ├─ Embedding-Based Semantic Matching
    ├─ Hybrid Scoring
    └─ Confidence Calculation
    ↓
Result: { "Office light 1": "light.hue_go_1" }
```

---

## 2. Full Model Chain Architecture

### Models Used

#### 2.1 Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Purpose**: Semantic similarity matching between query and entity names
- **Usage**: Converts query and candidate entity strings to embeddings, calculates cosine similarity
- **Weight**: 40% of final score
- **Lazy Loading**: Loaded on first use, cached in `self._embedding_model`

**How it works:**
```python
# Generate embeddings for query and all candidates
query_embedding = embedding_model.encode([query_term])
candidate_embeddings = embedding_model.encode(candidate_strings)

# Calculate cosine similarity for each candidate
similarity = dot_product / (norm_query * norm_candidate)
embedding_score = similarity  # 0.0 to 1.0
```

#### 2.2 NER Pipeline (Optional)
- **Model**: `dslim/bert-base-NER`
- **Purpose**: Named Entity Recognition for complex queries (not actively used yet)
- **Status**: Loaded but not integrated into scoring pipeline
- **Lazy Loading**: Loaded on first use, cached in `self._ner_pipeline`

---

## 3. Entity Enrichment Process

### 3.1 Data Sources

Entities are enriched with metadata from two sources:

#### Source 1: Entity Registry (Data API)
- **Endpoint**: `GET /api/entities/{entity_id}`
- **Method**: `data_api_client.get_entity_metadata(entity_id)`
- **Returns**:
  - `friendly_name`: User-friendly display name
  - `entity_id`: Entity identifier
  - `domain`: Entity type (light, sensor, etc.)
  - `area_id`: Room/area assignment (entity level)
  - `device_id`: Associated device ID

#### Source 2: Device Registry (Data API)
- **Endpoint**: `GET /api/devices/{device_id}`
- **Method**: `data_api_client.get_device_metadata(device_id)`
- **Returns**:
  - `name`: Device name (user-set or manufacturer name)
  - `manufacturer`: Device manufacturer (e.g., "Philips", "Hue")
  - `model`: Device model number/name
  - `area_id`: Room/area assignment (device level)
  - `integration`: Integration platform (e.g., "hue", "zigbee2mqtt")

### 3.2 Enrichment Process

```python
async def _enrich_entity_with_metadata(entity):
    enriched = entity.copy()
    
    # 1. Fetch device metadata if device_id exists
    if device_id:
        device_metadata = await get_device_metadata(device_id)
        enriched['device_name'] = device_metadata.get('name')
        enriched['device_manufacturer'] = device_metadata.get('manufacturer')
        enriched['device_model'] = device_metadata.get('model')
        enriched['device_area_id'] = device_metadata.get('area_id')
    
    # 2. Fetch entity metadata for friendly_name
    entity_metadata = await get_entity_metadata(entity_id)
    enriched['friendly_name'] = entity_metadata.get('friendly_name') or entity_metadata.get('name')
    
    return enriched
```

**Enrichment Priority:**
1. `friendly_name` - Highest priority for matching (user-facing name)
2. `device_name` - Second priority (device-level name)
3. `entity_id` - Fallback (technical identifier)

---

## 4. Available Device Attributes

### 4.1 Entity Attributes (from Data API)

| Attribute | Source | Type | Example | Description |
|-----------|--------|------|---------|-------------|
| `entity_id` | Entity Registry | string | `"light.hue_go_1"` | Unique entity identifier |
| `device_id` | Entity Registry | string | `"a1b2c3d4e5f6"` | Parent device ID |
| `domain` | Entity Registry | string | `"light"` | Entity type/domain |
| `platform` | Entity Registry | string | `"hue"` | Integration platform |
| `unique_id` | Entity Registry | string | `"00:17:88:01:02:ab:cd:ef"` | Platform-specific unique ID |
| `area_id` | Entity Registry | string/null | `"office"` | Room/area at entity level |
| `friendly_name` | Entity Metadata | string | `"Office Front Left"` | User-facing display name |
| `disabled` | Entity Registry | boolean | `false` | Whether entity is disabled |

### 4.2 Device Attributes (from Data API)

| Attribute | Source | Type | Example | Description |
|-----------|--------|------|---------|-------------|
| `device_id` | Device Registry | string | `"a1b2c3d4e5f6"` | Unique device identifier |
| `name` | Device Registry | string | `"Office Front Left Light"` | Device name (user-set or manufacturer) |
| `manufacturer` | Device Registry | string | `"Philips"` | Device manufacturer |
| `model` | Device Registry | string | `"LCA001"` | Device model number/name |
| `area_id` | Device Registry | string/null | `"office"` | Room/area at device level |
| `integration` | Device Registry | string | `"hue"` | Integration platform |
| `sw_version` | Device Registry | string/null | `"1.50.2_r30933"` | Software/firmware version |
| `last_seen` | Device Registry | datetime/null | `"2025-10-18T14:30:00Z"` | Last communication timestamp |
| `entity_count` | Device Registry | integer | `4` | Number of entities for this device |

### 4.3 Enriched Entity Attributes (After Processing)

After enrichment, entities have these additional attributes:

| Attribute | Source | Type | Description |
|-----------|--------|------|-------------|
| `device_name` | Device Metadata | string | Device name from device registry |
| `device_manufacturer` | Device Metadata | string | Manufacturer name |
| `device_model` | Device Metadata | string | Model number/name |
| `device_area_id` | Device Metadata | string/null | Device-level area_id (separate from entity area_id) |
| `friendly_name` | Entity Metadata | string | User-friendly display name |

**Key Insight:** Both `area_id` (entity level) and `device_area_id` (device level) are checked for location matching!

---

## 5. Hybrid Scoring System

### 5.1 Scoring Signals

The full chain uses a hybrid scoring system combining multiple signals:

| Signal | Weight | Description | Range |
|--------|--------|-------------|-------|
| **Embedding Similarity** | 40% | Semantic similarity from sentence-transformers | 0.0 - 1.0 |
| **Exact Name Matches** | 30% | Exact match on friendly_name or device_name | 0.0 or 1.0 |
| **Numbered Device Matching** | 20% | Exact number match (word boundaries) | 0.0 - 0.5 |
| **Location Matching** | 10% | Location/area match (+0.05) or mismatch penalty (×0.05) | Variable |

### 5.2 Scoring Logic

```python
score = 0.0

# Signal 1: Embedding similarity (40%)
if embedding_score:
    score += embedding_score * 0.4

# Signal 2: Exact name matches (30%)
if query_lower == friendly_name:
    score += 1.0 * 0.3  # Full points
elif query_lower == device_name:
    score += 1.0 * 0.3  # Full points

# Signal 3: Numbered device matching (20%)
if exact_number_match:
    score += 0.5 * 0.2  # Full points for exact number
    # Base term match boost
    score += base_match * 0.15
elif is_group_entity and numbered_query:
    score *= 0.1  # Heavy penalty for group entities

# Signal 4: Location matching (10%)
if location_match:
    score += 0.5 * 0.1  # +0.05 boost
elif location_mismatch:
    score *= 0.05  # Heavy penalty (reduce to 5%)

final_score = min(score, 1.0)  # Cap at 1.0
```

### 5.3 Numbered Device Matching

**Exact Number Matching:**
- Uses regex with word boundaries: `r'(^|[._\s])' + number + r'([._\s]|$)'`
- Ensures "2" matches "light_2" but NOT "light_20" or "light_12"
- Checks: `friendly_name`, `device_name`, `entity_id`

**Examples:**
- ✅ "Office light 1" → number "1" → matches `light.hue_go_1` (has "_1")
- ❌ "Office light 1" → number "1" → doesn't match `light.hue_go_10` (has "_10", not "_1")

### 5.4 Location Matching

**Location Sources (checked in order):**
1. `device_area_id` (device-level area)
2. Gelir `area_id` (entity-level area)
3. `friendly_name` (may contain location)
4. `device_name` (may contain location)
5. `entity_id` (fallback)

**Matching Logic:**
- **Match**: Location found → +0.05 boost
- **Mismatch**: Location specified but not found → ×0.05 penalty (very heavy)

**Example:**
```python
query: "Office light 3"
location_context: "office"

Entity: light.hue_color_downlight_3
  - device_area_id: "master_bedroom"  ❌ No match
  - entity area_id: None
  - friendly_name: "Master Bedroom Light 3"
  
Result: Heavy penalty (×0.05) because "office" not found
```

### 5.5 Group Entity Detection

**Heuristics to detect group entities:**
1. **No device_id**: Group/zone entities don't have physical devices
2. **Simple entity_id**: Matches pattern like `light.office`, `light.living_room`
3. **No numbers**: Group entities typically don't have numbers in entity_id
4. **Friendly name matches entity_id**: Often indicates a group

**Penalty:**
- When numbered device is requested: score × 0.1 (reduce to 10%)
- Prevents "Office light 1" from matching `light.office` (group)

---

## 6. Location Extraction

### 6.1 Pattern Matching

Extracts location from query using regex patterns:

**Common Locations:**
- `living room` / `livingroom`
- `bedroom` / `bed room`
- `kitchen`
- `office`
- `garage`
- `bathroom`
- `dining room`
- `family room`
- `basement`
- `attic`
- `patio` / `deck` / `porch`

Write `_extract_location_from_query(query)`:
1. Try regex patterns first
2. Fallback: Extract word before device keywords (`light`, `lamp`, `door`, etc.)

**Example:**
- "office light" → "office"
- "living room lamp" → "living_room"
- "bedroom light 1" → "bedroom"

---

## 7. Device Lookup Process

### 7.1 Initial Entity Fetch

```python
available_entities = await data_api_client.fetch_entities(
    domain="light",  # Optional filter
    area_id="office",  # Optional filter
    limit=1000
)
```

**Returns**: List of entity dictionaries with:
- `entity_id`
- `device_id`
- `domain`
- `platform`
- `area_id`
- `disabled`

### 7.2 Batch Enrichment

```python
# Enrich all candidate entities in parallel
enriched_entities = await asyncio.gather(*[
    _enrich_entity_with_metadata(entity)
    for entity in available_entities
])
```

**Parallel Processing:**
- Fetches device metadata for all entities with `device_id`
- Caches device metadata in `self._device_metadata_cache` to avoid duplicate fetches
- Fetches entity metadata for `friendly_name`

### 7.3 Candidate String Building

For embedding matching, builds searchable strings from enriched entities:

```python
candidate_strings = []
for entity in enriched_entities:
    search_terms = []
    
    # Priority order
    if friendly_name:
        search_terms.append(friendly_name)  # "Office Front Left"
    if device_name:
        search_terms.append(device_name)    # "Office Front Left Light"
    
    # Entity ID parts
    entity_name = entity_id.split('.', 1)[1]
    search_terms.append(entity_name)        # "hue_go_1"
    
    candidate_string = ' '.join(search_terms)
    candidate_strings.append(candidate_string)
```

**Example Candidate String:**
```
"Office Front Left Office Front Left Light hue_go_1"
```

---

## 8. Confidence Scoring

### 8.1 Confidence Calculation

```python
confidence = min(best_score, 1.0) if best_match else 0.0
```

**Confidence Thresholds:**
- **High confidence**: ≥ 0.5 (likely correct match)
- **Medium confidence**: 0.3 - 0.5 (possible match, may need verification)
- **Low confidence**: < 0.3 (uncertain, may be incorrect)

### 8.2 Numbered Query Stricter Threshold

For numbered device queries, stricter threshold:

```python
if is_numbered_query and confidence < 0.3:
    # Don't map - let system cleanup page address missing entities
    return None
```

**Rationale**: Numbered queries must be more precise (e.g., "Office light 1" vs "Office light 3")

---

## 9. Example: Complete Resolution Flow

### Input
```
Query: "Turn on Office light 1"
Entities: ["Office light 1"]
```

### Step 1: Location Extraction
```
location_context = "office"
```

### Step 2: Fetch Entities
```
available_entities = [
    {
        "entity_id": "light.hue_go_1",
        "device_id": "device_001",
        "area_id": "office",
        "domain": "light"
    },
    {
        "entity_id": "light.garage_2",
        "device_id": "device_002",
        "area_id": "garage",
        "domain": "light"
    },
    ...
]
```

### Step 3: Filter by Location
```
location_filtered = [
    {
        "entity_id": "light.hue_ **(1/2)**",
        "device_id": "device_001",
        "area_id": "office",
        "domain": "light"
    }
]
```

### Step 4: Enrich Entities
```
enriched = {
    "entity_id": "light.hue_go_1",
    "device_id": "device_001",
    "area_id": "office",
    "device_name": "Office Front Left",
    "device_manufacturer": "Philips",
    "device_model": "Hue Go",
    "device_area_id": "office",
    "friendly_name": "Office Front Left"
}
```

### Step 5: Embedding Matching
```
query: "Office light 1"
candidate: "Office Front Left Office Front Left Light hue_go_1"
embedding_score: 0.75
```

### Step 6: Hybrid Scoring
```
score = 0.0
score += 0.75 * 0.4  # Embedding: 0.30
score += 0.0 * 0.3   # Exact match: 0.00 (no exact match)
score += 0.5 * 0.2   # Numbered match: 0.10 (exact "1" found)
score += 0.15        # Base term match: 0.15
score += 0.5 * 0.1   # Location match: 0.05 (office matches)
total_score = 0.60
confidence = 0.60
```

### Step 7: Result
```
{
    "Office light 1": "light.hue_go_1"
}
confidence: 0.60
```

---

## 10. Key Takeaways

### Strengths
1. **Multi-source matching**: Combines semantic (embeddings), exact (name), numerical (numbers), and spatial (location) signals
2. **Prioritizes user-facing names**: `friendly_name` and `device_name` over technical `entity_id`
3. **Location-aware**: Uses both entity and device level `area_id` for accurate room matching
4. **Exact number matching**: Word boundaries prevent partial number matches
5. **Group entity detection**: Prevents numbered queries from matching group entities

### Limitations
1. **Entity ID numbers may not match user expectations**: HA entity IDs use integration-specific numbering (e.g., `_1_6`, `_2_2`), not user numbering ("light 1", "light 2")
2. **Location extraction relies on patterns**: May miss uncommon room names
3. **Embedding model can be slow**: First-time loading and embedding computation
4. **No fuzzy matching for typos**: Exact number matching may fail if user says "light 1" but device is "light 01"

### Recommendations
1. **Prioritize device_name and friendly_name** over entity_id numbers (as per HA naming research)
2. **Use location as primary filter** when available (most reliable attribute)
3. **Consider allowing user feedback** to improve matching confidence
4. **Cache embeddings** for better performance

---

## 11. Data API Endpoints Reference

### Entities
```
GET /api/entities
  - Filter: domain, platform, device_id, area_id
  - Returns: List of entities with entity_id, device_id, domain, platform, area_id

GET /api/entities/{entity_id}
  - Returns: Entity metadata including friendly_name
```

### Devices
```
GET /api/devices
  - Filter: manufacturer, model, area_id, platform
  - Returns: List of devices with device_id, name, manufacturer, model, area_id

GET /api/devices/{device_id}
  - Returns: Device metadata including name, manufacturer, model, area_id
```

### Response Format
```json
{
  "entity_id": "light.hue_go_1",
  "device_id": "device_001",
  "domain": "light",
  "platform": "hue",
  "area_id": "office",
  "friendly_name": "Office Front Left",
  "disabled": false
}
```

