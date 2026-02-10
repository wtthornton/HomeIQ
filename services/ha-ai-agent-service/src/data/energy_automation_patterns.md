# Energy Automation Patterns for Home Assistant

## TOU / Rate-Based Scheduling

### Shift Load to Off-Peak Hours
```yaml
alias: "Shift Laundry to Off-Peak"
description: "Start washer during off-peak electricity hours"
trigger:
  - platform: time
    at: "23:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.off_peak_electricity
    state: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.washing_machine
mode: single
```

### Peak Avoidance – Turn Off Non-Essential Loads
```yaml
alias: "Peak Avoidance - HVAC Setback"
description: "Raise thermostat setpoint during peak rate hours"
trigger:
  - platform: state
    entity_id: binary_sensor.peak_electricity
    to: "on"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 26
mode: single
```

### Restore After Peak
```yaml
alias: "Restore After Peak"
description: "Restore thermostat after peak period ends"
trigger:
  - platform: state
    entity_id: binary_sensor.peak_electricity
    to: "off"
action:
  - service: climate.set_temperature
    target:
      entity_id: climate.thermostat
    data:
      temperature: 22
mode: single
```

## Solar Production Triggers

### Battery Priority When Solar Is High
```yaml
alias: "Solar Surplus - Charge Battery"
description: "Prioritize battery charging when solar exceeds consumption"
trigger:
  - platform: numeric_state
    entity_id: sensor.solar_power_production
    above: 3000
condition:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_charge
    below: 90
action:
  - service: number.set_value
    target:
      entity_id: number.battery_charge_rate
    data:
      value: 100
mode: single
```

### Export Management – Divert to Water Heater
```yaml
alias: "Divert Solar to Water Heater"
description: "Use excess solar for water heating instead of grid export"
trigger:
  - platform: numeric_state
    entity_id: sensor.grid_export_power
    above: 1500
action:
  - service: switch.turn_on
    target:
      entity_id: switch.water_heater_boost
mode: single
```

## EV Charging Patterns

### Scheduled Off-Peak EV Charging
```yaml
alias: "EV Off-Peak Charging"
description: "Start EV charging during off-peak window"
trigger:
  - platform: time
    at: "00:00:00"
condition:
  - condition: state
    entity_id: binary_sensor.ev_connected
    state: "on"
  - condition: numeric_state
    entity_id: sensor.ev_battery_level
    below: 80
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ev_charger
mode: single
```

### Solar-Surplus EV Charging
```yaml
alias: "EV Solar Charging"
description: "Charge EV with solar surplus only"
trigger:
  - platform: numeric_state
    entity_id: sensor.solar_power_production
    above: 2000
condition:
  - condition: state
    entity_id: binary_sensor.ev_connected
    state: "on"
action:
  - service: switch.turn_on
    target:
      entity_id: switch.ev_charger
mode: single
```

### Stop EV Charging When Solar Drops
```yaml
alias: "Stop EV Solar Charging"
description: "Stop EV charging when solar production drops"
trigger:
  - platform: numeric_state
    entity_id: sensor.solar_power_production
    below: 1000
condition:
  - condition: state
    entity_id: switch.ev_charger
    state: "on"
action:
  - service: switch.turn_off
    target:
      entity_id: switch.ev_charger
mode: single
```

## Battery Management

### Discharge Battery During Peak
```yaml
alias: "Battery Discharge During Peak"
description: "Use battery power during peak rate hours"
trigger:
  - platform: state
    entity_id: binary_sensor.peak_electricity
    to: "on"
condition:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_charge
    above: 20
action:
  - service: select.select_option
    target:
      entity_id: select.battery_mode
    data:
      option: "discharge"
mode: single
```

### Charge Battery Before Peak
```yaml
alias: "Pre-Peak Battery Charge"
description: "Charge battery from grid before peak hours"
trigger:
  - platform: time
    at: "14:00:00"
condition:
  - condition: numeric_state
    entity_id: sensor.battery_state_of_charge
    below: 80
action:
  - service: select.select_option
    target:
      entity_id: select.battery_mode
    data:
      option: "charge"
mode: single
```

### Grid Fallback When Battery Low
```yaml
alias: "Battery Low - Grid Fallback"
description: "Switch to grid when battery is critically low"
trigger:
  - platform: numeric_state
    entity_id: sensor.battery_state_of_charge
    below: 10
action:
  - service: select.select_option
    target:
      entity_id: select.battery_mode
    data:
      option: "grid"
  - service: notify.notify
    data:
      title: "Battery Low"
      message: "Battery at {{ states('sensor.battery_state_of_charge') }}%. Switched to grid power."
mode: single
```

## Demand Response / Load Shedding

### Demand Response - Shed Non-Critical Loads
```yaml
alias: "Demand Response - Shed Loads"
description: "Turn off non-critical loads when demand exceeds threshold"
trigger:
  - platform: numeric_state
    entity_id: sensor.total_power_consumption
    above: 8000
action:
  - service: switch.turn_off
    target:
      entity_id:
        - switch.pool_pump
        - switch.water_heater_boost
        - switch.ev_charger
  - service: notify.notify
    data:
      title: "High Demand Alert"
      message: "Power consumption at {{ states('sensor.total_power_consumption') }}W. Non-critical loads shed."
mode: single
```

### Restore Loads When Demand Normalizes
```yaml
alias: "Demand Normalized - Restore Loads"
description: "Restore loads when demand drops below threshold"
trigger:
  - platform: numeric_state
    entity_id: sensor.total_power_consumption
    below: 5000
    for:
      minutes: 5
action:
  - service: switch.turn_on
    target:
      entity_id:
        - switch.pool_pump
        - switch.water_heater_boost
mode: single
```

## Common Entity Patterns

| Purpose | Entity Pattern | Example |
|---------|---------------|---------|
| Solar production | `sensor.solar_power_production` | 3200 W |
| Grid import | `sensor.grid_import_power` | 1500 W |
| Grid export | `sensor.grid_export_power` | 800 W |
| Battery SoC | `sensor.battery_state_of_charge` | 75 % |
| Total consumption | `sensor.total_power_consumption` | 4200 W |
| Electricity price | `sensor.electricity_price` | 0.28 $/kWh |
| Peak binary | `binary_sensor.peak_electricity` | on/off |
| Off-peak binary | `binary_sensor.off_peak_electricity` | on/off |
| EV connected | `binary_sensor.ev_connected` | on/off |
| EV battery | `sensor.ev_battery_level` | 65 % |
