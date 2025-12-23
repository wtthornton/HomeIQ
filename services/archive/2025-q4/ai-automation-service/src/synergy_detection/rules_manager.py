"""
Rules Management Utilities

Manages home layout rules: loading, adding, updating, and learning from feedback.

Phase 2: Real-World Rules Database
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import HomeLayoutRule
from .real_world_rules import REAL_WORLD_DEVICE_RULES

logger = logging.getLogger(__name__)


class RulesManager:
    """
    Manages home layout rules for spatial proximity validation.
    
    Provides methods to:
    - Load default rules from real_world_rules.py
    - Load home-specific rules from database
    - Add/update/delete user-defined rules
    - Learn rules from user feedback
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize rules manager.
        
        Args:
            db_session: Database session for rule operations
        """
        self.db_session = db_session
    
    async def load_default_rules(self) -> list[dict]:
        """
        Load default rules from real_world_rules.py.
        
        Returns:
            List of rule dictionaries ready for database insertion
        """
        rules = []
        
        # Convert door/lock rules
        door_rules = REAL_WORLD_DEVICE_RULES.get('door_lock_rules', {})
        for lock_type, rule_config in door_rules.items():
            # Create incompatible rules
            incompatible = rule_config.get('incompatible_lights', []) + \
                          rule_config.get('incompatible_sensors', [])
            
            for incompatible_device in incompatible:
                rules.append({
                    'home_id': 'default',
                    'rule_type': 'exclusion',
                    'device1_pattern': lock_type,
                    'device2_pattern': incompatible_device,
                    'relationship': 'incompatible',
                    'confidence': 1.0,
                    'source': 'system_default',
                    'metadata_json': {
                        'rationale': rule_config.get('rationale', '')
                    }
                })
        
        # Convert motion sensor rules
        motion_rules = REAL_WORLD_DEVICE_RULES.get('motion_sensor_rules', {})
        for motion_type, rule_config in motion_rules.items():
            incompatible = rule_config.get('incompatible_lights', [])
            
            for incompatible_device in incompatible:
                rules.append({
                    'home_id': 'default',
                    'rule_type': 'exclusion',
                    'device1_pattern': motion_type,
                    'device2_pattern': incompatible_device,
                    'relationship': 'incompatible',
                    'confidence': 1.0,
                    'source': 'system_default',
                    'metadata_json': {
                        'rationale': rule_config.get('rationale', '')
                    }
                })
        
        return rules
    
    async def load_home_rules(self, home_id: str = 'default') -> list[HomeLayoutRule]:
        """
        Load home-specific rules from database.
        
        Args:
            home_id: Home ID to load rules for (default: 'default')
            
        Returns:
            List of HomeLayoutRule objects
        """
        try:
            # Load rules for this home and default rules
            query = select(HomeLayoutRule).where(
                (HomeLayoutRule.home_id == home_id) | 
                (HomeLayoutRule.home_id == 'default')
            )
            
            result = await self.db_session.execute(query)
            rules = result.scalars().all()
            
            logger.info(f"Loaded {len(rules)} rules for home_id={home_id}")
            return list(rules)
        
        except Exception as e:
            logger.error(f"Failed to load home rules: {e}", exc_info=True)
            return []
    
    async def add_home_rule(
        self,
        home_id: str,
        rule_type: str,
        device1_pattern: str,
        device2_pattern: str,
        relationship: str,
        confidence: float = 1.0,
        source: str = 'user_defined',
        metadata: Optional[dict] = None
    ) -> HomeLayoutRule:
        """
        Add a new home layout rule.
        
        Args:
            home_id: Home ID
            rule_type: Type of rule ('proximity', 'adjacency', 'exclusion')
            device1_pattern: Pattern for first device (e.g., "front_door*")
            device2_pattern: Pattern for second device
            relationship: Relationship type ('compatible', 'incompatible', 'adjacent')
            confidence: Confidence score (0.0-1.0)
            source: Source of rule ('user_defined', 'learned', 'research', 'system_default')
            metadata: Optional metadata dictionary
            
        Returns:
            Created HomeLayoutRule object
        """
        rule = HomeLayoutRule(
            home_id=home_id,
            rule_type=rule_type,
            device1_pattern=device1_pattern,
            device2_pattern=device2_pattern,
            relationship=relationship,
            confidence=confidence,
            source=source,
            metadata_json=metadata or {}
        )
        
        self.db_session.add(rule)
        await self.db_session.commit()
        await self.db_session.refresh(rule)
        
        logger.info(f"Added home rule: {rule.id} for home_id={home_id}")
        return rule
    
    async def update_home_rule(
        self,
        rule_id: int,
        **kwargs
    ) -> Optional[HomeLayoutRule]:
        """
        Update an existing home layout rule.
        
        Args:
            rule_id: ID of rule to update
            **kwargs: Fields to update (rule_type, device1_pattern, etc.)
            
        Returns:
            Updated HomeLayoutRule object or None if not found
        """
        query = select(HomeLayoutRule).where(HomeLayoutRule.id == rule_id)
        result = await self.db_session.execute(query)
        rule = result.scalar_one_or_none()
        
        if not rule:
            logger.warning(f"Rule {rule_id} not found")
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        
        await self.db_session.commit()
        await self.db_session.refresh(rule)
        
        logger.info(f"Updated home rule: {rule_id}")
        return rule
    
    async def delete_home_rule(self, rule_id: int) -> bool:
        """
        Delete a home layout rule.
        
        Args:
            rule_id: ID of rule to delete
            
        Returns:
            True if deleted, False if not found
        """
        query = select(HomeLayoutRule).where(HomeLayoutRule.id == rule_id)
        result = await self.db_session.execute(query)
        rule = result.scalar_one_or_none()
        
        if not rule:
            logger.warning(f"Rule {rule_id} not found")
            return False
        
        await self.db_session.delete(rule)
        await self.db_session.commit()
        
        logger.info(f"Deleted home rule: {rule_id}")
        return True
    
    async def learn_from_feedback(
        self,
        home_id: str,
        device1: dict,
        device2: dict,
        user_rejected: bool
    ) -> Optional[HomeLayoutRule]:
        """
        Learn a rule from user feedback (rejection = incompatible).
        
        Args:
            home_id: Home ID
            device1: First device dict
            device2: Second device dict
            user_rejected: True if user rejected the suggestion
            
        Returns:
            Created HomeLayoutRule if learned, None otherwise
        """
        if not user_rejected:
            # Only learn from rejections (negative examples)
            return None
        
        # Extract patterns from device names/entity IDs
        name1 = device1.get('friendly_name', device1.get('entity_id', ''))
        name2 = device2.get('friendly_name', device2.get('entity_id', ''))
        entity_id1 = device1.get('entity_id', '')
        entity_id2 = device2.get('entity_id', '')
        
        # Create simple patterns (can be enhanced)
        pattern1 = name1.lower() or entity_id1.lower()
        pattern2 = name2.lower() or entity_id2.lower()
        
        # Check if rule already exists
        existing_query = select(HomeLayoutRule).where(
            HomeLayoutRule.home_id == home_id,
            HomeLayoutRule.device1_pattern == pattern1,
            HomeLayoutRule.device2_pattern == pattern2,
            HomeLayoutRule.relationship == 'incompatible'
        )
        result = await self.db_session.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Rule already exists, increase confidence
            existing.confidence = min(1.0, existing.confidence + 0.1)
            existing.updated_at = datetime.utcnow()
            await self.db_session.commit()
            logger.info(f"Updated learned rule confidence: {existing.id}")
            return existing
        
        # Create new learned rule
        rule = await self.add_home_rule(
            home_id=home_id,
            rule_type='exclusion',
            device1_pattern=pattern1,
            device2_pattern=pattern2,
            relationship='incompatible',
            confidence=0.7,  # Start with lower confidence for learned rules
            source='learned',
            metadata={
                'learned_from': 'user_feedback',
                'device1_name': name1,
                'device2_name': name2
            }
        )
        
        logger.info(f"Learned new rule from feedback: {rule.id}")
        return rule

