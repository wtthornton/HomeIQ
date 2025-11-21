"""
Duration Pattern Detector

Detects duration-based patterns using statistical analysis and ML clustering.
Identifies patterns in device usage duration, auto-off timers, and efficiency patterns.

Story AI5.3: Converted to incremental processing with aggregate storage.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from .ml_pattern_detector import MLPatternDetector

logger = logging.getLogger(__name__)


class DurationDetector(MLPatternDetector):
    """
    Detects duration-based patterns in device usage.

    Analyzes patterns based on:
    - Device usage duration patterns
    - Auto-off timer detection
    - Efficiency pattern analysis
    - Duration clustering and classification
    """

    def __init__(
        self,
        min_duration_seconds: int = 30,
        max_duration_hours: int = 24,
        duration_bins: int = 10,
        efficiency_threshold: float = 0.8,
        auto_off_tolerance_minutes: int = 5,
        aggregate_client=None,
        **kwargs,
    ):
        """
        Initialize duration detector.

        Args:
            min_duration_seconds: Minimum duration to consider
            max_duration_hours: Maximum duration to consider
            duration_bins: Number of bins for duration analysis
            efficiency_threshold: Threshold for efficiency patterns
            auto_off_tolerance_minutes: Tolerance for auto-off detection
            aggregate_client: PatternAggregateClient for storing daily aggregates (Story AI5.3)
            **kwargs: Additional MLPatternDetector parameters
        """
        super().__init__(**kwargs)
        self.min_duration_seconds = min_duration_seconds
        self.max_duration_hours = max_duration_hours
        self.duration_bins = duration_bins
        self.efficiency_threshold = efficiency_threshold
        self.auto_off_tolerance_minutes = auto_off_tolerance_minutes
        self.aggregate_client = aggregate_client

        logger.info(f"DurationDetector initialized: min_duration={min_duration_seconds}s, max_duration={max_duration_hours}h")

    def detect_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect duration patterns in events.

        Args:
            events_df: Events DataFrame with time, entity_id, state columns

        Returns:
            List of duration pattern dictionaries
        """
        start_time = datetime.utcnow()

        if not self._validate_events_dataframe(events_df):
            return []

        # Optimize DataFrame for processing
        events_df = self._optimize_dataframe(events_df)

        # Detect different types of duration patterns
        patterns = []

        # 1. Device usage duration patterns
        usage_duration_patterns = self._detect_usage_duration_patterns(events_df)
        patterns.extend(usage_duration_patterns)

        # 2. Auto-off timer patterns
        auto_off_patterns = self._detect_auto_off_patterns(events_df)
        patterns.extend(auto_off_patterns)

        # 3. Efficiency patterns
        efficiency_patterns = self._detect_efficiency_patterns(events_df)
        patterns.extend(efficiency_patterns)

        # 4. Duration clustering patterns
        duration_cluster_patterns = self._detect_duration_clusters(events_df)
        patterns.extend(duration_cluster_patterns)

        # 5. Statistical duration patterns
        statistical_patterns = self._detect_statistical_duration_patterns(events_df)
        patterns.extend(statistical_patterns)

        # Cluster similar duration patterns using ML
        if self.enable_ml and len(patterns) > 2:
            patterns = self._cluster_duration_patterns(patterns)

        # Update statistics
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        self.detection_stats["total_patterns"] += len(patterns)
        self.detection_stats["processing_time"] += processing_time

        logger.info(f"Detected {len(patterns)} duration patterns in {processing_time:.2f}s")

        # Story AI5.3: Store daily aggregates to InfluxDB
        if self.aggregate_client and patterns:
            self._store_daily_aggregates(patterns, events_df)

        return patterns

    def _store_daily_aggregates(self, patterns: list[dict], events_df: pd.DataFrame) -> None:
        """
        Store daily aggregates to InfluxDB.

        Story AI5.3: Incremental pattern processing with aggregate storage.

        Args:
            patterns: List of detected patterns
            events_df: Original events DataFrame
        """
        try:
            # Get date from events
            if events_df.empty or "time" not in events_df.columns:
                logger.warning("Cannot determine date from events for aggregate storage")
                return

            # Use the date of the first event (assuming 24h window)
            date = pd.to_datetime(events_df["time"].min()).date()
            date_str = date.strftime("%Y-%m-%d")

            logger.info(f"Storing daily aggregates for {date_str}")

            for pattern in patterns:
                entity_id = pattern.get("entity_id", pattern.get("devices", ["unknown"])[0] if pattern.get("devices") else "unknown")
                domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

                # Calculate metrics
                occurrences = pattern.get("occurrences", 0)
                confidence = pattern.get("confidence", 0.0)
                avg_duration = pattern.get("metadata", {}).get("avg_duration_seconds", 0)

                # Store aggregate
                try:
                    self.aggregate_client.write_duration_daily(
                        date=date_str,
                        entity_id=entity_id,
                        domain=domain,
                        occurrences=occurrences,
                        confidence=confidence,
                        avg_duration_seconds=avg_duration,
                    )
                except Exception as e:
                    logger.error(f"Failed to store aggregate for {entity_id}: {e}", exc_info=True)

            logger.info(f"✅ Stored {len(patterns)} daily aggregates to InfluxDB")

        except Exception as e:
            logger.error(f"Error storing daily aggregates: {e}", exc_info=True)

    def _detect_usage_duration_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect device usage duration patterns.

        Args:
            events_df: Events DataFrame

        Returns:
            List of usage duration patterns
        """
        patterns = []

        # Group by device and analyze usage durations
        for entity_id, device_events in events_df.groupby("entity_id"):
            if len(device_events) < self.min_occurrences:
                continue

            # Calculate usage durations
            durations = self._calculate_usage_durations(device_events)

            if len(durations) < self.min_occurrences:
                continue

            # Filter durations by valid range
            valid_durations = [
                d for d in durations
                if self.min_duration_seconds <= d <= self.max_duration_hours * 3600
            ]

            if len(valid_durations) < self.min_occurrences:
                continue

            # Analyze duration patterns
            duration_analysis = self._analyze_duration_patterns(valid_durations)

            # Calculate confidence
            confidence = self._calculate_duration_confidence(
                len(valid_durations), duration_analysis,
            )

            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type="usage_duration",
                    pattern_id=self._generate_pattern_id("duration"),
                    confidence=confidence,
                    occurrences=len(valid_durations),
                    devices=[entity_id],
                    metadata={
                        "entity_id": entity_id,
                        "avg_duration_seconds": duration_analysis["mean"],
                        "median_duration_seconds": duration_analysis["median"],
                        "std_duration_seconds": duration_analysis["std"],
                        "min_duration_seconds": duration_analysis["min"],
                        "max_duration_seconds": duration_analysis["max"],
                        "duration_consistency": duration_analysis["consistency"],
                        "duration_distribution": duration_analysis["distribution"],
                        "efficiency_score": duration_analysis["efficiency"],
                        "first_usage": device_events["time"].min().isoformat(),
                        "last_usage": device_events["time"].max().isoformat(),
                    },
                )
                patterns.append(pattern)

        return patterns

    def _detect_auto_off_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect auto-off timer patterns.

        Args:
            events_df: Events DataFrame

        Returns:
            List of auto-off patterns
        """
        patterns = []

        # Group by device and find auto-off patterns
        for entity_id, device_events in events_df.groupby("entity_id"):
            if len(device_events) < self.min_occurrences:
                continue

            # Find auto-off patterns
            auto_off_events = self._find_auto_off_events(device_events)

            if len(auto_off_events) < self.min_occurrences:
                continue

            # Analyze auto-off patterns
            auto_off_analysis = self._analyze_auto_off_patterns(auto_off_events)

            # Calculate confidence
            confidence = self._calculate_auto_off_confidence(
                len(auto_off_events), auto_off_analysis,
            )

            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type="auto_off",
                    pattern_id=self._generate_pattern_id("auto_off"),
                    confidence=confidence,
                    occurrences=len(auto_off_events),
                    devices=[entity_id],
                    metadata={
                        "entity_id": entity_id,
                        "avg_auto_off_duration_minutes": auto_off_analysis["avg_duration_minutes"],
                        "auto_off_consistency": auto_off_analysis["consistency"],
                        "auto_off_timer_accuracy": auto_off_analysis["accuracy"],
                        "auto_off_distribution": auto_off_analysis["distribution"],
                        "first_auto_off": auto_off_events[0]["time"].isoformat(),
                        "last_auto_off": auto_off_events[-1]["time"].isoformat(),
                    },
                )
                patterns.append(pattern)

        return patterns

    def _detect_efficiency_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect efficiency patterns in device usage.

        Args:
            events_df: Events DataFrame

        Returns:
            List of efficiency patterns
        """
        patterns = []

        # Group by device and analyze efficiency
        for entity_id, device_events in events_df.groupby("entity_id"):
            if len(device_events) < self.min_occurrences:
                continue

            # Calculate efficiency metrics
            efficiency_metrics = self._calculate_efficiency_metrics(device_events)

            if efficiency_metrics["efficiency_score"] < self.efficiency_threshold:
                continue

            # Calculate confidence
            confidence = self._calculate_efficiency_confidence(efficiency_metrics)

            if confidence >= self.min_confidence:
                pattern = self._create_pattern_dict(
                    pattern_type="efficiency",
                    pattern_id=self._generate_pattern_id("efficiency"),
                    confidence=confidence,
                    occurrences=len(device_events),
                    devices=[entity_id],
                    metadata={
                        "entity_id": entity_id,
                        "efficiency_score": efficiency_metrics["efficiency_score"],
                        "usage_frequency": efficiency_metrics["usage_frequency"],
                        "waste_score": efficiency_metrics["waste_score"],
                        "optimization_potential": efficiency_metrics["optimization_potential"],
                        "efficiency_trend": efficiency_metrics["trend"],
                        "recommended_actions": efficiency_metrics["recommendations"],
                    },
                )
                patterns.append(pattern)

        return patterns

    def _detect_duration_clusters(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect duration clusters using ML clustering.

        Args:
            events_df: Events DataFrame

        Returns:
            List of duration cluster patterns
        """
        patterns = []

        # Extract duration features for clustering
        duration_features = self._extract_duration_features(events_df)

        if len(duration_features) < 3:
            return patterns

        try:
            from sklearn.cluster import KMeans

            # Determine optimal number of clusters
            n_clusters = min(5, len(duration_features) // 2)
            if n_clusters < 2:
                return patterns

            # Cluster durations
            kmeans = KMeans(n_clusters=n_clusters, random_state=42)
            cluster_labels = kmeans.fit_predict(duration_features)

            # Analyze each cluster
            for cluster_id in range(n_clusters):
                cluster_durations = duration_features[cluster_labels == cluster_id]

                if len(cluster_durations) < self.min_occurrences:
                    continue

                cluster_confidence = self._calculate_cluster_confidence(
                    cluster_durations, cluster_id, kmeans,
                )

                if cluster_confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type="duration_cluster",
                        pattern_id=self._generate_pattern_id("duration_cluster"),
                        confidence=cluster_confidence,
                        occurrences=len(cluster_durations),
                        devices=[],  # Will be filled from cluster data
                        metadata={
                            "cluster_id": cluster_id,
                            "cluster_size": len(cluster_durations),
                            "cluster_characteristics": self._describe_duration_cluster(
                                cluster_durations, cluster_id,
                            ),
                            "cluster_centroid": kmeans.cluster_centers_[cluster_id].tolist(),
                        },
                    )
                    patterns.append(pattern)

        except Exception as e:
            logger.warning(f"Duration clustering failed: {e}")

        return patterns

    def _detect_statistical_duration_patterns(self, events_df: pd.DataFrame) -> list[dict]:
        """
        Detect statistical patterns in durations.

        Args:
            events_df: Events DataFrame

        Returns:
            List of statistical duration patterns
        """
        patterns = []

        # Group by device and analyze statistical patterns
        for entity_id, device_events in events_df.groupby("entity_id"):
            if len(device_events) < self.min_occurrences:
                continue

            # Calculate durations
            durations = self._calculate_usage_durations(device_events)
            valid_durations = [
                d for d in durations
                if self.min_duration_seconds <= d <= self.max_duration_hours * 3600
            ]

            if len(valid_durations) < self.min_occurrences:
                continue

            # Perform statistical analysis
            statistical_analysis = self._perform_statistical_analysis(valid_durations)

            # Check for significant patterns
            if statistical_analysis["has_pattern"]:
                confidence = self._calculate_statistical_confidence(statistical_analysis)

                if confidence >= self.min_confidence:
                    pattern = self._create_pattern_dict(
                        pattern_type="statistical_duration",
                        pattern_id=self._generate_pattern_id("stat_duration"),
                        confidence=confidence,
                        occurrences=len(valid_durations),
                        devices=[entity_id],
                        metadata={
                            "entity_id": entity_id,
                            "statistical_test": statistical_analysis["test_name"],
                            "p_value": statistical_analysis["p_value"],
                            "test_statistic": statistical_analysis["test_statistic"],
                            "pattern_description": statistical_analysis["description"],
                            "confidence_interval": statistical_analysis["confidence_interval"],
                            "effect_size": statistical_analysis["effect_size"],
                        },
                    )
                    patterns.append(pattern)

        return patterns

    def _calculate_usage_durations(self, device_events: pd.DataFrame) -> list[float]:
        """
        Calculate usage durations for a device.

        Args:
            device_events: Device events DataFrame

        Returns:
            List of usage durations in seconds
        """
        durations = []
        events_sorted = device_events.sort_values("time")

        # Find on/off pairs
        on_events = events_sorted[events_sorted["state"] == "on"]
        off_events = events_sorted[events_sorted["state"] == "off"]

        for _, on_event in on_events.iterrows():
            # Find next off event
            next_off = off_events[off_events["time"] > on_event["time"]]

            if not next_off.empty:
                next_off_event = next_off.iloc[0]
                duration = (next_off_event["time"] - on_event["time"]).total_seconds()
                durations.append(duration)

        return durations

    def _analyze_duration_patterns(self, durations: list[float]) -> dict[str, Any]:
        """
        Analyze duration patterns using statistical methods.

        Args:
            durations: List of durations in seconds

        Returns:
            Duration analysis dictionary
        """
        durations_array = np.array(durations)

        # Basic statistics
        mean_duration = np.mean(durations_array)
        median_duration = np.median(durations_array)
        std_duration = np.std(durations_array)
        min_duration = np.min(durations_array)
        max_duration = np.max(durations_array)

        # Consistency (inverse of coefficient of variation)
        consistency = 1.0 - (std_duration / mean_duration) if mean_duration > 0 else 0.0
        consistency = max(0.0, min(1.0, consistency))

        # Distribution analysis
        distribution = self._analyze_duration_distribution(durations_array)

        # Efficiency score
        efficiency = self._calculate_duration_efficiency(durations_array)

        return {
            "mean": mean_duration,
            "median": median_duration,
            "std": std_duration,
            "min": min_duration,
            "max": max_duration,
            "consistency": consistency,
            "distribution": distribution,
            "efficiency": efficiency,
        }

    def _analyze_duration_distribution(self, durations: np.ndarray) -> dict[str, Any]:
        """
        Analyze duration distribution.

        Args:
            durations: Array of durations

        Returns:
            Distribution analysis
        """
        # Create duration bins
        bins = np.linspace(durations.min(), durations.max(), self.duration_bins + 1)
        hist, bin_edges = np.histogram(durations, bins=bins)

        # Find peak duration
        peak_bin = np.argmax(hist)
        peak_duration = (bin_edges[peak_bin] + bin_edges[peak_bin + 1]) / 2

        # Calculate distribution characteristics
        return {
            "histogram": hist.tolist(),
            "bin_edges": bin_edges.tolist(),
            "peak_duration": peak_duration,
            "peak_frequency": hist[peak_bin],
            "distribution_type": self._classify_distribution(durations),
        }


    def _classify_distribution(self, durations: np.ndarray) -> str:
        """
        Classify duration distribution type.

        Args:
            durations: Array of durations

        Returns:
            Distribution type string
        """
        try:
            # Test for normal distribution
            _, p_value = stats.normaltest(durations)
            if p_value > 0.05:
                return "normal"

            # Test for log-normal distribution
            log_durations = np.log(durations[durations > 0])
            _, p_value = stats.normaltest(log_durations)
            if p_value > 0.05:
                return "log_normal"

            # Test for exponential distribution
            _, p_value = stats.kstest(durations, "expon", args=(0, durations.mean()))
            if p_value > 0.05:
                return "exponential"

            return "unknown"

        except Exception:
            return "unknown"

    def _calculate_duration_efficiency(self, durations: np.ndarray) -> float:
        """
        Calculate duration efficiency score.

        Args:
            durations: Array of durations

        Returns:
            Efficiency score (0.0 to 1.0)
        """
        if len(durations) == 0:
            return 0.0

        # Calculate efficiency based on consistency and optimal duration
        mean_duration = np.mean(durations)
        std_duration = np.std(durations)

        # Consistency component (lower std = higher efficiency)
        consistency_score = 1.0 - (std_duration / mean_duration) if mean_duration > 0 else 0.0

        # Optimal duration component (assume 1 hour is optimal for most devices)
        optimal_duration = 3600  # 1 hour in seconds
        duration_score = 1.0 - abs(mean_duration - optimal_duration) / optimal_duration
        duration_score = max(0.0, min(1.0, duration_score))

        # Combine scores
        efficiency = (consistency_score + duration_score) / 2.0

        return max(0.0, min(1.0, efficiency))

    def _find_auto_off_events(self, device_events: pd.DataFrame) -> list[dict]:
        """
        Find auto-off timer events.

        Args:
            device_events: Device events DataFrame

        Returns:
            List of auto-off events
        """
        auto_off_events = []
        events_sorted = device_events.sort_values("time")

        # Find on/off pairs with consistent duration
        on_events = events_sorted[events_sorted["state"] == "on"]
        off_events = events_sorted[events_sorted["state"] == "off"]

        for _, on_event in on_events.iterrows():
            # Find next off event
            next_off = off_events[off_events["time"] > on_event["time"]]

            if not next_off.empty:
                next_off_event = next_off.iloc[0]
                duration = (next_off_event["time"] - on_event["time"]).total_seconds()

                # Check if duration is consistent with auto-off timer
                if self._is_auto_off_duration(duration):
                    auto_off_events.append({
                        "time": on_event["time"],
                        "duration_seconds": duration,
                        "duration_minutes": duration / 60,
                    })

        return auto_off_events

    def _is_auto_off_duration(self, duration_seconds: float) -> bool:
        """
        Check if duration matches common auto-off timer values.

        Args:
            duration_seconds: Duration in seconds

        Returns:
            True if duration matches auto-off timer
        """
        # Common auto-off timer values (in minutes)
        common_timers = [5, 10, 15, 30, 60, 120, 240, 480]  # 5min to 8hours

        duration_minutes = duration_seconds / 60

        return any(abs(duration_minutes - timer) <= self.auto_off_tolerance_minutes for timer in common_timers)

    def _analyze_auto_off_patterns(self, auto_off_events: list[dict]) -> dict[str, Any]:
        """
        Analyze auto-off patterns.

        Args:
            auto_off_events: List of auto-off events

        Returns:
            Auto-off analysis
        """
        durations = [event["duration_minutes"] for event in auto_off_events]
        durations_array = np.array(durations)

        # Calculate statistics
        avg_duration = np.mean(durations_array)
        std_duration = np.std(durations_array)

        # Consistency (inverse of coefficient of variation)
        consistency = 1.0 - (std_duration / avg_duration) if avg_duration > 0 else 0.0
        consistency = max(0.0, min(1.0, consistency))

        # Accuracy (how close to expected timer values)
        accuracy = self._calculate_auto_off_accuracy(durations)

        # Distribution
        distribution = self._analyze_duration_distribution(durations_array * 60)  # Convert to seconds

        return {
            "avg_duration_minutes": avg_duration,
            "consistency": consistency,
            "accuracy": accuracy,
            "distribution": distribution,
        }

    def _calculate_auto_off_accuracy(self, durations: list[float]) -> float:
        """
        Calculate auto-off timer accuracy.

        Args:
            durations: List of durations in minutes

        Returns:
            Accuracy score (0.0 to 1.0)
        """
        if not durations:
            return 0.0

        # Common auto-off timer values
        common_timers = [5, 10, 15, 30, 60, 120, 240, 480]

        accuracy_scores = []
        for duration in durations:
            # Find closest timer
            closest_timer = min(common_timers, key=lambda x: abs(x - duration))
            error = abs(duration - closest_timer)
            accuracy = max(0.0, 1.0 - (error / closest_timer))
            accuracy_scores.append(accuracy)

        return np.mean(accuracy_scores)

    def _calculate_efficiency_metrics(self, device_events: pd.DataFrame) -> dict[str, Any]:
        """
        Calculate efficiency metrics for device usage.

        Args:
            device_events: Device events DataFrame

        Returns:
            Efficiency metrics
        """
        # Calculate usage durations
        durations = self._calculate_usage_durations(device_events)

        if not durations:
            return {
                "efficiency_score": 0.0,
                "usage_frequency": 0.0,
                "waste_score": 1.0,
                "optimization_potential": 0.0,
                "trend": "stable",
                "recommendations": [],
            }

        durations_array = np.array(durations)

        # Efficiency score based on consistency and optimal usage
        consistency = 1.0 - (np.std(durations_array) / np.mean(durations_array)) if np.mean(durations_array) > 0 else 0.0
        consistency = max(0.0, min(1.0, consistency))

        # Usage frequency (events per day)
        time_span_days = (device_events["time"].max() - device_events["time"].min()).total_seconds() / 86400
        usage_frequency = len(device_events) / max(time_span_days, 1)

        # Waste score (based on very short or very long durations)
        waste_score = self._calculate_waste_score(durations_array)

        # Optimization potential
        optimization_potential = 1.0 - consistency

        # Trend analysis
        trend = self._analyze_efficiency_trend(device_events)

        # Recommendations
        recommendations = self._generate_efficiency_recommendations(
            durations_array, consistency, waste_score,
        )

        # Overall efficiency score
        efficiency_score = (consistency + (1.0 - waste_score) + (1.0 - optimization_potential)) / 3.0

        return {
            "efficiency_score": max(0.0, min(1.0, efficiency_score)),
            "usage_frequency": usage_frequency,
            "waste_score": waste_score,
            "optimization_potential": optimization_potential,
            "trend": trend,
            "recommendations": recommendations,
        }

    def _calculate_waste_score(self, durations: np.ndarray) -> float:
        """
        Calculate waste score based on duration patterns.

        Args:
            durations: Array of durations in seconds

        Returns:
            Waste score (0.0 to 1.0, higher = more waste)
        """
        if len(durations) == 0:
            return 0.0

        # Define waste thresholds
        very_short_threshold = 60  # 1 minute
        very_long_threshold = 8 * 3600  # 8 hours

        # Calculate waste percentages
        very_short_pct = np.sum(durations < very_short_threshold) / len(durations)
        very_long_pct = np.sum(durations > very_long_threshold) / len(durations)

        # Waste score is combination of both
        waste_score = (very_short_pct + very_long_pct) / 2.0

        return max(0.0, min(1.0, waste_score))

    def _analyze_efficiency_trend(self, device_events: pd.DataFrame) -> str:
        """
        Analyze efficiency trend over time.

        Args:
            device_events: Device events DataFrame

        Returns:
            Trend description
        """
        if len(device_events) < 4:
            return "insufficient_data"

        # Calculate durations over time
        durations = self._calculate_usage_durations(device_events)

        if len(durations) < 3:
            return "insufficient_data"

        # Simple trend analysis
        durations_array = np.array(durations)
        x = np.arange(len(durations_array))

        try:
            # Linear regression
            slope, _, _, _, _ = stats.linregress(x, durations_array)

            if slope > 0.1:
                return "improving"
            if slope < -0.1:
                return "declining"
            return "stable"
        except Exception:
            return "unknown"

    def _generate_efficiency_recommendations(
        self,
        durations: np.ndarray,
        consistency: float,
        waste_score: float,
    ) -> list[str]:
        """
        Generate efficiency recommendations.

        Args:
            durations: Array of durations
            consistency: Consistency score
            waste_score: Waste score

        Returns:
            List of recommendations
        """
        recommendations = []

        if consistency < 0.5:
            recommendations.append("Consider setting up automation timers for more consistent usage")

        if waste_score > 0.3:
            recommendations.append("Review usage patterns to reduce waste")

        if np.mean(durations) > 4 * 3600:  # Average > 4 hours
            recommendations.append("Consider shorter usage sessions")

        if np.mean(durations) < 300:  # Average < 5 minutes
            recommendations.append("Consider longer usage sessions for better efficiency")

        return recommendations

    def _extract_duration_features(self, events_df: pd.DataFrame) -> np.ndarray:
        """
        Extract duration features for clustering.

        Args:
            events_df: Events DataFrame

        Returns:
            Feature matrix for clustering
        """
        features = []

        # Group by device and extract features
        for _entity_id, device_events in events_df.groupby("entity_id"):
            durations = self._calculate_usage_durations(device_events)
            valid_durations = [
                d for d in durations
                if self.min_duration_seconds <= d <= self.max_duration_hours * 3600
            ]

            if len(valid_durations) >= 2:
                durations_array = np.array(valid_durations)

                feature_vector = [
                    np.mean(durations_array),  # Mean duration
                    np.std(durations_array),   # Std duration
                    np.median(durations_array),  # Median duration
                    len(valid_durations),      # Usage count
                    np.min(durations_array),   # Min duration
                    np.max(durations_array),    # Max duration
                ]
                features.append(feature_vector)

        return np.array(features) if features else np.array([])

    def _calculate_duration_confidence(self, occurrences: int, duration_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for duration patterns.

        Args:
            occurrences: Number of occurrences
            duration_analysis: Duration analysis results

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from occurrences
        base_confidence = min(occurrences / 15.0, 1.0)

        # Consistency bonus
        consistency = duration_analysis.get("consistency", 0.0)
        consistency_bonus = consistency * 0.3

        # Efficiency bonus
        efficiency = duration_analysis.get("efficiency", 0.0)
        efficiency_bonus = efficiency * 0.2

        total_confidence = base_confidence + consistency_bonus + efficiency_bonus

        return min(total_confidence, 1.0)

    def _calculate_auto_off_confidence(self, occurrences: int, auto_off_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for auto-off patterns.

        Args:
            occurrences: Number of occurrences
            auto_off_analysis: Auto-off analysis results

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from occurrences
        base_confidence = min(occurrences / 10.0, 1.0)

        # Consistency bonus
        consistency = auto_off_analysis.get("consistency", 0.0)
        consistency_bonus = consistency * 0.4

        # Accuracy bonus
        accuracy = auto_off_analysis.get("accuracy", 0.0)
        accuracy_bonus = accuracy * 0.3

        total_confidence = base_confidence + consistency_bonus + accuracy_bonus

        return min(total_confidence, 1.0)

    def _calculate_efficiency_confidence(self, efficiency_metrics: dict[str, Any]) -> float:
        """
        Calculate confidence for efficiency patterns.

        Args:
            efficiency_metrics: Efficiency metrics

        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from efficiency score
        base_confidence = efficiency_metrics.get("efficiency_score", 0.0)

        # Usage frequency bonus
        frequency = efficiency_metrics.get("usage_frequency", 0.0)
        frequency_bonus = min(frequency / 10.0, 0.2)

        # Waste score penalty
        waste_score = efficiency_metrics.get("waste_score", 0.0)
        waste_penalty = waste_score * 0.2

        total_confidence = base_confidence + frequency_bonus - waste_penalty

        return max(0.0, min(total_confidence, 1.0))

    def _calculate_cluster_confidence(self, cluster_durations: np.ndarray, cluster_id: int, kmeans_model) -> float:
        """
        Calculate confidence for duration clusters.

        Args:
            cluster_durations: Durations in cluster
            cluster_id: Cluster identifier
            kmeans_model: Fitted KMeans model

        Returns:
            Confidence score (0.0 to 1.0)
        """
        occurrences = len(cluster_durations)
        base_confidence = min(occurrences / 8.0, 1.0)

        # Cluster cohesion bonus
        try:
            distances = kmeans_model.transform(cluster_durations)
            avg_distance = np.mean(distances[:, cluster_id])
            cohesion_bonus = max(0.0, 1.0 - avg_distance) * 0.3
            base_confidence += cohesion_bonus
        except Exception:
            pass

        return min(base_confidence, 1.0)

    def _describe_duration_cluster(self, cluster_durations: np.ndarray, cluster_id: int) -> dict[str, Any]:
        """
        Describe duration cluster characteristics.

        Args:
            cluster_durations: Durations in cluster
            cluster_id: Cluster identifier

        Returns:
            Cluster characteristics
        """
        return {
            "cluster_id": cluster_id,
            "duration_count": len(cluster_durations),
            "avg_duration_seconds": np.mean(cluster_durations),
            "median_duration_seconds": np.median(cluster_durations),
            "std_duration_seconds": np.std(cluster_durations),
            "min_duration_seconds": np.min(cluster_durations),
            "max_duration_seconds": np.max(cluster_durations),
        }

    def _perform_statistical_analysis(self, durations: list[float]) -> dict[str, Any]:
        """
        Perform statistical analysis on durations.

        Args:
            durations: List of durations

        Returns:
            Statistical analysis results
        """
        durations_array = np.array(durations)

        # Test for normal distribution
        try:
            statistic, p_value = stats.normaltest(durations_array)

            if p_value < 0.05:
                # Not normal, test for other distributions
                return {
                    "has_pattern": True,
                    "test_name": "normality_test",
                    "p_value": p_value,
                    "test_statistic": statistic,
                    "description": "Non-normal duration distribution detected",
                    "confidence_interval": stats.norm.interval(0.95, loc=np.mean(durations_array), scale=np.std(durations_array)),
                    "effect_size": "medium",
                }
            return {
                "has_pattern": False,
                "test_name": "normality_test",
                "p_value": p_value,
                "test_statistic": statistic,
                "description": "Normal duration distribution",
                "confidence_interval": None,
                "effect_size": "small",
            }

        except Exception as e:
            logger.warning(f"Statistical analysis failed: {e}")
            return {
                "has_pattern": False,
                "test_name": "error",
                "p_value": 1.0,
                "test_statistic": 0.0,
                "description": "Analysis failed",
                "confidence_interval": None,
                "effect_size": "unknown",
            }

    def _calculate_statistical_confidence(self, statistical_analysis: dict[str, Any]) -> float:
        """
        Calculate confidence for statistical patterns.

        Args:
            statistical_analysis: Statistical analysis results

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if not statistical_analysis["has_pattern"]:
            return 0.0

        # Base confidence from p-value
        p_value = statistical_analysis["p_value"]
        base_confidence = 1.0 - p_value

        # Effect size bonus
        effect_size = statistical_analysis.get("effect_size", "small")
        effect_bonus = {
            "small": 0.1,
            "medium": 0.2,
            "large": 0.3,
        }.get(effect_size, 0.1)

        total_confidence = base_confidence + effect_bonus

        return max(0.0, min(total_confidence, 1.0))

    def _cluster_duration_patterns(self, patterns: list[dict]) -> list[dict]:
        """
        Cluster similar duration patterns using ML.

        Args:
            patterns: List of duration patterns

        Returns:
            Clustered patterns with cluster information
        """
        if len(patterns) < 3:
            return patterns

        try:
            # Extract features for clustering
            features = self._extract_duration_pattern_features(patterns)

            # Cluster patterns
            patterns = self._cluster_patterns(patterns, features)

            logger.info(f"Clustered {len(patterns)} duration patterns")

        except Exception as e:
            logger.warning(f"Duration pattern clustering failed: {e}")

        return patterns

    def _extract_duration_pattern_features(self, patterns: list[dict]) -> np.ndarray:
        """
        Extract features for duration pattern clustering.

        Args:
            patterns: List of duration patterns

        Returns:
            Feature matrix for clustering
        """
        features = []

        for pattern in patterns:
            metadata = pattern["metadata"]

            # Extract numerical features
            feature_vector = [
                pattern["occurrences"],
                pattern["confidence"],
                len(pattern["devices"]),
                metadata.get("avg_duration_seconds", 0),
                metadata.get("duration_consistency", 0.0),
                metadata.get("efficiency_score", 0.0),
                metadata.get("auto_off_consistency", 0.0),
                metadata.get("waste_score", 0.0),
            ]

            # Add pattern type encoding
            pattern_type = pattern["pattern_type"]
            type_encoding = {
                "usage_duration": 0,
                "auto_off": 1,
                "efficiency": 2,
                "duration_cluster": 3,
                "statistical_duration": 4,
            }.get(pattern_type, 0)
            feature_vector.append(type_encoding)

            features.append(feature_vector)

        return np.array(features)
