# Performance Optimization Checklist

**Last Updated:** October 24, 2025  
**Purpose:** Comprehensive checklist for performance optimization in HomeIQ

## Before Making Changes

- [ ] **Profile first** - Use metrics_collector.py to identify bottlenecks
- [ ] **Measure baseline** - Record current performance metrics
- [ ] **Identify hot paths** - Focus on frequently-called code (health checks, device queries)
- [ ] **Check existing patterns** - Review performance patterns guide and existing code
- [ ] **Consider trade-offs** - Complexity vs performance gain

## Database Optimization

### SQLite Optimization
- [ ] **WAL mode enabled** - Check `PRAGMA journal_mode=WAL`
- [ ] **Indexes on filter columns** - Add indexes for WHERE clauses
- [ ] **Batch inserts used** - Use bulk operations, not loops
- [ ] **Query limits enforced** - All queries have LIMIT clause
- [ ] **Connection pooling configured** - Reuse database connections
- [ ] **Async operations used** - No blocking database calls
- [ ] **Eager loading used** - Avoid N+1 queries with selectinload
- [ ] **Context managers used** - Proper session management

### InfluxDB Optimization
- [ ] **Batch writes configured** - 1000 points per batch, 5s timeout
- [ ] **Appropriate tags vs fields** - Tags for filtering, fields for values
- [ ] **Retention policies set** - Configure data lifecycle
- [ ] **Query optimization** - Specific time range + field selection
- [ ] **Connection pooling** - Reuse InfluxDB client
- [ ] **No individual writes** - Always use batch writer

## API Optimization

### FastAPI Best Practices
- [ ] **Async/await throughout** - No blocking operations in async functions
- [ ] **Background tasks for slow ops** - Use FastAPI BackgroundTasks
- [ ] **Response validation** - Pydantic models for input/output
- [ ] **Correlation IDs added** - Track requests across services
- [ ] **Timeouts configured** - All external calls have timeout
- [ ] **Connection pooling** - Reuse HTTP client sessions
- [ ] **Error handling** - Proper exception handling
- [ ] **Request limits** - Prevent abuse with query limits

### Performance Monitoring
- [ ] **Metrics collection added** - Use metrics_collector.py
- [ ] **Timing decorators** - Track response times
- [ ] **Counter metrics** - Track request counts
- [ ] **Gauge metrics** - Track queue sizes, memory usage
- [ ] **Error tracking** - Monitor error rates

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

### Resource Limits
- [ ] **Memory limits** - 256MB-512MB per service
- [ ] **CPU limits** - Prevent one service from consuming all CPU
- [ ] **Health check intervals** - 30s interval, 10s timeout
- [ ] **Startup probes** - Grace period for slow-starting services

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

### Performance Testing
- [ ] **Load testing** - 100 concurrent users, 30 minutes
- [ ] **Stress testing** - 200 concurrent users, 10 minutes
- [ ] **Endurance testing** - 24-hour continuous operation
- [ ] **Performance regression tests** - Automated in CI/CD
- [ ] **Memory leak detection** - Monitor memory usage over time

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

### Response Time Targets
- [ ] **Health checks <10ms** - Verify all health endpoints
- [ ] **Device queries <10ms** - SQLite performance
- [ ] **Event queries <100ms** - InfluxDB performance
- [ ] **Dashboard load <2s** - Frontend performance
- [ ] **Webhook delivery <1s** - Automation performance

### Throughput Targets
- [ ] **Event processing 500/sec** - Sustained throughput
- [ ] **API requests 50/sec** - API performance
- [ ] **Batch writes 60/min** - Database performance
- [ ] **Concurrent users 50** - Dashboard capacity

### Resource Targets
- [ ] **CPU <20% normal** - Resource efficiency
- [ ] **Memory <60% of limit** - Memory efficiency
- [ ] **Disk usage <70%** - Storage efficiency
- [ ] **InfluxDB memory <400MB** - Database efficiency

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
