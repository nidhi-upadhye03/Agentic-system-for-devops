"""
Configuration Management for Analyzer Agent

Loads configuration from environment variables with sensible defaults.
"""
import os
from typing import List, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class AnalyzerConfig(BaseSettings):
    """Configuration settings for Analyzer Agent"""

    # Agent Info
    agent_name: str = Field(default="analyzer", description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")

    # Environment
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # LLM Service Configuration
    llm_service_url: str = Field(default="http://llm-service:8000", description="LLM service URL")
    llm_provider: str = Field(default="openai", description="LLM provider (openai, anthropic)")
    llm_model: str = Field(default="gpt-4", description="LLM model to use")
    llm_temperature: float = Field(default=0.2, description="LLM temperature (0-1)")
    llm_max_tokens: int = Field(default=2000, description="Max tokens for LLM response")
    llm_timeout: int = Field(default=60, description="LLM request timeout (seconds)")
    llm_mock_mode: bool = Field(default=False, description="Use mock LLM responses (bypass API calls)")

    # RabbitMQ Configuration
    rabbitmq_host: str = Field(default="rabbitmq", description="RabbitMQ host")
    rabbitmq_port: int = Field(default=5672, description="RabbitMQ port")
    rabbitmq_user: str = Field(default="devops", description="RabbitMQ username")
    rabbitmq_password: str = Field(default="devops123", description="RabbitMQ password")
    rabbitmq_vhost: str = Field(default="devops", description="RabbitMQ vhost")
    rabbitmq_exchange: str = Field(default="agent_events", description="RabbitMQ exchange")

    # Qdrant Configuration (for RAG)
    qdrant_host: str = Field(default="qdrant", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant HTTP port")
    qdrant_collection: str = Field(default="incident_history", description="Qdrant collection name")
    qdrant_api_key: str = Field(default="", description="Qdrant API key (optional)")

    # PostgreSQL Configuration
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="devops_db", description="PostgreSQL database")
    postgres_user: str = Field(default="devops", description="PostgreSQL username")
    postgres_password: str = Field(default="devops123", description="PostgreSQL password")

    # Redis Configuration
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="redis123", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database")

    # Analysis Configuration
    analysis_timeout: int = Field(default=120, description="Max time for analysis (seconds)")
    fetch_logs_enabled: bool = Field(default=True, description="Enable log fetching")
    log_fetch_window: int = Field(default=600, description="Log fetch time window (seconds)")
    max_log_lines: int = Field(default=100, description="Max log lines to analyze")

    # RAG Configuration
    rag_enabled: bool = Field(default=True, description="Enable RAG search")
    rag_top_k: int = Field(default=5, description="Number of similar incidents to retrieve")
    rag_similarity_threshold: float = Field(default=0.7, description="Minimum similarity score")

    # Confidence thresholds
    min_confidence_for_action: float = Field(default=70.0, description="Minimum confidence to recommend action (%)")
    high_confidence_threshold: float = Field(default=90.0, description="High confidence threshold (%)")

    # Action mapping
    action_keywords: Dict[str, str] = Field(
        default={
            "scale": "scale_deployment",
            "restart": "restart_pods",
            "rollback": "rollback_deployment",
            "update": "update_config",
            "increase": "scale_deployment"
        },
        description="Keywords to action type mapping"
    )

    # Criticality mapping
    criticality_keywords: Dict[str, str] = Field(
        default={
            "rollback": "critical",
            "delete": "critical",
            "update": "medium",
            "scale": "low",
            "restart": "low"
        },
        description="Action to criticality mapping"
    )

    class Config:
        env_file = ".env"
        env_prefix = "ANALYZER_"  # Match ANALYZER_ prefix from environment
        case_sensitive = False


# Global config instance
config = AnalyzerConfig()

print(f"DEBUG: Loaded RabbitMQ Config: Host={config.rabbitmq_host}, Port={config.rabbitmq_port}, User={config.rabbitmq_user}, VHost={config.rabbitmq_vhost}")

