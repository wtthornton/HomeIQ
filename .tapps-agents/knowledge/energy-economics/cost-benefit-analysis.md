# Energy Cost-Benefit Analysis

**Last Updated**: December 2025  
**Status**: Current analysis methods and frameworks for 2025

## Analysis Framework

### Cost Components

**1. Initial Investment**:
- Device/equipment costs
- Installation costs
- Setup/configuration time

**2. Ongoing Costs**:
- Energy consumption of device itself
- Maintenance costs
- Subscription fees (if any)
- Time for optimization/maintenance

**3. Opportunity Costs**:
- Alternative uses of investment
- Time spent on setup/maintenance

### Benefit Components

**1. Direct Energy Savings**:
- Reduced energy consumption (kWh saved)
- Lower energy costs (dollar savings)
- Load shifting benefits (price optimization)

**2. Indirect Benefits**:
- Increased comfort/convenience
- Reduced maintenance (longer device life)
- Environmental benefits (carbon reduction)
- Time savings (automation)

**3. Additional Income**:
- Demand response program payments
- Utility rebates/incentives
- Tax credits (where applicable)

## Calculation Methods

### Simple Payback Analysis

**Formula**: Payback Period = Initial Investment / Annual Savings

**Use Case**: Quick assessment of investment viability

**Decision Rule**: Accept if payback period < acceptable threshold (typically 3-5 years)

**Example**:
- Smart thermostat: $200 investment
- Annual savings: $80
- Payback: 2.5 years ✅

### Net Present Value (NPV)

**Formula**: NPV = Σ(Cash Flow_t / (1 + r)^t) - Initial Investment

Where:
- Cash Flow_t = Annual savings in year t
- r = Discount rate (typically 5-10%)
- t = Year number

**Use Case**: More sophisticated analysis considering time value of money

**Decision Rule**: Accept if NPV > 0

### Internal Rate of Return (IRR)

**Definition**: Discount rate at which NPV = 0

**Use Case**: Compare returns across different investments

**Decision Rule**: Accept if IRR > required rate of return

### Cost per kWh Saved

**Formula**: Cost per kWh Saved = Annual Cost / Annual kWh Saved

**Use Case**: Compare efficiency of different energy-saving measures

**Benchmark**: Utility generation cost (~$0.05-0.10/kWh)

**Example**:
- Programmable thermostat: $10/year / 500 kWh saved = $0.02/kWh saved ✅

## Analysis Examples

### Example 1: Smart Thermostat

**Costs**:
- Device: $200 (one-time)
- Installation: $50 (one-time)
- Annual maintenance: $0 (negligible)
- Energy usage: 2 kWh/year × $0.15/kWh = $0.30/year

**Benefits**:
- Energy savings: 600 kWh/year × $0.15/kWh = $90/year
- Comfort improvement: $20/year (estimated value)
- Time savings: $10/year (estimated value)

**Analysis**:
- Initial investment: $250
- Annual savings: $90 + $20 + $10 - $0.30 = $119.70
- Simple payback: $250 / $119.70 = 2.1 years ✅
- 10-year NPV (5% discount): $670

### Example 2: Smart Lighting

**Costs**:
- Smart bulbs (10 bulbs): $150 (one-time)
- Setup time: 1 hour × $25/hour = $25 (one-time)
- Annual energy: 50 kWh/year × $0.15/kWh = $7.50/year

**Benefits**:
- Energy savings: 400 kWh/year × $0.15/kWh = $60/year
- Convenience value: $30/year (estimated)
- Longevity: $10/year (longer bulb life)

**Analysis**:
- Initial investment: $175
- Annual savings: $60 + $30 + $10 - $7.50 = $92.50
- Simple payback: $175 / $92.50 = 1.9 years ✅

### Example 3: Battery Storage System

**Costs**:
- System: $10,000 (one-time)
- Installation: $2,000 (one-time)
- Annual maintenance: $100/year
- Energy losses: 200 kWh/year × $0.15/kWh = $30/year

**Benefits**:
- Load shifting savings: $300/year
- Demand response income: $200/year
- Backup power value: $100/year (estimated)
- Peak shaving: $150/year

**Analysis**:
- Initial investment: $12,000
- Annual savings: $300 + $200 + $100 + $150 - $100 - $30 = $620
- Simple payback: $12,000 / $620 = 19.4 years ❌
- Note: May be viable with higher utility rates or incentives

## Decision Criteria

### Minimum Viable ROI

**Thresholds**:
- Simple payback: <5 years
- Cost per kWh saved: <$0.10/kWh
- NPV (10 years, 5% discount): >0

### Risk Considerations

**Low Risk** (High confidence in savings):
- Proven technologies
- Predictable savings
- Low initial investment

**Medium Risk** (Moderate confidence):
- Newer technologies
- Variable savings potential
- Moderate investment

**High Risk** (Lower confidence):
- Experimental technologies
- Uncertain savings
- High investment

**Adjustment**: Require higher returns for higher risk investments

## Best Practices

### Comprehensive Analysis

**Include**:
- All costs (initial, ongoing, opportunity)
- All benefits (direct, indirect, qualitative)
- Uncertainty ranges
- Sensitivity analysis

### Conservative Estimates

**Savings**: Use conservative estimates (lower end of range)
**Costs**: Use realistic estimates (higher end of range)
**Result**: More reliable decision-making

### Regular Review

**Update**:
- Actual vs. estimated savings
- Changing energy prices
- New optimization opportunities
- Technology improvements

**Benefit**: Continuous improvement and optimization

