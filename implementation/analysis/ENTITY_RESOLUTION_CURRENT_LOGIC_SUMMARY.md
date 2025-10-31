# Entity Resolution: Current Logic, Models, and Device Attributes

**Date:** October 29, 2025  
**Purpose:** Comprehensive summary of entity resolution logic, ML models, and available device attributes

---

## 1. Current Logic Flow

### High-Level Pipeline

```
User Query: "Turn on sleepy light" (or "Turn on Office light 1")
    ↓
map_query_to_entities(query, entities)
    ↓
0. Alias Check (fast indexed lookup) → If found, return immediately
    ↓
1. Extract domain ("light") and location ("office") from query
    ↓
2. Multi-Level Blocking:
   - Domain filter: 10,000 → ~500 entities (90% reduction)
   - Location filter: ~500 → ~50 entities (additional 90% reduction)
    ↓
3. Fetch available entities from Data API (with filters applied)
    ↓
4. Full Chain Matching (if enabled)
    ├─ Entity Enrichment (device metadata + name_by_user, suggested_area, integration)
    ├─ Embedding-Based Semantic Matching (35% weight)
    ├─ Exact Name Matching (30% weight)
    ├─ Fuzzy String Matching (15% weight) - handles typos, abbreviations
    ├─ Numbered Device Matching (15% weight)
    ├─ Location Matching (5% weight) - with heavy mismatch penalty
    └─ Confidence Calculation
    ↓
Result: { "sleepy light": "light.bedroom_1" } or { "Office light 1": "light.hue_go_1" }
```

---

## 2. Full Model Chain Architecture

### Models Used

#### 2.1 Embedding Model
- **Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Purpose**: Semantic similarity matching between query and entity names
- **Usage**: Converts query and candidate entity strings to embeddings, calculates cosine similarity
- **Weight**: 35% of final score (reduced from 40% to accommodate fuzzy matching)
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
        # Priority: name_by_user > name
        enriched['device_name'] = device_metadata.get('name_by_user') or device_metadata.get('name')
        enriched['name_by_user'] = device_metadata.get('name_by_user')
        enriched['device_manufacturer'] = device_metadata.get('manufacturer')
        enriched['device_model'] = device_metadata.get('model')
        enriched['device_area_id'] = device_metadata.get('area_id')
        enriched['suggested_area'] = device_metadata.get('suggested_area')
        enriched['integration'] = device_metadata.get('integration')
        # Fallback to suggested_area if area_id missing
        if not enriched.get('area_id') and device_metadata.get('suggested_area'):
            enriched['area_id'] = device_metadata.get('suggested_area')
    
    # 2. Fetch entity metadata for friendly_name
    entity_metadata = await get_entity_metadata(entity_id)
    enriched['friendly_name'] = entity_metadata.get('friendly_name') or entity_metadata.get('name')
    
    return enriched
```

**Enrichment Priority (Updated):**
1. `friendly_name` - Highest priority (user-facing entity name)
2. `name_by_user` - User-customized device name (high priority)
3. `device_name` - Device-level name (falls back to `name` if `name_by_user` not set)
4. `entity_id` - Fallback (technical identifier)

**New Fields Added:**
- `name_by_user`: User-customized device name from HA device registry
- `suggested_area`: HA-suggested area (used as fallback if `area_id` missing)
- `integration`: Integration platform name (e.g., "hue", "zigbee2mqtt")

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
| **Embedding Similarity** | 35% | Semantic similarity from sentence-transformers | 0.0 - 1.0 |
| **Exact Name Matches** | 30% | Exact match on friendly_name, name_by_user, or device_name | 0.0 or 1.0 |
| **Fuzzy String Matching** | 15% | Typo/abbreviation handling via rapidfuzz | 0.0 - 1.0 |
| **Numbered Device Matching** | 15% | Exact number match (word boundaries) | 0.0 - 0.5 |
| **Location Matching** | 5% | Location/area match (+0.025) or mismatch penalty (×0.05) | Variable |

### 5.2 Scoring Logic

```python
score = 0.0

