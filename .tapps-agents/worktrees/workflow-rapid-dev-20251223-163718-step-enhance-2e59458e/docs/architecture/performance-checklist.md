# Performance Optimization Checklist

**Last Updated:** January 2025  
**Purpose:** Comprehensive checklist for performance optimization in HomeIQ  
**Target Platform:** Home Assistant single-home deployment on NUC (Next Unit of Computing)  
**Context7 Patterns:** Integrated throughout

## Before Making Changes

- [ ] **Profile first** - Use metrics_collector.py to identify bottlenecks
- [ ] **Measure baseline** - Record current performance metrics
- [ ] **Identify hot paths** - Focus on frequently-called code (health checks, device queries)
- [ ] **Check existing patterns** - Review performance patterns guide and existing code
- [ ] **Consider trade-offs** - Complexity vs performance gain
- [ ] **NUC resource awareness** - Consider CPU/memory constraints (2-4 cores, 4-16GB RAM)
- [ ] **Single-home context** - Optimize for 1 home, not multi-tenant
- [ ] **Context7 compliance** - Follow Context7 patterns (lifespan, Pydantic settings, telemetry)

## Database Optimization

### SQLite Optimization (NUC-Optimized)
- [ ] **WAL mode enabled** - Check `PRAGMA journal_mode=WAL`
- [ ] **Indexes on filter columns** - Add indexes for WHERE clauses
- [ ] **Batch inserts used** - Use bulk operations, not loops
- [ ] **Query limits enforced** - All queries have LIMIT clause
- [ ] **Connection pooling configured** - Reuse database connections
- [ ] **Async operations used** - No blocking database calls
- [ ] **Eager loading used** - Avoid N+1 queries with selectinload
- [ ] **Context managers used** - Proper session management
- [ ] **NUC cache size** - `PRAGMA cache_size=-32000` (32MB for NUC)
- [ ] **Memory temp store** - `PRAGMA temp_store=MEMORY` (use RAM)

### InfluxDB Optimization (NUC-Optimized)
- [ ] **Batch writes configured** - 500 points per batch, 3-5s timeout (NUC)
- [ ] **Appropriate tags vs fields** - Tags for filtering, fields for values
- [ ] **Retention policies set** - Configure data lifecycle (single-home)
- [ ] **Query optimization** - Specific time range + field selection
- [ ] **Connection pooling** - Reuse InfluxDB client
- [ ] **No individual writes** - Always use batch writer
- [ ] **Memory limit** - 256MB max (vs 400MB for larger systems)
- [ ] **Single-home tuning** - Reduced batch sizes for lower event volume

## API Optimization

### FastAPI Best Practices (Context7 Patterns)
- [ ] **Lifespan context managers** - Use `@asynccontextmanager` for startup/shutdown
- [ ] **Pydantic settings pattern** - Type-validated configuration with `@lru_cache`
- [ ] **Global state with setter** - Context7 pattern for telemetry and service injection
- [ ] **Async/await throughout** - No blocking operations in async functions
- [ ] **Background tasks for slow ops** - Use FastAPI BackgroundTasks
- [ ] **Response validation** - Pydantic models for input/output
- [ ] **Correlation IDs added** - Track requests across services (Context7 structured logging)
- [ ] **Timeouts configured** - All external calls have timeout
- [ ] **Connection pooling** - Reuse HTTP client sessions
- [ ] **Error handling** - Proper exception handling with HTTPException
- [ ] **Request limits** - Prevent abuse with query limits

### Performance Monitoring (Context7 Telemetry)
- [ ] **Structured logging** - JSON format with correlation IDs
- [ ] **Metrics collection added** - Use metrics_collector.py
- [ ] **Timing decorators** - Track response times
- [ ] **Counter metrics** - Track request counts
- [ ] **Gauge metrics** - Track queue sizes, memory usage
- [ ] **Error tracking** - Monitor error rates
- [ ] **NUC resource monitoring** - CPU, memory, disk usage per service
- [ ] **Context7 telemetry** - Global state pattern for service stats
- [ ] **Correlation ID tracking** - Request tracing across services
- [ ] **Single-home metrics** - Event rate, WebSocket connection status

