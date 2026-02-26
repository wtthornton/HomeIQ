# Security Best Practices for Proactive Suggestions

## Presence Simulation

### Away-Mode Lighting
When nobody is home, cycle lights to simulate occupancy.
- Trigger: `group.all_persons` state `not_home` for 30+ minutes
- Action: Random on/off of living room, bedroom, and kitchen lights
- Schedule: Sunset to 23:00, varying by 15-30 minute intervals

### Vacation Mode
Extended absence (>24h) should activate comprehensive presence simulation.
- Lights, TV (via smart plug), and blinds on randomized schedules
- Reduce HVAC to eco mode but keep pipes from freezing
- Enable all motion sensor notifications

## Lock and Door Management

### Auto-Lock Forgotten Doors
Doors left unlocked for more than 5 minutes should auto-lock.
- Trigger: `lock.front_door` state `unlocked` for 5 minutes
- Action: Lock and send notification
- Exception: During daytime when someone is home (configurable)

### Bedtime Security Check
At bedtime, verify all doors locked and garage closed.
- Trigger: Bedtime scene activation or time-based (e.g., 23:00)
- Check: All locks, garage door, alarm panel
- Notify if any are open/unlocked with one-tap fix action

## Motion and Intrusion Detection

### Nobody-Home Motion Alerts
Motion detected when everyone is away should trigger high-priority alerts.
- Include camera snapshot if available
- Use `importance: high` for mobile notifications
- Optionally trigger siren after 30-second delay

### Night Motion in Perimeter Zones
Outdoor motion at night warrants different handling than daytime.
- Trigger: Motion sensors in garage, driveway, or garden after 23:00
- Action: Turn on exterior lights, send notification with camera image
- Auto-off lights after 5 minutes of no motion

## Notification Gaps

### Sensor Battery Alerts
Door/window sensors running low on battery create security blind spots.
- Monitor `sensor.*_battery` entities below 20%
- Suggest replacing batteries before they die
- Priority: Entry point sensors (doors, windows) over interior

### Offline Device Alerts
Security devices that go offline should be flagged immediately.
- Monitor: Cameras, locks, alarm panels, motion sensors
- Alert within 15 minutes of going unavailable
- Distinguish between: Wi-Fi issues, battery dead, device failure

## Common Suggestion Templates

| Scenario | Suggestion Pattern |
|----------|-------------------|
| Everyone left, door unlocked | "Front door is unlocked and nobody's home — lock it?" |
| Night + no alarm armed | "It's 23:00 and the alarm isn't armed — arm it?" |
| Away 2+ days, no vacation mode | "You've been away 2 days — enable vacation mode?" |
| Motion + nobody home | "Motion in living room while you're away — check camera?" |
| Lock battery <15% | "Front door lock battery at 12% — replace soon?" |
