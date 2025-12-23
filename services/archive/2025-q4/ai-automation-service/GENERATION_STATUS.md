# 400 Home Generation Status

**Started:** December 2, 2025  
**Status:** ⏸️ Stopped and Cleaned Up

## Configuration

- **Total Homes:** 400
- **Days per Home:** 30 days of events
- **OpenAI Enhancement:** Disabled (template-based only)
- **External Data:** All enabled
  - ✅ Weather data
  - ✅ Carbon intensity
  - ✅ Electricity pricing
  - ✅ Calendar events
- **Output Directory:** `tests/datasets/synthetic_homes_400`

## Expected Output

### Per Home (Average)
- **Areas:** 10-15 areas
- **Devices:** 20-50 devices
- **Events:** ~15,000-30,000 events (30 days)
- **Weather:** 720 points (30 days × 24 hours)
- **Carbon:** 2,880 points (30 days × 96 intervals)
- **Pricing:** 720 points (30 days × 24 hours)
- **Calendar:** ~150-200 events

### Total (400 Homes)
- **Total Areas:** ~4,000-6,000
- **Total Devices:** ~8,000-20,000
- **Total Events:** ~6,000,000-12,000,000
- **Total Weather Points:** ~288,000
- **Total Carbon Points:** ~1,152,000
- **Total Pricing Points:** ~288,000
- **Total Calendar Events:** ~60,000-80,000

## Time Estimates

- **Template Generation:** ~10-20 minutes (400 homes)
- **Event Generation:** ~5-10 hours (30 days × 400 homes)
- **External Data:** ~1-2 hours
- **Total Estimated Time:** ~6-12 hours

## Progress Tracking

Check progress with:
```powershell
Get-ChildItem tests/datasets/synthetic_homes_400/home_*.json | Measure-Object | Select-Object -ExpandProperty Count
```

## Cleanup Status

- ✅ Test data cleaned up
- ✅ Ready for fresh generation

---

**Note:** Generation is running in the background. Monitor progress by checking the output directory.

