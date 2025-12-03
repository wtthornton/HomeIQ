#!/usr/bin/env python3
"""
Execute Model Training

Train models using collected simulation data.
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from retraining.retraining_manager import RetrainingManager
from retraining.data_sufficiency import DataSufficiencyChecker
from reporting.summary_generator import SummaryGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Execute model training."""
    logger.info("=" * 60)
    logger.info("Model Training Execution")
    logger.info("=" * 60)
    
    # Setup paths
    training_data_dir = Path("simulation/training_data")
    model_dir = Path("simulation/models")
    output_dir = Path("simulation_results")
    
    # Initialize components
    data_sufficiency_checker = DataSufficiencyChecker()
    retraining_manager = RetrainingManager(
        training_data_directory=training_data_dir,
        model_directory=model_dir,
        data_sufficiency_checker=data_sufficiency_checker
    )
    summary_generator = SummaryGenerator(output_dir)
    
    # Check data counts
    logger.info("Checking training data availability...")
    data_counts = {}
    
    # GNN Synergy
    gnn_file = training_data_dir / "gnn_synergy_data.json"
    if gnn_file.exists():
        with open(gnn_file) as f:
            gnn_data = json.load(f)
            data_counts["gnn_synergy"] = len(gnn_data) if isinstance(gnn_data, list) else 0
            logger.info(f"  GNN Synergy: {data_counts['gnn_synergy']} samples")
    
    # Soft Prompt
    soft_prompt_file = training_data_dir / "soft_prompt_data.json"
    if soft_prompt_file.exists():
        with open(soft_prompt_file) as f:
            soft_prompt_data = json.load(f)
            data_counts["soft_prompt"] = len(soft_prompt_data) if isinstance(soft_prompt_data, list) else 0
            logger.info(f"  Soft Prompt: {data_counts['soft_prompt']} samples")
    
    # Check sufficiency
    logger.info("\nChecking data sufficiency...")
    triggers = retraining_manager.check_retraining_trigger(data_counts)
    
    for model_type, should_train in triggers.items():
        status = "✅ Eligible" if should_train else "❌ Insufficient"
        logger.info(f"  {model_type}: {status}")
    
    # Train eligible models
    logger.info("\n" + "=" * 60)
    logger.info("Starting Model Training")
    logger.info("=" * 60)
    
    training_summaries = []
    eligible_models = [m for m, should_train in triggers.items() if should_train]
    total_models = len(eligible_models)
    current_model = 0
    
    for model_type, should_train in triggers.items():
        if not should_train:
            logger.info(f"\n⏭️  Skipping {model_type}: Insufficient data")
            continue
        
        current_model += 1
        progress_pct = int((current_model / total_models) * 100) if total_models > 0 else 0
        
        logger.info(f"\n{'=' * 60}")
        logger.info(f"[{current_model}/{total_models}] ({progress_pct}%) Training: {model_type}")
        logger.info(f"{'=' * 60}")
        
        data_count = data_counts.get(model_type, 0)
        logger.info(f"📊 Data samples: {data_count}")
        logger.info(f"⏳ Starting training...")
        
        try:
            import time
            start_time = time.time()
            
            result = await retraining_manager.retrain_model(
                model_type=model_type,
                force=True  # Force retraining with new data
            )
            
            elapsed = time.time() - start_time
            
            if result.get("success"):
                logger.info(f"✅ {model_type} training completed successfully ({elapsed:.1f}s)")
                
                # Generate training summary
                training_summary_path = summary_generator.generate_training_summary(
                    model_type=model_type,
                    status="success",
                    metrics=result.get("metrics", {}),
                    model_path=result.get("model_path"),
                    training_time_seconds=result.get("duration_seconds"),
                    errors=None
                )
                training_summaries.append(training_summary_path)
                logger.info(f"  Summary: {training_summary_path}")
            else:
                logger.error(f"❌ {model_type} training failed: {result.get('error')}")
                
                # Generate training summary with error
                training_summary_path = summary_generator.generate_training_summary(
                    model_type=model_type,
                    status="failed",
                    metrics={},
                    model_path=None,
                    training_time_seconds=None,
                    errors=[result.get("error", "Unknown error")]
                )
                training_summaries.append(training_summary_path)
                
        except Exception as e:
            logger.error(f"❌ {model_type} training exception: {e}", exc_info=True)
            
            # Generate training summary with error
            training_summary_path = summary_generator.generate_training_summary(
                model_type=model_type,
                status="failed",
                metrics={},
                model_path=None,
                training_time_seconds=None,
                errors=[str(e)]
            )
            training_summaries.append(training_summary_path)
    
    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("Training Execution Complete")
    logger.info("=" * 60)
    
    successful = sum(1 for s in training_summaries if "success" in str(s))
    failed = len(training_summaries) - successful
    total_attempted = successful + failed
    success_rate = (successful / total_attempted * 100) if total_attempted > 0 else 0
    
    logger.info(f"✅ Successful: {successful}/{total_attempted} ({success_rate:.0f}%)")
    logger.info(f"❌ Failed: {failed}/{total_attempted}")
    logger.info(f"📊 Summaries: {len(training_summaries)}")
    
    if training_summaries:
        logger.info("\nTraining summaries generated:")
        for summary_path in training_summaries:
            logger.info(f"  - {summary_path}")


if __name__ == "__main__":
    asyncio.run(main())

