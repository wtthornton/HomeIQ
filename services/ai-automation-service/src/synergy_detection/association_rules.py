"""
Association Rules Mining for Dynamic Synergy Discovery

Implements Apriori algorithm to discover frequent itemsets and
association rules from Home Assistant event co-occurrences.

Epic: Dynamic Synergy Discovery (#3)
Algorithm: Apriori (Agrawal & Srikant, 1994)
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import combinations

import pandas as pd

logger = logging.getLogger(__name__)


class AssociationRule:
    """Represents an association rule: X → Y"""

    def __init__(
        self,
        antecedent: frozenset[str],
        consequent: frozenset[str],
        support: float,
        confidence: float,
        lift: float
    ):
        """
        Initialize association rule.

        Args:
            antecedent: Set of items in the "if" part (X)
            consequent: Set of items in the "then" part (Y)
            support: P(X ∪ Y) - Frequency of pattern
            confidence: P(Y|X) - Reliability of rule
            lift: P(Y|X) / P(Y) - Strength of association
        """
        self.antecedent = antecedent
        self.consequent = consequent
        self.support = support
        self.confidence = confidence
        self.lift = lift

    def __str__(self):
        return (
            f"{set(self.antecedent)} → {set(self.consequent)} "
            f"(support={self.support:.3f}, confidence={self.confidence:.3f}, lift={self.lift:.2f})"
        )

    def __repr__(self):
        return self.__str__()


class AprioriMiner:
    """
    Apriori algorithm for frequent itemset mining.

    Key concepts:
    - Support: How often itemset appears in transactions
    - Confidence: Conditional probability P(Y|X)
    - Lift: How much more likely Y occurs given X vs. baseline
    """

    def __init__(
        self,
        min_support: float = 0.05,
        min_confidence: float = 0.7,
        min_lift: float = 1.5,
        max_itemset_size: int = 4
    ):
        """
        Initialize Apriori miner.

        Args:
            min_support: Minimum support threshold (0.0-1.0)
            min_confidence: Minimum confidence threshold (0.0-1.0)
            min_lift: Minimum lift threshold (>1.0 means positive correlation)
            max_itemset_size: Maximum size of itemsets to mine (2-4 recommended)
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_lift = min_lift
        self.max_itemset_size = max_itemset_size

        logger.info(
            f"AprioriMiner initialized: support={min_support}, "
            f"confidence={min_confidence}, lift={min_lift}, max_size={max_itemset_size}"
        )

    def mine_frequent_itemsets(
        self,
        transactions: list[set[str]]
    ) -> dict[frozenset[str], float]:
        """
        Mine frequent itemsets using Apriori algorithm.

        Args:
            transactions: List of transaction sets (each set = entities active in time window)

        Returns:
            Dictionary mapping itemsets to their support values
        """
        start_time = datetime.now(timezone.utc)
        total_transactions = len(transactions)

        if total_transactions == 0:
            logger.warning("No transactions provided for mining")
            return {}

        logger.info(f"⛏️ Mining frequent itemsets from {total_transactions} transactions...")

        # Step 1: Find frequent 1-itemsets
        item_counts = defaultdict(int)
        for transaction in transactions:
            for item in transaction:
                item_counts[item] += 1

        # Calculate support and filter by min_support
        frequent_itemsets = {}
        min_count = self.min_support * total_transactions

        for item, count in item_counts.items():
            if count >= min_count:
                itemset = frozenset([item])
                support = count / total_transactions
                frequent_itemsets[itemset] = support

        logger.info(f"  → Found {len(frequent_itemsets)} frequent 1-itemsets")

        # Step 2: Generate larger itemsets iteratively
        k = 2
        previous_frequent = set(frequent_itemsets.keys())

        while previous_frequent and k <= self.max_itemset_size:
            # Generate candidate k-itemsets from (k-1)-itemsets
            candidates = self._generate_candidates(previous_frequent, k)
            logger.debug(f"  → Generated {len(candidates)} {k}-itemset candidates")

            # Count candidate support
            candidate_counts = defaultdict(int)
            for transaction in transactions:
                transaction_frozen = frozenset(transaction)
                for candidate in candidates:
                    if candidate.issubset(transaction_frozen):
                        candidate_counts[candidate] += 1

            # Filter by min_support
            current_frequent = set()
            for candidate, count in candidate_counts.items():
                if count >= min_count:
                    support = count / total_transactions
                    frequent_itemsets[candidate] = support
                    current_frequent.add(candidate)

            logger.info(f"  → Found {len(current_frequent)} frequent {k}-itemsets")

            previous_frequent = current_frequent
            k += 1

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"✅ Mining complete in {duration:.2f}s: "
            f"{len(frequent_itemsets)} frequent itemsets found"
        )

        return frequent_itemsets

    def _generate_candidates(
        self,
        previous_itemsets: set[frozenset[str]],
        k: int
    ) -> set[frozenset[str]]:
        """
        Generate k-itemset candidates from (k-1)-itemsets.

        Uses lexicographic ordering and self-joining.

        Args:
            previous_itemsets: Set of frequent (k-1)-itemsets
            k: Size of candidates to generate

        Returns:
            Set of candidate k-itemsets
        """
        candidates = set()

        # Convert to sorted lists for efficient joining
        itemsets_list = [sorted(list(itemset)) for itemset in previous_itemsets]

        # Self-join: merge itemsets that differ by only one item
        for i, itemset1 in enumerate(itemsets_list):
            for itemset2 in itemsets_list[i+1:]:
                # Check if first (k-2) items are the same
                if k > 2 and itemset1[:-1] != itemset2[:-1]:
                    continue

                # Merge to create k-itemset candidate
                candidate = frozenset(itemset1) | frozenset(itemset2)

                if len(candidate) == k:
                    # Prune: all (k-1) subsets must be frequent
                    if self._has_frequent_subsets(candidate, previous_itemsets):
                        candidates.add(candidate)

        return candidates

    def _has_frequent_subsets(
        self,
        itemset: frozenset[str],
        frequent_itemsets: set[frozenset[str]]
    ) -> bool:
        """
        Check if all (k-1) subsets of itemset are frequent.

        Apriori property: If itemset is frequent, all subsets must be frequent.

        Args:
            itemset: Candidate itemset
            frequent_itemsets: Set of known frequent itemsets

        Returns:
            True if all subsets are frequent
        """
        k = len(itemset)
        if k <= 1:
            return True

        # Generate all (k-1) subsets
        itemset_list = list(itemset)
        for subset_items in combinations(itemset_list, k - 1):
            subset = frozenset(subset_items)
            if subset not in frequent_itemsets:
                return False

        return True

    def generate_association_rules(
        self,
        frequent_itemsets: dict[frozenset[str], float]
    ) -> list[AssociationRule]:
        """
        Generate association rules from frequent itemsets.

        For each itemset, generate all possible X → Y rules where:
        - X ∪ Y = itemset
        - X and Y are non-empty
        - Confidence(X → Y) >= min_confidence
        - Lift(X → Y) >= min_lift

        Args:
            frequent_itemsets: Dictionary of itemsets and their support

        Returns:
            List of AssociationRule objects
        """
        logger.info("📏 Generating association rules from frequent itemsets...")

        rules = []

        # Only generate rules from itemsets of size >= 2
        multi_item_sets = {
            itemset: support
            for itemset, support in frequent_itemsets.items()
            if len(itemset) >= 2
        }

        for itemset, support in multi_item_sets.items():
            # Generate all non-empty proper subsets as antecedents
            itemset_list = list(itemset)

            for r in range(1, len(itemset_list)):
                for antecedent_items in combinations(itemset_list, r):
                    antecedent = frozenset(antecedent_items)
                    consequent = itemset - antecedent

                    if len(consequent) == 0:
                        continue

                    # Calculate confidence: P(Y|X) = P(X ∪ Y) / P(X)
                    antecedent_support = frequent_itemsets.get(antecedent, 0)
                    if antecedent_support == 0:
                        continue

                    confidence = support / antecedent_support

                    if confidence < self.min_confidence:
                        continue

                    # Calculate lift: P(Y|X) / P(Y)
                    consequent_support = frequent_itemsets.get(consequent, 0)
                    if consequent_support == 0:
                        continue

                    lift = confidence / consequent_support

                    if lift < self.min_lift:
                        continue

                    # Create rule
                    rule = AssociationRule(
                        antecedent=antecedent,
                        consequent=consequent,
                        support=support,
                        confidence=confidence,
                        lift=lift
                    )

                    rules.append(rule)

        logger.info(f"✅ Generated {len(rules)} association rules")

        # Sort by confidence * lift for best rules first
        rules.sort(key=lambda r: r.confidence * r.lift, reverse=True)

        return rules


