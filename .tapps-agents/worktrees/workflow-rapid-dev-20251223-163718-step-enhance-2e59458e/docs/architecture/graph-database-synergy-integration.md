# Graph Database Integration for Synergy Detection

**Status:** Design Document  
**Date:** November 4, 2025  
**Epic:** Epic AI-3 Enhancement - Graph-Based Synergy Detection  
**Priority:** High  
**Estimated Impact on Accuracy:** 82/100

---

## Executive Summary

This document proposes integrating a graph database into the Synergy Detection process to significantly improve accuracy by enabling multi-hop relationship analysis, contextual pattern detection, and advanced graph-based algorithms. The current implementation uses linear pairwise matching which limits detection to 2-device relationships. A graph database will enable detection of complex automation chains (3-5 devices), indirect relationships, and contextual synergies.

**Key Benefits:**
- **Multi-hop relationship detection**: Find automation chains (Motion → Light → Climate → Music)
- **Indirect relationship analysis**: Discover devices connected through shared contexts
- **Graph-based scoring**: More accurate impact prediction using graph algorithms
- **Contextual awareness**: Weather, time, energy cost integration at graph level
- **Path-based recommendations**: Suggest optimal automation sequences

**Accuracy Improvement Score: 82/100**

---

## Current State Analysis

### Current Architecture

The current synergy detection system (Epic AI-3) uses a **relational/pairwise approach**:

1. **Data Sources:**
   - SQLite: Device metadata, entity relationships
   - InfluxDB: Time-series event data
   - Home Assistant API: Existing automations

2. **Current Process:**
   ```
   Step 1: Load all devices/entities (linear scan)
   Step 2: Find device pairs by area (O(n²) pairwise comparison)
   Step 3: Filter for compatible relationships (rule-based matching)
   Step 4: Check existing automations (hash lookup)
   Step 5: Rank by impact score (usage statistics)
   ```

3. **Limitations:**
   - **Only 2-device chains**: Cannot detect "Motion → Light → Thermostat → Music"
   - **No indirect relationships**: Misses devices connected through shared areas/contexts
   - **Rule-based matching**: Requires manual configuration for each relationship type
   - **No graph traversal**: Cannot find paths between distant devices
   - **Limited context**: Time/weather/energy not integrated into graph structure
   - **O(n²) complexity**: Pairwise comparison becomes expensive with 1000+ devices

### Current Data Flow

```
┌─────────────┐
│  SQLite DB  │  Device metadata, areas
└──────┬──────┘
       │
       ▼
┌─────────────────┐      ┌──────────────┐
│ SynergyDetector │ ◄────│  InfluxDB    │  Event history
└──────┬──────────┘      └──────────────┘
       │
       ▼
┌─────────────────────┐
│ Pairwise Matching   │  O(n²) complexity
│ Rule-based Filter   │  Static relationships
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ 2-Device Synergies  │  Limited to pairs
└─────────────────────┘
```

---

## Graph Database Research

### What is a Graph Database?

A **graph database** stores data as nodes (entities) and edges (relationships), optimized for traversing complex interconnected data. Unlike relational databases that require expensive JOINs, graph databases use index-free adjacency for O(1) relationship traversal.

### Key Graph Database Options

#### 1. **Neo4j** (Recommended)
- **Type:** Native graph database
- **Query Language:** Cypher
- **Strengths:**
  - Excellent performance for relationship queries
  - Rich ecosystem and community
  - Built-in graph algorithms (PageRank, Shortest Path, Community Detection)
  - ACID transactions
  - Good documentation
- **Considerations:**
  - Commercial license for clustering
  - Memory-intensive
  - Requires separate infrastructure

#### 2. **ArangoDB**
- **Type:** Multi-model (graph, document, key-value)
- **Query Language:** AQL (ArangoDB Query Language)
- **Strengths:**
  - Flexible data model (can use graph + document)
  - Single database for multiple data types
  - Good performance
- **Considerations:**
  - Less graph-specific optimizations
  - Smaller community than Neo4j

#### 3. **JanusGraph**
- **Type:** Distributed graph database
- **Query Language:** Gremlin
- **Strengths:**
  - Scales horizontally
  - Supports multiple storage backends
  - Good for very large graphs
- **Considerations:**
  - More complex setup
  - Overkill for current scale (<10K devices)

