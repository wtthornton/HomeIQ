# Multi-Scale Temporal Pattern Detection for Home Automation

**Last Updated:** 2025-10-15  
**Category:** Machine Learning, Time Series Analysis  
**Technologies:** Prophet, scikit-learn, statsmodels, pandas  
**Use Case:** Hierarchical pattern detection in IoT/home automation

## Overview

Multi-scale temporal pattern detection involves identifying patterns that occur at different time scales (hourly, daily, weekly, monthly, seasonal) and understanding how they interact and compose.

## Key Concepts

### 1. Temporal Hierarchies

**Definition:** Patterns exist at multiple temporal resolutions simultaneously.

```
Hierarchy Example:
- Micro (Hourly): "Lights on between 18:00-19:00"
- Daily: "Pattern occurs every day"
- Weekly: "Pattern only on weekdays"
- Monthly: "Pattern stronger in winter months"
- Seasonal: "Pattern shifts with daylight savings"
- Annual: "Pattern evolves year over year"
```

### 2. Pattern Composition

**Definition:** Specific patterns are compositions of general patterns plus constraints.

```
General Pattern: "Thermostat adjusted to 72°F"
+ Weekly Constraint: "Only Monday-Friday"
+ Seasonal Constraint: "Only in winter (Dec-Feb)"
= Composite: "Thermostat set to 72°F on weekdays in winter"
```

### 3. Overlapping Pattern Resolution

**Challenge:** Multiple patterns may describe the same behavior at different levels of specificity.

**Resolution Strategy:**
- More specific patterns with high confidence override general patterns
- Use confidence thresholds to filter noise
- Prefer composite patterns over simple patterns

## Technology Stack

### Prophet (Facebook)

**Best For:** Seasonal decomposition and multi-scale patterns

**Strengths:**
- Built-in daily, weekly, yearly seasonality
- Handles missing data and outliers
- Automatic changepoint detection
- Holiday effects support
- Works well with irregular intervals

**Usage Pattern:**
```python
from prophet import Prophet

# Fit model with multiple seasonalities
model = Prophet(
    yearly_seasonality=True,
    weekly_seasonality=True,
    daily_seasonality=True,
    seasonality_mode='multiplicative'  # For patterns that scale
)

model.add_seasonality(
    name='monthly',
    period=30.5,
    fourier_order=5
)

model.fit(df)
forecast = model.predict(future)

# Extract seasonal components
yearly_pattern = forecast['yearly']
weekly_pattern = forecast['weekly']
```

**Limitations:**
- Memory intensive (100-200MB per device)
- Slow on large datasets
- Requires consistent time series

**Home Automation Optimization:**
- Run on subset of most-used devices
- Use daily aggregations, not raw events
- Cache results for 7 days

### scikit-learn

**Best For:** Pattern clustering and classification

**Strengths:**
- Fast clustering algorithms (KMeans, DBSCAN)
- Anomaly detection (Isolation Forest)
- Feature importance (Random Forest)
- Low memory footprint

**Usage Pattern:**
```python
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Cluster similar daily patterns
scaler = StandardScaler()
scaled_features = scaler.fit_transform(daily_features)

clustering = DBSCAN(eps=0.5, min_samples=3)
labels = clustering.fit_predict(scaled_features)

# Identify pattern groups
for label in set(labels):
    if label == -1:  # Noise
        continue
    cluster = daily_features[labels == label]
    # Analyze cluster for patterns
```

**Limitations:**
- Doesn't inherently understand temporal relationships
- Requires feature engineering
- Sensitive to scale

### statsmodels

**Best For:** Statistical time series analysis

**Strengths:**
- ARIMA models for forecasting
- Seasonal decomposition (STL)
- Statistical tests (stationarity, autocorrelation)
- More lightweight than Prophet

**Usage Pattern:**
```python
from statsmodels.tsa.seasonal import seasonal_decompose

# Decompose time series
result = seasonal_decompose(
    time_series,
    model='additive',
    period=7  # Weekly seasonality
)

trend = result.trend
seasonal = result.seasonal
residual = result.resid
```

## Implementation Patterns

### Pattern 1: Hierarchical Detection

**Approach:** Detect patterns at each scale independently, then consolidate.