class TransactionBuilder:
    """
    Build transactions from Home Assistant events.

    A transaction = set of entities that changed state within a time window.
    """

    def __init__(
        self,
        time_window_seconds: int = 60,
        min_transaction_size: int = 2
    ):
        """
        Initialize transaction builder.

        Args:
            time_window_seconds: Time window for co-occurrence (default: 60s)
            min_transaction_size: Minimum entities per transaction (default: 2)
        """
        self.time_window_seconds = time_window_seconds
        self.min_transaction_size = min_transaction_size

        logger.info(
            f"TransactionBuilder initialized: window={time_window_seconds}s, "
            f"min_size={min_transaction_size}"
        )

    def build_transactions(
        self,
        events_df: pd.DataFrame,
        start_time: datetime | None = None,
        end_time: datetime | None = None
    ) -> list[set[str]]:
        """
        Build transactions from events DataFrame.

        Sliding window approach:
        1. Sort events by timestamp
        2. Create time windows
        3. Group entities that changed state in each window

        Args:
            events_df: Events DataFrame with columns: time, entity_id
            start_time: Optional start time filter
            end_time: Optional end time filter

        Returns:
            List of transaction sets
        """
        logger.info("🔨 Building transactions from events...")

        if events_df.empty or 'time' not in events_df.columns or 'entity_id' not in events_df.columns:
            logger.warning("Invalid events DataFrame for transaction building")
            return []

        # Filter by time range
        df = events_df.copy()
        if start_time:
            df = df[df['time'] >= start_time]
        if end_time:
            df = df[df['time'] <= end_time]

        if df.empty:
            return []

        # Sort by time
        df = df.sort_values('time').reset_index(drop=True)

        # Build transactions using sliding window
        transactions = []
        i = 0
        total_events = len(df)

        while i < total_events:
            window_start = df.loc[i, 'time']
            window_end = window_start + timedelta(seconds=self.time_window_seconds)

            # Collect all entities in this window
            window_entities = set()
            j = i

            while j < total_events and df.loc[j, 'time'] <= window_end:
                entity_id = df.loc[j, 'entity_id']
                window_entities.add(entity_id)
                j += 1

            # Add transaction if it meets minimum size
            if len(window_entities) >= self.min_transaction_size:
                transactions.append(window_entities)

            # Move to next window (slide by 1 event to capture overlapping patterns)
            i += 1

        logger.info(
            f"✅ Built {len(transactions)} transactions from {total_events} events "
            f"(avg {len(transactions)/max(total_events, 1):.2f} transactions per event)"
        )

        return transactions