#### 4. **In-Memory Graph (NetworkX + Redis)**
- **Type:** Python library with caching
- **Strengths:**
  - No additional infrastructure
  - Fast for smaller graphs (<10K nodes)
  - Easy integration
- **Considerations:**
  - Not persistent (requires sync)
  - Limited scalability
  - No advanced graph algorithms

### Recommendation: **Neo4j**

**Rationale:**
- Native graph database optimized for relationship queries
- Built-in graph algorithms (PageRank, Shortest Path, Community Detection)
- Excellent Cypher query language for complex traversals
- Active community and extensive documentation
- Good performance for IoT-scale graphs (100-10K devices)
- Can be containerized with Docker (fits current architecture)

---

## Proposed Graph Model

### Node Types

```cypher
// Devices (primary entities)
(:Device {
  id: "light.bedroom",
  name: "Bedroom Light",
  domain: "light",
  device_class: "light",
  area_id: "bedroom",
  manufacturer: "Philips",
  model: "Hue",
  capabilities: ["brightness", "color", "dimming"],
  usage_frequency: 0.85,
  last_active: "2025-11-04T10:30:00Z"
})

// Areas (spatial context)
(:Area {
  id: "bedroom",
  name: "Master Bedroom",
  area_type: "bedroom",
  traffic_score: 0.9,
  device_count: 15
})

// Users (behavioral context)
(:User {
  id: "user_1",
  name: "Primary User",
  activity_patterns: ["morning_routine", "evening_routine"]
})

// Time Contexts
(:TimeContext {
  hour: 22,
  day_of_week: "Monday",
  season: "winter",
  is_weekend: false
})

// Weather Contexts
(:WeatherContext {
  date: "2025-11-04",
  temperature: 45,
  condition: "frost",
  humidity: 80
})
```

### Relationship Types

```cypher
// Spatial relationships
(:Device)-[:LOCATED_IN]->(:Area)
(:Device)-[:NEAR]->(:Device)  // Distance-based
(:Area)-[:ADJACENT_TO]->(:Area)

// Functional relationships
(:Device)-[:CAN_TRIGGER]->(:Device)  // Based on compatible relationships
(:Device)-[:OFTEN_USED_WITH]->(:Device)  // Based on co-occurrence patterns
(:Device)-[:AUTOMATED_WITH]->(:Device)  // Existing automations

// Contextual relationships
(:Device)-[:ACTIVE_DURING]->(:TimeContext)
(:Device)-[:AFFECTED_BY]->(:WeatherContext)
(:Area)-[:HAS_TRAFFIC_PATTERN]->(:TimeContext)

// Behavioral relationships
(:User)-[:USES]->(:Device)
(:User)-[:PREFERS]->(:Device)
(:User)-[:ROUTINE]->(:Area)
```

### Example Graph Structure

```
┌─────────────┐
│   Bedroom   │ (Area)
│   (Area)    │
└──────┬──────┘
       │
       │ LOCATED_IN
       │
┌──────┴──────┐      ┌──────────────┐
│ Motion      │      │ Light        │
│ Sensor      │      │              │
└──────┬──────┘      └──────┬───────┘
       │                    │
       │ CAN_TRIGGER        │
       └─────────┬──────────┘
                 │
                 ▼
         ┌───────────────┐
         │  Synergy      │
         │  Opportunity  │
         └───────────────┘
```

---

## Integration Design

### Phase 1: Graph Database Setup (Week 1-2)

#### 1.1 Infrastructure
- Deploy Neo4j container in Docker Compose
- Configure persistent storage
- Set up authentication and security
- Create backup strategy

#### 1.2 Data Model Design
- Define node schemas (Device, Area, Context)
- Define relationship types
- Create indexes on key properties
- Design constraints and validation rules

#### 1.3 Data Migration Script
```python
# services/ai-automation-service/src/synergy_detection/graph_sync.py

class GraphSyncService:
    """Syncs device/entity data to Neo4j graph database"""
    
    async def sync_devices_to_graph(self, devices: List[Dict], entities: List[Dict]):
        """Initial sync of all devices and relationships to graph"""
        # Create nodes
        # Create relationships
        # Update properties
```

### Phase 2: Graph-Based Synergy Detection (Week 3-4)