```python
class HierarchicalPatternDetector:
    def detect_all_scales(self, data):
        patterns = {
            'hourly': self.detect_hourly(data),
            'daily': self.detect_daily(data),
            'weekly': self.detect_weekly(data),
            'monthly': self.detect_monthly(data),
            'seasonal': self.detect_seasonal_prophet(data)
        }
        return self.consolidate_patterns(patterns)
```

**Advantages:**
- Independent analysis at each scale
- Easier to debug and understand
- Can skip scales with insufficient data

**Disadvantages:**
- Potential redundancy
- Requires consolidation logic

### Pattern 2: Prophet-First

**Approach:** Use Prophet to decompose seasonality, then analyze residuals for other patterns.

```python
def prophet_first_approach(data):
    # 1. Prophet decomposes time series
    model = Prophet(...)
    forecast = model.predict(data)
    
    # 2. Extract seasonal components
    yearly = forecast['yearly']
    weekly = forecast['weekly']
    daily = forecast['daily']
    
    # 3. Analyze residuals for non-seasonal patterns
    residuals = data['y'] - forecast['yhat']
    anomalies = detect_anomalies(residuals)
    
    return {
        'seasonal': {
            'yearly': yearly,
            'weekly': weekly,
            'daily': daily
        },
        'anomalies': anomalies
    }
```

**Advantages:**
- Prophet handles complex seasonality automatically
- Residuals reveal non-seasonal patterns
- Unified framework

**Disadvantages:**
- Memory intensive
- Prophet may miss some patterns
- Slower processing

### Pattern 3: Feature-Based Clustering

**Approach:** Engineer features at multiple scales, then cluster.

```python
def feature_based_clustering(data):
    # Engineer temporal features
    features = pd.DataFrame({
        'hour': data['timestamp'].dt.hour,
        'day_of_week': data['timestamp'].dt.dayofweek,
        'month': data['timestamp'].dt.month,
        'is_weekend': data['timestamp'].dt.dayofweek >= 5,
        'is_winter': data['timestamp'].dt.month.isin([12,1,2]),
        'device_state': data['state'],
        # Rolling statistics
        'rolling_mean_24h': data['state'].rolling(24).mean(),
        'rolling_std_7d': data['state'].rolling(7*24).std()
    })
    
    # Cluster similar patterns
    from sklearn.cluster import KMeans
    kmeans = KMeans(n_clusters=10)
    labels = kmeans.fit_predict(features)
    
    # Analyze each cluster
    for i in range(10):
        cluster = features[labels == i]
        describe_cluster(cluster)
```

**Advantages:**
- Fast (scikit-learn is efficient)
- Works with limited data
- Interpretable features

**Disadvantages:**
- Requires domain expertise for features
- May miss complex patterns
- Manual feature engineering

## Best Practices

### 1. Data Requirements

| Scale | Minimum Data | Confidence | Recommendation |
|-------|-------------|-----------|----------------|
| Hourly | 3 days | Medium | 7+ days for patterns |
| Daily | 7 days | Medium | 30+ days for confidence |
| Weekly | 2 weeks | Low | 8+ weeks for patterns |
| Monthly | 2 months | Low | 6+ months for patterns |
| Seasonal | 6 months | Very Low | 12+ months required |
| Annual | 12 months | Very Low | 24+ months for trends |

### 2. Confidence Scoring

**Formula for Composite Patterns:**

```python
def composite_confidence(base_confidence, num_constraints, constraint_confidences):
    """
    More specific patterns have lower confidence due to:
    1. Less data (fewer matching instances)
    2. More constraints (more ways to fail)
    
    Balance specificity with confidence.
    """
    # Start with base
    confidence = base_confidence
    
    # Penalty for each constraint (0.9^n)
    specificity_penalty = 0.9 ** num_constraints
    confidence *= specificity_penalty
    
    # Multiply by constraint confidences
    for c_conf in constraint_confidences:
        confidence *= c_conf
    
    return confidence

# Example:
# Base: "Lights on at 7 AM" (0.95 confidence, 28/30 days)
# + Weekly: "Only weekdays" (0.90 confidence, 20/20 weekdays)
# + Seasonal: "In winter" (0.80 confidence, 85/90 winter days)
# 
# Composite confidence:
# 0.95 * (0.9^2) * 0.90 * 0.80 = 0.95 * 0.81 * 0.90 * 0.80 = 0.55
# 
# Still acceptable (>0.5) but appropriately reduced
```

