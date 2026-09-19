"""
Configuration settings for Worker Service
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "worker-service"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # RabbitMQ
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "devops"
    RABBITMQ_PASSWORD: str = "devops123"
    RABBITMQ_VHOST: str = "devops"
    RABBITMQ_EXCHANGE: str = "devops_exchange"
    RABBITMQ_RECONNECT_DELAY: int = 5

    # Queue Names
    QUEUE_LLM_REQUESTS: str = "llm_requests"
    QUEUE_APPROVALS: str = "approvals"
    QUEUE_NOTIFICATIONS: str = "notifications"
    QUEUE_DEAD_LETTER: str = "dead_letter"

    # Worker Settings
    WORKER_PREFETCH_COUNT: int = 10
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5

    # PostgreSQL
    DATABASE_HOST: str = "postgres"
    DATABASE_PORT: int = 5432
    DATABASE_NAME: str = "devops_db"
    DATABASE_USER: str = "devops"
    DATABASE_PASSWORD: str = "devops123"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )

    # LLM Service
    LLM_SERVICE_URL: str = "http://llm-service:8000"
    LLM_SERVICE_TIMEOUT: int = 300  # 5 minutes
    LLM_SERVICE_MAX_RETRIES: int = 3

    # Email/Notification Service
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "noreply@example.com"
    SMTP_FROM_NAME: str = "DevOps System"
    SMTP_USE_TLS: bool = True

    # Slack Integration (Optional)
    SLACK_WEBHOOK_URL: Optional[str] = None
    SLACK_ENABLED: bool = False

    # Monitoring
    METRICS_ENABLED: bool = True
    METRICS_PORT: int = 9090

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
