# Device Setup Patterns for Home Assistant

## Zigbee (via Zigbee2MQTT)

### Pairing a New Zigbee Device
1. **Enable permit join** — In Zigbee2MQTT frontend or via MQTT:
   - Topic: `zigbee2mqtt/bridge/request/permit_join`
   - Payload: `{"value": true, "time": 120}`
2. **Put device in pairing mode** — Usually hold the reset button for 5-10 seconds until LED blinks
3. **Wait for interview** — Zigbee2MQTT will interview the device (30-120 seconds)
4. **Entity creation** — HA auto-discovers entities via MQTT discovery
5. **Rename device** — Set a friendly name in Zigbee2MQTT config

### Common Zigbee Devices
| Device Type | Example Entities Created |
|-------------|------------------------|
| Motion sensor | `binary_sensor.{name}_occupancy`, `sensor.{name}_illuminance` |
| Door sensor | `binary_sensor.{name}_contact` |
| Temperature sensor | `sensor.{name}_temperature`, `sensor.{name}_humidity` |
| Smart plug | `switch.{name}`, `sensor.{name}_power` |
| Light bulb | `light.{name}` |
| Button/remote | `sensor.{name}_action` |

### Zigbee Troubleshooting
| Issue | Solution |
|-------|----------|
| Device won't pair | Reset device, move closer to coordinator, check permit join is active |
| Device drops offline | Check signal strength, add Zigbee router devices (smart plugs) |
| Entity not created | Restart Zigbee2MQTT, check MQTT discovery is enabled in HA |
| Interview fails | Remove and re-pair device, update Zigbee2MQTT firmware |

## Philips Hue

### Hue Bridge Setup
1. **Connect bridge** — Plug Hue Bridge into router via Ethernet
2. **Add integration** — Go to Settings > Devices & Services > Add Integration > Philips Hue
3. **Press bridge button** — HA will prompt you to press the button on the bridge
4. **Discovery** — All paired lights, sensors, and accessories are auto-discovered

### Pairing New Hue Devices
1. **In Hue app** — Add device through the official Hue app first
2. **Sync to HA** — HA picks up new devices automatically (may take 30 seconds)
3. **Room/zone assignment** — Rooms from Hue app map to HA areas

### Hue Entity Patterns
| Device | Entity Pattern |
|--------|---------------|
| Light bulb | `light.{room}_{name}` |
| Light strip | `light.{room}_lightstrip` |
| Motion sensor | `binary_sensor.{room}_motion`, `sensor.{room}_temperature` |
| Dimmer switch | `sensor.{name}_action` (via events) |
| Smart plug | `switch.{name}` |

### Hue Troubleshooting
| Issue | Solution |
|-------|----------|
| Bridge not found | Ensure Ethernet is connected, check same subnet |
| Light unreachable | Power cycle the light, check Hue app |
| Slow response | Check bridge firmware is up to date |
| Missing entities | Reload Hue integration in HA |

## Z-Wave

### Z-Wave Inclusion (Pairing)
1. **Start inclusion** — In HA: Settings > Devices & Services > Z-Wave JS > Add Device
2. **Secure inclusion** — Select S2 security if device supports it (recommended)
3. **Put device in inclusion mode** — Usually triple-press a button
4. **Wait for interview** — Z-Wave interview takes 1-5 minutes
5. **Entity creation** — Entities appear after interview completes

### Z-Wave Device Types
| Device Type | Example Entities |
|-------------|-----------------|
| Dimmer switch | `light.{name}`, `sensor.{name}_electric_consumption` |
| Door lock | `lock.{name}`, `sensor.{name}_battery` |
| Thermostat | `climate.{name}`, `sensor.{name}_temperature` |
| Multisensor | `binary_sensor.{name}_motion`, `sensor.{name}_temperature`, `sensor.{name}_luminance` |
| Garage door | `cover.{name}` |

### Z-Wave Troubleshooting
| Issue | Solution |
|-------|----------|
| Device not found | Move closer to controller, ensure inclusion mode is active |
| Dead node | Check device power, perform node heal |
| Slow network | Add repeater nodes, heal network |
| Interview incomplete | Re-interview device from Z-Wave JS UI |

## MQTT

### Broker Setup (Mosquitto)
1. **Install add-on** — Settings > Add-ons > Mosquitto broker > Install
2. **Create user** — Set a username/password for MQTT authentication
3. **Start broker** — Start the Mosquitto add-on
4. **HA integration** — Add MQTT integration (auto-discovered if using add-on)

### MQTT Topic Structure
```
homeassistant/          # Discovery prefix
  sensor/               # Component
    {device_id}/        # Device identifier
      config            # Discovery payload
      state             # State topic
```

### MQTT Auto-Discovery
Devices publish discovery payloads to `homeassistant/{component}/{device_id}/config`. HA auto-creates entities from these payloads.

### MQTT Troubleshooting
| Issue | Solution |
|-------|----------|
| Cannot connect | Check broker URL, port (1883), credentials |
| No discovery | Verify discovery prefix matches (`homeassistant/`) |
| Messages not received | Check topic subscription, use MQTT Explorer to debug |
| Retained messages | Clear retained messages if entity is stale |

## Matter / Thread

### Matter Commissioning
1. **Ensure Thread border router** — Use Apple HomePod Mini, Google Nest Hub, or SkyConnect
2. **Add integration** — Settings > Devices & Services > Add Integration > Matter
3. **Commission device** — Scan QR code or enter pairing code
4. **Fabric joining** — Device joins the Matter fabric

### Thread Network
- Thread devices form a mesh network
- Border routers bridge Thread to IP network
- HA acts as a Matter controller

### Matter Troubleshooting
| Issue | Solution |
|-------|----------|
| Commission fails | Ensure device is in pairing mode, check Thread network |
| Device unreachable | Verify Thread border router is online |
| Missing entities | Matter support varies; check HA release notes |
| Multi-fabric issues | Remove from other controllers, re-commission |

## General Setup Tips

### Before Pairing
- Ensure firmware is up to date on coordinator/bridge
- Position coordinator centrally for best range
- Have the device physically close during initial pairing

### After Pairing
- Rename entities with friendly names
- Assign devices to areas/rooms
- Test entity states in Developer Tools > States
- Create a test automation to verify the device works
