"""
User Profile Builder - Phase 3 Improvement

Builds user profiles from feedback and usage patterns to personalize suggestions:
- Preferred categories (energy, security, convenience, comfort)
- Preferred devices
- Time preferences (morning, afternoon, evening, night)
- Complexity preferences (simple, medium, advanced)
- Automation style preferences
"""

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Suggestion, UserFeedback

logger = logging.getLogger(__name__)


class UserProfileBuilder:
    """
    Builds user profiles from feedback and usage patterns.
    
    Phase 3 improvement: Learn user preferences to personalize suggestions.
    """

    def __init__(self):
        """Initialize user profile builder."""
        logger.info("UserProfileBuilder initialized")

    async def build_user_profile(
        self,
        db: AsyncSession,
        user_id: str = 'default'
    ) -> dict[str, Any]:
        """
        Build comprehensive user profile from feedback and suggestions.
        
        Args:
            db: Database session
            user_id: User identifier (default: 'default' for single-home)
        
        Returns:
            User profile dictionary with preferences
        """
        profile = {
            'user_id': user_id,
            'preferred_categories': {},
            'preferred_devices': {},
            'time_preferences': {},
            'complexity_preference': 'medium',
            'automation_style': 'balanced',
            'total_approvals': 0,
            'total_rejections': 0,
            'approval_rate': 0.0,
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

        try:
            # 1. Analyze feedback patterns
            feedback_stats = await self._analyze_feedback_patterns(db, user_id)
            profile.update(feedback_stats)

            # 2. Analyze approved suggestions
            approved_prefs = await self._analyze_approved_suggestions(db, user_id)
            profile['preferred_categories'] = approved_prefs.get('categories', {})
            profile['preferred_devices'] = approved_prefs.get('devices', {})
            profile['time_preferences'] = approved_prefs.get('time_preferences', {})

            # 3. Determine complexity preference
            profile['complexity_preference'] = await self._determine_complexity_preference(db, user_id)

            # 4. Determine automation style
            profile['automation_style'] = await self._determine_automation_style(db, user_id)

            logger.info(f"✅ Built user profile for {user_id}: {len(profile['preferred_categories'])} categories, {len(profile['preferred_devices'])} devices")
            
        except Exception as e:
            logger.warning(f"Failed to build user profile: {e}")
            # Return default profile on error

        return profile

    async def _analyze_feedback_patterns(
        self,
        db: AsyncSession,
        user_id: str
    ) -> dict[str, Any]:
        """Analyze user feedback to determine approval patterns."""
        stats = {
            'total_approvals': 0,
            'total_rejections': 0,
            'approval_rate': 0.0
        }

        try:
            # Get all feedback (for single-home, user_id is 'default')
            # Join with suggestions to get category/device info
            query = (
                select(
                    UserFeedback.action,
                    Suggestion.category,
                    Suggestion.priority,
                    func.count(UserFeedback.id).label('count')
                )
                .join(Suggestion, UserFeedback.suggestion_id == Suggestion.id)
                .group_by(UserFeedback.action, Suggestion.category, Suggestion.priority)
            )

            result = await db.execute(query)
            rows = result.all()

            approvals = 0
            rejections = 0

            for action, category, priority, count in rows:
                if action == 'approved':
                    approvals += count
                elif action == 'rejected':
                    rejections += count

            stats['total_approvals'] = approvals
            stats['total_rejections'] = rejections
            
            total = approvals + rejections
            if total > 0:
                stats['approval_rate'] = approvals / total

        except Exception as e:
            logger.warning(f"Failed to analyze feedback patterns: {e}")

        return stats

    async def _analyze_approved_suggestions(
        self,
        db: AsyncSession,
        user_id: str
    ) -> dict[str, Any]:
        """Analyze approved suggestions to determine preferences."""
        preferences = {
            'categories': {},
            'devices': {},
            'time_preferences': {}
        }

        try:
            # Get approved suggestions (those with approved feedback)
            query = (
                select(Suggestion)
                .join(UserFeedback, Suggestion.id == UserFeedback.suggestion_id)
                .where(UserFeedback.action == 'approved')
                .order_by(Suggestion.created_at.desc())
                .limit(100)  # Analyze last 100 approved
            )

            result = await db.execute(query)
            suggestions = result.scalars().all()

            category_counts = Counter()
            device_counts = Counter()
            hour_counts = Counter()

            for suggestion in suggestions:
                # Category preferences
                if suggestion.category:
                    category_counts[suggestion.category] += 1

                # Device preferences (from device_id or devices_involved)
                if suggestion.device_id:
                    device_counts[suggestion.device_id] += 1
                if suggestion.devices_involved:
                    for device in suggestion.devices_involved:
                        if isinstance(device, str):
                            device_counts[device] += 1

                # Time preferences (from created_at hour - when user approved)
                if suggestion.approved_at:
                    hour = suggestion.approved_at.hour
                    # Categorize into time periods
                    if 6 <= hour < 12:
                        hour_counts['morning'] += 1
                    elif 12 <= hour < 17:
                        hour_counts['afternoon'] += 1
                    elif 17 <= hour < 22:
                        hour_counts['evening'] += 1
                    else:
                        hour_counts['night'] += 1

            # Normalize to 0-1 scores
            total = len(suggestions)
            if total > 0:
                preferences['categories'] = {
                    cat: count / total
                    for cat, count in category_counts.items()
                }
                preferences['devices'] = {
                    device: count / total
                    for device, count in device_counts.most_common(10).items()
                }
                preferences['time_preferences'] = {
                    period: count / total
                    for period, count in hour_counts.items()
                }

        except Exception as e:
            logger.warning(f"Failed to analyze approved suggestions: {e}")

        return preferences

    async def _determine_complexity_preference(
        self,
        db: AsyncSession,
        user_id: str
    ) -> str:
        """Determine user's preferred automation complexity."""
        try:
            # Analyze approved suggestions by priority (high = complex, low = simple)
            query = (
                select(Suggestion.priority, func.count(Suggestion.id).label('count'))
                .join(UserFeedback, Suggestion.id == UserFeedback.suggestion_id)
                .where(UserFeedback.action == 'approved')
                .group_by(Suggestion.priority)
            )

            result = await db.execute(query)
            rows = result.all()

            priority_counts = {row[0]: row[1] for row in rows if row[0]}

            if not priority_counts:
                return 'medium'  # Default

            # Determine preference
            high_count = priority_counts.get('high', 0)
            medium_count = priority_counts.get('medium', 0)
            low_count = priority_counts.get('low', 0)

            total = high_count + medium_count + low_count
            if total == 0:
                return 'medium'

            high_ratio = high_count / total
            low_ratio = low_count / total

            if high_ratio > 0.4:
                return 'advanced'
            elif low_ratio > 0.4:
                return 'simple'
            else:
                return 'medium'

        except Exception as e:
            logger.warning(f"Failed to determine complexity preference: {e}")
            return 'medium'

    async def _determine_automation_style(
        self,
        db: AsyncSession,
        user_id: str
    ) -> str:
        """Determine user's automation style (conservative, balanced, aggressive)."""
        try:
            # Analyze approval rate and suggestion types
            # Extract source_type from JSON suggestion_metadata field (renamed from metadata to avoid SQLAlchemy conflict)
            # Handle case where suggestion_metadata column doesn't exist yet (graceful fallback)
            try:
                source_type_expr = func.json_extract(Suggestion.suggestion_metadata, '$.source_type').label('source_type')
                query = (
                    select(
                        UserFeedback.action,
                        source_type_expr,
                        func.count(UserFeedback.id).label('count')
                    )
                    .join(Suggestion, UserFeedback.suggestion_id == Suggestion.id)
                    .group_by(UserFeedback.action, source_type_expr)
                )
            except (AttributeError, Exception) as col_error:
                # Column doesn't exist yet - use default 'pattern' for all suggestions
                logger.debug(f"suggestion_metadata column not found, using default source_type: {col_error}")
                query = (
                    select(
                        UserFeedback.action,
                        func.literal('pattern').label('source_type'),  # Default to pattern
                        func.count(UserFeedback.id).label('count')
                    )
                    .join(Suggestion, UserFeedback.suggestion_id == Suggestion.id)
                    .group_by(UserFeedback.action)
                )

            result = await db.execute(query)
            rows = result.all()

            # Count approvals by source type
            source_approvals = defaultdict(int)
            total_approvals = 0

            for action, source_type, count in rows:
                if action == 'approved':
                    source_approvals[source_type or 'pattern'] += count
                    total_approvals += count

            if total_approvals == 0:
                return 'balanced'  # Default

            # Conservative: mostly pattern-based, high confidence
            # Balanced: mix of sources
            # Aggressive: many predictive/cascade, lower confidence OK

            pattern_ratio = source_approvals.get('pattern', 0) / total_approvals
            predictive_ratio = source_approvals.get('predictive', 0) / total_approvals
            cascade_ratio = source_approvals.get('cascade', 0) / total_approvals

            if pattern_ratio > 0.7:
                return 'conservative'
            elif predictive_ratio + cascade_ratio > 0.4:
                return 'aggressive'
            else:
                return 'balanced'

        except Exception as e:
            logger.warning(f"Failed to determine automation style: {e}")
            return 'balanced'

    def calculate_preference_match(
        self,
        suggestion: dict[str, Any],
        user_profile: dict[str, Any]
    ) -> float:
        """
        Calculate how well a suggestion matches user preferences.
        
        Args:
            suggestion: Suggestion dictionary
            user_profile: User profile dictionary
        
        Returns:
            Match score (0.0-1.0)
        """
        score = 0.0
        factors = 0

        # Category match
        category = suggestion.get('category')
        if category and user_profile.get('preferred_categories'):
            category_score = user_profile['preferred_categories'].get(category, 0.0)
            score += category_score * 0.3
            factors += 0.3

        # Device match
        device_id = suggestion.get('device_id')
        if device_id and user_profile.get('preferred_devices'):
            device_score = user_profile['preferred_devices'].get(device_id, 0.0)
            score += device_score * 0.2
            factors += 0.2

        # Priority/complexity match
        priority = suggestion.get('priority', 'medium')
        complexity_pref = user_profile.get('complexity_preference', 'medium')
        if (priority == 'high' and complexity_pref == 'advanced') or \
           (priority == 'low' and complexity_pref == 'simple') or \
           (priority == 'medium' and complexity_pref == 'medium'):
            score += 0.2
        factors += 0.2

        # Source type match (based on automation style)
        source_type = suggestion.get('metadata', {}).get('source_type', 'pattern')
        automation_style = user_profile.get('automation_style', 'balanced')
        
        if automation_style == 'conservative' and source_type == 'pattern':
            score += 0.3
        elif automation_style == 'aggressive' and source_type in ['predictive', 'cascade']:
            score += 0.3
        elif automation_style == 'balanced':
            score += 0.15  # Neutral
        factors += 0.3

        # Normalize score
        if factors > 0:
            return min(1.0, score / factors)
        return 0.5  # Default neutral score