# Signal 1: Embedding similarity (35%)
if embedding_score:
    score += embedding_score * 0.35

# Signal 2: Exact name matches (30%) - Priority: friendly_name > name_by_user > device_name
if query_lower == friendly_name:
    score += 1.0 * 0.3  # Full points
elif query_lower == name_by_user:
    score += 1.0 * 0.3  # Full points
elif query_lower == device_name:
    score += 1.0 * 0.3  # Full points

# Signal 2.5: Fuzzy string matching (15%) - Only if exact match failed
if not exact_match:
    fuzzy_score = max_fuzzy_score  # Best fuzzy match across all names
    if fuzzy_score > 0.6:  # Threshold for meaningful match
        score += fuzzy_score * 0.15

# Signal 3: Numbered device matching (15%)
if exact_number_match:
    score += 0.5 * 0.15  # Full points for exact number
    # Base term match boost (proportionally reduced)
    score += base_match * 0.10
elif is_group_entity and numbered_query:
    score *= 0.1  # Heavy penalty for group entities

# Signal 4: Location matching (5%)
if location_match:
    score += 0.5 * 0.05  # +0.025 boost
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

### 5.3.1 Fuzzy String Matching (NEW)

**Purpose:** Handle typos, abbreviations, and partial matches

**Library:** `rapidfuzz` (fast C++ implementation)
- **Method**: `token_sort_ratio` - Order-independent matching
- **Weight**: 15% of final score
- **Threshold**: Only applied if score > 0.6 (meaningful match)
- **Activation**: Only used when exact match fails (doesn't penalize exact matches)

**How it works:**
```python
from rapidfuzz import fuzz

# Order-independent matching (handles "living room light" vs "light living room")
similarity = fuzz.token_sort_ratio(query.lower(), candidate.lower()) / 100.0
```

**Examples:**
- ✅ "office lite" → "office light" (typo handling)
- ✅ "LR light" → "Living Room Light" (abbreviation)
- ✅ "kitchen" → "Kitchen Light" (partial match)

### 5.4 Location Matching

**Location Sources (checked in order):**
1. `device_area_id` (device-level area)
2. `area_id` (entity-level area)
3. `suggested_area` (HA-suggested area, fallback)
4. `friendly_name` (may contain location)
5. `device_name` (may contain location)
6. `entity_id` (fallback)

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

## 6. Multi-Level Blocking/Indexing (NEW)

### 6.1 Domain Extraction

**Purpose:** Reduce candidate entities before ML matching (90-95% reduction)

**Method:** `_extract_domain_from_query(query)` extracts device domain from query keywords.

**Supported Domains:**
| Domain | Keywords |
|--------|----------|
| `light` | light, lamp, bulb, led, brightness, dim, bright, illuminate |
| `switch` | switch, outlet, plug, power |
| `climate` | temperature, thermostat, heat, cool, ac, hvac, climate, temp |
| `cover` | blind, shade, curtain, garage door, door, cover, open, close |
| `sensor` | sensor, motion sensor, temperature sensor |
| `binary_sensor` | motion, door sensor, window sensor, door, window |
| `fan` | fan, ventilation |
| `media_player` | tv, television, speaker, music, audio |
| `lock` | lock, unlock, door lock |

**Example:**
```python
query = "Turn on the light"
domain = _extract_domain_from_query(query)  # Returns: "light"
```

### 6.2 Blocking Pipeline

**Two-Level Filtering:**

1. **Level 1: Domain Filter**
   - Filters entities by domain before fetching from Data API
   - Reduces: 10,000 entities → ~500 entities (90% reduction)
   - API call: `fetch_entities(domain="light")`

2. **Level 2: Location Filter** (if location found)
   - Further filters by area_id/location
   - Reduces: ~500 entities → ~50 entities (additional 90% reduction)
   - API call: `fetch_entities(domain="light", area_id="office")`

**Performance Benefits:**
- Faster API queries (filtering at database level)
- Reduced embedding computation (fewer candidates)
- Improved matching accuracy (less noise)
- Total reduction: 90-95% (from 10,000 to 50-100 entities)

**Performance Logging:**
```
🔍 BLOCKING: Domain filter (light) → 487 entities (23.4ms)
🔍 BLOCKING: Location filter (office) → 52 entities (18.7ms)
🔍 BLOCKING SUMMARY: 52 entities after blocking (~95% reduction), total blocking time: 42.1ms
```

---

## 7. User-Defined Aliases (NEW)

### 7.1 Overview

**Purpose:** Allow users to create personalized nicknames for entities

**Example:** User creates alias "sleepy light" → `light.bedroom_1`

### 7.2 Database Schema

**Table:** `entity_aliases`
- `id`: Primary key (auto-increment)
- `entity_id`: Entity being aliased
- `alias`: User-defined nickname (lowercase, trimmed)
- `user_id`: User identifier (default: "anonymous")
- `created_at`, `updated_at`: Timestamps

**Constraints:**
- Unique constraint: `(alias, user_id)` - one alias per user
- Indexes: `(alias, user_id)` for fast lookup, `entity_id`, `user_id`

### 7.3 Integration

**Priority:** Alias checking happens FIRST (before full chain matching)
- Fast indexed lookup (<10ms)
- High confidence match (bypasses ML matching)
- Multi-user support (isolated by user_id)

**Flow:**
```python
# Check aliases first
alias_entity_id = await _check_aliases(query_term, user_id)
if alias_entity_id:
    return alias_entity_id  # Fast path - skip ML matching

# Otherwise, proceed with full chain matching
```

### 7.4 API Endpoints

**Create Alias:**
```bash
POST /api/v1/ask-ai/aliases
{
  "entity_id": "light.bedroom_1",
  "alias": "sleepy light",
  "user_id": "user123"
}
```

**Delete Alias:**
```bash
DELETE /api/v1/ask-ai/aliases/sleepy%20light?user_id=user123
```

**List Aliases:**
```bash
GET /api/v1/ask-ai/aliases?user_id=user123
# Returns: { "light.bedroom_1": ["sleepy light", "bedroom main"] }
```

---

## 8. Location Extraction

### 8.1 Pattern Matching

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

**Extraction Method:** `_extract_location_from_query(query)`:
1. Try regex patterns first
2. Fallback: Extract word before device keywords (`light`, `lamp`, `door`, etc.)

**Example:**
- "office light" → "office"
- "living room lamp" → "living_room"
- "bedroom light 1" → "bedroom"

---

## 9. Device Lookup Process

### 9.1 Initial Entity Fetch

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

### 9.2 Batch Enrichment

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

### 9.3 Candidate String Building

For embedding matching, builds searchable strings from enriched entities:

```python
candidate_strings = []
for entity in enriched_entities:
    search_terms = []
    
    # Priority order: friendly_name > name_by_user > device_name
    if friendly_name:
        search_terms.append(friendly_name)  # "Office Front Left"
    if name_by_user:
        search_terms.append(name_by_user)   # User-customized name
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

## 10. Confidence Scoring

### 10.1 Confidence Calculation

```python
confidence = min(best_score, 1.0) if best_match else 0.0
```

**Confidence Thresholds:**
- **High confidence**: ≥ 0.5 (likely correct match)
- **Medium confidence**: 0.3 - 0.5 (possible match, may need verification)
- **Low confidence**: < 0.3 (uncertain, may be incorrect)

### 10.2 Numbered Query Stricter Threshold

For numbered device queries, stricter threshold:

```python
if is_numbered_query and confidence < 0.3:
    # Don't map - let system cleanup page address missing entities
    return None
```

**Rationale**: Numbered queries must be more precise (e.g., "Office light 1" vs "Office light 3")

---

## 11. Example: Complete Resolution Flow

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

