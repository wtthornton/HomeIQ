# Rate Limit Configuration - 2025 Best Practices

**Date:** November 25, 2025  
**Status:** ✅ Updated for 2025 OpenAI API Rate Limits

---

## 2025 OpenAI API Rate Limits (gpt-4o-mini)

### Tier-Based Limits

| Tier | RPM (Requests/Minute) | TPM (Tokens/Minute) | Typical Account Type |
|------|------------------------|---------------------|---------------------|
| Tier 1 | 3-5 RPM | ~40K TPM | Free/New accounts |
| Tier 2 | 60-500 RPM | ~1M TPM | Paid accounts |
| Tier 3+ | 500+ RPM | 1M+ TPM | High-usage accounts |

**Note:** Limits vary by model and account. Check your limits at: https://platform.openai.com/account/limits

---

## Current Configuration

### Default Settings
- **Rate Limit:** 20 RPM (conservative for tier 2)
- **Delay Between Requests:** 3.3 seconds (60/20 * 1.1 buffer)
- **Retry Strategy:** Exponential backoff (4s, 8s, 16s, 32s, 60s max)

### Why 20 RPM?
- **Safe for Tier 2:** Well below 60 RPM minimum
- **Conservative:** 10% buffer added
- **Configurable:** Can be adjusted via `--rate-limit-rpm` parameter

---

## Code Updates

### 1. ✅ Configurable Rate Limit

**Before:**
```python
delay = 2.0  # Fixed 2 seconds (30 RPM)
```

**After:**
```python
def __init__(self, openai_client: OpenAIClient, rate_limit_rpm: int = 20):
    self.rate_limit_rpm = rate_limit_rpm
    self.request_delay = (60.0 / rate_limit_rpm) * 1.1  # 10% buffer
```

### 2. ✅ Command-Line Parameter

```bash
# Use default (20 RPM)
python scripts/generate_synthetic_homes.py --count 100

# Use tier 1 limits (3 RPM)
python scripts/generate_synthetic_homes.py --count 100 --rate-limit-rpm 3

# Use tier 2 limits (60 RPM)
python scripts/generate_synthetic_homes.py --count 100 --rate-limit-rpm 60
```

### 3. ✅ All LLM Calls Respect Rate Limits

- Home generation: Uses configured delay
- Area generation: Uses configured delay
- Device generation: Uses configured delay
- Event generation: No LLM (local only)

---

## Rate Limit Calculation

### Formula
```
delay_seconds = (60 / RPM) * 1.1
```

### Examples

| RPM | Delay | Notes |
|-----|-------|-------|
| 3 (Tier 1) | 22.0s | Very conservative |
| 20 (Default) | 3.3s | Safe for tier 2 |
| 60 (Tier 2) | 1.1s | Tier 2 minimum |
| 500 (Tier 3) | 0.13s | High tier |

---

## Usage Recommendations

### For Tier 1 Accounts (Free/New)
```bash
python scripts/generate_synthetic_homes.py --count 100 --rate-limit-rpm 3
```
- **Delay:** 22 seconds between calls
- **Time for 100 homes:** ~37 minutes (just API calls)
- **Total time:** ~40-50 minutes

### For Tier 2 Accounts (Paid - Default)
```bash
python scripts/generate_synthetic_homes.py --count 100 --rate-limit-rpm 20
```
- **Delay:** 3.3 seconds between calls
- **Time for 100 homes:** ~5.5 minutes (just API calls)
- **Total time:** ~6-8 minutes

### For Tier 2+ Accounts (Higher Limits)
```bash
python scripts/generate_synthetic_homes.py --count 100 --rate-limit-rpm 60
```
- **Delay:** 1.1 seconds between calls
- **Time for 100 homes:** ~2 minutes (just API calls)
- **Total time:** ~3-4 minutes

---

## Verification

### Check Your Rate Limits
1. Visit: https://platform.openai.com/account/limits
2. Find your tier and RPM limit
3. Use appropriate `--rate-limit-rpm` value

### Test Rate Limiting
```bash
# Test with 2 homes to verify delays
python scripts/generate_synthetic_homes.py --count 2 --rate-limit-rpm 20

# Watch logs for delay messages
# Should see: "Waiting 3.30s before next API call..."
```

---

## Files Updated

1. ✅ `services/ai-automation-service/src/training/synthetic_home_generator.py`
   - Added `rate_limit_rpm` parameter
   - Calculated delay from RPM
   - Updated comments with 2025 limits

2. ✅ `services/ai-automation-service/scripts/generate_synthetic_homes.py`
   - Added `--rate-limit-rpm` argument
   - Passes rate limit to generator
   - Updated delays for area/device generation

---

## Best Practices

### 1. Start Conservative
- Use default (20 RPM) if unsure
- Monitor for rate limit errors
- Increase if no errors occur

### 2. Monitor Your Tier
- Check limits regularly
- Adjust as account tier increases
- Use highest safe RPM for faster generation

### 3. Handle Errors Gracefully
- Code automatically retries on rate limits
- 60-second wait on rate limit errors
- Falls back gracefully

---

## Expected Generation Times

### With 20 RPM (Default)
- **100 homes:** ~6-8 minutes (API calls only)
- **With 90 days events:** ~26-52 hours total
- **Events are local:** No API calls, fast

### With 60 RPM (Tier 2)
- **100 homes:** ~3-4 minutes (API calls only)
- **With 90 days events:** ~26-52 hours total
- **Faster API calls:** But event generation is same

---

**Status:** ✅ **Rate Limits Configured for 2025 Best Practices**

