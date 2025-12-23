"""
Synthetic Home Generator

Generate synthetic homes using template-based approach for training home type classifier.
Follows home-assistant-datasets generation pattern.

Template-based generation using predefined distributions and templates.
"""

import asyncio
import json
import logging
import random
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .synthetic_home_openai_generator import SyntheticHomeOpenAIGenerator
    from ..llm.openai_client import OpenAIClient

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
    
    def __init__(
        self,
        enable_openai_enhancement: bool = False,
        openai_client: "OpenAIClient | None" = None,
        rate_limit_rpm: int = 20  # Default: 20 requests per minute (conservative for tier 2)
    ):
        """
        Initialize synthetic home generator.
        
        Args:
            enable_openai_enhancement: Enable OpenAI enhancement (default: False)
            openai_client: OpenAI client instance (optional, loads from settings if not provided)
        """
        self.enable_openai_enhancement = enable_openai_enhancement
        self.openai_client = openai_client
        self.openai_generator = None
        
        # Rate limiting: Calculate delay between requests to avoid exceeding OpenAI thresholds
        # Formula: delay = (60 seconds / RPM) * 1.1 (10% safety buffer)
        self.rate_limit_rpm = rate_limit_rpm
        self.request_delay = (60.0 / rate_limit_rpm) * 1.1 if rate_limit_rpm > 0 else 0.0
        logger.info(f"Rate limiting configured: {rate_limit_rpm} RPM = {self.request_delay:.2f}s delay between requests")
        
        if enable_openai_enhancement:
            if not openai_client:
                try:
                    from ..llm.openai_client import OpenAIClient
                    from ..config import settings
                    
                    if not settings.openai_api_key:
                        logger.warning("⚠️ OpenAI API key not configured, disabling OpenAI enhancement")
                        self.enable_openai_enhancement = False
                    else:
                        self.openai_client = OpenAIClient(
                            api_key=settings.openai_api_key,
                            model=settings.openai_model
                        )
                        from .synthetic_home_openai_generator import SyntheticHomeOpenAIGenerator
                        self.openai_generator = SyntheticHomeOpenAIGenerator(
                            openai_client=self.openai_client
                        )
                        logger.info("SyntheticHomeGenerator initialized with OpenAI enhancement")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to initialize OpenAI enhancement: {e}")
                    self.enable_openai_enhancement = False
            else:
                from .synthetic_home_openai_generator import SyntheticHomeOpenAIGenerator
                self.openai_generator = SyntheticHomeOpenAIGenerator(
                    openai_client=openai_client
                )
                logger.info("SyntheticHomeGenerator initialized with OpenAI enhancement")
        else:
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
    
    async def generate_homes_hybrid(
        self,
        target_count: int = 100,
        home_types: list[str] | None = None,
        enhancement_percentage: float = 0.20,
        validate_percentage: float = 0.10
    ) -> list[dict[str, Any]]:
        """
        Generate synthetic homes using hybrid approach (template + OpenAI).
        
        Args:
            target_count: Total number of homes to generate (default: 100)
            home_types: Optional list of specific home types to generate
            enhancement_percentage: Percentage of homes to generate with OpenAI (default: 0.20)
            validate_percentage: Percentage of template homes to validate (default: 0.10)
        
        Returns:
            List of synthetic home dictionaries
        """
        if not self.enable_openai_enhancement or not self.openai_generator:
            logger.warning("⚠️ OpenAI enhancement not enabled, falling back to template-only generation")
            return self.generate_homes(target_count=target_count, home_types=home_types)
        
        logger.info(f"Generating {target_count} synthetic homes (hybrid: {enhancement_percentage*100:.0f}% OpenAI-enhanced)...")
        
        # Calculate counts
        template_count = int(target_count * (1 - enhancement_percentage))
        enhanced_count = target_count - template_count
        
        logger.info(f"  - Template-based: {template_count} homes")
        logger.info(f"  - OpenAI-enhanced: {enhanced_count} homes")
        
        # Generate template-based homes
        template_homes = self.generate_homes(target_count=template_count, home_types=home_types)
        
        # Generate OpenAI-enhanced homes
        enhanced_homes = []
        if enhanced_count > 0:
            logger.info(f"Generating {enhanced_count} OpenAI-enhanced homes...")
            
            # Determine home type distribution for enhanced homes
            if home_types:
                enhanced_type_counts = {ht: enhanced_count // len(home_types) for ht in home_types}
                remainder = enhanced_count % len(home_types)
                for i, ht in enumerate(home_types[:remainder]):
                    enhanced_type_counts[ht] = enhanced_type_counts.get(ht, 0) + 1
            else:
                # Use default distribution scaled to enhanced_count
                total_default = sum(self.HOME_TYPE_DISTRIBUTION.values())
                enhanced_type_counts = {
                    ht: int((count / total_default) * enhanced_count)
                    for ht, count in self.HOME_TYPE_DISTRIBUTION.items()
                }
                current_total = sum(enhanced_type_counts.values())
                if current_total < enhanced_count:
                    enhanced_type_counts['single_family_house'] += (enhanced_count - current_total)
            
            # Rate limiting: Add delay between OpenAI API calls to prevent rate limit errors
            # Default: 20 RPM (3.3 seconds between calls) - conservative for tier 2 accounts
            request_delay = getattr(self, 'request_delay', 3.3)  # Default delay in seconds
            
            for home_type, count in enhanced_type_counts.items():
                if count == 0:
                    continue
                
                for i in range(count):
                    try:
                        size_category = self._select_size_category()
                        enhanced_home = await self.openai_generator.generate_enhanced_home(
                            home_type=home_type,
                            size_category=size_category,
                            home_index=i + 1
                        )
                        enhanced_homes.append(enhanced_home)
                        logger.info(f"✅ Generated enhanced home {len(enhanced_homes)}/{enhanced_count}: {home_type} #{i+1}")
                        
                        # Rate limiting: Wait before next API call (except for last home)
                        if i < count - 1 or len(enhanced_homes) < enhanced_count:
                            logger.debug(f"⏳ Waiting {request_delay:.1f}s before next OpenAI API call (rate limiting)...")
                            await asyncio.sleep(request_delay)
                            
                    except Exception as e:
                        logger.error(f"❌ Failed to generate enhanced {home_type} home #{i+1}: {e}")
                        # Fallback to template generation
                        try:
                            fallback_home = self._generate_single_home(
                                home_type=home_type,
                                home_index=i + 1,
                                total_for_type=count
                            )
                            enhanced_homes.append(fallback_home)
                            logger.info(f"✅ Fallback to template for {home_type} #{i+1}")
                        except Exception as fallback_error:
                            logger.error(f"❌ Fallback also failed: {fallback_error}")
                            continue
                        
                        # Still wait after fallback to maintain rate limit consistency
                        if i < count - 1 or len(enhanced_homes) < enhanced_count:
                            await asyncio.sleep(request_delay)
        
        # Validate sample of template homes
        validated_count = 0
        if validate_percentage > 0 and template_homes:
            validate_count = max(1, int(len(template_homes) * validate_percentage))
            logger.info(f"Validating {validate_count} template homes...")
            
            # Import area and device generators for validation
            from .synthetic_area_generator import SyntheticAreaGenerator
            from .synthetic_device_generator import SyntheticDeviceGenerator
            
            area_generator = SyntheticAreaGenerator()
            device_generator = SyntheticDeviceGenerator()
            
            # Sample homes to validate
            import random
            homes_to_validate = random.sample(template_homes, min(validate_count, len(template_homes)))
            
            # Rate limiting: Add delay between validation API calls
            request_delay = getattr(self, 'request_delay', 3.3)
            
            for idx, home in enumerate(homes_to_validate):
                try:
                    # Generate areas and devices for validation
                    areas = area_generator.generate_areas(home)
                    devices = device_generator.generate_devices(home, areas)
                    
                    # Validate with OpenAI
                    validation_result = await self.openai_generator.validate_home(home, areas, devices)
                    
                    if not validation_result.get('is_realistic', True):
                        logger.warning(f"⚠️ Home {home.get('home_type')} validation issues: {validation_result.get('issues', [])}")
                    
                    validated_count += 1
                    
                    # Rate limiting: Wait before next validation call (except for last)
                    if idx < len(homes_to_validate) - 1:
                        logger.debug(f"⏳ Waiting {request_delay:.1f}s before next validation API call...")
                        await asyncio.sleep(request_delay)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Validation failed for home: {e}")
                    continue
        
        # Combine all homes
        all_homes = template_homes + enhanced_homes
        
        logger.info(f"✅ Generated {len(all_homes)} synthetic homes total")
        logger.info(f"  - Template-based: {len(template_homes)}")
        logger.info(f"  - OpenAI-enhanced: {len(enhanced_homes)}")
        logger.info(f"  - Validated: {validated_count}")
        
        return all_homes
    
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
    
    def enrich_with_external_data(
        self,
        homes: list[dict[str, Any]],
        days: int = 7,
        enable_pricing: bool = True,
        enable_calendar: bool = True
    ) -> list[dict[str, Any]]:
        """
        Enrich homes with external data (Epic 34 - Story 34.11).
        
        Adds electricity pricing and calendar data to homes.
        
        Args:
            homes: List of synthetic home dictionaries
            days: Number of days of external data to generate
            enable_pricing: Enable electricity pricing generation
            enable_calendar: Enable calendar event generation
        
        Returns:
            List of homes enriched with external_data section
        """
        from datetime import datetime, timedelta, timezone
        
        logger.info(f"Enriching {len(homes)} homes with external data (pricing: {enable_pricing}, calendar: {enable_calendar})...")
        
        enriched_homes = []
        start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        
        if enable_pricing:
            from .synthetic_electricity_pricing_generator import SyntheticElectricityPricingGenerator
            pricing_generator = SyntheticElectricityPricingGenerator()
        
        if enable_calendar:
            from .synthetic_calendar_generator import SyntheticCalendarGenerator
            calendar_generator = SyntheticCalendarGenerator()
        
        for home in homes:
            enriched_home = home.copy()
            
            # Initialize external_data section
            if 'external_data' not in enriched_home:
                enriched_home['external_data'] = {}
            
            # Generate electricity pricing
            if enable_pricing:
                try:
                    pricing_data = pricing_generator.generate_pricing(
                        home=home,
                        start_date=start_date,
                        days=days
                    )
                    enriched_home['external_data']['electricity_pricing'] = pricing_data
                    logger.debug(f"Added {len(pricing_data)} pricing data points to home")
                except Exception as e:
                    logger.warning(f"Failed to generate pricing data: {e}")
            
            # Generate calendar events
            if enable_calendar:
                try:
                    calendar_events = calendar_generator.generate_calendar(
                        home=home,
                        start_date=start_date,
                        days=days
                    )
                    enriched_home['external_data']['calendar'] = calendar_events
                    logger.debug(f"Added {len(calendar_events)} calendar events to home")
                except Exception as e:
                    logger.warning(f"Failed to generate calendar data: {e}")
            
            enriched_homes.append(enriched_home)
        
        logger.info(f"✅ Enriched {len(enriched_homes)} homes with external data")
        return enriched_homes

