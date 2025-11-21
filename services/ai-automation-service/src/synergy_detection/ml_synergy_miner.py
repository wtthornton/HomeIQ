"""
ML-Based Dynamic Synergy Miner

Discovers novel device relationships from actual usage patterns using
association rule mining and temporal sequence analysis.

Epic: Dynamic Synergy Discovery (#3)
Impact: Expand from 16 hardcoded patterns to 50-100+ discovered patterns
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from .association_rules import AprioriMiner, AssociationRule, TransactionBuilder

logger = logging.getLogger(__name__)


class DiscoveredSynergy:
    """Represents a dynamically discovered synergy relationship"""

    def __init__(
        self,
        trigger_entity: str,
        action_entity: str,
        support: float,
        confidence: float,
        lift: float,
        frequency: int,
        consistency: float,
        time_window_seconds: int,
        discovered_at: datetime,
        source: str = "mined",
    ):
        """
        Initialize discovered synergy.

        Args:
            trigger_entity: Entity that triggers the action
            action_entity: Entity that gets activated
            support: How often this pattern appears
            confidence: Reliability of the pattern
            lift: Strength of association
            frequency: Number of occurrences
            consistency: Temporal consistency (0.0-1.0)
            time_window_seconds: Time window for co-occurrence
            discovered_at: When this pattern was discovered
            source: 'mined' for ML-discovered, 'predefined' for hardcoded
        """
        self.trigger_entity = trigger_entity
        self.action_entity = action_entity
        self.support = support
        self.confidence = confidence
        self.lift = lift
        self.frequency = frequency
        self.consistency = consistency
        self.time_window_seconds = time_window_seconds
        self.discovered_at = discovered_at
        self.source = source

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "trigger_entity": self.trigger_entity,
            "action_entity": self.action_entity,
            "support": self.support,
            "confidence": self.confidence,
            "lift": self.lift,
            "frequency": self.frequency,
            "consistency": self.consistency,
            "time_window_seconds": self.time_window_seconds,
            "discovered_at": self.discovered_at.isoformat(),
            "source": self.source,
        }

    def __str__(self):
        return (
            f"{self.trigger_entity} → {self.action_entity} "
            f"(conf={self.confidence:.2f}, lift={self.lift:.2f}, freq={self.frequency})"
        )


class DynamicSynergyMiner:
    """
    Discovers device synergies from historical event data using ML.

    Three-phase approach:
    1. Co-Occurrence Mining: Find frequent itemsets (Apriori)
    2. Temporal Sequence Analysis: Detect consistent ordering
    3. Validation & Ranking: Filter and rank by impact
    """

    def __init__(
        self,
        influxdb_client,
        min_support: float = 0.05,
        min_confidence: float = 0.7,
        min_lift: float = 1.5,
        min_consistency: float = 0.8,
        time_window_seconds: int = 60,
        lookback_days: int = 30,
        min_occurrences: int = 10,
    ):
        """
        Initialize dynamic synergy miner.

        Args:
            influxdb_client: InfluxDB client for querying events
            min_support: Minimum support for frequent itemsets (0.05 = 5%)
            min_confidence: Minimum confidence for rules (0.7 = 70%)
            min_lift: Minimum lift for positive correlation (1.5 = 50% stronger)
            min_consistency: Minimum temporal consistency (0.8 = 80% consistent)
            time_window_seconds: Time window for co-occurrence (60s default)
            lookback_days: Days of history to analyze (30 days default)
            min_occurrences: Minimum occurrences to consider valid (10 default)
        """
        self.influxdb_client = influxdb_client
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.min_consistency = min_consistency
        self.time_window_seconds = time_window_seconds
        self.lookback_days = lookback_days
        self.min_occurrences = min_occurrences

        # Initialize miners
        self.apriori_miner = AprioriMiner(
            min_support=min_support,
            min_confidence=min_confidence,
            min_lift=min_lift,
            max_itemset_size=4,
        )

        self.transaction_builder = TransactionBuilder(
            time_window_seconds=time_window_seconds,
            min_transaction_size=2,
        )

        logger.info(
            f"DynamicSynergyMiner initialized: support={min_support}, "
            f"confidence={min_confidence}, consistency={min_consistency}, "
            f"lookback={lookback_days}d",
        )

    async def mine_synergies(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[DiscoveredSynergy]:
        """
        Mine synergies from historical event data.

        Three-phase process:
        1. Query co-occurring state changes from InfluxDB
        2. Build association rules using Apriori
        3. Validate temporal consistency

        Args:
            start_time: Start time for analysis (default: lookback_days ago)
            end_time: End time for analysis (default: now)

        Returns:
            List of discovered synergies
        """
        overall_start = datetime.now(timezone.utc)

        # Default time range
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=self.lookback_days)

        logger.info(
            f"⛏️ Mining synergies from {start_time.date()} to {end_time.date()} "
            f"({self.lookback_days} days)...",
        )

        # Phase 1: Query co-occurring events
        logger.info("📊 Phase 1: Querying co-occurring state changes from InfluxDB...")
        events_df = await self._query_cooccurring_events(start_time, end_time)

        if events_df.empty:
            logger.warning("No events found in time range")
            return []

        logger.info(f"  → Retrieved {len(events_df)} state change events")

        # Phase 2: Build transactions
        logger.info("🔨 Phase 2: Building transactions...")
        transactions = self.transaction_builder.build_transactions(
            events_df,
            start_time=start_time,
            end_time=end_time,
        )

        if not transactions:
            logger.warning("No transactions could be built from events")
            return []

        logger.info(f"  → Built {len(transactions)} transactions")

        # Phase 3: Mine frequent itemsets
        logger.info("⛏️ Phase 3: Mining frequent itemsets (Apriori)...")
        frequent_itemsets = self.apriori_miner.mine_frequent_itemsets(transactions)

        if not frequent_itemsets:
            logger.warning("No frequent itemsets found")
            return []

        logger.info(f"  → Found {len(frequent_itemsets)} frequent itemsets")

        # Phase 4: Generate association rules
        logger.info("📏 Phase 4: Generating association rules...")
        rules = self.apriori_miner.generate_association_rules(frequent_itemsets)

        if not rules:
            logger.warning("No association rules met confidence/lift thresholds")
            return []

        logger.info(f"  → Generated {len(rules)} association rules")

        # Phase 5: Analyze temporal patterns
        logger.info("⏱️ Phase 5: Analyzing temporal consistency...")
        temporal_patterns = await self._analyze_temporal_patterns(rules, events_df)

        logger.info(f"  → Found {len(temporal_patterns)} temporally consistent patterns")

        # Phase 6: Validate and rank
        logger.info("✅ Phase 6: Validating and ranking synergies...")
        validated_synergies = self._validate_synergies(temporal_patterns)

        duration = (datetime.now(timezone.utc) - overall_start).total_seconds()
        logger.info(
            f"✅ Synergy mining complete in {duration:.2f}s: "
            f"{len(validated_synergies)} validated synergies discovered",
        )

        # Log top 5 discoveries
        if validated_synergies:
            logger.info("🏆 Top 5 discovered synergies:")
            for i, synergy in enumerate(validated_synergies[:5], 1):
                logger.info(f"  {i}. {synergy}")

        return validated_synergies

    async def _query_cooccurring_events(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """
        Query co-occurring state changes from InfluxDB.

        Optimized query to get only state changes within time windows.

        Args:
            start_time: Start time
            end_time: End time

        Returns:
            DataFrame with columns: time, entity_id, state, old_state
        """
        try:
            # Query state_changed events from InfluxDB
            # Note: Using the existing InfluxDBEventClient from clients/influxdb_client.py
            events_df = await self.influxdb_client.query_events(
                start=start_time,
                stop=end_time,
                measurement="home_assistant_events",
                filters={"event_type": "state_changed"},
            )

            if events_df.empty:
                return pd.DataFrame()

            # Ensure required columns
            required_cols = ["time", "entity_id"]
            for col in required_cols:
                if col not in events_df.columns:
                    logger.error(f"Missing required column: {col}")
                    return pd.DataFrame()

            # Convert time to datetime if needed
            if not pd.api.types.is_datetime64_any_dtype(events_df["time"]):
                events_df["time"] = pd.to_datetime(events_df["time"])

            # Sort by time
            return events_df.sort_values("time").reset_index(drop=True)


        except Exception as e:
            logger.error(f"Failed to query events from InfluxDB: {e}", exc_info=True)
            return pd.DataFrame()

    async def _analyze_temporal_patterns(
        self,
        rules: list[AssociationRule],
        events_df: pd.DataFrame,
    ) -> list[tuple[AssociationRule, float, int]]:
        """
        Analyze temporal consistency of association rules.

        For each rule X → Y, calculate:
        - Temporal consistency: % of times Y follows X within time window
        - Frequency: Number of occurrences

        Args:
            rules: List of association rules
            events_df: Events DataFrame

        Returns:
            List of (rule, consistency, frequency) tuples
        """
        temporal_patterns = []

        for rule in rules:
            # Only analyze pairwise rules (single trigger → single action)
            if len(rule.antecedent) != 1 or len(rule.consequent) != 1:
                continue

            trigger_entity = next(iter(rule.antecedent))
            action_entity = next(iter(rule.consequent))

            # Calculate temporal consistency
            consistency, frequency = self._calculate_temporal_consistency(
                events_df,
                trigger_entity,
                action_entity,
            )

            if consistency >= self.min_consistency and frequency >= self.min_occurrences:
                temporal_patterns.append((rule, consistency, frequency))

        # Sort by confidence * consistency * frequency
        temporal_patterns.sort(
            key=lambda x: x[0].confidence * x[1] * np.log1p(x[2]),
            reverse=True,
        )

        return temporal_patterns

    def _calculate_temporal_consistency(
        self,
        events_df: pd.DataFrame,
        trigger_entity: str,
        action_entity: str,
    ) -> tuple[float, int]:
        """
        Calculate temporal consistency for trigger → action pattern.

        Consistency = (# times action follows trigger within window) / (# trigger events)

        Args:
            events_df: Events DataFrame
            trigger_entity: Trigger entity ID
            action_entity: Action entity ID

        Returns:
            (consistency, frequency) tuple
        """
        # Get trigger events
        trigger_events = events_df[events_df["entity_id"] == trigger_entity].copy()

        if trigger_events.empty:
            return (0.0, 0)

        # Count how many times action follows trigger within window
        consistent_count = 0
        window_delta = timedelta(seconds=self.time_window_seconds)

        for _, trigger_event in trigger_events.iterrows():
            trigger_time = trigger_event["time"]
            window_end = trigger_time + window_delta

            # Check if action entity changed state within window
            action_in_window = events_df[
                (events_df["entity_id"] == action_entity) &
                (events_df["time"] > trigger_time) &
                (events_df["time"] <= window_end)
            ]

            if not action_in_window.empty:
                consistent_count += 1

        consistency = consistent_count / len(trigger_events)
        frequency = consistent_count

        return (consistency, frequency)

    def _validate_synergies(
        self,
        temporal_patterns: list[tuple[AssociationRule, float, int]],
    ) -> list[DiscoveredSynergy]:
        """
        Validate and convert temporal patterns to DiscoveredSynergy objects.

        Filters out:
        - Self-loops (entity triggering itself)
        - Reverse duplicates (A→B and B→A, keep only stronger one)

        Args:
            temporal_patterns: List of (rule, consistency, frequency) tuples

        Returns:
            List of validated DiscoveredSynergy objects
        """
        validated = []
        seen_pairs = set()

        for rule, consistency, frequency in temporal_patterns:
            trigger_entity = next(iter(rule.antecedent))
            action_entity = next(iter(rule.consequent))

            # Skip self-loops
            if trigger_entity == action_entity:
                continue

            # Skip reverse duplicates
            pair = tuple(sorted([trigger_entity, action_entity]))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            # Create DiscoveredSynergy
            synergy = DiscoveredSynergy(
                trigger_entity=trigger_entity,
                action_entity=action_entity,
                support=rule.support,
                confidence=rule.confidence,
                lift=rule.lift,
                frequency=frequency,
                consistency=consistency,
                time_window_seconds=self.time_window_seconds,
                discovered_at=datetime.now(timezone.utc),
                source="mined",
            )

            validated.append(synergy)

        # Sort by impact score (confidence * consistency * log(frequency))
        validated.sort(
            key=lambda s: s.confidence * s.consistency * np.log1p(s.frequency),
            reverse=True,
        )

        return validated

    def get_statistics(
        self,
        discovered_synergies: list[DiscoveredSynergy],
    ) -> dict[str, Any]:
        """
        Calculate statistics for discovered synergies.

        Args:
            discovered_synergies: List of discovered synergies

        Returns:
            Dictionary with statistics
        """
        if not discovered_synergies:
            return {
                "total_count": 0,
                "avg_confidence": 0,
                "avg_consistency": 0,
                "avg_frequency": 0,
                "avg_lift": 0,
            }

        return {
            "total_count": len(discovered_synergies),
            "avg_confidence": np.mean([s.confidence for s in discovered_synergies]),
            "avg_consistency": np.mean([s.consistency for s in discovered_synergies]),
            "avg_frequency": np.mean([s.frequency for s in discovered_synergies]),
            "avg_lift": np.mean([s.lift for s in discovered_synergies]),
            "max_frequency": max([s.frequency for s in discovered_synergies]),
            "min_frequency": min([s.frequency for s in discovered_synergies]),
        }
