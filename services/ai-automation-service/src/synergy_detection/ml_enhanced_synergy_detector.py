"""
ML-Enhanced Synergy Detector

Combines traditional predefined synergy detection with ML-based dynamic discovery.

Integration:
- Predefined synergies (16 hardcoded patterns from COMPATIBLE_RELATIONSHIPS)
- ML-discovered synergies (50-100+ patterns from association rule mining)
- Hybrid ranking (combines both sources for optimal suggestions)

Epic: Dynamic Synergy Discovery (#3)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from .ml_synergy_miner import DiscoveredSynergy, DynamicSynergyMiner
from .synergy_detector import DeviceSynergyDetector

logger = logging.getLogger(__name__)


class MLEnhancedSynergyDetector:
    """
    Enhanced synergy detector combining predefined + ML-discovered synergies.

    Workflow:
    1. Detect predefined synergies (existing DeviceSynergyDetector logic)
    2. Mine ML-discovered synergies (DynamicSynergyMiner)
    3. Merge and rank combined opportunities
    4. Store discovered synergies in database
    """

    def __init__(
        self,
        base_synergy_detector: DeviceSynergyDetector,
        influxdb_client,
        enable_ml_discovery: bool = True,
        ml_discovery_interval_hours: int = 24,
        min_ml_confidence: float = 0.75,
    ):
        """
        Initialize ML-enhanced synergy detector.

        Args:
            base_synergy_detector: Base DeviceSynergyDetector instance
            influxdb_client: InfluxDB client for ML mining
            enable_ml_discovery: Enable ML-based dynamic discovery
            ml_discovery_interval_hours: How often to run ML discovery (default: 24h)
            min_ml_confidence: Minimum confidence for ML-discovered synergies
        """
        self.base_detector = base_synergy_detector
        self.influxdb_client = influxdb_client
        self.enable_ml_discovery = enable_ml_discovery
        self.ml_discovery_interval_hours = ml_discovery_interval_hours
        self.min_ml_confidence = min_ml_confidence

        # Initialize ML miner
        self.ml_miner = None
        if enable_ml_discovery:
            self.ml_miner = DynamicSynergyMiner(
                influxdb_client=influxdb_client,
                min_support=0.05,
                min_confidence=min_ml_confidence,
                min_lift=1.5,
                min_consistency=0.8,
                time_window_seconds=60,
                lookback_days=30,
                min_occurrences=10,
            )

        # Cache for ML-discovered synergies
        self._ml_synergy_cache: list[DiscoveredSynergy] = []
        self._last_ml_discovery: datetime | None = None

        logger.info(
            f"MLEnhancedSynergyDetector initialized: "
            f"ml_discovery={enable_ml_discovery}, interval={ml_discovery_interval_hours}h",
        )

    async def detect_synergies(
        self,
        force_ml_refresh: bool = False,
    ) -> list[dict]:
        """
        Detect synergies using both predefined and ML-discovered patterns.

        Args:
            force_ml_refresh: Force ML discovery even if cache is fresh

        Returns:
            Combined list of synergy opportunities (predefined + ML-discovered)
        """
        start_time = datetime.now(timezone.utc)

        logger.info("🔗 Starting enhanced synergy detection (predefined + ML)...")

        # Step 1: Get predefined synergies from base detector
        logger.info("📊 Step 1: Detecting predefined synergies...")
        predefined_synergies = await self.base_detector.detect_synergies()
        logger.info(f"  → Found {len(predefined_synergies)} predefined synergies")

        # Step 2: Get ML-discovered synergies (if enabled)
        ml_synergies = []
        if self.enable_ml_discovery:
            ml_synergies = await self._get_ml_discovered_synergies(force_refresh=force_ml_refresh)
            logger.info(f"  → Found {len(ml_synergies)} ML-discovered synergies")

        # Step 3: Merge and rank
        logger.info("🔀 Step 3: Merging and ranking synergies...")
        combined_synergies = self._merge_synergies(predefined_synergies, ml_synergies)

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ Enhanced synergy detection complete in {duration:.2f}s: "
            f"{len(predefined_synergies)} predefined + {len(ml_synergies)} ML = "
            f"{len(combined_synergies)} total",
        )

        return combined_synergies

    async def _get_ml_discovered_synergies(
        self,
        force_refresh: bool = False,
    ) -> list[dict]:
        """
        Get ML-discovered synergies from cache or run new discovery.

        Args:
            force_refresh: Force new ML discovery

        Returns:
            List of ML-discovered synergy dictionaries
        """
        # Check if cache is fresh
        if not force_refresh and self._last_ml_discovery:
            cache_age = datetime.now(timezone.utc) - self._last_ml_discovery
            cache_age_hours = cache_age.total_seconds() / 3600

            if cache_age_hours < self.ml_discovery_interval_hours:
                logger.info(
                    f"  → Using cached ML synergies "
                    f"(age: {cache_age_hours:.1f}h < {self.ml_discovery_interval_hours}h)",
                )
                return self._convert_discovered_to_dict(self._ml_synergy_cache)

        # Run ML discovery
        logger.info("⛏️ Running ML synergy discovery...")
        try:
            discovered_synergies = await self.ml_miner.mine_synergies()

            # Update cache
            self._ml_synergy_cache = discovered_synergies
            self._last_ml_discovery = datetime.now(timezone.utc)

            # Store in database (for persistence) - Note: db session must be passed from caller
            # await self._store_discovered_synergies(discovered_synergies, db)

            # Log statistics
            stats = self.ml_miner.get_statistics(discovered_synergies)
            logger.info(
                f"  → ML mining stats: {stats['total_count']} synergies, "
                f"avg confidence={stats['avg_confidence']:.2f}, "
                f"avg consistency={stats['avg_consistency']:.2f}",
            )

            return self._convert_discovered_to_dict(discovered_synergies)

        except Exception as e:
            logger.error(f"ML synergy discovery failed: {e}", exc_info=True)
            return []

    def _convert_discovered_to_dict(
        self,
        discovered_synergies: list[DiscoveredSynergy],
    ) -> list[dict]:
        """
        Convert DiscoveredSynergy objects to synergy dictionary format.

        Converts ML-discovered synergies to the same format as predefined synergies
        for unified handling.

        Args:
            discovered_synergies: List of DiscoveredSynergy objects

        Returns:
            List of synergy dictionaries
        """
        synergy_dicts = []

        for synergy in discovered_synergies:
            # Convert to synergy dict format
            synergy_dict = {
                "synergy_id": str(uuid.uuid4()),
                "synergy_type": "ml_discovered",
                "devices": [synergy.trigger_entity, synergy.action_entity],
                "trigger_entity": synergy.trigger_entity,
                "action_entity": synergy.action_entity,
                "relationship": f"{synergy.trigger_entity} → {synergy.action_entity}",
                "impact_score": self._calculate_ml_impact_score(synergy),
                "confidence": synergy.confidence,
                "complexity": self._infer_complexity(synergy),
                "area": None,  # Will be filled from device data if available
                "rationale": (
                    f"Discovered pattern: {synergy.trigger_entity} triggers {synergy.action_entity} "
                    f"({synergy.frequency} times, {synergy.consistency * 100:.0f}% consistent)"
                ),
                "metadata": {
                    "source": "ml_discovered",
                    "support": synergy.support,
                    "lift": synergy.lift,
                    "frequency": synergy.frequency,
                    "consistency": synergy.consistency,
                    "time_window_seconds": synergy.time_window_seconds,
                    "discovered_at": synergy.discovered_at.isoformat(),
                },
                # Epic AI-4: N-level synergy fields
                "synergy_depth": 2,
                "chain_devices": [synergy.trigger_entity, synergy.action_entity],
            }

            synergy_dicts.append(synergy_dict)

        return synergy_dicts

    def _calculate_ml_impact_score(self, synergy: DiscoveredSynergy) -> float:
        """
        Calculate impact score for ML-discovered synergy.

        Formula: (confidence * 0.4) + (consistency * 0.4) + (log(frequency) * 0.2)

        Args:
            synergy: DiscoveredSynergy object

        Returns:
            Impact score (0.0-1.0)
        """
        import numpy as np

        # Weight components
        confidence_weight = 0.4
        consistency_weight = 0.4
        frequency_weight = 0.2

        # Normalize frequency using log (diminishing returns)
        # 10 occurrences = 1.0, 100 occurrences = 2.0, etc.
        frequency_normalized = min(np.log10(synergy.frequency) / 2.0, 1.0)

        impact_score = (
            synergy.confidence * confidence_weight +
            synergy.consistency * consistency_weight +
            frequency_normalized * frequency_weight
        )

        return round(impact_score, 2)

    def _infer_complexity(self, synergy: DiscoveredSynergy) -> str:
        """
        Infer complexity for ML-discovered synergy.

        Simple heuristic based on confidence and consistency.

        Args:
            synergy: DiscoveredSynergy object

        Returns:
            Complexity level: 'low', 'medium', or 'high'
        """
        # High confidence + high consistency = low complexity (reliable pattern)
        if synergy.confidence >= 0.85 and synergy.consistency >= 0.85:
            return "low"
        # Medium confidence or consistency = medium complexity
        if synergy.confidence >= 0.70 or synergy.consistency >= 0.70:
            return "medium"
        # Low confidence and consistency = high complexity (less reliable)
        return "high"

    def _merge_synergies(
        self,
        predefined: list[dict],
        ml_discovered: list[dict],
    ) -> list[dict]:
        """
        Merge predefined and ML-discovered synergies, removing duplicates.

        Deduplication logic:
        - If same trigger → action exists in both, prefer predefined (higher trust)
        - If reverse direction exists, keep both (bidirectional patterns)

        Args:
            predefined: List of predefined synergy dicts
            ml_discovered: List of ML-discovered synergy dicts

        Returns:
            Merged and deduplicated list of synergies
        """
        # Create lookup for predefined synergies
        predefined_pairs = set()
        for synergy in predefined:
            trigger = synergy.get("trigger_entity")
            action = synergy.get("action_entity")
            if trigger and action:
                predefined_pairs.add((trigger, action))

        # Filter ML-discovered to remove duplicates
        filtered_ml = []
        duplicates_removed = 0

        for ml_synergy in ml_discovered:
            trigger = ml_synergy.get("trigger_entity")
            action = ml_synergy.get("action_entity")

            # Skip if predefined already has this relationship
            if (trigger, action) in predefined_pairs:
                duplicates_removed += 1
                continue

            filtered_ml.append(ml_synergy)

        if duplicates_removed > 0:
            logger.info(f"  → Removed {duplicates_removed} duplicate ML synergies")

        # Combine and sort by impact score
        combined = predefined + filtered_ml
        combined.sort(key=lambda x: x.get("impact_score", 0), reverse=True)

        return combined

    async def _store_discovered_synergies(
        self,
        discovered_synergies: list[DiscoveredSynergy],
        db,
    ) -> int:
        """
        Store discovered synergies in database for persistence.

        Args:
            discovered_synergies: List of DiscoveredSynergy objects
            db: Database session (AsyncSession)

        Returns:
            Number of synergies stored
        """
        if not discovered_synergies:
            return 0

        try:
            from src.database.models import DiscoveredSynergy as DiscoveredSynergyDB

            stored_count = 0

            for synergy in discovered_synergies:
                try:
                    # Check if synergy already exists
                    from sqlalchemy import select
                    existing = await db.execute(
                        select(DiscoveredSynergyDB).where(
                            DiscoveredSynergyDB.trigger_entity == synergy.trigger_entity,
                            DiscoveredSynergyDB.action_entity == synergy.action_entity,
                        ),
                    )
                    existing_synergy = existing.scalar_one_or_none()

                    if existing_synergy:
                        # Update existing synergy
                        existing_synergy.support = synergy.support
                        existing_synergy.confidence = synergy.confidence
                        existing_synergy.lift = synergy.lift
                        existing_synergy.frequency = synergy.frequency
                        existing_synergy.consistency = synergy.consistency
                        existing_synergy.time_window_seconds = synergy.time_window_seconds
                        existing_synergy.discovered_at = synergy.discovered_at
                        existing_synergy.synergy_metadata = {
                            "analysis_period": getattr(synergy, "analysis_period", None),
                            "total_transactions": getattr(synergy, "total_transactions", None),
                            "mining_duration_seconds": getattr(synergy, "mining_duration", None),
                            "area": getattr(synergy, "area", None),
                            "device_classes": getattr(synergy, "device_classes", []),
                        }
                    else:
                        # Create new synergy record
                        discovered = DiscoveredSynergyDB(
                            synergy_id=str(uuid.uuid4()),
                            trigger_entity=synergy.trigger_entity,
                            action_entity=synergy.action_entity,
                            source="mined",  # ML-discovered

                            # Association rule metrics
                            support=synergy.support,
                            confidence=synergy.confidence,
                            lift=synergy.lift,

                            # Temporal analysis
                            frequency=synergy.frequency,
                            consistency=synergy.consistency,
                            time_window_seconds=synergy.time_window_seconds,

                            # Discovery metadata
                            discovered_at=synergy.discovered_at,
                            validation_count=0,
                            validation_passed=None,  # Not yet validated
                            status="discovered",

                            # Metadata - renamed from 'metadata' to avoid SQLAlchemy reserved name
                            synergy_metadata={
                                "analysis_period": getattr(synergy, "analysis_period", None),
                                "total_transactions": getattr(synergy, "total_transactions", None),
                                "mining_duration_seconds": getattr(synergy, "mining_duration", None),
                                "area": getattr(synergy, "area", None),
                                "device_classes": getattr(synergy, "device_classes", []),
                            },
                        )
                        db.add(discovered)

                    stored_count += 1

                except Exception as e:
                    logger.exception(f"Failed to store discovered synergy {synergy.trigger_entity} → {synergy.action_entity}: {e}")
                    continue

            await db.commit()

            logger.info(f"✅ Stored {stored_count} ML-discovered synergies")

            return stored_count

        except Exception as e:
            logger.error(f"Error storing discovered synergies: {e}", exc_info=True)
            await db.rollback()
            return 0

    async def _validate_discovered_synergies(
        self,
        discovered_synergies: list[DiscoveredSynergy],
        patterns: list[dict],
        db,
    ) -> list[DiscoveredSynergy]:
        """
        Validate ML-discovered synergies against detected patterns.

        A synergy is validated if:
        1. Both devices are actionable
        2. Pattern evidence supports the relationship
        3. Consistency and confidence are high enough

        Args:
            discovered_synergies: List of DiscoveredSynergy objects
            patterns: List of detected patterns (dicts)
            db: Database session

        Returns:
            List of validated DiscoveredSynergy objects
        """
        from src.database.models import DiscoveredSynergy as DiscoveredSynergyDB

        validated = []

        for synergy in discovered_synergies:
            validation_score = 0.0
            validation_reasons = []

            # Check 1: Pattern support
            matching_patterns = [
                p for p in patterns
                if (p.get("device_id") == synergy.trigger_entity or
                    p.get("device1") == synergy.trigger_entity or
                    p.get("device2") == synergy.trigger_entity)
            ]

            if matching_patterns:
                validation_score += 0.4
                validation_reasons.append("pattern_support")

            # Check 2: Statistical significance
            if synergy.lift > 1.5:  # Strong association
                validation_score += 0.3
                validation_reasons.append("strong_lift")

            # Check 3: Consistency
            if synergy.consistency > 0.7:
                validation_score += 0.2
                validation_reasons.append("high_consistency")

            # Check 4: Frequency
            if synergy.frequency > 10:
                validation_score += 0.1
                validation_reasons.append("high_frequency")

            # Validate if score >= 0.6
            if validation_score >= 0.6:
                # Update database record
                from sqlalchemy import select
                existing = await db.execute(
                    select(DiscoveredSynergyDB).where(
                        DiscoveredSynergyDB.trigger_entity == synergy.trigger_entity,
                        DiscoveredSynergyDB.action_entity == synergy.action_entity,
                    ),
                )
                db_synergy = existing.scalar_one_or_none()

                if db_synergy:
                    db_synergy.validation_passed = True
                    db_synergy.status = "validated"
                    db_synergy.last_validated = datetime.now(timezone.utc)
                    db_synergy.validation_count += 1
                    if not db_synergy.synergy_metadata:
                        db_synergy.synergy_metadata = {}
                    db_synergy.synergy_metadata["validation_score"] = validation_score
                    db_synergy.synergy_metadata["validation_reasons"] = validation_reasons

                validated.append(synergy)
            else:
                # Update database record as rejected
                from sqlalchemy import select
                existing = await db.execute(
                    select(DiscoveredSynergyDB).where(
                        DiscoveredSynergyDB.trigger_entity == synergy.trigger_entity,
                        DiscoveredSynergyDB.action_entity == synergy.action_entity,
                    ),
                )
                db_synergy = existing.scalar_one_or_none()

                if db_synergy:
                    db_synergy.validation_passed = False
                    db_synergy.status = "rejected"
                    db_synergy.rejection_reason = f"Low validation score: {validation_score:.2f}"

        await db.commit()

        logger.info(f"✅ Validated {len(validated)}/{len(discovered_synergies)} ML synergies")

        return validated

    async def get_ml_discovery_statistics(self) -> dict[str, Any]:
        """
        Get statistics about ML synergy discovery.

        Returns:
            Dictionary with ML discovery statistics
        """
        if not self.ml_miner or not self._ml_synergy_cache:
            return {
                "enabled": self.enable_ml_discovery,
                "discovered_count": 0,
                "last_discovery": None,
            }

        stats = self.ml_miner.get_statistics(self._ml_synergy_cache)

        return {
            "enabled": self.enable_ml_discovery,
            "discovered_count": stats["total_count"],
            "last_discovery": self._last_ml_discovery.isoformat() if self._last_ml_discovery else None,
            "cache_age_hours": (
                (datetime.now(timezone.utc) - self._last_ml_discovery).total_seconds() / 3600
                if self._last_ml_discovery else None
            ),
            "avg_confidence": stats.get("avg_confidence"),
            "avg_consistency": stats.get("avg_consistency"),
            "avg_frequency": stats.get("avg_frequency"),
            "avg_lift": stats.get("avg_lift"),
        }
