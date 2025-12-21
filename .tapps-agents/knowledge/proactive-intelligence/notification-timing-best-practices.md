# Notification Timing Best Practices

**Last Updated**: December 2025  
**Status**: Current notification timing strategies for 2025

## Timing Principles

### 1. Right Time, Right Context

**Principle**: Notifications should arrive when user is ready and context is relevant.

**Why it matters**: Well-timed notifications have 3-5x higher engagement rates than poorly timed ones.

**Timing Factors**:
- **User availability**: When user is likely to engage
- **Context relevance**: When suggestion context is most relevant
- **Urgency**: Time-sensitive vs. can-wait suggestions
- **User preferences**: Respect user's notification preferences

### 2. Avoid Interruption

**Principle**: Don't interrupt users unless suggestion is urgent or highly relevant.

**Why it matters**: Interruptions reduce user satisfaction and increase notification fatigue.

**Interruption Thresholds**:
- **High urgency**: Energy cost spike, security alert → Interrupt OK
- **Medium urgency**: Pattern suggestion, optimization → Batch or schedule
- **Low urgency**: Feature discovery, weekly summary → Batch only

### 3. Respect User Rhythms

**Principle**: Adapt to user's daily and weekly patterns.

**Why it matters**: Users have natural rhythms for reviewing information. Respecting these improves engagement.

**Rhythm Patterns**:
- **Morning**: Review and planning (good for suggestions)
- **Midday**: Focused work (avoid unless urgent)
- **Evening**: Relaxation and reflection (good for suggestions)
- **Weekends**: More time, less urgency

## Optimal Timing Windows

### Daily Timing Windows

**High Engagement Windows**:
- **7:00-9:00 AM**: Morning routine, reviewing day
- **6:00-8:00 PM**: Evening, winding down, open to improvements
- **Weekend mornings (9:00-11:00 AM)**: Leisure time, high engagement

**Medium Engagement Windows**:
- **12:00-1:00 PM**: Lunch break, quick reviews
- **5:00-6:00 PM**: End of workday, transition time
- **Weekend afternoons**: Available but less focused

**Low Engagement Windows** (Avoid):
- **Before 7:00 AM**: Too early, users rushed
- **9:00 AM-5:00 PM weekdays**: Work hours, users distracted
- **After 10:00 PM**: Too late, users tired
- **During meals**: Interrupts social time

### Contextual Timing

**Weather-Based Timing**:
- **Before weather events**: Suggest preemptive actions (e.g., "Rain expected in 2 hours, close windows?")
- **During weather events**: Immediate context suggestions (e.g., "It's cloudy now, turn on lights?")

**Energy Pricing Timing**:
- **Before peak pricing**: Suggest preemptive actions (e.g., "Prices spike at 2 PM, pre-cool now?")
- **During low pricing**: Suggest energy-intensive tasks (e.g., "Prices are low, good time to run dishwasher")

**Time-of-Day Patterns**:
- **Morning**: Routine suggestions (e.g., "Daily pattern detected, automate?")
- **Evening**: Reflection suggestions (e.g., "Today's energy usage summary")
- **Night**: Next-day planning (e.g., "Tomorrow's forecast suggests...")

## Notification Frequency

### Frequency Guidelines

**Daily Maximums**:
- **Urgent notifications**: 1-2 per day (energy spikes, security)
- **Regular suggestions**: 2-3 per day (patterns, optimizations)
- **Feature discoveries**: 1 per day
- **Total proactive**: 3-5 per day maximum

**Weekly Patterns**:
- **Monday**: Weekly summary + new week patterns
- **Mid-week**: Optimization suggestions
- **Friday**: Weekend preparation suggestions
- **Weekend**: Feature discoveries, less urgent suggestions

**Batching Strategy**:
- **Urgent**: Send immediately (1-2 per day)
- **Regular**: Batch in daily summary (2-3 per day)
- **Low priority**: Weekly summary (5-10 per week)

