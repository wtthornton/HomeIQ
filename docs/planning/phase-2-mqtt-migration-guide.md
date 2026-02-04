# Phase 2: MQTT Migration Guide - asyncio-mqtt → aiomqtt

**Date:** February 4, 2026
**Status:** Code Changes Required
**Affected Services:** ha-simulator

---

## Overview

The `asyncio-mqtt` package has been renamed to `aiomqtt` (version 2.4.0). This requires import statement updates in any code that uses the MQTT client.

---

## Package Changes

### requirements.txt Updates (✅ COMPLETED)

**Before:**
```txt
asyncio-mqtt==0.16.1
```

**After:**
```txt
aiomqtt==2.4.0
paho-mqtt==2.1.0  # Required by aiomqtt
```

---

## Code Changes Required

### Service: ha-simulator

**Location:** `services/ha-simulator/`

**Import Changes:**

**Before:**
```python
from asyncio_mqtt import Client
```

**After:**
```python
from aiomqtt import Client
```

### Search for Usage

Run the following command to find all files that need updates:

```bash
grep -r "asyncio_mqtt" services/ha-simulator/
# or
grep -r "from asyncio_mqtt" services/ha-simulator/
```

---

## API Compatibility

Good news! The `aiomqtt` API is largely compatible with `asyncio-mqtt`. The main changes are:

1. **Import path changed** - Just update the import statement
2. **Context manager usage** - Same as before
3. **Message handling** - Same async patterns

### Example Code Pattern

**Before (`asyncio-mqtt`):**
```python
import asyncio
from asyncio_mqtt import Client

async def main():
    async with Client("test.mosquitto.org") as client:
        await client.subscribe("my/topic")
        async for message in client.messages:
            print(message.payload.decode())

asyncio.run(main())
```

**After (`aiomqtt`):**
```python
import asyncio
from aiomqtt import Client

async def main():
    async with Client("test.mosquitto.org") as client:
        await client.subscribe("my/topic")
        async for message in client.messages:
            print(message.payload.decode())

asyncio.run(main())
```

**The code is identical!** Only the import changed.

---

## Testing Checklist

After making code changes:

### 1. Verify Imports
```bash
cd services/ha-simulator
python -c "from aiomqtt import Client; print('✓ Import successful')"
```

### 2. Run Unit Tests
```bash
pytest
```

### 3. Integration Testing
- Test MQTT connection to broker
- Verify message publish works
- Verify message subscription works
- Check reconnection logic

### 4. Manual Testing
- Start the ha-simulator service
- Monitor MQTT traffic
- Verify no errors in logs

---

## Migration Steps

### Step 1: Search for asyncio-mqtt usage
```bash
cd services/ha-simulator
grep -rn "asyncio_mqtt" .
```

### Step 2: Update Import Statements
Replace:
```python
from asyncio_mqtt import Client
```
With:
```python
from aiomqtt import Client
```

Also check for:
```python
import asyncio_mqtt
```
Replace with:
```python
import aiomqtt
```

### Step 3: Test
```bash
pip install -r requirements.txt
pytest
# Or run service manually
python -m ha_simulator  # or whatever the entry point is
```

### Step 4: Commit
```bash
git add services/ha-simulator/
git commit -m "feat: migrate ha-simulator from asyncio-mqtt to aiomqtt

- Update imports from asyncio_mqtt to aiomqtt
- Compatible API, no logic changes required
- Part of Phase 2 library upgrades

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Rollback Plan

If issues arise:

### Revert requirements.txt
```bash
git checkout HEAD~1 -- services/ha-simulator/requirements.txt
pip install -r services/ha-simulator/requirements.txt
```

### Revert code changes
```bash
git checkout HEAD~1 -- services/ha-simulator/
```

---

## Additional Resources

- **aiomqtt Documentation:** https://sbtinstruments.github.io/aiomqtt/
- **Migration Guide:** https://github.com/empicano/aiomqtt
- **Changelog:** https://github.com/empicano/aiomqtt/releases

---

## Status Tracking

- [x] requirements.txt updated (ha-simulator)
- [x] requirements.txt updated (ai-pattern-service) - uses paho-mqtt directly
- [ ] Code imports updated (ha-simulator) - **ACTION REQUIRED**
- [ ] Unit tests passing
- [ ] Integration tests passing
- [ ] Deployed to staging

---

## Notes

### ai-pattern-service
This service uses `paho-mqtt` directly (not via asyncio-mqtt), so it only needed the version bump to 2.1.0. No code changes required.

### Future Services
If other services use asyncio-mqtt in the future, follow the same migration pattern:
1. Update requirements.txt
2. Change import statement
3. Test thoroughly
4. Commit

---

**Next Steps:**
1. Update ha-simulator imports (see Step 1-4 above)
2. Test thoroughly
3. Deploy to staging for validation

---

**End of Guide**
