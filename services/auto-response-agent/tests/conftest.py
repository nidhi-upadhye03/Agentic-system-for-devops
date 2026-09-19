"""
Pytest fixtures for auto-response-agent tests
"""
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.log_level = "INFO"
    config.agent_name = "auto-response-test"
    config.agent_version = "1.0.0-test"
    config.environment = "test"
    config.k8s_dry_run = True
    config.k8s_in_cluster = False
    config.k8s_namespace = "test-namespace"
    config.approval_api_url = "http://test-approval:3000/api"
    config.approval_timeout = 300
    config.approval_poll_interval = 5
    config.auto_execute_threshold = 95
    config.require_approval_actions = ["rollback"]
    config.require_approval_criticality = ["critical"]
    config.max_scale_replicas = 10
    config.min_scale_replicas = 1
    config.rabbitmq_host = "test-rabbitmq"
    config.rabbitmq_port = 5672
    config.rabbitmq_user = "test"
    config.rabbitmq_password = "test"
    config.rabbitmq_vhost = "test"
    config.rabbitmq_exchange = "test_events"
    config.rabbitmq_analysis_routing_key = "analyzer.analysis.complete"
    config.max_retries = 3
    config.retry_delay = 1
    config.action_timeout = 60
    return config


@pytest.fixture
def sample_analysis_event() -> Dict[str, Any]:
    """Sample analysis complete event"""
    return {
        "agent": "analyzer",
        "type": "analysis_complete",
        "incident_id": "test-incident-123",
        "timestamp": "2025-11-01T20:00:00Z",
        "original_incident": {
            "severity": "high",
            "data": {
                "metric": "cpu_usage_percent",
                "current_value": 95.0,
                "threshold": 80.0,
                "affected_services": ["user-service"]
            }
        },
        "analysis": {
            "root_cause": "High CPU from traffic spike",
            "confidence": 90,
            "severity": "high"
        },
        "recommendations": [
            {
                "type": "scale_deployment",
                "action_type": "scale_deployment",
                "target": "user-service",
                "target_type": "deployment",
                "replicas": 5,
                "criticality": "high",
                "confidence": 90,
                "reasoning": "Scale to handle traffic spike"
            }
        ]
    }


@pytest.fixture
def sample_low_confidence_event() -> Dict[str, Any]:
    """Sample analysis with low confidence requiring approval"""
    return {
        "agent": "analyzer",
        "type": "analysis_complete",
        "incident_id": "test-incident-456",
        "timestamp": "2025-11-01T20:05:00Z",
        "original_incident": {
            "severity": "medium",
            "data": {
                "metric": "memory_usage_percent",
                "current_value": 88.0,
                "threshold": 85.0
            }
        },
        "analysis": {
            "root_cause": "Possible memory leak",
            "confidence": 60,
            "severity": "medium"
        },
        "recommendations": [
            {
                "type": "restart_pods",
                "action_type": "restart_pods",
                "target": "database-service",
                "criticality": "medium",
                "confidence": 60
            }
        ]
    }


@pytest.fixture
def mock_executor():
    """Mock action executor"""
    executor = AsyncMock()
    executor.get_executor_type = MagicMock(return_value="MockExecutor")
    executor.scale_deployment = AsyncMock(return_value={
        "status": "success",
        "action": "scaled",
        "service": "user-service",
        "replicas": 5
    })
    executor.restart_pods = AsyncMock(return_value={
        "status": "success",
        "action": "restarted",
        "pods_restarted": 3
    })
    executor.rollback_deployment = AsyncMock(return_value={
        "status": "success",
        "action": "rolled_back",
        "revision": "previous"
    })
    return executor


@pytest.fixture
def mock_approval_client():
    """Mock approval client"""
    client = AsyncMock()
    client.disconnect = AsyncMock()
    client.request_approval = AsyncMock(return_value="approval-123")
    client.wait_for_approval = AsyncMock(return_value={
        "approved": True,
        "approver": "admin",
        "comment": "Approved for production"
    })
    return client


@pytest.fixture
def mock_action_validator():
    """Mock action validator"""
    validator = MagicMock()
    validator.should_auto_execute = MagicMock(return_value=True)
    validator.validate_action = MagicMock(return_value={"valid": True})
    validator.validate_scale_parameters = MagicMock(return_value={"valid": True, "replicas": 5})
    return validator


@pytest.fixture
def mock_event_consumer():
    """Mock event consumer"""
    consumer = AsyncMock()
    consumer.connect = AsyncMock()
    consumer.disconnect = AsyncMock()
    consumer.set_message_handler = MagicMock()
    consumer.start_consuming = AsyncMock()
    return consumer


@pytest.fixture
def mock_event_publisher():
    """Mock event publisher"""
    publisher = AsyncMock()
    publisher.connect = AsyncMock()
    publisher.disconnect = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
def sample_scale_action():
    """Sample scale deployment action"""
    return {
        "type": "scale_deployment",
        "action_type": "scale_deployment",
        "target": "user-service",
        "target_type": "deployment",
        "replicas": 5,
        "criticality": "high",
        "confidence": 90
    }


@pytest.fixture
def sample_restart_action():
    """Sample restart pods action"""
    return {
        "type": "restart_pods",
        "action_type": "restart_pods",
        "target": "database-service",
        "target_type": "deployment",
        "criticality": "medium",
        "confidence": 85
    }


@pytest.fixture
def sample_rollback_action():
    """Sample rollback deployment action"""
    return {
        "type": "rollback_deployment",
        "action_type": "rollback_deployment",
        "target": "api-service",
        "target_type": "deployment",
        "criticality": "critical",
        "confidence": 95
    }


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client"""
    client = MagicMock()
    client.AppsV1Api = MagicMock()
    client.CoreV1Api = MagicMock()
    return client
