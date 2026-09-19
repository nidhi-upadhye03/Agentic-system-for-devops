"""
Memory Agent Configuration

Manages configuration for the Memory Agent using Pydantic settings.
"""
from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Memory Agent configuration"""

    # Agent metadata
    agent_name: str = "memory"
    agent_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # PostgreSQL configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "devops_db"
    postgres_user: str = "devops"
    postgres_password: str = "devops123"
    db_pool_min: int = 2
    db_pool_max: int = 10
    db_connection_timeout: int = 30000

    # RabbitMQ configuration
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "devops"
    rabbitmq_password: str = "devops123"
    rabbitmq_vhost: str = "devops"
    rabbitmq_exchange: str = "devops_events"
    rabbitmq_queue_durable: bool = True
    rabbitmq_queue_auto_delete: bool = False
    rabbitmq_prefetch_count: int = 10

    # Event routing keys to subscribe to (all agent events)
    rabbitmq_incident_routing_key: str = "monitoring.incident.*"
    rabbitmq_analysis_routing_key: str = "analyzer.analysis.complete"
    rabbitmq_action_routing_key: str = "autoresponse.action.*"
    rabbitmq_approval_routing_key: str = "autoresponse.action.pending"

    # Qdrant configuration (Cloud) - Optional for local development
    qdrant_host: str = "localhost"
    qdrant_http_port: int = 6333
    qdrant_api_key: str = "dummy-key"
    qdrant_collection_name: str = "incident_embeddings"
    qdrant_vector_size: int = 1536

    # OpenAI configuration - Optional for local development
    openai_api_key: str = "sk-dummy-key-for-local-dev"
    openai_model: str = "text-embedding-3-small"
    openai_timeout: int = 60

    # Pattern detection configuration
    pattern_detection_enabled: bool = True
    pattern_similarity_threshold: float = 0.85
    pattern_min_occurrences: int = 3
    pattern_time_window_hours: int = 168  # 7 days

    # Learning configuration
    learning_enabled: bool = True
    successful_resolution_threshold: float = 0.8
    embedding_batch_size: int = 10

    # Storage settings
    incident_retention_days: int = 90
    embedding_retention_days: int = 90

    class Config:
        env_prefix = ""  # No prefix to match deployment script env vars
        env_file = ".env"
        case_sensitive = False


# Global config instance
config = Config()
