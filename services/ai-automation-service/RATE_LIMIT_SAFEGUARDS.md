# OpenAI Rate Limit Safeguards for 400 Home Generation

**Last Updated:** December 2025  
**Status:** ✅ Implemented

## Overview

Comprehensive safeguards have been implemented to prevent exceeding OpenAI API rate limits and quotas when generating 400 synthetic homes with OpenAI enhancement.

---

## Safeguards Implemented

### 1. ✅ Automatic Request Throttling

**What it does:**
- Adds automatic delays between OpenAI API calls
- Prevents rapid-fire requests that could trigger rate limits

**Configuration:**
- Default: **20 RPM** (Requests Per Minute)
- Delay: **3.3 seconds** between each API call
- Formula: `delay = (60 seconds / RPM) * 1.1` (10% safety buffer)

**Command-line control:**
```bash
# Use default (20 RPM - conservative)
python scripts/generate_synthetic_homes.py --count 400 --enable-openai

# Use tier 1 limits (3 RPM - very conservative for free accounts)
python scripts/generate_synthetic_homes.py --count 400 --enable-openai --rate-limit-rpm 3

# Use tier 2 limits (60 RPM - faster, requires paid account)
python scripts/generate_synthetic_homes.py --count 400 --enable-openai --rate-limit-rpm 60
```

### 2. ✅ Exponential Backoff Retry Strategy

**What it does:**
- Automatically retries failed requests with increasing delays
- Distinguishes between rate limits (temporary) and quota errors (permanent)

**Retry configuration:**
- Max attempts: **5 retries**
- Initial wait: **4 seconds**
- Max wait: **60 seconds**
- Multiplier: **2x per retry** (4s → 8s → 16s → 32s → 60s)

**Error handling:**
- **Rate limit errors (429):** Automatic retry with exponential backoff
- **Quota errors:** Immediate failure with clear error message (requires account action)
- **Other API errors:** Retry with backoff

### 3. ✅ Quota vs Rate Limit Detection

**What it does:**
- Distinguishes between temporary rate limits and permanent quota issues
- Provides clear error messages for quota problems

**Behavior:**
- **Rate limit (429):** Retries automatically (temporary)
- **Quota exceeded (429 with `insufficient_quota`):** Stops immediately with error message

### 4. ✅ Applied to All OpenAI Calls

**Rate limiting is applied to:**
- ✅ Home generation (80 enhanced homes)
- ✅ Home validation (10% of template homes)
- ✅ All OpenAI API calls in the pipeline

---

## Rate Limit Configuration Guide

### Understanding Your OpenAI Tier

Check your rate limits at: https://platform.openai.com/account/limits

| Tier | RPM Limit | Typical Account | Recommended RPM |
|------|-----------|-----------------|-----------------|
| Tier 1 | 3-5 RPM | Free/New accounts | 3 RPM (22s delay) |
| Tier 2 | 60-500 RPM | Paid accounts | 20 RPM (3.3s delay) - Default |
| Tier 3+ | 500+ RPM | High-usage accounts | 60+ RPM (1.1s+ delay) |

### Recommended Settings for 400 Homes

#### Conservative (Default - Recommended)
```bash
--rate-limit-rpm 20
```
- **Delay:** 3.3 seconds between calls
- **Time for 80 OpenAI homes:** ~4.4 minutes (just API calls)
- **Safety:** 10% buffer below tier 2 minimum
- **Best for:** Most users, unknown tier status

#### Very Conservative (Free/New Accounts)
```bash
--rate-limit-rpm 3
```
- **Delay:** 22 seconds between calls
- **Time for 80 OpenAI homes:** ~29 minutes (just API calls)
- **Safety:** Safe for tier 1 accounts
- **Best for:** Free accounts or new API keys

#### Fast (Higher Tier Accounts)
```bash
--rate-limit-rpm 60
```
- **Delay:** 1.1 seconds between calls
- **Time for 80 OpenAI homes:** ~1.5 minutes (just API calls)
- **Safety:** At tier 2 minimum (risky if not verified)
- **Best for:** Verified tier 2+ accounts