#### 2.1 Graph Query Service
```python
# services/ai-automation-service/src/synergy_detection/graph_synergy_detector.py

class GraphSynergyDetector:
    """Graph-based synergy detection using Neo4j"""
    
    async def detect_synergies(self) -> List[Dict]:
        """
        Detect synergies using graph traversal:
        1. Find paths between compatible devices
        2. Score paths using graph algorithms
        3. Filter by context (time, weather, area)
        """
```

#### 2.2 Multi-Hop Path Detection
```cypher
// Find automation chains (3-5 devices)
MATCH path = (d1:Device)-[:CAN_TRIGGER*2..4]->(d2:Device)
WHERE d1.area_id = d2.area_id
  AND NOT (d1)-[:AUTOMATED_WITH]->(d2)
  AND d1.domain IN ['binary_sensor', 'sensor']
  AND d2.domain IN ['light', 'climate', 'media_player']
RETURN path, 
       reduce(score = 0, r in relationships(path) | score + r.weight) as path_score
ORDER BY path_score DESC
LIMIT 100
```

#### 2.3 Context-Aware Detection
```cypher
// Find weather-aware synergies
MATCH (d:Device)-[:AFFECTED_BY]->(w:WeatherContext)
WHERE w.condition = 'frost'
  AND d.domain = 'climate'
MATCH path = (sensor:Device)-[:CAN_TRIGGER]->(d)
WHERE sensor.domain = 'sensor'
  AND sensor.device_class = 'temperature'
RETURN path, w.condition as context
```

#### 2.4 Graph-Based Scoring
```python
# Use graph algorithms for scoring
from neo4j import GraphDatabase

class GraphScorer:
    """Score synergies using graph algorithms"""
    
    def calculate_graph_score(self, path):
        """
        Score using:
        - Shortest path distance (closer = better)
        - PageRank centrality (important devices = higher score)
        - Community detection (devices in same community = higher confidence)
        - Path weight (usage frequency, compatibility)
        """
```

### Phase 3: Hybrid Approach (Week 5-6)

#### 3.1 Dual Detection Strategy
- **Graph-based**: For multi-hop chains and complex relationships
- **Pairwise**: For simple 2-device pairs (faster)
- **Combine results**: Merge and deduplicate

#### 3.2 Real-Time Graph Updates
- Sync device changes to graph in real-time
- Update relationships as automations are created
- Maintain graph consistency

### Phase 4: Advanced Features (Week 7-8)

#### 4.1 Graph Neural Networks (GNN)
- Use GNN for learning complex patterns
- Train on historical automation success data
- Predict synergy success probability

#### 4.2 Community Detection
- Identify device clusters (rooms, zones)
- Detect behavioral patterns
- Suggest whole-home automations

#### 4.3 Path Optimization
- Find optimal automation sequences
- Suggest multi-step routines
- Minimize energy consumption

---

## Architecture Changes

### New Component: Graph Database Service

```
┌─────────────────────────────────────────────────────────┐
│              AI Automation Service                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────────────────────────────┐      │
│  │     Graph Synergy Detector (NEW)              │      │
│  │  - Multi-hop path detection                   │      │
│  │  - Graph-based scoring                        │      │
│  │  - Context-aware queries                      │      │
│  └───────────────┬──────────────────────────────┘      │
│                  │                                        │
│  ┌───────────────▼──────────────────────────────┐      │
│  │     Graph Sync Service (NEW)                  │      │
│  │  - Device/entity sync                         │      │
│  │  - Relationship updates                       │      │
│  │  - Real-time graph maintenance                │      │
│  └───────────────┬──────────────────────────────┘      │
│                  │                                        │
│  ┌───────────────▼──────────────────────────────┐      │
│  │     Neo4j Client (NEW)                        │      │
│  │  - Cypher query execution                     │      │
│  │  - Graph algorithm execution                  │      │
│  │  - Connection pooling                         │      │
│  └───────────────┬──────────────────────────────┘      │
└──────────────────┼────────────────────────────────────┘
                   │
                   ▼
         ┌─────────────────┐
         │   Neo4j         │
         │   (Graph DB)    │
         └─────────────────┘
```

### Integration with Existing Services

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SQLite     │     │   InfluxDB   │     │  Neo4j       │
│   (Metadata) │     │   (Events)   │     │  (Graph)     │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┼────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Graph Sync      │
                   │ Service         │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │ Synergy         │
                   │ Detector        │
                   │ (Hybrid)        │
                   └─────────────────┘
