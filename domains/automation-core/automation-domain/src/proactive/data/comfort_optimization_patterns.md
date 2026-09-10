# Comfort Optimization Patterns for Proactive Suggestions

## Schedule Optimization

### Morning Warm-Up
Pre-heat the home before wake-up time so it's comfortable on arrival.
- Trigger: 30 minutes before typical wake time (learned from activity patterns)
- Action: Set thermostat to comfort temperature
- Adapt: Different schedules for weekdays vs weekends

### Arrival Comfort
Prepare the home before someone arrives.
- Trigger: Person enters home zone (geofence) or phone connects to Wi-Fi
- Action: Set thermostat, turn on entry lights, disarm alarm
- Lead time: Start HVAC 15-20 minutes before estimated arrival

### Sleep Optimization
Gradually adjust environment for better sleep.
- Lower thermostat 1-2 degrees at bedtime
- Dim lights progressively over 30 minutes
- Turn off screens/TVs, enable do-not-disturb

## Seasonal Adjustments

### Summer Cooling Strategy
- Close blinds on south-facing windows during peak sun hours
- Run ceiling fans before switching to AC
- Set AC to 24-25C rather than overcooling
- Suggest opening windows when outdoor temp drops below indoor

### Winter Heating Strategy
- Open south-facing blinds during sunny winter days (free solar heat)
- Close blinds at sunset to retain heat
- Use zone heating — only heat occupied rooms
- Lower temperature in unused rooms by 3-4 degrees

## Occupancy-Based Comfort

### Empty Room Detection
Rooms unoccupied for 15+ minutes should reduce energy use.
- Turn off lights and reduce HVAC in empty rooms
- Use motion sensors or door sensors for detection
- Restore when occupancy resumes

### Activity-Aware Adjustments
Adjust environment based on detected household activity.
- Cooking: Boost kitchen ventilation, reduce kitchen heating
- Sleeping: Lower temperature, minimize noise
- Working from home: Optimize office lighting and temperature
- Entertaining: Adjust living room scene, boost music volume

## Humidity and Air Quality

### Humidity Comfort Band
Maintain indoor humidity between 40-60% for comfort.
- Below 40%: Suggest running humidifier
- Above 60%: Suggest dehumidifier or bathroom fan
- Monitor: `sensor.indoor_humidity`

### Ventilation Reminders
Suggest fresh air intake when CO2 levels rise or after cooking.
- Trigger: CO2 above 1000ppm or cooking activity detected
- Action: Open windows (if weather permits) or run ventilation
- Duration: 15-20 minutes

## Common Suggestion Templates

| Scenario | Suggestion Pattern |
|----------|-------------------|
| Cold morning + wake time approaching | "It's 5C outside — pre-heat the house for your 7AM alarm?" |
| Person heading home (geofence) | "You're 15 min from home — start warming up the house?" |
| Humidity >65% | "Indoor humidity is 68% — run the dehumidifier?" |
| Empty house + HVAC full blast | "Nobody's been home for 2 hours — switch to eco mode?" |
| Hot day + blinds open | "It's 32C and sunny — close the south-facing blinds?" |
| Bedtime + lights still on | "It's past your usual bedtime — dim the lights?" |
