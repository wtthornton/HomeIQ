# RAG UI Metrics Proposal

## Metrics Currently Implemented ✅
1. **Total Events Received** - Total events in period (from Statistics API)
2. **Throughput (Events/Minute)** - Current event processing rate
3. **Connection Attempts** - WebSocket connection attempts count
4. **Last Data Refresh** - Timestamp of last statistics refresh
5. **Error Rate** - Percentage of errors
6. **Response Time** - Average latency in milliseconds
7. **Data Source** - Source of statistics data
8. **Period** - Time period for statistics (1h, 6h, 24h, etc.)

## Additional Available Metrics (Not Yet Implemented) 📊

### Data Volume Metrics
- [ ] **Unique Entities Count** - Number of distinct entities in period
- [ ] **Events per Entity** - Average events per unique entity
- [ ] **Events per Hour** - Hourly event rate
- [ ] **Events per Day** - Daily event rate (calculated)

### Event Type Breakdown (Type of Data)
- [ ] **Event Types Distribution** - Breakdown by event type (state_changed, device_online, etc.)
  - Display as list or chart (top 5-10 event types)
  - Show count and percentage for each type
  - Example: `state_changed: 1,234 (45%)`, `device_online: 567 (21%)`

### Data Read/Query Metrics (How many times data was read)
- [ ] **Query Count** - Number of times data was queried/read (if available)
- [ ] **API Request Count** - Number of API requests to data endpoints
- [ ] **Cache Hit/Miss Ratio** - If caching is implemented
- [ ] **Data Access Frequency** - How often data is accessed

### Refresh/Update Metrics (Last time data was refreshed)
- [ ] **Statistics Last Updated** - When statistics were last calculated ✅ (already have)
- [ ] **Data Source Last Updated** - When underlying data was last updated
- [ ] **Cache Last Refreshed** - If caching is used
- [ ] **Refresh Interval** - How often data is refreshed
- [ ] **Time Since Last Update** - Human-readable time ago (e.g., "5 minutes ago") ✅ (already have)

### Service Breakdown Metrics
- [ ] **Per-Service Statistics** - Breakdown by service (websocket-ingestion, etc.)
  - Events per service
  - Error rate per service
  - Response time per service

### Trend Metrics
- [ ] **Trend Indicators** - Show if metrics are increasing/decreasing
- [ ] **Historical Comparison** - Compare current period to previous period
- [ ] **Peak Events** - Peak events per minute in period
- [ ] **Minimum Events** - Minimum events per minute in period

### Storage/Data Metrics
- [ ] **Database Size** - Total size of stored data (if available)
- [ ] **Data Retention Period** - How long data is kept
- [ ] **Storage Utilization** - Percentage of storage used
- [ ] **Write Operations** - Number of write operations to storage

### Performance Metrics
- [ ] **P95/P99 Latency** - 95th/99th percentile latency (if available)
- [ ] **Queue Size** - Current queue size (if available)
- [ ] **Processing Lag** - Delay between event occurrence and processing
- [ ] **Batch Size** - Average batch size for processing

## Recommended Metrics to Add 🎯

Based on your original request, I recommend adding:

### High Priority (From Your Request)
1. **Event Types Breakdown** - "type of data" ✅ REQUIRED
2. **Unique Entities Count** - Better "amount of data" metric
3. **Data Read/Query Count** - "how many times data was read" (if available)
4. **More detailed refresh info** - Already partially implemented

### Medium Priority (Useful Context)
5. **Events per Entity** - Average events per entity
6. **Service Breakdown** - Per-service statistics
7. **Trend Indicators** - Up/down arrows for metrics

### Low Priority (Nice to Have)
8. **Peak/Minimum Events** - Range of event rates
9. **Historical Comparison** - Compare to previous period

---

## Questions for Approval

1. **Event Types Display Format**: How should event types be displayed?
   - [ ] List format (top 5-10 with counts/percentages)
   - [ ] Chart/visualization (bar chart, pie chart)
   - [ ] Collapsible section (expand to see all)

2. **Data Read Count**: Where should this come from?
   - [ ] Data-API query endpoint metrics (if available)
   - [ ] WebSocket event read count (events processed)
   - [ ] API request count to statistics endpoints
   - [ ] Other source?

3. **Display Location**: Where should these metrics appear?
   - [ ] In the RAG Status Card (main card view)
   - [ ] Only in RAG Details Modal (expanded view)
   - [ ] Both locations (summary in card, details in modal)

4. **Metrics to Include**: Please check which metrics you want:
   - [ ] Event Types Breakdown (REQUIRED - "type of data")
   - [ ] Unique Entities Count
   - [ ] Events per Entity
   - [ ] Data Read/Query Count
   - [ ] Service Breakdown
   - [ ] Trend Indicators
   - [ ] Historical Comparison
   - [ ] Other: ___________
