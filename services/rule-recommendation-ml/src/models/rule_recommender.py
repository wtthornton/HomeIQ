"""
Rule Recommendation Model using Collaborative Filtering

Uses the Implicit library for efficient ALS (Alternating Least Squares)
collaborative filtering optimized for implicit feedback data.

This model learns from the Wyze Rule Recommendation dataset to suggest
automation rules based on:
1. What rules similar users have created
2. What device combinations are commonly automated together
"""

import logging
import pickle
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

logger = logging.getLogger(__name__)


class RuleRecommender:
    """
    Collaborative filtering model for rule recommendations using Implicit ALS.
    
    This model:
    1. Learns user preferences from historical rule creation data
    2. Identifies similar users based on automation patterns
    3. Recommends rules that similar users have created
    4. Supports both user-based and item-based recommendations
    """
    
    def __init__(
        self,
        factors: int = 64,
        iterations: int = 50,
        regularization: float = 0.01,
        use_gpu: bool = False,
        random_state: int = 42,
    ):
        """
        Initialize the rule recommender.
        
        Args:
            factors: Number of latent factors for matrix factorization
            iterations: Number of ALS iterations
            regularization: Regularization parameter to prevent overfitting
            use_gpu: Whether to use GPU acceleration (disabled for NUC deployment)
            random_state: Random seed for reproducibility
        """
        try:
            import implicit
        except ImportError:
            raise ImportError(
                "Please install the implicit library: pip install implicit>=0.7.0"
            )
        
        self.factors = factors
        self.iterations = iterations
        self.regularization = regularization
        self.use_gpu = use_gpu
        self.random_state = random_state
        
        # Initialize ALS model
        self.model = implicit.als.AlternatingLeastSquares(
            factors=factors,
            iterations=iterations,
            regularization=regularization,
            use_gpu=use_gpu,
            random_state=random_state,
        )
        
        # Mappings (set during training)
        self.idx_to_user: dict[int, str] = {}
        self.idx_to_pattern: dict[int, str] = {}
        self.user_to_idx: dict[str, int] = {}
        self.pattern_to_idx: dict[str, int] = {}
        
        # Training data reference
        self._user_items: csr_matrix | None = None
        self._is_fitted: bool = False
    
    def fit(
        self,
        user_rule_matrix: csr_matrix,
        idx_to_user: dict[int, str],
        idx_to_pattern: dict[int, str],
    ) -> "RuleRecommender":
        """
        Train the recommendation model.
        
        Args:
            user_rule_matrix: Sparse CSR matrix of user-rule interactions
                Shape: (n_users, n_rules)
            idx_to_user: Mapping from matrix index to user ID
            idx_to_pattern: Mapping from matrix index to rule pattern
            
        Returns:
            Self for method chaining
        """
        logger.info(
            f"Training ALS model with {user_rule_matrix.shape[0]:,} users "
            f"and {user_rule_matrix.shape[1]:,} rule patterns..."
        )
        
        # Store mappings
        self.idx_to_user = idx_to_user
        self.idx_to_pattern = idx_to_pattern
        self.user_to_idx = {v: k for k, v in idx_to_user.items()}
        self.pattern_to_idx = {v: k for k, v in idx_to_pattern.items()}
        
        # Store user-items matrix (needed for recommendations)
        self._user_items = user_rule_matrix
        
        # Train the model
        # Implicit expects item-user matrix (transposed)
        self.model.fit(user_rule_matrix.T.tocsr())
        
        self._is_fitted = True
        logger.info("Model training complete")
        
        return self
    
    def recommend(
        self,
        user_id: str | None = None,
        user_idx: int | None = None,
        n: int = 10,
        filter_already_used: bool = True,
    ) -> list[tuple[str, float]]:
        """
        Get top-N rule recommendations for a user.
        
        Args:
            user_id: User ID string (use either this or user_idx)
            user_idx: User index in the matrix (use either this or user_id)
            n: Number of recommendations to return
            filter_already_used: Whether to filter out rules user already has
            
        Returns:
            List of (rule_pattern, score) tuples, sorted by score descending
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before making recommendations")
        
        if user_id is not None:
            if user_id not in self.user_to_idx:
                logger.warning(f"Unknown user {user_id}, returning popular items")
                return self.get_popular_rules(n)
            user_idx = self.user_to_idx[user_id]
        
        if user_idx is None:
            raise ValueError("Must provide either user_id or user_idx")
        
        # Get user's existing items for filtering
        user_items = self._user_items[user_idx] if filter_already_used else None
        
        # Get recommendations
        ids, scores = self.model.recommend(
            user_idx,
            user_items,
            N=n,
            filter_already_liked_items=filter_already_used,
        )
        
        # Convert to pattern names
        recommendations = [
            (self.idx_to_pattern.get(idx, f"unknown_{idx}"), float(score))
            for idx, score in zip(ids, scores)
        ]
        
        return recommendations
    
    def recommend_for_devices(
        self,
        device_domains: list[str],
        n: int = 10,
    ) -> list[tuple[str, float]]:
        """
        Get recommendations based on device domains the user has.
        
        This is useful for new users without history - we recommend
        popular rules that match their device inventory.
        
        Args:
            device_domains: List of Home Assistant domains (e.g., ["light", "switch"])
            n: Number of recommendations
            
        Returns:
            List of (rule_pattern, score) tuples
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before making recommendations")
        
        # Find patterns that use these domains
        matching_patterns = []
        for pattern, idx in self.pattern_to_idx.items():
            # Pattern format: "trigger_domain_to_action_domain"
            parts = pattern.split("_to_")
            if len(parts) == 2:
                trigger_domain, action_domain = parts
                # Score based on domain matches
                score = 0.0
                if trigger_domain in device_domains:
                    score += 0.5
                if action_domain in device_domains:
                    score += 0.5
                if score > 0:
                    # Weight by pattern popularity
                    pattern_popularity = self._user_items[:, idx].sum()
                    score *= np.log1p(pattern_popularity)
                    matching_patterns.append((pattern, score))
        
        # Sort by score and return top N
        matching_patterns.sort(key=lambda x: x[1], reverse=True)
        return matching_patterns[:n]
    
    def get_similar_rules(
        self,
        rule_pattern: str,
        n: int = 10,
    ) -> list[tuple[str, float]]:
        """
        Find rules similar to a given rule pattern.
        
        Args:
            rule_pattern: The rule pattern to find similar rules for
            n: Number of similar rules to return
            
        Returns:
            List of (rule_pattern, similarity_score) tuples
        """
        if not self._is_fitted:
            raise RuntimeError("Model must be fitted before finding similar rules")
        
        if rule_pattern not in self.pattern_to_idx:
            logger.warning(f"Unknown rule pattern: {rule_pattern}")
            return []
        
        pattern_idx = self.pattern_to_idx[rule_pattern]
        
        # Get similar items using the model
        ids, scores = self.model.similar_items(pattern_idx, N=n + 1)
        
        # Convert to pattern names (skip first which is the query item itself)
        similar = [
            (self.idx_to_pattern.get(idx, f"unknown_{idx}"), float(score))
            for idx, score in zip(ids[1:], scores[1:])
        ]
        
        return similar
    
    def get_popular_rules(self, n: int = 10) -> list[tuple[str, float]]:
        """
        Get the most popular rule patterns overall.
        
        Useful as a fallback for new users without history.
        
        Args:
            n: Number of popular rules to return
            
        Returns:
            List of (rule_pattern, count) tuples
        """
        if self._user_items is None:
            return []
        
        # Sum interactions per pattern
        pattern_counts = np.asarray(self._user_items.sum(axis=0)).flatten()
        
        # Get top N indices
        top_indices = np.argsort(pattern_counts)[::-1][:n]
        
        return [
            (self.idx_to_pattern.get(idx, f"unknown_{idx}"), float(pattern_counts[idx]))
            for idx in top_indices
        ]
    
    def save(self, path: Path | str) -> None:
        """
        Save the trained model to disk.
        
        Args:
            path: Path to save the model
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            "model_state": {
                "user_factors": self.model.user_factors,
                "item_factors": self.model.item_factors,
            },
            "mappings": {
                "idx_to_user": self.idx_to_user,
                "idx_to_pattern": self.idx_to_pattern,
            },
            "config": {
                "factors": self.factors,
                "iterations": self.iterations,
                "regularization": self.regularization,
                "random_state": self.random_state,
            },
            "user_items_shape": self._user_items.shape if self._user_items is not None else None,
        }
        
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
        
        # Also save the sparse matrix separately (more efficient)
        if self._user_items is not None:
            from scipy.sparse import save_npz
            save_npz(path.with_suffix(".npz"), self._user_items)
        
        logger.info(f"Saved model to {path}")
    
    @classmethod
    def load(cls, path: Path | str) -> "RuleRecommender":
        """
        Load a trained model from disk.
        
        Args:
            path: Path to the saved model
            
        Returns:
            Loaded RuleRecommender instance
        """
        import implicit
        from scipy.sparse import load_npz
        
        path = Path(path)
        
        with open(path, "rb") as f:
            model_data = pickle.load(f)
        
        # Create instance with saved config
        config = model_data["config"]
        instance = cls(
            factors=config["factors"],
            iterations=config["iterations"],
            regularization=config["regularization"],
            random_state=config["random_state"],
        )
        
        # Restore model state
        instance.model.user_factors = model_data["model_state"]["user_factors"]
        instance.model.item_factors = model_data["model_state"]["item_factors"]
        
        # Restore mappings
        instance.idx_to_user = model_data["mappings"]["idx_to_user"]
        instance.idx_to_pattern = model_data["mappings"]["idx_to_pattern"]
        instance.user_to_idx = {v: k for k, v in instance.idx_to_user.items()}
        instance.pattern_to_idx = {v: k for k, v in instance.idx_to_pattern.items()}
        
        # Load sparse matrix if it exists
        npz_path = path.with_suffix(".npz")
        if npz_path.exists():
            instance._user_items = load_npz(npz_path)
        
        instance._is_fitted = True
        
        logger.info(f"Loaded model from {path}")
        
        return instance
    
    def get_model_info(self) -> dict[str, Any]:
        """Get model information and statistics."""
        return {
            "is_fitted": self._is_fitted,
            "factors": self.factors,
            "iterations": self.iterations,
            "regularization": self.regularization,
            "num_users": len(self.idx_to_user),
            "num_patterns": len(self.idx_to_pattern),
            "matrix_shape": self._user_items.shape if self._user_items is not None else None,
            "matrix_nnz": self._user_items.nnz if self._user_items is not None else 0,
        }


def main():
    """Example usage of RuleRecommender."""
    logging.basicConfig(level=logging.INFO)
    
    from scipy.sparse import random as sparse_random
    
    # Create synthetic data for testing
    n_users, n_patterns = 1000, 100
    density = 0.01  # 1% of user-pattern pairs have interactions
    
    user_items = sparse_random(n_users, n_patterns, density=density, format="csr")
    user_items.data[:] = 1  # Binary interactions
    
    idx_to_user = {i: f"user_{i}" for i in range(n_users)}
    idx_to_pattern = {i: f"pattern_{i}" for i in range(n_patterns)}
    
    # Train model
    recommender = RuleRecommender(factors=32, iterations=20)
    recommender.fit(user_items, idx_to_user, idx_to_pattern)
    
    # Get recommendations for a user
    recommendations = recommender.recommend(user_id="user_0", n=5)
    print(f"\nRecommendations for user_0: {recommendations}")
    
    # Get popular rules
    popular = recommender.get_popular_rules(n=5)
    print(f"\nPopular rules: {popular}")
    
    # Save and load
    recommender.save("test_model.pkl")
    loaded = RuleRecommender.load("test_model.pkl")
    print(f"\nModel info: {loaded.get_model_info()}")


if __name__ == "__main__":
    main()