## Caching Optimization

### Cache Strategy
- [ ] **Cache expensive operations** - Database queries, API calls, computations
- [ ] **Appropriate TTLs set** - Match data freshness requirements
- [ ] **Hit rates monitored** - Track and optimize cache effectiveness
- [ ] **LRU eviction configured** - Prevent unbounded memory growth
- [ ] **Cache invalidation strategy** - Handle stale data correctly
- [ ] **Memory limits set** - Prevent cache from consuming too much memory

### Cache Implementation
- [ ] **TTL-based cache** - Weather data (5min), sports data (15s-1h)
- [ ] **Differentiated TTLs** - Different TTLs for different data types
- [ ] **Direct database cache** - SQLite for devices/entities
- [ ] **HTTP client pooling** - Implicit caching via connection reuse
- [ ] **Cache statistics** - Monitor hit rates and evictions

## Frontend Optimization

### Build Optimization
- [ ] **Code splitting configured** - Vendor chunk separated
- [ ] **Lazy loading used** - Load components on demand
- [ ] **Memoization applied** - useMemo for expensive calculations
- [ ] **API calls consolidated** - Reduce request count
- [ ] **State management optimized** - Selective Zustand subscriptions
- [ ] **Bundle size optimized** - <500KB total bundle size

### React Performance
- [ ] **useMemo for expensive calculations** - Prevent unnecessary recalculations
- [ ] **useCallback for event handlers** - Prevent unnecessary re-renders
- [ ] **Selective subscriptions** - Subscribe to specific state slices
- [ ] **Batch updates** - Single state update instead of multiple
- [ ] **Virtualization for long lists** - Only render visible items
- [ ] **Debouncing for search** - Prevent excessive API calls

## Event Processing Optimization

### Batch Processing
- [ ] **Batch size configured** - 100 events per batch
- [ ] **Batch timeout set** - 5 seconds maximum wait
- [ ] **Flush triggers implemented** - Size-based and time-based
- [ ] **Memory management** - Bounded queues with maxlen
- [ ] **Error handling** - Retry logic with exponential backoff

### Memory Management
- [ ] **Bounded queues** - Use deque with maxlen
- [ ] **Weak references for caches** - Auto-removes unused entries
- [ ] **Periodic cleanup** - Clean up expired cache entries
- [ ] **Memory monitoring** - Track memory usage
- [ ] **Garbage collection** - Trigger GC when needed

## Docker & Resource Management

### Container Optimization
- [ ] **Multi-stage builds** - Minimize production image size
- [ ] **Resource limits set** - Memory and CPU limits in docker-compose.yml
- [ ] **Health checks configured** - All services have health endpoints
- [ ] **Log rotation enabled** - Prevent disk filling up
- [ ] **Alpine base images** - Use lightweight base images

### Resource Limits (NUC-Optimized)
- [ ] **Memory limits** - 128MB-256MB per service (NUC constraint)
- [ ] **CPU limits** - Prevent one service from consuming all CPU
- [ ] **Health check intervals** - 30s interval, 10s timeout
- [ ] **Startup probes** - Grace period for slow-starting services
- [ ] **Total system memory** - <1GB for HomeIQ services (reserve for HA)
- [ ] **InfluxDB memory** - 256MB max (vs 400MB for larger systems)
- [ ] **SQLite cache** - 32MB max (vs 64MB for larger systems)
- [ ] **CPU per service** - <30% normal, <60% peak (NUC constraint)

## Monitoring & Alerting

### Performance Monitoring
- [ ] **Metrics collection** - Use metrics_collector.py
- [ ] **Performance monitoring enabled** - Track response times, throughput
- [ ] **Alerts configured** - Notify on performance degradation
- [ ] **Logs structured** - JSON format with correlation IDs
- [ ] **Dashboards updated** - Visualize performance metrics

### Alert Thresholds
- [ ] **Response time alerts** - P95 > target × 2
- [ ] **Error rate alerts** - >5% for 5 minutes
- [ ] **Memory usage alerts** - >80% of limit for 10 minutes
- [ ] **CPU usage alerts** - >80% for 15 minutes
- [ ] **Queue size alerts** - >1000 events for 5 minutes

