# Performance Optimization Guide

**Epic 39, Story 39.15: Performance Optimization**

## Overview

This guide documents performance optimization strategies, caching patterns, and best practices for the AI Automation Service.

## Caching Strategies

### Correlation Cache
- **Location**: `shared/correlation_cache.py`
- **Type**: Two-tier (in-memory LRU + SQLite)
- **Usage**: Caches correlation computations
- **TTL**: 1 hour (configurable)
- **Target Hit Rate**: >80%

```python
from shared.correlation_cache import CorrelationCache

cache = CorrelationCache(cache_db_path="/path/to/cache.db")
correlation = cache.get(entity1_id, entity2_id, ttl_seconds=3600)
if correlation is None:
    correlation = compute_correlation(...)
    cache.set(entity1_id, entity2_id, correlation, ttl_seconds=3600)
```

### Cache Manager (New)
- **Location**: `src/utils/cache_manager.py`
- **Usage**: Centralized cache management
- **Features**: Unified interface for multiple cache types

```python
from ..utils.cache_manager import get_cache_manager

cache_manager = get_cache_manager()
result = cache_manager.get_from_cache("my_key", cache_type="memory")
if result is None:
    result = expensive_operation()
    cache_manager.set_in_cache("my_key", result, ttl=3600)
```

### Decorator Caching
- **Usage**: Automatic function result caching

```python
from ..utils.cache_manager import cached

@cached(ttl=3600, cache_key_prefix="query")
async def expensive_query(param):
    # Your code here
    return result
```

## Database Query Optimization

### Connection Pooling
- **Location**: `shared/database_pool.py`
- **Usage**: Shared database connection pooling
- **Pool Size**: 10 connections per service (max 20)
- **Max Overflow**: 5 connections

```python
from shared.database_pool import create_shared_db_engine

engine = create_shared_db_engine(
    database_url="sqlite+aiosqlite:////app/data/db.sqlite",
    pool_size=10,
    max_overflow=5
)
```

### Batch Operations
- **Location**: `src/utils/query_optimizer.py`
- **Usage**: Batch database operations to reduce round trips

```python
from ..utils.query_optimizer import QueryOptimizer

# Instead of:
# for id in ids:
#     record = await db.get(Model, id)  # N queries

# Use:
records = await QueryOptimizer.batch_fetch(
    db, 
    lambda ids: select(Model).where(Model.id.in_(ids)),
    ids,
    batch_size=100
)
```

### Eager Loading
- **Usage**: Load relationships in single query

```python
from ..utils.query_optimizer import QueryOptimizer

query = select(ParentModel)
query = await QueryOptimizer.eager_load_relationships(
    db,
    query,
    ["children", "metadata"]
)
```

## Token Usage Optimization

### Token Budget Enforcement
- **Location**: `src/utils/token_budget.py`
- **Usage**: Enforce token limits on prompt components

```python
from ..utils.token_budget import enforce_token_budget

token_budget = {
    'max_entity_context_tokens': 10_000,
    'max_enrichment_context_tokens': 2_000,
    'max_conversation_history_tokens': 1_000,
    'max_total_tokens': 30_000
}

optimized_prompt = enforce_token_budget(prompt_dict, token_budget, model="gpt-4o")
```

### Best Practices
1. **Truncate Long Contexts**: Use token budget enforcement
2. **Cache LLM Responses**: Cache responses for identical queries
3. **Batch Similar Queries**: Combine similar queries to reduce API calls
4. **Use Smaller Models**: Use GPT-4o-mini for non-critical paths

## Performance Monitoring

### Performance Monitor
- **Location**: `src/utils/performance.py`
- **Usage**: Track operation times and cache statistics

```python
from ..utils.performance import get_performance_monitor, track_performance

# Using decorator
@track_performance("database_query")
async def my_query():
    ...

# Using context manager
monitor = get_performance_monitor()
async with monitor.track("operation_name"):
    # Your code here
    pass

# Get statistics
stats = monitor.get_stats()
print(f"Avg query time: {stats['operations']['database_query']['avg_time']}")
print(f"Cache hit rate: {stats['cache_stats']['correlation']['hit_rate']}%")
```

## Performance Targets

### Query Latency
- **Query Service**: <500ms P95
- **Database Queries**: <50ms P95
- **Health Checks**: <10ms

### Cache Hit Rates
- **Correlation Cache**: >80%
- **Entity Context Cache**: >70%
- **General Memory Cache**: >60%

### Token Usage
- **Average per Query**: <5,000 tokens
- **Max per Query**: <30,000 tokens
- **Budget Enforcement**: Always enabled

## Hot Path Optimization

### Query Processing Endpoint
1. **Entity Extraction**: Use cached entity lookups
2. **Pattern/Synergy Context**: Batch queries, use cache
3. **LLM Calls**: Cache responses where possible
4. **Database Queries**: Batch operations, eager load relationships

### Daily Analysis Scheduler
1. **Batch Processing**: Process patterns in batches
2. **Parallel Operations**: Use asyncio.gather for independent operations
3. **Incremental Updates**: Only process new data
4. **Cache Warmup**: Pre-load frequently accessed data

## Optimization Checklist

- ✅ Use connection pooling (configured)
- ✅ Implement caching for expensive operations
- ✅ Batch database operations
- ✅ Enforce token budgets
- ✅ Monitor performance metrics
- ✅ Optimize hot paths
- ✅ Use async/await consistently
- ✅ Profile and measure improvements

## Monitoring & Metrics

### Performance Metrics Endpoint
Create endpoint to expose performance statistics:

```python
@router.get("/performance/stats")
async def get_performance_stats():
    monitor = get_performance_monitor()
    stats = monitor.get_stats()
    
    cache_manager = get_cache_manager()
    cache_stats = cache_manager.get_cache_stats()
    
    return {
        "operations": stats["operations"],
        "cache_stats": stats["cache_stats"],
        "cache_manager": cache_stats
    }
```

## Next Steps

1. Add performance metrics endpoint
2. Implement cache warming for startup
3. Profile hot paths with real data
4. Optimize based on profiling results
5. Set up performance monitoring dashboard