### 3. Memory Optimization

**Challenge:** Prophet uses 100-200MB RAM per device time series.

**Solutions:**

```python
# Option 1: Process subset of devices
top_devices = get_most_used_devices(limit=20)
for device in top_devices:
    run_prophet_analysis(device)

# Option 2: Downsample before Prophet
daily_aggregated = downsample_to_daily(hourly_data)
run_prophet_analysis(daily_aggregated)  # 24x less data

# Option 3: Batch processing with cleanup
for device_batch in chunk_devices(all_devices, batch_size=5):
    results = [run_prophet(d) for d in device_batch]
    save_results(results)
    del results  # Free memory
    gc.collect()
```

### 4. Incremental Updates

**Challenge:** Don't recompute everything daily.

**Solution:** Differential updates

```python
# Daily: Only analyze last 24 hours
daily_update = analyze_last_24h(new_data)
merge_with_existing_patterns(daily_update, existing_patterns)

# Weekly: Full re-analysis of weekly patterns
weekly_update = analyze_last_7d(data)
update_weekly_patterns(weekly_update)

# Monthly/Seasonal: Only on schedule
if today.day == 1:  # First of month
    run_full_monthly_analysis()
```

### 5. Pattern Validation

**Before presenting patterns to user:**

```python
def validate_pattern(pattern, data):
    """Validate pattern is real, not noise"""
    
    # 1. Minimum occurrences
    if pattern['occurrences'] < 3:
        return False
    
    # 2. Confidence threshold
    if pattern['confidence'] < 0.7:
        return False
    
    # 3. Statistical significance
    p_value = chi_square_test(pattern, data)
    if p_value > 0.05:
        return False  # Not statistically significant
    
    # 4. Practical significance
    if pattern['impact'] < threshold:
        return False  # Too minor to automate
    
    return True
```

## Common Pitfalls

### 1. Overfitting to Noise

**Problem:** Detecting patterns in random data.

**Solution:** 
- Require minimum occurrences (3+)
- Use statistical significance tests
- Validate patterns on hold-out data

### 2. Insufficient Data

**Problem:** Trying to detect seasonal patterns with 2 months of data.

**Solution:**
- Bootstrap strategy (start with daily/weekly)
- Clear confidence indicators
- Wait for sufficient data before seasonal analysis

### 3. Combinatorial Explosion

**Problem:** Too many possible pattern combinations.

**Solution:**
- Limit constraint depth (max 3 levels)
- Prune low-confidence patterns early
- Focus on most impactful patterns

### 4. Ignoring Context

**Problem:** Patterns without understanding WHY.

**Solution:**
- Include contextual features (weather, occupancy)
- Use LLM to explain patterns to user
- Allow user feedback to refine

## Recommended Stack for Home Automation

### Minimal (Single NUC/Pi):
```python
- pandas (data manipulation)
- scikit-learn (clustering, anomaly detection)
- statsmodels (basic seasonal decomposition)
- Prophet (ONLY for top 10-20 devices)
```

### Full-Featured (Dedicated Server):
```python
- All minimal stack +
- Prophet (all devices)
- Deep learning (LSTM) for complex patterns
- Vector database for pattern similarity
```

## Performance Benchmarks

### Prophet Processing Time:
```
Single device (1 year hourly data):
  - Fit model: 10-30 seconds
  - Generate forecast: 2-5 seconds
  - Total: ~30 seconds per device

20 devices: 10 minutes
100 devices: 50 minutes (batch with parallelization)
```

### scikit-learn Processing Time:
```
KMeans clustering (10k samples, 10 features):
  - Fit: <1 second
  - Predict: <0.1 seconds

DBSCAN (10k samples):
  - Fit: 2-5 seconds
```

## References

- **Prophet Documentation:** https://facebook.github.io/prophet/
- **scikit-learn Time Series:** https://scikit-learn.org/stable/modules/clustering.html
- **statsmodels Seasonal:** https://www.statsmodels.org/stable/tsa.html
- **Hierarchical Pattern Mining:** Academic research in temporal data mining

---

**Maintenance:**
- Update quarterly with new ML techniques
- Revise based on production performance
- Add real-world benchmarks from deployments