## Testing & Validation

### Performance Testing (Single-Home NUC)
- [ ] **Load testing** - 1-3 concurrent users, 30 minutes (single-home)
- [ ] **Stress testing** - 5 concurrent users, 10 minutes (single-home)
- [ ] **Event volume testing** - 200-500 events/sec sustained
- [ ] **Endurance testing** - 24-hour continuous operation
- [ ] **Performance regression tests** - Automated in CI/CD
- [ ] **Memory leak detection** - Monitor memory usage over time
- [ ] **NUC resource testing** - Verify CPU/memory constraints
- [ ] **Single-home scenarios** - Typical home automation event patterns

### Validation
- [ ] **Baseline comparison** - Compare before/after metrics
- [ ] **Load test verification** - Verify performance under realistic load
- [ ] **Memory profiling** - Check for memory leaks
- [ ] **Log review** - Ensure no new errors or warnings
- [ ] **Production monitoring** - Watch metrics for regressions

## After Making Changes

### Verification
- [ ] **Benchmark performance** - Compare before/after metrics
- [ ] **Load test** - Verify performance under realistic load
- [ ] **Memory profiling** - Check for memory leaks
- [ ] **Review logs** - Ensure no new errors or warnings
- [ ] **Update documentation** - Document performance characteristics
- [ ] **Monitor production** - Watch metrics for regressions

### Documentation
- [ ] **Performance characteristics documented** - Update service docs
- [ ] **Optimization history recorded** - Track changes and impact
- [ ] **Monitoring setup documented** - Metrics and alerting config
- [ ] **Troubleshooting guide updated** - Common issues and solutions

## Performance Targets Verification

### Response Time Targets (NUC Single-Home)
- [ ] **Health checks <10ms** - Verify all health endpoints
- [ ] **Device queries <10ms** - SQLite performance
- [ ] **Event queries <100ms** - InfluxDB performance
- [ ] **Dashboard load <2s** - Frontend performance
- [ ] **Webhook delivery <1s** - Automation performance
- [ ] **WebSocket events <50ms** - Real-time event processing
- [ ] **Context7 telemetry** - <1ms overhead per request

### Throughput Targets (Single-Home NUC)
- [ ] **Event processing 200/sec** - Sustained throughput (single-home)
- [ ] **API requests 20/sec** - API performance (single user)
- [ ] **Batch writes 30/min** - Database performance (single-home)
- [ ] **Concurrent users 1-3** - Dashboard capacity (single home)
- [ ] **Home Assistant events 150/sec** - Typical single-home rate

### Resource Targets (NUC-Optimized)
- [ ] **CPU <30% normal** - Resource efficiency (NUC constraint)
- [ ] **Memory <60% of limit** - Memory efficiency
- [ ] **Total system memory <70%** - NUC constraint
- [ ] **Disk usage <70%** - Storage efficiency
- [ ] **InfluxDB memory <256MB** - Database efficiency (NUC)
- [ ] **SQLite cache <32MB** - Memory efficiency (NUC)

## Quick Reference

### Critical Performance Patterns
1. **Async Everything** - Use async/await throughout
2. **Batch Operations** - Batch database writes and API calls
3. **Connection Pooling** - Reuse HTTP and database connections
4. **Intelligent Caching** - Cache with appropriate TTLs
5. **Resource Limits** - Set memory and CPU limits
6. **Performance Monitoring** - Track metrics and alert on issues

### Performance Tools
- **Profiling:** `python -m cProfile`, `python -m memory_profiler`
- **Load Testing:** `ab`, `locust`, `wrk`
- **Monitoring:** `docker stats`, `metrics_collector.py`
- **Database:** `PRAGMA` commands, query analysis
- **Frontend:** React DevTools, Bundle Analyzer

### Emergency Performance Issues
1. **High CPU:** Check for blocking operations, optimize hot paths
2. **High Memory:** Check for memory leaks, reduce cache sizes
3. **Slow Queries:** Add indexes, optimize query patterns
4. **Slow API:** Check connection pooling, add caching
5. **Slow Frontend:** Check bundle size, optimize re-renders
