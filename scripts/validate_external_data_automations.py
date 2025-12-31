#!/usr/bin/env python3
"""
Validate External Data Patterns Against Home Assistant Automations

Checks if external data entities (sports, weather, calendar) are used in
Home Assistant automations. Only patterns involving external data that are
actually used in automations should be considered valid.
"""

import asyncio
import json
import logging
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

import httpx

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# External data entity patterns
EXTERNAL_DATA_PATTERNS = {
    'sports': [
        'sensor.team_tracker_',
        'sensor.nfl_',
        'sensor.nhl_',
        'sensor.mlb_',
        'sensor.nba_',
        '_tracker',
    ],
    'weather': [
        'weather.',
        'sensor.weather_',
        'sensor.openweathermap_',
    ],
    'calendar': [
        'calendar.',
        'sensor.calendar_',
    ],
    'energy': [
        'sensor.carbon_intensity_',
        'sensor.electricity_pricing_',
        'sensor.national_grid_',
    ],
}


class AutomationEntityExtractor:
    """Extract entity IDs from Home Assistant automations."""
    
    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url.rstrip('/')
        self.ha_token = ha_token
        self.headers = {
            'Authorization': f'Bearer {ha_token}',
            'Content-Type': 'application/json',
        }
    
    async def get_automations(self) -> List[Dict[str, Any]]:
        """Fetch all automations from Home Assistant."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.ha_url}/api/config/automation/config",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    automations = response.json()
                    logger.info(f"Fetched {len(automations)} automations from Home Assistant")
                    return automations
                else:
                    logger.warning(f"Failed to fetch automations: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching automations: {e}")
            return []
    
    def extract_entities_from_automation(self, automation: Dict[str, Any]) -> Set[str]:
        """
        Extract all entity IDs from an automation.
        
        Checks triggers, conditions, and actions.
        """
        entities = set()
        
        # Extract from triggers
        triggers = automation.get('trigger', [])
        for trigger in triggers:
            entities.update(self._extract_entities_from_section(trigger))
        
        # Extract from conditions
        conditions = automation.get('condition', [])
        for condition in conditions:
            entities.update(self._extract_entities_from_section(condition))
        
        # Extract from actions
        actions = automation.get('action', [])
        for action in actions:
            entities.update(self._extract_entities_from_section(action))
        
        return entities
    
    def _extract_entities_from_section(self, section: Dict[str, Any]) -> Set[str]:
        """Extract entity IDs from a trigger/condition/action section."""
        entities = set()
        
        # Direct entity_id field
        entity_id = section.get('entity_id')
        if entity_id:
            if isinstance(entity_id, str):
                entities.add(entity_id)
            elif isinstance(entity_id, list):
                entities.update(entity_id)
        
        # Target entity_id (for actions)
        target = section.get('target', {})
        if isinstance(target, dict):
            target_entity_id = target.get('entity_id')
            if target_entity_id:
                if isinstance(target_entity_id, str):
                    entities.add(target_entity_id)
                elif isinstance(target_entity_id, list):
                    entities.update(target_entity_id)
        
        # Service entity_id (for service calls)
        service_data = section.get('service_data', {})
        if isinstance(service_data, dict):
            service_entity_id = service_data.get('entity_id')
            if service_entity_id:
                if isinstance(service_entity_id, str):
                    entities.add(service_entity_id)
                elif isinstance(service_entity_id, list):
                    entities.update(service_entity_id)
        
        # Template entities (basic extraction)
        value_template = section.get('value_template')
        if value_template and isinstance(value_template, str):
            # Simple extraction: states('entity_id')
            import re
            matches = re.findall(r"states\(['\"]([^'\"]+)['\"]\)", value_template)
            entities.update(matches)
        
        return entities
    
    def is_external_data_entity(self, entity_id: str) -> bool:
        """Check if an entity ID is external data."""
        entity_id_lower = entity_id.lower()
        
        for category, patterns in EXTERNAL_DATA_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in entity_id_lower:
                    return True
        
        return False
    
    def categorize_external_entity(self, entity_id: str) -> str | None:
        """Categorize external data entity."""
        entity_id_lower = entity_id.lower()
        
        for category, patterns in EXTERNAL_DATA_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in entity_id_lower:
                    return category
        
        return None


class ExternalDataAutomationValidator:
    """Validate external data patterns against automations."""
    
    def __init__(self, ha_url: str, ha_token: str):
        self.extractor = AutomationEntityExtractor(ha_url, ha_token)
        self.automations: List[Dict[str, Any]] = []
        self.external_entities_in_automations: Set[str] = set()
        self.external_entities_not_in_automations: Set[str] = set()
        self.automation_usage: Dict[str, List[str]] = defaultdict(list)  # entity_id -> [automation_ids]
    
    async def analyze(self) -> Dict[str, Any]:
        """Analyze external data usage in automations."""
        logger.info("=" * 80)
        logger.info("External Data Automation Validation")
        logger.info("=" * 80)
        
        # Fetch automations
        self.automations = await self.extractor.get_automations()
        
        if not self.automations:
            logger.warning("No automations found - cannot validate external data usage")
            return {
                'automations_count': 0,
                'external_entities_in_automations': [],
                'external_entities_not_in_automations': [],
                'automation_usage': {},
                'recommendations': [
                    'No automations found - cannot validate external data patterns'
                ]
            }
        
        # Extract all entities from automations
        all_automation_entities = set()
        for automation in self.automations:
            automation_id = automation.get('id', 'unknown')
            entities = self.extractor.extract_entities_from_automation(automation)
            all_automation_entities.update(entities)
            
            # Track which automations use which entities
            for entity_id in entities:
                if self.extractor.is_external_data_entity(entity_id):
                    self.external_entities_in_automations.add(entity_id)
                    self.automation_usage[entity_id].append(automation_id)
        
        logger.info(f"Found {len(all_automation_entities)} unique entities in automations")
        logger.info(f"Found {len(self.external_entities_in_automations)} external data entities used in automations")
        
        # Categorize external entities
        external_by_category = defaultdict(set)
        for entity_id in self.external_entities_in_automations:
            category = self.extractor.categorize_external_entity(entity_id)
            if category:
                external_by_category[category].add(entity_id)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(external_by_category)
        
        results = {
            'automations_count': len(self.automations),
            'external_entities_in_automations': sorted(self.external_entities_in_automations),
            'external_entities_not_in_automations': sorted(self.external_entities_not_in_automations),
            'external_by_category': {
                category: sorted(entities)
                for category, entities in external_by_category.items()
            },
            'automation_usage': {
                entity_id: automation_ids
                for entity_id, automation_ids in self.automation_usage.items()
            },
            'recommendations': recommendations
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("Analysis Complete")
        logger.info("=" * 80)
        
        return results
    
    def _generate_recommendations(self, external_by_category: Dict[str, Set[str]]) -> List[str]:
        """Generate recommendations based on analysis."""
        recommendations = []
        
        total_external = len(self.external_entities_in_automations)
        
        if total_external == 0:
            recommendations.append(
                "No external data entities found in automations - "
                "all external data patterns should be filtered out"
            )
        else:
            recommendations.append(
                f"Found {total_external} external data entities used in automations - "
                "these should be allowed in patterns"
            )
            
            for category, entities in external_by_category.items():
                recommendations.append(
                    f"{category.capitalize()}: {len(entities)} entities used in automations"
                )
        
        recommendations.append(
            "Filter external data patterns: Only include if entity is used in automation"
        )
        recommendations.append(
            "External data synergies: Only create if external data triggers automation"
        )
        
        return recommendations
    
    def is_external_entity_valid(self, entity_id: str) -> bool:
        """Check if external data entity is valid (used in automation)."""
        if not self.extractor.is_external_data_entity(entity_id):
            return True  # Not external data, always valid
        
        return entity_id in self.external_entities_in_automations


async def main():
    """Main execution function."""
    import argparse
    import os
    
    parser = argparse.ArgumentParser(
        description='Validate external data patterns against Home Assistant automations'
    )
    parser.add_argument(
        '--ha-url',
        type=str,
        default=os.getenv('HA_URL', 'http://localhost:8123'),
        help='Home Assistant URL'
    )
    parser.add_argument(
        '--ha-token',
        type=str,
        default=os.getenv('HA_TOKEN', ''),
        help='Home Assistant API token'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='reports/quality/external_data_automation_validation.json',
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    if not args.ha_token:
        logger.error("Home Assistant token required (--ha-token or HA_TOKEN env var)")
        sys.exit(1)
    
    try:
        validator = ExternalDataAutomationValidator(args.ha_url, args.ha_token)
        results = await validator.analyze()
        
        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"\nResults saved to: {output_path}")
        
        # Print summary
        print("\n" + "=" * 80)
        print("External Data Automation Validation Summary")
        print("=" * 80)
        print(f"Automations Analyzed: {results['automations_count']}")
        print(f"External Entities in Automations: {len(results['external_entities_in_automations'])}")
        print("\nExternal Data by Category:")
        for category, entities in results['external_by_category'].items():
            print(f"  {category.capitalize()}: {len(entities)} entities")
            if len(entities) <= 5:
                for entity in entities:
                    print(f"    - {entity}")
        
        print("\nRecommendations:")
        for rec in results['recommendations']:
            print(f"  - {rec}")
        print("=" * 80)
        
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
