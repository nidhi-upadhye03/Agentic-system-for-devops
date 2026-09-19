"""
Notifier Agent Configuration

Manages all configuration settings using Pydantic for validation.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Config(BaseSettings):
    """Configuration for Notifier Agent"""

    # Agent metadata
    agent_name: str = "notifier"
    agent_version: str = "1.0.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Slack configuration
    slack_token: str = "xoxb-dummy-token-for-local-dev"  # Changed from slack_bot_token to match deployment script
    slack_channel: str = "#devopsalerts"
    slack_username: str = "DevOps Copilot"
    slack_icon_emoji: str = ":robot_face:"
    slack_timeout: int = 10  # seconds

    # Email configuration (SMTP)
    email_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    email_recipients: str = ""  # Comma-separated email addresses

    # SMS configuration (Twilio)
    sms_enabled: bool = False
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""
    sms_recipients: str = ""  # Comma-separated phone numbers in E.164 format (+1234567890)

    # PagerDuty configuration (Events API v2)
    pagerduty_enabled: bool = False
    pagerduty_integration_key: str = ""

    # RabbitMQ configuration
    rabbitmq_host: str = "rabbitmq"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "devops"
    rabbitmq_password: str = "devops123"
    rabbitmq_vhost: str = "devops"
    rabbitmq_exchange: str = "agent_events"

    # Event routing keys to subscribe to
    rabbitmq_incident_routing_key: str = "monitoring.incident.*"
    rabbitmq_analysis_routing_key: str = "analyzer.analysis.complete"
    rabbitmq_action_routing_key: str = "autoresponse.action.*"
    rabbitmq_approval_routing_key: str = "autoresponse.action.pending"

    # PostgreSQL configuration (for additional data)
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "devops_db"
    postgres_user: str = "devops"
    postgres_password: str = "devops123"

    # Notification settings
    notify_incidents: bool = True
    notify_analysis: bool = True
    notify_actions: bool = True
    notify_approvals: bool = True

    # Severity filters (only notify for these severities)
    notify_severity_levels: list = ["medium", "high", "critical"]

    # Grafana integration (optional)
    grafana_url: Optional[str] = "http://grafana:3000"
    grafana_api_key: Optional[str] = None

    # Message formatting
    include_timestamps: bool = True
    include_metadata: bool = True
    truncate_long_messages: bool = True
    max_message_length: int = 3000

    class Config:
        env_prefix = ""  # No prefix to match deployment script env vars
        case_sensitive = False


# Global config instance
config = Config()
