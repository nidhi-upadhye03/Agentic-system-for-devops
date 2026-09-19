"""
Auto-Response Agent Configuration

Manages all configuration settings using Pydantic for validation.
"""
from pydantic_settings import BaseSettings
from typing import Dict, List
import os


class Config(BaseSettings):
    """Configuration for Auto-Response Agent"""

    # Agent metadata
    agent_name: str = "auto-response"
    agent_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Kubernetes configuration
    k8s_in_cluster: bool = False
    k8s_namespace: str = "default"
    k8s_dry_run: bool = False  # Safety: enable dry-run mode

    # RabbitMQ configuration
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "devops"
    rabbitmq_password: str = "devops123"
    rabbitmq_vhost: str = "devops"
    rabbitmq_exchange: str = "agent_events"
    rabbitmq_analysis_routing_key: str = "analyzer.analysis.complete"
    rabbitmq_action_routing_key: str = "autoresponse.action.executed"

    # PostgreSQL configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "devops_db"
    postgres_user: str = "devops"
    postgres_password: str = "devops123"

    # Approval Dashboard API
    approval_api_url: str = "http://approval-backend:3000/api/v1"
    approval_timeout: int = 300  # 5 minutes timeout for approval
    approval_poll_interval: int = 5  # Poll every 5 seconds

    # Action execution settings
    auto_execute_threshold: int = 95  # Auto-execute if confidence >= 95%
    max_retries: int = 3
    retry_delay: int = 10  # seconds

    # Safety settings
    require_approval_actions: List[str] = [
        "rollback_deployment",
        "delete_pods",
        "update_config",
        "scale_down_critical"
    ]

    # Criticality levels requiring approval
    require_approval_criticality: List[str] = ["critical", "high"]

    # Action timeout
    action_timeout: int = 120  # 2 minutes per action

    # Kubernetes operation limits
    max_scale_replicas: int = 10
    min_scale_replicas: int = 1

    class Config:
        env_prefix = ""  # No prefix to match deployment script env vars
        case_sensitive = False


# Global config instance
config = Config()