### Frequency Tuning

**High-Engagement Users**:
- Can handle 5-7 suggestions per day
- More frequent feature discoveries
- Real-time context suggestions

**Medium-Engagement Users**:
- 3-5 suggestions per day optimal
- Daily batch summary
- Less frequent feature discoveries

**Low-Engagement Users**:
- 1-2 suggestions per day maximum
- Weekly summary preferred
- Only high-value suggestions

## Notification Channels

### Channel Selection

**Push Notifications** (Mobile):
- **Use for**: Urgent, time-sensitive suggestions
- **Examples**: Energy price spikes, security alerts, weather changes
- **Frequency**: 1-2 per day maximum
- **Requirements**: User opt-in required

**In-App Notifications**:
- **Use for**: Regular suggestions, can review when convenient
- **Examples**: Pattern suggestions, optimization opportunities
- **Frequency**: 3-5 per day
- **Persistence**: Until dismissed

**Email Summaries**:
- **Use for**: Non-urgent suggestions, batch delivery
- **Examples**: Weekly summaries, feature discoveries
- **Frequency**: Daily or weekly
- **Format**: Digest with links to review

**Dashboard Widgets**:
- **Use for**: Persistent display, always available
- **Examples**: Suggestion count, quick access
- **Frequency**: Real-time updates
- **Visibility**: Always visible when dashboard open

### Channel Preferences

**User Preferences**:
- Allow users to choose notification channels
- Respect "do not disturb" settings
- Provide channel-specific preferences
- Allow time-based channel rules (e.g., email only during work hours)

**Default Strategy**:
- **Urgent**: Push notification
- **Regular**: In-app notification
- **Low priority**: Email summary
- **Persistent**: Dashboard widget

## Timing Optimization

### A/B Testing

**Test Variables**:
- Time of day (morning vs evening)
- Day of week (weekday vs weekend)
- Frequency (1 vs 3 vs 5 per day)
- Channel (push vs in-app vs email)

**Metrics to Track**:
- Engagement rate (open/click rate)
- Approval rate
- Time to review
- User satisfaction

**Optimization Process**:
1. Test different timing strategies
2. Measure engagement metrics
3. Identify optimal timing
4. Apply winning strategy
5. Continue testing and refining

### Learning from User Behavior

**Behavioral Signals**:
- **High engagement**: User reviews suggestions quickly → Can increase frequency
- **Low engagement**: User ignores suggestions → Reduce frequency
- **Timing preferences**: User reviews at specific times → Schedule for those times
- **Channel preferences**: User engages more with certain channels → Prioritize those channels

**Adaptive Timing**:
- Learn user's preferred review times
- Adapt notification timing to user patterns
- Respect user's "busy" periods
- Increase frequency for high-engagement users

## Anti-Patterns

### Timing Anti-Patterns

**1. Too Frequent**
- Sending >5 suggestions per day
- Multiple notifications in short time
- **Impact**: Notification fatigue, reduced engagement

**2. Poor Timing**
- Late night notifications (after 10 PM)
- During work hours for non-urgent items
- During meals or social time
- **Impact**: User annoyance, ignored suggestions

**3. No Batching**
- Sending each suggestion individually
- Not grouping related suggestions
- **Impact**: Notification overload, reduced engagement

**4. Ignoring User Preferences**
- Not respecting "do not disturb"
- Not learning from user behavior
- **Impact**: User frustration, opt-out

**5. Same Time Always**
- Fixed schedule regardless of context
- Not adapting to user patterns
- **Impact**: Missed optimal engagement windows

### Best Practices

**Do**:
- Batch non-urgent suggestions
- Respect user's notification preferences
- Learn optimal timing from user behavior
- Use contextual timing when relevant
- Provide clear notification controls

**Don't**:
- Send notifications too frequently
- Interrupt users unnecessarily
- Ignore user preferences
- Use fixed schedules rigidly
- Send during inappropriate times

