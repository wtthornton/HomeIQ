#!/usr/bin/env python3
"""
Train Pattern Quality Model

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.2: Pattern Quality Model Training

Command-line script to train the pattern quality model.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.models import init_db, async_session
from services.pattern_quality.model_trainer import PatternQualityTrainer

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Main training function."""
    logger.info("Starting pattern quality model training...")
    
    # Initialize database
    await init_db()
    
    # Get database session
    async with async_session() as db_session:
        try:
            # Create trainer
            trainer = PatternQualityTrainer(db_session)
            
            # Train model
            logger.info("Training model on user feedback data...")
            metrics = await trainer.train()
            
            # Print metrics
            logger.info("Training Metrics:")
            logger.info(f"  Accuracy: {metrics.get('accuracy', 0):.3f}")
            logger.info(f"  Precision: {metrics.get('precision', 0):.3f}")
            logger.info(f"  Recall: {metrics.get('recall', 0):.3f}")
            logger.info(f"  F1 Score: {metrics.get('f1', 0):.3f}")
            logger.info(f"  ROC AUC: {metrics.get('roc_auc', 0):.3f}")
            
            # Check if model meets performance threshold
            if metrics.get('accuracy', 0) < 0.85:
                logger.warning(f"Model accuracy {metrics['accuracy']:.3f} is below 0.85 threshold")
            else:
                logger.info("Model meets performance threshold (accuracy >= 0.85)")
            
            # Save model
            model_path = Path(__file__).parent.parent / "models" / "pattern_quality_model.joblib"
            trainer.save_model(str(model_path))
            logger.info(f"Model saved to {model_path}")
            
            # Feature importance
            model = trainer.get_model()
            top_features = model.get_feature_importance(top_n=10)
            if top_features:
                logger.info("Top 10 Most Important Features:")
                for feature, importance in top_features.items():
                    logger.info(f"  {feature}: {importance:.4f}")
            
        except Exception as e:
            logger.error(f"Error during training: {e}", exc_info=True)
            sys.exit(1)
    
    logger.info("Training complete!")


if __name__ == "__main__":
    asyncio.run(main())

