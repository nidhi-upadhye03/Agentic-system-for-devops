"""
Configuration for Monitoring Agent
"""
import os
from typing import Dict, List
from pydantic_settings import BaseSettings
from pydantic import Field


class MonitoringConfig(BaseSettings):
    """Configuration settings for Monitoring Agent"""

    # Agent Info
    agent_name: str = Field(default="monitoring", description="Agent name")
    agent_version: str = Field(default="1.0.0", description="Agent version")

    # Environment
    environment: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")

    # Prometheus Configuration
    prometheus_url: str = Field(default="http://prometheus:9090", description="Prometheus server URL")
    prometheus_scrape_interval: int = Field(default=30, description="How often to check metrics (seconds)")

    # Kubernetes Configuration
    k8s_in_cluster: bool = Field(default=True, description="Running inside K8s cluster")
    k8s_namespace: str = Field(default="ai-system", description="K8s namespace to monitor")

    # RabbitMQ Configuration
    rabbitmq_host: str = Field(default="rabbitmq", description="RabbitMQ host")
    rabbitmq_port: int = Field(default=5672, description="RabbitMQ port")
    rabbitmq_user: str = Field(default="devops", description="RabbitMQ username")
    rabbitmq_password: str = Field(default="devops123", description="RabbitMQ password")
    rabbitmq_vhost: str = Field(default="devops", description="RabbitMQ vhost")
    rabbitmq_exchange: str = Field(default="agent_events", description="RabbitMQ exchange")

    # Redis Configuration
    redis_host: str = Field(default="redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: str = Field(default="redis123", description="Redis password")
    redis_db: int = Field(default=0, description="Redis database")

    # PostgreSQL Configuration
    postgres_host: str = Field(default="postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="devops_db", description="PostgreSQL database")
    postgres_user: str = Field(default="devops", description="PostgreSQL username")
    postgres_password: str = Field(default="devops123", description="PostgreSQL password")

    # Monitoring Thresholds
    cpu_threshold: float = Field(default=90.0, description="CPU usage threshold (%)")
    memory_threshold: float = Field(default=90.0, description="Memory usage threshold (MB)")
    error_rate_threshold: float = Field(default=10.0, description="Error rate threshold (%)")
    pod_restart_threshold: int = Field(default=3, description="Pod restart count threshold")
    response_time_threshold: float = Field(default=2000.0, description="Response time threshold (ms)")

    # Anomaly Detection
    anomaly_detection_enabled: bool = Field(default=True, description="Enable anomaly detection")
    anomaly_sensitivity: float = Field(default=2.0, description="Sensitivity for anomaly detection (std devs)")
    min_data_points: int = Field(default=10, description="Minimum data points for anomaly detection")

    # Severity Mapping
    severity_mapping: Dict[str, str] = Field(
        default={
            "cpu_high": "high",
            "memory_high": "high",
            "error_rate_high": "critical",
            "pod_restarts": "medium",
            "response_time_slow": "medium",
            "service_down": "critical"
        },
        description="Metric to severity mapping"
    )

    # Metrics to Monitor
    metrics_to_monitor: List[str] = Field(
        default=[
            "test_app_cpu_percent",
            "test_app_memory_mb",
            "test_app_requests_total",
            "test_app_errors_total"
        ],
        description="List of Prometheus metrics to monitor"
    )

    # Allow overriding metrics via environment variable (comma-separated)
    custom_metrics: str = Field(default="", description="Custom metrics to monitor (comma-separated)")

    class Config:
        env_file = ".env"
        env_prefix = ""  # No prefix to match [CLOUD_PROVIDER] deployment env vars
        case_sensitive = False


# Global config instance
config = MonitoringConfig()
