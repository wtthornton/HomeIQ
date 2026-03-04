"""Configuration settings for Rule Recommendation ML Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Model paths
    model_path: str = "./models/rule_recommender.pkl"
    feedback_db_path: str = "/data/feedback.db"

    # Debug mode
    debug: bool = False

    # Override base defaults
    service_port: int = 8035
    service_name: str = "rule-recommendation-ml"


settings = Settings()
