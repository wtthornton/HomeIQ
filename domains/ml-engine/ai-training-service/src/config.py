"""Configuration management for AI Training Service.

Inherits common fields from BaseServiceSettings (service_name, service_port,
log_level, cors_origins, postgres_url, database_url, database_schema, etc.).
"""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment.

    Service-specific fields only; common fields come from BaseServiceSettings.
    """

    # Database (additional to base)
    database_path: str = "/app/data/ai_automation.db"
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # Training Configuration
    training_script_path: str = "/app/scripts/train_soft_prompt.py"
    soft_prompt_model_dir: str = "/app/models/soft_prompts"
    training_script_sha256: str | None = None

    # GNN Training Configuration
    gnn_training_script_path: str = "/app/scripts/train_gnn_synergy.py"
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

    # OpenAI (for synthetic data generation)
    openai_api_key: str | None = None

    # Override base defaults
    service_port: int = 8022
    service_name: str = "ai-training-service"
    database_schema: str = "automation"


settings = Settings()
