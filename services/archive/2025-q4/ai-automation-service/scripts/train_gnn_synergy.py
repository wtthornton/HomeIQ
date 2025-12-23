#!/usr/bin/env python3
"""
Standalone GNN Synergy Training Script

This script can be run independently to train GNN models for synergy detection.
It can be used for:
- Scheduled model retraining
- Manual model updates
- Testing model training in isolation
- CI/CD pipeline integration

Usage:
    python scripts/train_gnn_synergy.py [--epochs 30] [--force] [--verbose]
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import service modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import settings
from src.clients.data_api_client import DataAPIClient
from src.database.models import get_db_session
from src.synergy_detection.gnn_synergy_detector import GNNSynergyDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('gnn_training.log')
    ]
)
logger = logging.getLogger(__name__)


async def train_gnn_synergy(
    epochs: int | None = None,
    force: bool = False,
    verbose: bool = False,
    simulation_entities_json: str | None = None,
    db_path: Path | None = None
):
    """Train GNN synergy detection model."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logger.info("=" * 80)
    logger.info("GNN Synergy Detection Training Script")
    logger.info("=" * 80)
    logger.info(f"Epochs: {epochs or settings.gnn_epochs}")
    logger.info(f"Force retrain: {force}")
    logger.info("")
    
    try:
        # Initialize data API client
        logger.info("📊 Initializing data API client...")
        data_api_client = DataAPIClient(base_url=settings.data_api_url)
        logger.info("✅ Data API client initialized")
        
        # Create GNN detector
        logger.info("🤖 Creating GNN synergy detector...")
        detector = GNNSynergyDetector(
            hidden_dim=settings.gnn_hidden_dim,
            num_layers=settings.gnn_num_layers,
            learning_rate=settings.gnn_learning_rate,
            batch_size=settings.gnn_batch_size,
            epochs=epochs or settings.gnn_epochs,
            early_stopping_patience=settings.gnn_early_stopping_patience,
            model_path=settings.gnn_model_path
        )
        
        # Check if model already exists
        await detector.initialize()
        if detector._is_initialized and detector.model and not force:
            logger.info("ℹ️  Model is already trained. Use --force to retrain.")
            if detector.metadata:
                logger.info(f"   Training date: {detector.metadata.get('training_date', 'unknown')}")
            return 0
        
        # Load entities (support simulation mode with JSON file)
        if simulation_entities_json and Path(simulation_entities_json).exists():
            logger.info("📥 Loading entities from simulation JSON...")
            import json
            with open(simulation_entities_json, "r") as f:
                entities = json.load(f)
            logger.info(f"✅ Loaded {len(entities)} entities from JSON")
        else:
            logger.info("📥 Loading entities from data-api...")
            entities = await data_api_client.fetch_entities(limit=10000)
            logger.info(f"✅ Loaded {len(entities)} entities")
        
        if not entities:
            logger.error("❌ Insufficient data for training: no entities found")
            return 1
        
        # Load synergies from database (support simulation mode with custom DB)
        if db_path and db_path.exists():
            logger.info("📥 Loading synergies from simulation database...")
            # Use async session for simulation database (same pattern as retraining_manager)
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker
            from src.database.models import Base
            
            engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)  # Create tables if they don't exist
            
            AsyncSessionLocal = sessionmaker(
                autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
            )
            async with AsyncSessionLocal() as db:
                synergies = await detector._load_synergies_from_database(db)
            logger.info(f"✅ Loaded {len(synergies)} synergies from simulation database")
        else:
            # Check environment variable as fallback
            import os
            simulation_db = os.getenv("SIMULATION_SYNERGY_DB")
            if simulation_db and Path(simulation_db).exists():
                logger.info("📥 Loading synergies from simulation database (env var)...")
                # Use async session for simulation database
                from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
                from sqlalchemy.orm import sessionmaker
                from src.database.models import Base
                
                engine = create_async_engine(f"sqlite+aiosqlite:///{simulation_db}", echo=False)
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
                
                AsyncSessionLocal = sessionmaker(
                    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
                )
                async with AsyncSessionLocal() as db:
                    synergies = await detector._load_synergies_from_database(db)
                logger.info(f"✅ Loaded {len(synergies)} synergies from simulation database")
            else:
                logger.info("📥 Loading synergies from database...")
                async with get_db_session() as db:
                    synergies = await detector._load_synergies_from_database(db)
                logger.info(f"✅ Loaded {len(synergies)} synergies from database")
        
        # Generate synthetic synergies if none exist (cold start scenario)
        if not synergies:
            logger.info("⚠️  No synergies found in database. Generating synthetic synergies for training...")
            # Import the function from admin_router
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from src.api.admin_router import _generate_synthetic_synergies
            synergies = _generate_synthetic_synergies(entities)
            if synergies:
                logger.info(f"✅ Generated {len(synergies)} synthetic synergies for cold start training")
            else:
                logger.error("❌ Could not generate synthetic synergies")
                logger.error(f"   Entities: {len(entities)}")
                return 1
        
        if not synergies:
            logger.error("❌ Insufficient data for training")
            logger.error(f"   Entities: {len(entities)}")
            logger.error(f"   Synergies: 0 (could not generate synthetic)")
            return 1
        
        # Train model
        logger.info("🚀 Starting GNN training...")
        logger.info("")
        
        async with get_db_session() as db:
            result = await detector.learn_from_data(
                entities=entities,
                known_synergies=synergies,
                db_session=db,
                data_api_client=data_api_client
            )
        
        if result.get('status') == 'complete':
            logger.info("")
            logger.info("=" * 80)
            logger.info("✅ Training Complete!")
            logger.info("=" * 80)
            logger.info(f"Nodes: {result.get('nodes', 0)}")
            logger.info(f"Edges: {result.get('edges', 0)}")
            logger.info(f"Training Pairs: {result.get('training_pairs', 0)}")
            logger.info(f"Validation Pairs: {result.get('validation_pairs', 0)}")
            logger.info("")
            logger.info("Final Performance:")
            logger.info(f"  - Train Loss: {result.get('final_train_loss', 0):.4f}")
            logger.info(f"  - Val Loss: {result.get('final_val_loss', 0):.4f}")
            logger.info(f"  - Train Accuracy: {result.get('final_train_acc', 0):.4f}")
            logger.info(f"  - Val Accuracy: {result.get('final_val_acc', 0):.4f}")
            logger.info(f"  - Epochs Trained: {result.get('epochs_trained', 0)}")
            logger.info("")
            logger.info("=" * 80)
            
            return 0
        else:
            logger.error(f"❌ Training failed: {result.get('reason', 'unknown')}")
            return 1
    
    except Exception as e:
        logger.error(f"❌ Error during training: {e}", exc_info=True)
        return 1


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Train GNN model for Synergy Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Train with default settings (30 epochs)
  python scripts/train_gnn_synergy.py
  
  # Train with custom epochs
  python scripts/train_gnn_synergy.py --epochs 50
  
  # Force retrain even if model exists
  python scripts/train_gnn_synergy.py --force
  
  # Verbose output
  python scripts/train_gnn_synergy.py --verbose
        """
    )
    
    parser.add_argument(
        '--epochs',
        type=int,
        default=None,
        help='Number of training epochs (default: from config)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force retraining even if model already exists'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--simulation-entities-json',
        type=str,
        help='Path to JSON file containing simulation entities (for simulation mode)'
    )
    parser.add_argument(
        '--db-path',
        type=Path,
        help='Path to the SQLite database for training data (for simulation mode)'
    )
    
    args = parser.parse_args()
    
    # Run training
    exit_code = asyncio.run(train_gnn_synergy(
        epochs=args.epochs,
        force=args.force,
        verbose=args.verbose,
        simulation_entities_json=args.simulation_entities_json,
        db_path=args.db_path
    ))
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