---

## Example: Generating 400 Homes

### With Default Rate Limiting (20 RPM)

```bash
python scripts/generate_synthetic_homes.py \
    --count 400 \
    --enable-openai \
    --enhancement-percentage 0.20 \
    --days 7 \
    --rate-limit-rpm 20 \
    --output tests/datasets/synthetic_homes_400_test
```

**What happens:**
1. Generates 320 template homes (fast, no API calls)
2. Generates 80 OpenAI-enhanced homes:
   - Each call waits 3.3 seconds after completion
   - Automatic retry on rate limit errors
   - Total API time: ~4.4 minutes
3. Validates 32 template homes (10%):
   - Each validation waits 3.3 seconds after completion
   - Total validation time: ~1.7 minutes
4. **Total OpenAI API time:** ~6 minutes (safe, well below limits)

### With Batch Script (Windows)

```powershell
.\generate_400_homes.bat
```

Uses default rate limiting (20 RPM) automatically.

---

## Monitoring and Troubleshooting

### Check Rate Limits Before Running

```bash
python scripts/check_openai_rate_limits.py
```

This will show your current rate limits and recommendations.

### Watch for Rate Limit Warnings

The script will log:
- `⏳ Waiting 3.30s before next OpenAI API call...` - Normal throttling
- `⚠️ OpenAI API rate limit hit, will retry with exponential backoff` - Temporary issue (will retry)
- `❌ OpenAI API quota exceeded` - Permanent issue (requires account action)

### If You Hit Rate Limits

1. **Rate limit (temporary):** Script will automatically retry with backoff
2. **Quota exceeded:** Check your billing at https://platform.openai.com/account/billing
3. **Too many retries:** Lower `--rate-limit-rpm` and try again

---

## Cost Estimates (400 Homes, 20% Enhancement)

### OpenAI API Costs
- **80 enhanced homes:** ~$0.40-1.60
- **32 validations:** ~$0.10-0.40
- **Total:** ~$0.50-2.00

### Time Estimates (with 20 RPM rate limiting)

| Component | Time | Notes |
|-----------|------|-------|
| Template homes (320) | ~5-15 min | No API calls |
| OpenAI homes (80) | ~4.4 min | API calls only |
| Validations (32) | ~1.7 min | API calls only |
| Events (400 homes × 7 days) | ~2-4 hours | Local computation |
| **Total** | **~3-5 hours** | Most time is event generation |

---

## Best Practices

### 1. Start Conservative
- Use default 20 RPM unless you know your tier
- Increase RPM only if you've verified higher limits

### 2. Monitor During Generation
- Watch logs for rate limit warnings
- Check OpenAI dashboard for usage: https://platform.openai.com/usage

### 3. Adjust if Needed
- If you see many rate limit warnings: Lower RPM
- If generation is too slow: Verify limits and increase RPM cautiously

### 4. Check Quota Before Large Runs
- Visit: https://platform.openai.com/account/billing
- Ensure you have sufficient credits
- 400 homes with 20% enhancement: ~$0.50-2.00

---

## Files Modified

1. ✅ `src/training/synthetic_home_generator.py`
   - Added `rate_limit_rpm` parameter
   - Added automatic delays between API calls
   - Added rate limiting to validation calls

2. ✅ `scripts/generate_synthetic_homes.py`
   - Added `--rate-limit-rpm` command-line argument
   - Passes rate limit to generator

3. ✅ `generate_400_homes.bat`
   - Updated with rate limiting information
   - Uses default 20 RPM setting

---

## Summary

✅ **Automatic throttling** prevents rapid-fire requests  
✅ **Exponential backoff** handles temporary rate limits gracefully  
✅ **Quota detection** stops immediately on quota issues  
✅ **Configurable limits** allow adjustment for your account tier  
✅ **Applied everywhere** - all OpenAI calls respect rate limits  

**Result:** Safe generation of 400 homes without exceeding OpenAI thresholds!

---

**Last Updated:** December 2025  
**Status:** ✅ Production Ready

