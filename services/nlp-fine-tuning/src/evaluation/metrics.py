"""
Evaluation Metrics for NLP Fine-Tuning

Provides comprehensive evaluation of fine-tuned models for
Home Assistant command understanding.
"""

import json
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class NLPEvaluator:
    """
    Evaluate fine-tuned NLP models for Home Assistant commands.
    
    Metrics:
    - Intent classification accuracy
    - Entity extraction F1 score
    - Exact match accuracy
    - BLEU score for response quality
    - Domain-specific accuracy
    """
    
    def __init__(self):
        """Initialize the evaluator."""
        self.results: dict[str, Any] = {}
    
    def evaluate_intent_classification(
        self,
        predictions: list[str],
        ground_truth: list[str],
    ) -> dict[str, float]:
        """
        Evaluate intent classification accuracy.
        
        Args:
            predictions: Predicted intents
            ground_truth: True intents
            
        Returns:
            Dictionary with accuracy metrics
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        correct = sum(p == g for p, g in zip(predictions, ground_truth))
        total = len(predictions)
        
        # Per-class accuracy
        class_correct = defaultdict(int)
        class_total = defaultdict(int)
        
        for pred, true in zip(predictions, ground_truth):
            class_total[true] += 1
            if pred == true:
                class_correct[true] += 1
        
        per_class_accuracy = {
            cls: class_correct[cls] / class_total[cls]
            for cls in class_total
        }
        
        results = {
            "accuracy": correct / total if total > 0 else 0.0,
            "correct": correct,
            "total": total,
            "per_class_accuracy": per_class_accuracy,
        }
        
        self.results["intent_classification"] = results
        logger.info(f"Intent classification accuracy: {results['accuracy']:.2%}")
        
        return results
    
    def evaluate_entity_extraction(
        self,
        predictions: list[dict[str, str]],
        ground_truth: list[dict[str, str]],
    ) -> dict[str, float]:
        """
        Evaluate entity extraction using F1 score.
        
        Args:
            predictions: Predicted entities (list of {entity_type: value} dicts)
            ground_truth: True entities
            
        Returns:
            Dictionary with precision, recall, F1 metrics
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        total_tp = 0
        total_fp = 0
        total_fn = 0
        
        # Per-entity-type metrics
        entity_metrics = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
        
        for pred, true in zip(predictions, ground_truth):
            pred_set = set(pred.items())
            true_set = set(true.items())
            
            tp = len(pred_set & true_set)
            fp = len(pred_set - true_set)
            fn = len(true_set - pred_set)
            
            total_tp += tp
            total_fp += fp
            total_fn += fn
            
            # Track per-entity-type
            for entity_type, value in true.items():
                if entity_type in pred and pred[entity_type] == value:
                    entity_metrics[entity_type]["tp"] += 1
                else:
                    entity_metrics[entity_type]["fn"] += 1
            
            for entity_type, value in pred.items():
                if entity_type not in true or true[entity_type] != value:
                    entity_metrics[entity_type]["fp"] += 1
        
        # Calculate overall metrics
        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        # Per-entity-type F1
        per_entity_f1 = {}
        for entity_type, counts in entity_metrics.items():
            tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
            p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            per_entity_f1[entity_type] = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        
        results = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "per_entity_f1": per_entity_f1,
        }
        
        self.results["entity_extraction"] = results
        logger.info(f"Entity extraction F1: {f1:.2%}")
        
        return results
    
    def evaluate_exact_match(
        self,
        predictions: list[str],
        ground_truth: list[str],
        normalize: bool = True,
    ) -> dict[str, float]:
        """
        Evaluate exact match accuracy.
        
        Args:
            predictions: Predicted responses
            ground_truth: True responses
            normalize: Whether to normalize text before comparison
            
        Returns:
            Dictionary with exact match metrics
        """
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        def normalize_text(text: str) -> str:
            if normalize:
                return text.lower().strip()
            return text
        
        correct = sum(
            normalize_text(p) == normalize_text(g)
            for p, g in zip(predictions, ground_truth)
        )
        total = len(predictions)
        
        results = {
            "exact_match_accuracy": correct / total if total > 0 else 0.0,
            "correct": correct,
            "total": total,
        }
        
        self.results["exact_match"] = results
        logger.info(f"Exact match accuracy: {results['exact_match_accuracy']:.2%}")
        
        return results
    
    def evaluate_bleu(
        self,
        predictions: list[str],
        ground_truth: list[str],
    ) -> dict[str, float]:
        """
        Evaluate response quality using BLEU score.
        
        Args:
            predictions: Predicted responses
            ground_truth: True responses
            
        Returns:
            Dictionary with BLEU metrics
        """
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
        except ImportError:
            logger.warning("NLTK not installed, skipping BLEU evaluation")
            return {"bleu": 0.0, "error": "NLTK not installed"}
        
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        smoothing = SmoothingFunction().method1
        
        scores = []
        for pred, true in zip(predictions, ground_truth):
            pred_tokens = pred.lower().split()
            true_tokens = true.lower().split()
            
            if pred_tokens and true_tokens:
                score = sentence_bleu(
                    [true_tokens],
                    pred_tokens,
                    smoothing_function=smoothing,
                )
                scores.append(score)
        
        avg_bleu = sum(scores) / len(scores) if scores else 0.0
        
        results = {
            "bleu": avg_bleu,
            "num_samples": len(scores),
        }
        
        self.results["bleu"] = results
        logger.info(f"BLEU score: {avg_bleu:.4f}")
        
        return results
    
    def evaluate_domain_accuracy(
        self,
        predictions: list[str],
        ground_truth: list[str],
        domains: list[str],
    ) -> dict[str, dict[str, float]]:
        """
        Evaluate accuracy per domain.
        
        Args:
            predictions: Predicted responses
            ground_truth: True responses
            domains: Domain labels for each example
            
        Returns:
            Dictionary with per-domain accuracy
        """
        if len(predictions) != len(ground_truth) != len(domains):
            raise ValueError("All inputs must have same length")
        
        domain_correct = defaultdict(int)
        domain_total = defaultdict(int)
        
        for pred, true, domain in zip(predictions, ground_truth, domains):
            domain_total[domain] += 1
            if pred.lower().strip() == true.lower().strip():
                domain_correct[domain] += 1
        
        per_domain_accuracy = {
            domain: domain_correct[domain] / domain_total[domain]
            for domain in domain_total
        }
        
        results = {
            "per_domain_accuracy": per_domain_accuracy,
            "domain_counts": dict(domain_total),
        }
        
        self.results["domain_accuracy"] = results
        logger.info(f"Domain accuracy: {per_domain_accuracy}")
        
        return results
    
    def get_summary(self) -> dict[str, Any]:
        """Get summary of all evaluation results."""
        summary = {
            "overall_metrics": {},
            "detailed_results": self.results,
        }
        
        # Extract key metrics
        if "intent_classification" in self.results:
            summary["overall_metrics"]["intent_accuracy"] = self.results["intent_classification"]["accuracy"]
        
        if "entity_extraction" in self.results:
            summary["overall_metrics"]["entity_f1"] = self.results["entity_extraction"]["f1"]
        
        if "exact_match" in self.results:
            summary["overall_metrics"]["exact_match"] = self.results["exact_match"]["exact_match_accuracy"]
        
        if "bleu" in self.results:
            summary["overall_metrics"]["bleu"] = self.results["bleu"]["bleu"]
        
        return summary
    
    def save_results(self, output_path: str) -> None:
        """Save evaluation results to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.get_summary(), f, indent=2)
        
        logger.info(f"Saved evaluation results to {output_path}")


def main():
    """Example usage of NLPEvaluator."""
    logging.basicConfig(level=logging.INFO)
    
    evaluator = NLPEvaluator()
    
    # Example data
    pred_intents = ["HassTurnOn", "HassTurnOff", "HassTurnOn"]
    true_intents = ["HassTurnOn", "HassTurnOff", "HassSetBrightness"]
    
    pred_entities = [
        {"domain": "light", "area": "living room"},
        {"domain": "switch", "area": "bedroom"},
        {"domain": "light", "area": "kitchen"},
    ]
    true_entities = [
        {"domain": "light", "area": "living room"},
        {"domain": "switch", "area": "bedroom"},
        {"domain": "light", "area": "kitchen", "brightness": "50"},
    ]
    
    # Evaluate
    evaluator.evaluate_intent_classification(pred_intents, true_intents)
    evaluator.evaluate_entity_extraction(pred_entities, true_entities)
    
    # Get summary
    summary = evaluator.get_summary()
    print(f"\nEvaluation Summary:\n{json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    main()