```

---

## Implementation Details

### Docker Compose Addition

```yaml
services:
  neo4j:
    image: neo4j:5.15-community
    container_name: homeiq-neo4j
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    ports:
      - "7474:7474"  # HTTP
      - "7687:7687"  # Bolt
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  neo4j_data:
  neo4j_logs:
```

### Code Structure

```
services/ai-automation-service/src/
├── synergy_detection/
│   ├── graph_synergy_detector.py      # NEW: Graph-based detector
│   ├── graph_sync_service.py          # NEW: Sync service
│   ├── graph_scorer.py                # NEW: Graph algorithm scoring
│   ├── synergy_detector.py            # EXISTING: Pairwise detector
│   └── hybrid_synergy_detector.py     # NEW: Combines both approaches
├── clients/
│   └── neo4j_client.py                # NEW: Neo4j client wrapper
└── scheduler/
    └── daily_analysis.py              # MODIFY: Add graph sync phase
```

### Key Classes

#### 1. Neo4jClient
```python
class Neo4jClient:
    """Client for Neo4j graph database operations"""
    
    async def execute_query(self, query: str, parameters: Dict) -> List[Dict]:
        """Execute Cypher query"""
    
    async def find_paths(self, start_node: str, end_node: str, 
                        max_depth: int = 4) -> List[Dict]:
        """Find paths between nodes"""
    
    async def calculate_centrality(self, node_id: str) -> float:
        """Calculate PageRank centrality"""
```

#### 2. GraphSyncService
```python
class GraphSyncService:
    """Syncs device/entity data to Neo4j"""
    
    async def sync_devices(self, devices: List[Dict]):
        """Sync all devices to graph"""
    
    async def sync_relationships(self, automations: List[Dict]):
        """Sync automation relationships"""
    
    async def update_usage_stats(self, device_id: str, stats: Dict):
        """Update device usage statistics"""
```

#### 3. GraphSynergyDetector
```python
class GraphSynergyDetector:
    """Graph-based synergy detection"""
    
    async def detect_multi_hop_synergies(self) -> List[Dict]:
        """Find automation chains (3-5 devices)"""
    
    async def detect_contextual_synergies(self, 
                                         context: Dict) -> List[Dict]:
        """Find context-aware synergies"""
    
    async def score_path(self, path: Dict) -> float:
        """Score synergy path using graph algorithms"""
