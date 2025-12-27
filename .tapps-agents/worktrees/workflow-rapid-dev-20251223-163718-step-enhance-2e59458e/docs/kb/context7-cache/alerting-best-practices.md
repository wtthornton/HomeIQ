# Alerting Best Practices - Context7 KB Research

**Source**: Prometheus Alerting Documentation  
**Date**: October 12, 2025  
**Epic**: 17.4 - Critical Alerting System  

## Key Insights from Prometheus (Industry Standard)

### 1. Alert Severity Levels
Based on Prometheus standards:
- **CRITICAL** (page): Requires immediate attention, wakes people up
- **WARNING**: Needs attention but not urgent
- **INFO**: Informational, for awareness

### 2. Grouping & Deduplication
- Group alerts by similar characteristics (alertname, service, cluster)
- Use `group_wait` (30s default): Wait to batch initial alerts
- Use `group_interval` (5m default): Check for new alerts in group
- Use `repeat_interval` (4h default): Resend interval

### 3. Inhibition Rules
- Suppress WARNING alerts if CRITICAL alert is firing
- Prevents alert fatigue
- Matches on common labels (alertname, service)

### 4. Alert Structure
```yaml
alert: AlertName
expr: metric > threshold
for: 10m              # Duration before firing
labels:
  severity: critical
annotations:
  summary: "Brief description"
  description: "Detailed info with {{ $value }}"
```

### 5. Cooldown Periods
- Prevent alert spam
- Typical: 5-15 minutes for warnings
- Shorter for critical: 1-3 minutes

### 6. Best Practices for Our Implementation

#### ✅ What We Should Do:
1. **Threshold-based rules**: Simple, predictable
2. **Severity levels**: INFO, WARNING, CRITICAL
3. **Cooldown periods**: 5 min for warnings, 3 min for critical
4. **Alert grouping**: By service and alert name
5. **Status tracking**: ACTIVE, ACKNOWLEDGED, RESOLVED
6. **Alert history**: Keep for analysis (limit: 100)
7. **Auto-resolve**: Clear old resolved alerts (24h+)

#### ❌ What We Should Avoid (Non-Goals):
1. **External integrations**: No PagerDuty, Slack, email
2. **Complex routing**: Single in-app display
3. **Escalation policies**: Simple acknowledgment only
4. **Alert clustering**: Keep it simple
5. **Template language**: Use Python f-strings

## Application to Story 17.4

### Our Lightweight Approach:
```python
# Simple threshold checks
if cpu_percent > 80:
    alert_manager.trigger_alert(
        name="high_cpu",
        severity=WARNING,
        message=f"CPU usage at {cpu_percent}%"
    )

# Cooldown prevents spam
# Alert stored in memory
# Displayed in dashboard
# No external notifications
```

### Integration Points:
1. **Health Checks** (Story 17.2): Trigger alerts on critical status
2. **Metrics** (Story 17.3): Monitor thresholds (CPU, memory, response time)
3. **Dashboard**: Display active alerts prominently
4. **API**: Simple REST endpoints for alert management

### Success Criteria:
- ✅ Threshold-based alert generation
- ✅ In-memory alert storage
- ✅ Dashboard display
- ✅ Acknowledgment/resolution
- ✅ No over-engineering (no external systems)

---

**Conclusion**: Our `alert_manager.py` implementation follows Prometheus best practices while staying lightweight and avoiding over-engineering. Perfect for Story 17.4!

