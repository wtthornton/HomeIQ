"""Configuration management for AI Training Service"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Database
    database_path: str = "/app/data/ai_automation.db"
    database_url: str = "sqlite+aiosqlite:////app/data/ai_automation.db"  # Absolute path for SQLite
    database_pool_size: int = 10  # Connection pool size (max 20 per service)
    database_max_overflow: int = 5  # Max overflow connections
    
    # Training Configuration
    training_script_path: str = "/app/scripts/train_soft_prompt.py"  # Soft prompt training script
    soft_prompt_model_dir: str = "/app/models/soft_prompts"
    training_script_sha256: str | None = None  # Optional hash validation
    
    # GNN Training Configuration
    gnn_training_script_path: str = "/app/scripts/train_gnn_synergy.py"  # GNN training script
    gnn_model_path: str = "/app/models/gnn_synergy.pth"
    gnn_hidden_dim: int = 64
    gnn_num_layers: int = 2
    gnn_learning_rate: float = 0.001
    gnn_batch_size: int = 32
    gnn_epochs: int = 10
    gnn_early_stopping_patience: int = 3
    
    # Home Type Classifier Training Configuration
    home_type_training_script_path: str = "/app/scripts/train_home_type_classifier.py"
    home_type_model_path: str = "/app/models/home_type_classifier.pkl"
    
    # Model Storage
    model_storage_dir: str = "/app/models"
    
    # Logging
    log_level: str = "INFO"
    
    # Service Configuration
    service_port: int = 8022
    service_name: str = "ai-training-service"
    
    # OpenAI (for synthetic data generation)
    openai_api_key: str | None = None
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

