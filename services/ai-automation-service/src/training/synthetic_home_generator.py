"""
Synthetic Home Generator

Generate synthetic homes using template-based approach for training home type classifier.
Follows home-assistant-datasets generation pattern.

Template-based generation using predefined distributions and templates.
"""

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SyntheticHomeGenerator:
    """
    Generate synthetic homes using template-based approach.
    
    Uses predefined distributions and templates to generate homes without LLM calls.
    Follows home-assistant-datasets generation pattern.
    """
    
    # Home type distribution (100 homes)
    HOME_TYPE_DISTRIBUTION = {
        'single_family_house': 30,
        'apartment': 20,
        'condo': 15,
        'townhouse': 10,
        'cottage': 10,
        'studio': 5,
        'multi_story': 5,
        'ranch_house': 5
    }
    
    # Size distribution
    SIZE_DISTRIBUTION = {
        'small': (10, 20, 30),      # device_count_range, percentage
        'medium': (20, 40, 40),
        'large': (40, 60, 20),
        'extra_large': (60, 100, 10)
    }
    
    def __init__(self):
        """
        Initialize synthetic home generator.
        """
        logger.info("SyntheticHomeGenerator initialized (template-based generation)")
    
    def generate_homes(
        self,
        target_count: int = 100,
        home_types: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic homes with diversity.
        
        Distribution:
        - Single-family house: 30 homes
        - Apartment: 20 homes
        - Condo: 15 homes
        - Townhouse: 10 homes
        - Cottage: 10 homes
        - Studio: 5 homes
        - Multi-story: 5 homes
        - Ranch house: 5 homes
        
        Args:
            target_count: Total number of homes to generate (default: 100)
            home_types: Optional list of specific home types to generate
        
        Returns:
            List of synthetic home dictionaries
        """
        logger.info(f"Generating {target_count} synthetic homes...")
        
        # Determine home type distribution
        if home_types:
            # Generate only specified types
            type_counts = {ht: target_count // len(home_types) for ht in home_types}
            remainder = target_count % len(home_types)
            for i, ht in enumerate(home_types[:remainder]):
                type_counts[ht] = type_counts.get(ht, 0) + 1
        else:
            # Use default distribution scaled to target_count
            total_default = sum(self.HOME_TYPE_DISTRIBUTION.values())
            type_counts = {
                ht: int((count / total_default) * target_count)
                for ht, count in self.HOME_TYPE_DISTRIBUTION.items()
            }
            # Adjust for rounding
            current_total = sum(type_counts.values())
            if current_total < target_count:
                # Add to most common type
                type_counts['single_family_house'] += (target_count - current_total)
        
        homes = []
        
        for home_type, count in type_counts.items():
            if count == 0:
                continue
            
            logger.info(f"Generating {count} {home_type} homes...")
            
            for i in range(count):
                try:
                    home = self._generate_single_home(
                        home_type=home_type,
                        home_index=i + 1,
                        total_for_type=count
                    )
                    homes.append(home)
                    logger.info(f"✅ Generated home {len(homes)}/{target_count}: {home_type} #{i+1}")
                except Exception as e:
                    logger.error(f"❌ Failed to generate {home_type} home #{i+1}: {e}")
                    continue
        
        logger.info(f"✅ Generated {len(homes)} synthetic homes total")
        return homes
    
    def _generate_single_home(
        self,
        home_type: str,
        home_index: int,
        total_for_type: int
    ) -> dict[str, Any]:
        """
        Generate a single synthetic home using template-based approach.
        
        Args:
            home_type: Type of home (e.g., 'single_family_house', 'apartment')
            home_index: Index within this home type (1-based)
            total_for_type: Total homes to generate for this type
        
        Returns:
            Synthetic home dictionary with metadata
        """
        # Select size category based on distribution
        size_category = self._select_size_category()
        
        # Generate home metadata without LLM
        home_type_descriptions = {
            'single_family_house': 'a single-family house with multiple bedrooms, living areas, and outdoor spaces',
            'apartment': 'an apartment in a multi-unit building with limited space',
            'condo': 'a condominium with shared amenities',
            'townhouse': 'a townhouse with multiple floors and shared walls',
            'cottage': 'a small cottage or cabin, often in a rural setting',
            'studio': 'a studio apartment with minimal space and open layout',
            'multi_story': 'a large multi-story house with many rooms',
            'ranch_house': 'a single-level ranch-style house'
        }
        
        home_description = home_type_descriptions.get(home_type, f'a {home_type} home')
        
        # Create basic metadata structure
        metadata = {
            'home': {
                'name': f"{home_type.replace('_', ' ').title()} {home_index}",
                'type': home_type,
                'size_category': size_category,
                'description': home_description
            }
        }
        
        # Extract home data
        home_data = {
            'home_type': home_type,
            'size_category': size_category,
            'home_index': home_index,
            'metadata': metadata,
            'generated_at': self._get_timestamp()
        }
        
        return home_data
    
    def _select_size_category(self) -> str:
        """
        Select size category based on distribution.
        
        Returns:
            Size category string
        """
        # Weighted random selection
        categories = []
        weights = []
        
        for category, (_, _, percentage) in self.SIZE_DISTRIBUTION.items():
            categories.append(category)
            weights.append(percentage)
        
        return random.choices(categories, weights=weights, k=1)[0]
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as ISO string."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def save_homes(
        self,
        homes: list[dict[str, Any]],
        output_dir: Path | str
    ) -> Path:
        """
        Save generated homes to directory.
        
        Args:
            homes: List of synthetic home dictionaries
            output_dir: Directory to save homes
        
        Returns:
            Path to output directory
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save each home as JSON
        for i, home in enumerate(homes):
            home_file = output_path / f"home_{i+1:03d}_{home['home_type']}.json"
            with open(home_file, 'w', encoding='utf-8') as f:
                json.dump(home, f, indent=2, ensure_ascii=False)
        
        # Save summary
        summary = {
            'total_homes': len(homes),
            'home_types': {},
            'size_categories': {},
            'generated_at': self._get_timestamp()
        }
        
        for home in homes:
            home_type = home['home_type']
            size_category = home['size_category']
            
            summary['home_types'][home_type] = summary['home_types'].get(home_type, 0) + 1
            summary['size_categories'][size_category] = summary['size_categories'].get(size_category, 0) + 1
        
        summary_file = output_path / "summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved {len(homes)} homes to {output_path}")
        return output_path

