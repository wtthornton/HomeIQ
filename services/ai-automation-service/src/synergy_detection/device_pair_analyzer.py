"""
Device Pair Analyzer with Usage Frequency and Area Traffic

Enhances synergy detection with InfluxDB usage statistics to prioritize
high-impact automation opportunities.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.2: Same-Area Device Pair Detection
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


class DevicePairAnalyzer:
    """
    Analyzes device pairs with usage frequency and area traffic data.

    Enhances basic synergy detection (AI3.1) with InfluxDB usage statistics
    to calculate more accurate impact scores.

    Story AI3.2: Same-Area Device Pair Detection
    """

    def __init__(self, influxdb_client):
        """
        Initialize device pair analyzer.

        Args:
            influxdb_client: InfluxDB client for usage queries
        """
        self.influxdb = influxdb_client
        self._usage_cache = {}
        self._area_cache = {}

        logger.info("DevicePairAnalyzer initialized")

    async def get_device_usage_frequency(
        self,
        device_id: str,
        days: int = 30,
    ) -> float:
        """
        Get device usage frequency from InfluxDB.

        Args:
            device_id: Entity ID to query
            days: Number of days to analyze (default: 30)

        Returns:
            Usage frequency score (0.0-1.0) using continuous logarithmic scale
            - 1.0: Very active (approaches 1.0 for 100+ events/day)
            - Varies continuously based on actual event frequency
            - Preserves granular differences (no bucket collisions)
        """
        # Check cache
        cache_key = f"{device_id}_{days}"
        if cache_key in self._usage_cache:
            return self._usage_cache[cache_key]

        try:
            # Query InfluxDB for event count
            query = f"""
            from(bucket: "home_assistant_events")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
              |> filter(fn: (r) => r["entity_id"] == "{device_id}")
              |> count()
            """

            # InfluxDB query_api.query is synchronous
            result = self.influxdb.query_api.query(query, org=self.influxdb.org)

            # Parse result to get event count
            event_count = 0
            if result and len(result) > 0:
                for table in result:
                    for record in table.records:
                        event_count += record.get_value()

            # Calculate frequency score using continuous logarithmic scale
            # Eliminates bucket collisions and preserves granular differences
            events_per_day = event_count / days if days > 0 else 0

            if events_per_day > 0:
                # Smooth curve: 0 events = 0.05, 100+ events approaches 1.0
                # Formula: 0.05 + 0.95 * (1 - 1/(1 + events_per_day/15))
                frequency = min(1.0, 0.05 + 0.95 * (1 - 1 / (1 + events_per_day / 15)))
            else:
                frequency = 0.05  # Minimum for devices with no events

            # Cache result
            self._usage_cache[cache_key] = frequency

            logger.debug(
                f"Device usage: {device_id} = {event_count} events in {days} days "
                f"({events_per_day:.1f}/day) → frequency score: {frequency}",
            )

            return frequency

        except Exception as e:
            logger.warning(f"Failed to get usage for {device_id}: {e}")
            return 0.5  # Default moderate usage

    async def get_area_traffic(
        self,
        area: str,
        entities: list[dict],
        days: int = 30,
    ) -> float:
        """
        Get area traffic score based on all entities in that area.

        Args:
            area: Area ID
            entities: List of entities from data-api
            days: Number of days to analyze

        Returns:
            Area traffic score (0.5-1.0)
            - 1.0: Very high traffic (bedroom, kitchen)
            - 0.8: High traffic (living room, bathroom)
            - 0.6: Medium traffic (office, garage)
            - 0.5: Low traffic (storage, utility room)
        """
        # Check cache
        cache_key = f"{area}_{days}"
        if cache_key in self._area_cache:
            return self._area_cache[cache_key]

        try:
            # Get all entities in this area
            area_entities = [e["entity_id"] for e in entities if e.get("area_id") == area]

            if not area_entities:
                return 0.5  # Default low traffic

            # Query total events for area (sample up to 10 entities to avoid expensive queries)
            sample_entities = area_entities[:10]
            entity_filter = " or ".join([f'r["entity_id"] == "{e}"' for e in sample_entities])

            query = f"""
            from(bucket: "home_assistant_events")
              |> range(start: -{days}d)
              |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
              |> filter(fn: (r) => {entity_filter})
              |> count()
            """

            # InfluxDB query_api.query is synchronous
            result = self.influxdb.query_api.query(query, org=self.influxdb.org)

            # Parse result
            total_events = 0
            if result and len(result) > 0:
                for table in result:
                    for record in table.records:
                        total_events += record.get_value()

            # Calculate traffic score (events per day across all entities)
            events_per_day = total_events / days if days > 0 else 0

            if events_per_day >= 500:
                traffic = 1.0  # Very high (bedroom, kitchen)
            elif events_per_day >= 200:
                traffic = 0.9  # High (living room, bathroom)
            elif events_per_day >= 100:
                traffic = 0.7  # Medium-high (office, hallway)
            elif events_per_day >= 50:
                traffic = 0.6  # Medium (guest room, garage)
            else:
                traffic = 0.5  # Low (storage, utility)

            # Cache result
            self._area_cache[cache_key] = traffic

            logger.debug(
                f"Area traffic: {area} = {total_events} events in {days} days "
                f"({events_per_day:.1f}/day) → traffic score: {traffic}",
            )

            return traffic

        except Exception as e:
            logger.warning(f"Failed to get area traffic for {area}: {e}")
            return 0.7  # Default moderate traffic

    async def calculate_advanced_impact_score(
        self,
        synergy: dict,
        entities: list[dict],
        all_synergies_in_area: list[dict] | None = None,
        days: int = 30,
    ) -> float:
        """
        Calculate advanced impact score using usage and area data.

        Phase 4: Enhanced scoring with time-of-day awareness and area normalization

        Formula:
            impact = benefit_score * usage_freq * area_traffic * time_weight * health_factor * (1 - complexity_penalty)
            Then normalized within area if all_synergies_in_area provided

        Args:
            synergy: Synergy opportunity from DeviceSynergyDetector
            entities: List of entities for area lookup
            all_synergies_in_area: Optional list of all synergies in same area for normalization
            days: Days of history to analyze

        Returns:
            Advanced impact score (0.0-1.0)
        """
        try:
            # Get base benefit score and complexity from synergy
            # Prefer relationship_config.benefit_score (raw benefit), fallback to impact_score
            base_benefit = 0.7  # Default
            if "relationship_config" in synergy and isinstance(synergy["relationship_config"], dict):
                base_benefit = synergy["relationship_config"].get("benefit_score", base_benefit)
            else:
                # Fallback: use impact_score (might already have adjustments, but better than default)
                base_benefit = synergy.get("impact_score", base_benefit)

            complexity = synergy.get("complexity", "medium")

            # Complexity penalty
            complexity_penalty = {
                "low": 0.0,
                "medium": 0.1,
                "high": 0.3,
            }.get(complexity, 0.1)

            # Get usage frequencies for both devices
            trigger_entity = synergy.get("trigger_entity")
            action_entity = synergy.get("action_entity")

            trigger_usage = await self.get_device_usage_frequency(trigger_entity, days)
            action_usage = await self.get_device_usage_frequency(action_entity, days)

            # Combined usage frequency - use minimum (weakest link principle)
            # Automation is limited by least active device
            usage_freq = min(trigger_usage, action_usage)

            # Get device health scores from entities (if available)
            trigger_entity_data = next((e for e in entities if e.get("entity_id") == trigger_entity), {})
            action_entity_data = next((e for e in entities if e.get("entity_id") == action_entity), {})

            # MinMaxScaler pattern: Normalize 0-100 health score to 0-1 range
            # Default to 100 if not available (assume healthy device)
            trigger_health = trigger_entity_data.get("health_score", 100) / 100.0
            action_health = action_entity_data.get("health_score", 100) / 100.0

            # Geometric mean for health (both devices must be reasonably healthy)
            # Geometric mean better for multiplicative factors
            health_factor = (trigger_health * action_health) ** 0.5

            # Log health factor for debugging (only if different from 1.0 to avoid spam)
            if health_factor < 0.99:
                logger.debug(
                    f"Health factor < 1.0: trigger={trigger_entity} ({trigger_health:.2f}), "
                    f"action={action_entity} ({action_health:.2f}), factor={health_factor:.3f}",
                )

            # Get area traffic
            area = synergy.get("area", "unknown")
            area_traffic = await self.get_area_traffic(area, entities, days)

            # NEW: Time-of-day weighting (Phase 4)
            time_weight = 1.0  # Default
            if self.influxdb:
                peak_usage = await self._check_peak_hours(trigger_entity, action_entity)
                if peak_usage:
                    time_weight = 1.2  # Boost impact for peak-hour usage

            # Calculate base impact with time weighting and health factor
            impact = base_benefit * usage_freq * area_traffic * time_weight * health_factor * (1 - complexity_penalty)

            # Debug logging for first few synergies to understand score calculation
            if hasattr(self, "_debug_count"):
                self._debug_count += 1
            else:
                self._debug_count = 1

            if self._debug_count <= 5:
                logger.info(
                    f"Advanced scoring sample {self._debug_count}: "
                    f"trigger={trigger_entity[:30]}, action={action_entity[:30]}, "
                    f"base={base_benefit:.2f}, usage={usage_freq:.3f}, area_traffic={area_traffic:.3f}, "
                    f"time={time_weight:.2f}, health={health_factor:.3f}, penalty={complexity_penalty:.2f}, "
                    f"impact={impact:.4f}",
                )

            # Apply area-specific normalization if multiple synergies in same area
            if all_synergies_in_area and len(all_synergies_in_area) > 1:
                # Calculate percentile position within area based on base benefit scores
                # This provides relative ranking without needing full impact calculations
                area_base_scores = []
                for s in all_synergies_in_area:
                    # Try to get benefit_score from relationship_config first (most accurate)
                    s_base = 0.7  # Default
                    if "relationship_config" in s and isinstance(s["relationship_config"], dict):
                        s_base = s["relationship_config"].get("benefit_score", s_base)
                    elif "relationship" in s:
                        # Fallback: try to get from COMPATIBLE_RELATIONSHIPS if we can
                        # For now, use impact_score as proxy if available
                        s_base = s.get("impact_score", s_base)
                    else:
                        # Last resort: use impact_score (might already include adjustments)
                        s_base = s.get("impact_score", s_base)
                    area_base_scores.append(s_base)

                # Sort to get percentile position
                sorted_scores = sorted(area_base_scores, reverse=True)
                try:
                    current_base = base_benefit
                    # Find position in sorted list (handle duplicates)
                    position = 0
                    for i, score in enumerate(sorted_scores):
                        if score <= current_base:
                            position = i
                            break
                    else:
                        position = len(sorted_scores) - 1

                    percentile_position = position / len(sorted_scores) if len(sorted_scores) > 1 else 0.5
                except (ValueError, ZeroDivisionError, IndexError):
                    percentile_position = 0.5  # Default to middle if not found

                # Normalization factor: 0.95-1.05 range based on position
                # Higher percentile (better base score) = slight boost, lower = slight penalty
                normalization_factor = 0.95 + (percentile_position * 0.1)
                impact *= normalization_factor

                logger.debug(
                    f"Area normalization: {area} position={percentile_position:.2f}, "
                    f"factor={normalization_factor:.3f}, area_size={len(all_synergies_in_area)}",
                )

            logger.debug(
                f"Advanced impact: {trigger_entity} + {action_entity} = {impact:.3f} "
                f"(benefit={base_benefit}, usage={usage_freq:.2f}, area={area_traffic}, "
                f"time_weight={time_weight}, health_factor={health_factor:.2f}, complexity_penalty={complexity_penalty})",
            )

            # Add deterministic tie-breaker and increase precision
            # Calculate deterministic micro-adjustment (0.0000-0.0099)
            # Uses MD5 hash for stable, deterministic ordering
            entity_pair = f"{trigger_entity}{action_entity}"
            entity_hash = int(hashlib.md5(entity_pair.encode()).hexdigest()[:8], 16)
            micro_adjust = (entity_hash % 100) / 10000.0  # 0.0000-0.0099

            # Round to 4 decimals for more precision (handles floating-point precision issues)
            # Increased from 3 to 4 decimals to show more distinction
            final_impact = round(impact + micro_adjust, 4)

            # Log final score with tie-breaker for debugging (first 5 only)
            if hasattr(self, "_debug_count") and self._debug_count <= 5:
                logger.info(
                    f"Final score with tie-breaker: {final_impact:.4f} "
                    f"(base={impact:.4f}, micro_adjust={micro_adjust:.4f}, entity_hash={entity_hash % 100})",
                )

            return final_impact

        except Exception as e:
            logger.warning(f"Failed to calculate advanced impact: {e}")
            return synergy.get("impact_score", 0.5)  # Fallback to basic score

    async def _check_peak_hours(self, trigger_entity: str, action_entity: str) -> bool:
        """
        Simple check: Are devices used during peak hours (6-10am or 6-10pm)?

        Phase 4: Time-of-day weighting enhancement

        This is a simple InfluxDB query, not complex graph analysis.

        Args:
            trigger_entity: Trigger entity ID
            action_entity: Action entity ID

        Returns:
            True if devices are used during peak hours
        """
        try:
            # Query for events during morning peak hours (6-10am) - last 30 days
            query_morning = f"""
            from(bucket: "home_assistant_events")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
              |> filter(fn: (r) => r["entity_id"] == "{trigger_entity}" or r["entity_id"] == "{action_entity}")
              |> filter(fn: (r) => hour(t: r._time) >= 6 and hour(t: r._time) < 10)
              |> count()
            """

            result_morning = self.influxdb.query_api.query(query_morning, org=self.influxdb.org)

            # Count events during morning peak
            morning_events = 0
            if result_morning and len(result_morning) > 0:
                for table in result_morning:
                    for record in table.records:
                        morning_events += record.get_value()

            # Query for events during evening peak hours (6-10pm) - last 30 days
            query_evening = f"""
            from(bucket: "home_assistant_events")
              |> range(start: -30d)
              |> filter(fn: (r) => r["_measurement"] == "home_assistant_events")
              |> filter(fn: (r) => r["entity_id"] == "{trigger_entity}" or r["entity_id"] == "{action_entity}")
              |> filter(fn: (r) => hour(t: r._time) >= 18 and hour(t: r._time) < 22)
              |> count()
            """

            result_evening = self.influxdb.query_api.query(query_evening, org=self.influxdb.org)

            # Count events during evening peak
            evening_events = 0
            if result_evening and len(result_evening) > 0:
                for table in result_evening:
                    for record in table.records:
                        evening_events += record.get_value()

            # If >30 events during peak hours, consider it peak usage
            total_peak = morning_events + evening_events
            if total_peak > 30:  # Simple threshold
                logger.debug(
                    f"Peak hours detected: {trigger_entity} + {action_entity} "
                    f"({morning_events} morning + {evening_events} evening = {total_peak} peak events)",
                )
                return True

            return False

        except Exception as e:
            logger.warning(f"Failed to check peak hours: {e}")
            return False

    def clear_cache(self):
        """Clear cached usage data."""
        self._usage_cache = {}
        self._area_cache = {}
        logger.debug("DevicePairAnalyzer cache cleared")

