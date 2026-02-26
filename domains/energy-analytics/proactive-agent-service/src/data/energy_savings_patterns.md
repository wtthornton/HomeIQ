# Energy Savings Patterns for Proactive Suggestions

## Peak Avoidance

### Shift Heavy Loads to Off-Peak
When electricity prices are high or carbon intensity is elevated, suggest
shifting dishwashers, laundry, and EV charging to off-peak windows.
- Trigger: `binary_sensor.peak_electricity` turns on
- Action: Notify user to delay energy-intensive tasks
- Typical savings: 15-30% on electricity bills

### Pre-Cool / Pre-Heat Before Peak
Run HVAC aggressively during off-peak, then coast through peak hours.
- Trigger: 30 minutes before peak period starts
- Action: Lower thermostat 2-3 degrees (cooling) or raise 2-3 degrees (heating)
- Let thermal mass carry through the peak window

## Solar Optimization

### Maximize Self-Consumption
When solar production exceeds household consumption, run deferrable loads.
- Start pool pump, water heater boost, or EV charging
- Monitor `sensor.solar_power_production` vs `sensor.total_power_consumption`
- Goal: minimize grid export, maximize on-site usage

### Battery Charging Strategy
Charge home battery from solar during midday, discharge during evening peak.
- Morning: grid charge to 30% if battery below threshold
- Midday: solar charge to 90%+
- Evening peak: discharge to power the home

## Smart Meter Insights

### Standby Power Reduction
Identify devices with high standby consumption via smart meter data.
- Flag devices consuming >5W in standby
- Suggest smart plug automations to cut phantom loads
- Typical savings: 5-10% of total consumption

### Usage Pattern Anomalies
Alert when daily consumption deviates significantly from the 7-day average.
- Threshold: >20% above rolling average
- Could indicate: forgotten appliance, HVAC issue, or guest usage

## Carbon-Aware Scheduling

### Low-Carbon Windows
Schedule flexible loads when grid carbon intensity drops below threshold.
- Monitor `sensor.carbon_intensity`
- Batch laundry, dishwasher, EV charging during green windows
- Notify user of upcoming low-carbon periods

## Common Suggestion Templates

| Scenario | Suggestion Pattern |
|----------|-------------------|
| High carbon + EV plugged in | "Grid carbon is high — delay EV charging until tonight?" |
| Solar surplus + battery full | "Solar surplus detected — run the pool pump now?" |
| Peak starting + HVAC running | "Peak rates starting — pre-cool and coast?" |
| High standby overnight | "5 devices drew 45W overnight — add smart plugs?" |
| Below-average usage streak | "Great job — you've used 15% less energy this week!" |
