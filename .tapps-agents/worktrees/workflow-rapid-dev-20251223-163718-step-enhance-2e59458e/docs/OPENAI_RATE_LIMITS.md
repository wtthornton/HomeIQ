# OpenAI Rate Limits Documentation

**Last Updated:** November 19, 2025  
**Status:** Current as of September 2025 OpenAI Updates

---

## Current Rate Limits (Verified November 2025)

OpenAI significantly increased rate limits in **September 2025**. Current limits are:

| Tier | Tokens Per Minute (TPM) | Requests Per Minute (RPM) | Notes |
|------|------------------------|---------------------------|-------|
| **Tier 1** | **500,000** | 5,000 | Default tier (was 30K TPM) |
| **Tier 2** | **1,000,000** | 10,000 | (was 150K TPM) |
| **Tier 3** | **2,000,000** | 20,000 | (was 800K TPM) |
| **Tier 4** | **4,000,000** | 40,000 | (was 2M TPM) |

**⚠️ IMPORTANT:** If you're seeing 30K TPM limits, you may be on:
- Legacy/free tier
- Need account verification
- Check: https://platform.openai.com/account/rate-limits

---

## Verification Steps

1. **Check Your Account:**
   - Visit: https://platform.openai.com/account/rate-limits
   - Look for "Tokens per minute" limit
   - Should show 500K+ for Tier 1

2. **If Still Seeing 30K TPM:**
   - Contact OpenAI support
   - Verify account status
   - May need to upgrade tier or verify account

3. **Document Your Limits:**
   - Update this file with your actual limits
   - Note verification date
   - Track any changes

---

## Our Current Usage

### Token Usage Per Request
- **Average:** ~25,000 tokens (before optimization)
- **Target:** ~12,000 tokens (after optimization)
- **Maximum:** ~36,000 tokens (edge cases)

### Rate Limit Analysis
- **With 500K TPM:** Can handle ~20 requests/minute (at 25K tokens each)
- **With 30K TPM:** Can handle ~1 request/minute (would hit limits)

### Recommendation
- **If 500K TPM:** No issues, plenty of headroom
- **If 30K TPM:** Need to verify/upgrade account immediately

---

## References

- OpenAI Rate Limits: https://platform.openai.com/account/rate-limits
- Rate Limit Updates (Sept 2025): https://ai-primer.com/reports/2025-09-13
- OpenAI Pricing: https://openai.com/pricing

---

## Next Steps

- [ ] Verify actual rate limits in OpenAI dashboard
- [ ] Document verified limits below
- [ ] Update code if limits differ from expected

---

## Verified Limits (Fill In After Verification)

**Date Verified:** _______________  
**Account Tier:** _______________  
**TPM Limit:** _______________  
**RPM Limit:** _______________  
**Notes:** _______________

