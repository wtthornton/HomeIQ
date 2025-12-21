# Energy Consumption Tracking

**Last Updated**: December 2025  
**Status**: Current best practices for 2025 energy monitoring systems

## Overview

Energy consumption tracking is the foundation of effective energy management. It involves collecting, storing, and analyzing power usage data from devices and systems throughout the home.

## Core Principles

### 1. Granular Data Collection

**Principle**: Collect data at the right granularity for your use case.

**Why it matters**: Too granular (per-second) creates storage overhead. Too coarse (daily totals) limits analysis capabilities. Balance is key.

**Best Practices (2025)**:
- **Device-level tracking**: Monitor individual high-consumption devices (HVAC, water heater, EV charger)
- **Circuit-level tracking**: Track whole circuits for aggregate analysis
- **Room-level aggregation**: Sum device usage by room/area for spatial insights
- **Time-series storage**: Use time-series databases (InfluxDB) for efficient storage and querying

**Data Collection Frequency**:
- **Real-time devices**: 1-5 minute intervals (smart plugs, energy monitors)
- **High-frequency devices**: 15-60 minute intervals (whole-home monitors)
- **Aggregated metrics**: Hourly or daily summaries for long-term trends

### 2. Data Quality and Accuracy

**Principle**: Accurate data is essential for reliable energy management decisions.

**Why it matters**: Poor data quality leads to incorrect optimization decisions, wasted energy, and user distrust.

**Best Practices (2025)**:
- **Calibration**: Calibrate energy monitors against known loads
- **Validation**: Cross-check device-reported usage against utility meter readings
- **Error handling**: Detect and handle sensor failures, communication errors, missing data
- **Data normalization**: Normalize units (W, kW, kWh) for consistent analysis
- **Timestamp accuracy**: Ensure accurate timestamps, handle timezone issues

**Common Issues**:
- Sensor drift over time
- Communication failures causing data gaps
- Device firmware bugs reporting incorrect values
- Unit conversion errors (W vs kW vs kWh)

### 3. Time-Series Storage Patterns

**Principle**: Use time-series databases optimized for energy data patterns.

**Why it matters**: Relational databases struggle with time-series queries. Specialized databases provide better performance and compression.

**Best Practices (2025)**:
- **InfluxDB**: Recommended for energy data (high write throughput, efficient compression)
- **Retention policies**: Define data retention (raw: 30-90 days, aggregated: years)
- **Tagging strategy**: Use tags for device_id, room, device_type, manufacturer
- **Field structure**: Store power (W), energy (kWh), voltage, current as separate fields
- **Downsampling**: Create aggregated views (hourly, daily) for long-term analysis

**Schema Example**:
```
measurement: energy_consumption
tags: device_id, room, device_type, manufacturer
fields: power_w, energy_kwh, voltage_v, current_a
timestamp: Unix timestamp (nanosecond precision)
```

### 4. Real-Time Monitoring and Alerts

**Principle**: Provide real-time visibility into energy consumption patterns.

**Why it matters**: Users need immediate feedback to understand their energy usage and make informed decisions.

**Best Practices (2025)**:
- **Dashboard updates**: Update energy dashboards every 1-5 minutes
- **Live device status**: Show real-time power consumption per device
- **Usage comparisons**: Compare current usage to historical averages, same time yesterday/week
- **Anomaly detection**: Alert on unusual consumption patterns (potential device malfunction)
- **Threshold alerts**: Notify when consumption exceeds defined thresholds

**Alert Types**:
- **Anomaly alerts**: Unusual consumption detected (statistical outlier)
- **Threshold alerts**: Consumption exceeds user-defined limits
- **Device failure alerts**: Device not reporting data or reporting zeros
- **High usage alerts**: Consumption significantly above historical average

### 5. Historical Analysis and Trends

**Principle**: Analyze historical data to identify patterns and trends.

**Why it matters**: Historical analysis reveals usage patterns, seasonal trends, and optimization opportunities.

**Best Practices (2025)**:
- **Daily summaries**: Calculate daily totals, averages, peak consumption times
- **Weekly patterns**: Identify day-of-week patterns (weekend vs weekday usage)
- **Seasonal trends**: Compare monthly/yearly trends for seasonal adjustments
- **Device breakdown**: Analyze consumption by device, room, device type
- **Correlation analysis**: Identify relationships (e.g., HVAC usage vs outdoor temperature)

**Analysis Metrics**:
- **Total consumption**: Daily, weekly, monthly totals (kWh)
- **Average power**: Mean, median power consumption (W)
- **Peak demand**: Maximum power draw and when it occurred
- **Load factor**: Average power / peak power (efficiency metric)
- **Consumption by time**: Hourly, daily patterns

## Integration with Home Assistant

### Device Integration

**Energy Monitors**:
- Smart plugs with energy monitoring (TP-Link Kasa, Shelly)
- Whole-home energy monitors (Sense, Emporia Vue)
- Utility meter integrations (P1 Smart Meter, AMI meters)
- Solar/battery monitoring (Enphase, SolarEdge, Tesla Powerwall)

**Data Collection**:
- Use Home Assistant integrations for device-specific protocols
- Store data in InfluxDB via websocket-ingestion service
- Query via data-api service for dashboards and analysis

### Automation Integration

**Energy-Aware Automations**:
- Trigger automations based on energy consumption thresholds
- Pause non-essential devices during high-demand periods
- Optimize HVAC schedules based on historical consumption patterns
- Adjust device behavior based on real-time grid conditions

## Related Domains

- **Energy Economics**: Cost analysis, pricing optimization, ROI calculations
- **Pattern Analytics**: Consumption pattern detection, trend analysis
- **Device Ecosystem**: Device compatibility, manufacturer-specific implementations

## Best Practices Summary

1. ✅ Collect granular data at appropriate intervals
2. ✅ Ensure data quality and accuracy through validation
3. ✅ Use time-series databases for efficient storage
4. ✅ Provide real-time monitoring and alerts
5. ✅ Analyze historical data for patterns and trends
6. ✅ Integrate with Home Assistant for device monitoring
7. ✅ Enable energy-aware automations

## Technology Standards (2025)

- **InfluxDB 2.7+**: Recommended for time-series storage
- **Home Assistant 2025.10+**: Integration platform
- **MQTT/WebSocket**: Real-time data transmission
- **REST APIs**: Device communication protocols

