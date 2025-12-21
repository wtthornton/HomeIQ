# Energy Pricing Models

**Last Updated**: December 2025  
**Status**: Current for 2025 energy market conditions

## Pricing Model Types

### 1. Time-of-Use (TOU) Pricing

**Definition**: Electricity price varies by time of day.

**Common Structures**:
- **Peak**: High price during high-demand hours (e.g., 4-9 PM weekdays)
- **Off-Peak**: Low price during low-demand hours (e.g., 10 PM-6 AM)
- **Mid-Peak**: Moderate price during transition hours

**Typical Rates (2025)**:
- Peak: $0.25-0.45/kWh (varies by region and utility)
- Mid-Peak: $0.15-0.30/kWh
- Off-Peak: $0.08-0.18/kWh
- Note: Rates vary significantly by region, utility, and time of year

**Optimization Strategy**: Shift usage to off-peak hours when possible.

### 2. Real-Time Pricing (RTP)

**Definition**: Electricity price changes throughout the day based on market conditions.

**Price Updates**: Hourly or sub-hourly updates based on supply/demand.

**Typical Range (2025)**: $0.05-0.60/kWh (varies significantly by market conditions, region, and time)

**Optimization Strategy**: Use price forecasts to pre-schedule high-energy tasks during low-price periods.

### 3. Tiered Pricing

**Definition**: Price increases as usage increases (tiers).

**Common Structure**:
- Tier 1 (0-500 kWh): Base rate (e.g., $0.12/kWh)
- Tier 2 (501-1000 kWh): Higher rate (e.g., $0.15/kWh)
- Tier 3 (1000+ kWh): Highest rate (e.g., $0.20/kWh)

**Optimization Strategy**: Stay within lower tiers to avoid higher rates.

### 4. Flat Rate Pricing

**Definition**: Constant price regardless of time or usage level.

**Typical Rate (2025)**: $0.12-0.18/kWh (varies by region and utility)

**Optimization Strategy**: Focus on reducing total consumption rather than timing.

## Pricing Optimization Strategies

### Load Shifting

**Strategy**: Move energy-intensive tasks to lower-price periods.

**Examples**:
- Run dishwasher during off-peak hours
- Pre-cool/pre-heat during low-price periods
- Charge EV during off-peak hours
- Delay laundry to off-peak periods

**Savings Potential**: 20-40% on shifted loads

### Peak Shaving

**Strategy**: Reduce consumption during peak pricing periods.

**Methods**:
- Reduce heating/cooling during peak
- Defer non-essential tasks
- Use battery storage during peak
- Pre-cool/pre-heat before peak

**Savings Potential**: $50-200/month depending on usage

### Energy Arbitrage

**Strategy**: Buy energy when cheap, use stored energy when expensive.

**Requirements**: Battery storage system

**Example**: Charge battery during $0.08/kWh off-peak, discharge during $0.30/kWh peak.

**Savings Potential**: $0.22/kWh difference × battery capacity

## Demand Response Programs

### Program Types

**1. Price-Based Programs**:
- Users respond to price signals
- Voluntary participation
- Savings through load shifting

**2. Incentive-Based Programs**:
- Utilities pay users to reduce demand during events
- Event-based reductions
- Typically $0.50-2.00/kWh incentive

**3. Capacity Programs**:
- Long-term commitment to reduce demand
- Monthly capacity payments
- Requires reliable reduction capability

### Participation Benefits

**Financial**:
- Direct payments for reductions
- Lower energy bills through optimization
- Potential equipment incentives

**Environmental**:
- Reduced grid stress
- Support for renewable energy integration
- Lower carbon emissions

## Cost Calculation

### Basic Calculation

**Formula**: Cost = Usage (kWh) × Price per kWh

**Example**: 100 kWh × $0.15/kWh = $15.00

### Time-Varying Calculation

**Formula**: Cost = Σ(Usage_hour × Price_hour)

**Example**:
- 50 kWh at $0.10/kWh (off-peak) = $5.00
- 30 kWh at $0.25/kWh (peak) = $7.50
- 20 kWh at $0.15/kWh (mid-peak) = $3.00
- Total: $15.50

### Tiered Calculation

**Formula**: Cost = Tier1_usage × Tier1_rate + Tier2_usage × Tier2_rate + ...

**Example** (using 800 kWh total):
- Tier 1: 500 kWh × $0.12 = $60.00
- Tier 2: 300 kWh × $0.15 = $45.00
- Total: $105.00

## ROI Analysis for Energy Optimization

### Simple Payback Period

**Formula**: Payback Period = Investment Cost / Annual Savings

**Example (2025)**:
- Smart thermostat cost: $200-250 (typical range in 2025)
- Annual energy savings: $80-120 (varies by usage and region)
- Payback period: $200 / $100 = 2 years (typical)

### Annual Savings Calculation

**Components**:
- Usage reduction (kWh saved)
- Price optimization (load shifting savings)
- Demand response income (if participating)

**Example**:
- 500 kWh/year saved × $0.15/kWh = $75
- Load shifting savings = $50/year
- Demand response income = $25/year
- Total annual savings: $150

### Lifecycle Value

**Calculation**: (Annual Savings × Years) - Initial Investment

**Example** (10-year lifecycle):
- Annual savings: $150
- 10-year savings: $1,500
- Initial investment: $200
- Net value: $1,300