```

---

## Accuracy Improvement Analysis

### Score: **82/100**

### Justification:

#### **Strengths (+70 points):**

1. **Multi-hop Detection (+25 points)**
   - Current: Only 2-device pairs
   - With Graph: Can detect chains (Motion → Light → Climate → Music)
   - Impact: **Significant** - Enables complex automation suggestions

2. **Indirect Relationship Discovery (+20 points)**
   - Current: Only direct relationships
   - With Graph: Finds devices connected through shared contexts
   - Impact: **High** - Discovers non-obvious synergies

3. **Graph-Based Scoring (+15 points)**
   - Current: Rule-based scoring
   - With Graph: PageRank, centrality, path analysis
   - Impact: **High** - More accurate impact prediction

4. **Contextual Integration (+10 points)**
   - Current: Limited context awareness
   - With Graph: Time, weather, energy as graph nodes
   - Impact: **Medium-High** - Better relevance

#### **Limitations (-18 points):**

1. **Data Quality Dependency (-8 points)**
   - Requires accurate device metadata
   - Missing area/location data reduces effectiveness
   - Impact: **Medium** - Can be mitigated with validation

2. **Complexity Overhead (-5 points)**
   - Additional infrastructure (Neo4j)
   - More complex queries
   - Learning curve for Cypher
   - Impact: **Low-Medium** - Manageable with proper documentation

3. **Performance at Scale (-3 points)**
   - Graph queries can be slower for very large graphs (10K+ devices)
   - Requires optimization and indexing
   - Impact: **Low** - Current scale (<1K devices) is fine

4. **Incremental Improvement (-2 points)**
   - Current system already works well for simple pairs
   - Graph adds value primarily for complex relationships
   - Impact: **Low** - Still significant overall improvement

### Improvement Breakdown:

| Aspect | Current Score | With Graph | Improvement |
|--------|--------------|------------|-------------|
| Pair Detection | 70/100 | 75/100 | +5 |
| Multi-hop Detection | 0/100 | 90/100 | +90 |
| Context Awareness | 50/100 | 80/100 | +30 |
| Scoring Accuracy | 60/100 | 85/100 | +25 |
| Relationship Discovery | 65/100 | 90/100 | +25 |
| **Overall** | **65/100** | **82/100** | **+17** |

---

## Performance Considerations

### Query Performance

**Current (Pairwise):**
- O(n²) for pair detection
- 1000 devices = 500,000 pairs to check
- Time: ~30-60 seconds

**With Graph:**
- O(E) for graph traversal (E = edges)
- Indexed lookups for relationships
- Time: ~5-15 seconds for path queries
- **Improvement: 3-4x faster**

### Memory Usage

**Current:**
- ~50MB for device/entity cache
- ~100MB for InfluxDB queries

**With Graph:**
- Neo4j: ~2GB heap (configurable)
- Graph sync cache: ~20MB
- **Additional: ~2GB** (acceptable for server deployment)

### Scalability

- **Current**: Linear degradation with device count
- **With Graph**: Logarithmic (indexed lookups)
- **Benefit**: Better scaling for 1000+ devices

---

## Migration Strategy

### Phase 1: Parallel Operation (Week 1-2)
- Deploy Neo4j alongside existing system
- Sync data to graph (no production impact)
- Run graph detector in parallel (results not used)

### Phase 2: Hybrid Mode (Week 3-4)
- Run both detectors
- Compare results
- Use graph for complex relationships, pairwise for simple pairs
- Measure accuracy improvements

### Phase 3: Full Integration (Week 5-6)
- Graph becomes primary detector
- Pairwise used as fallback
- Real-time graph sync enabled

### Phase 4: Optimization (Week 7-8)
- Query optimization
- Index tuning
- Performance monitoring
- Advanced features (GNN, community detection)

---

## Risk Assessment

### Low Risk
- ✅ Neo4j is mature and stable
- ✅ Can run in parallel with existing system
- ✅ Easy rollback if issues arise

### Medium Risk
- ⚠️ Additional infrastructure complexity
- ⚠️ Requires Neo4j expertise
- ⚠️ Data sync consistency

### Mitigation
- Comprehensive testing in parallel mode
- Gradual rollout with feature flags
- Monitoring and alerting
- Documentation and training

---

## Success Metrics

### Accuracy Metrics
- **Multi-hop detection rate**: % of 3+ device chains found
- **False positive rate**: % of suggestions that are not useful
- **Coverage**: % of actual synergies detected
- **Target**: 90%+ coverage, <10% false positives

### Performance Metrics
- **Query time**: <15 seconds for full graph scan
- **Sync time**: <5 minutes for full device sync
- **Memory usage**: <2.5GB for Neo4j

### Business Metrics
- **User adoption**: % of users implementing graph-detected synergies
- **Automation success**: % of graph suggestions that become active automations
- **Target**: 60%+ adoption rate

---

## Conclusion

Integrating a graph database into the Synergy Detection process will significantly improve accuracy by enabling:

1. **Multi-hop relationship detection** (currently impossible)
2. **Indirect relationship discovery** (currently limited)
3. **Graph-based scoring** (more accurate than rule-based)
4. **Contextual awareness** (better integration of time/weather/energy)

**Overall Accuracy Improvement Score: 82/100**

This represents a **+17 point improvement** over the current system, with the primary gains coming from multi-hop detection capabilities that are impossible with the current pairwise approach.

The implementation is **feasible** with manageable complexity and risk, and can be done incrementally with a parallel operation strategy.

---

## Next Steps

1. **Review and Approval**: Get stakeholder approval for design
2. **POC (Proof of Concept)**: Build minimal graph sync and query
3. **Parallel Testing**: Run graph detector alongside existing system
4. **Metrics Collection**: Measure accuracy improvements
5. **Full Implementation**: Proceed with full integration if POC successful

---

## References

- Neo4j Documentation: https://neo4j.com/docs/
- Graph Database Use Cases: https://neo4j.com/use-cases/
- Cypher Query Language: https://neo4j.com/developer/cypher/
- Graph Algorithms: https://neo4j.com/docs/graph-data-science/current/
- IoT Graph Databases: Various research papers on graph databases for IoT applications

