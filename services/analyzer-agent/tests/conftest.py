"""
Pytest fixtures for analyzer-agent tests
"""
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.log_level = "INFO"
    config.agent_name = "analyzer-test"
    config.agent_version = "1.0.0-test"
    config.llm_service_url = "http://test-llm:8000"
    config.llm_provider = "openai"
    config.llm_model = "gpt-4"
    config.llm_temperature = 0.2
    config.llm_max_tokens = 2000
    config.llm_timeout = 60
    config.fetch_logs_enabled = False
    config.log_fetch_window = 600
    config.max_log_lines = 100
    config.rag_enabled = False
    config.rag_top_k = 5
    config.rag_similarity_threshold = 0.7
    config.qdrant_host = "test-qdrant"
    config.qdrant_port = 6333
    config.qdrant_collection = "test_incidents"
    config.rabbitmq_host = "test-rabbitmq"
    config.rabbitmq_port = 5672
    config.rabbitmq_user = "test"
    config.rabbitmq_password = "test"
    config.rabbitmq_vhost = "test"
    config.rabbitmq_exchange = "test_events"
    config.analysis_timeout = 60
    return config


@pytest.fixture
def sample_incident_event() -> Dict[str, Any]:
    """Sample incident event from monitoring agent"""
    return {
        "agent": "monitoring",
        "type": "incident_detected",
        "incident_id": "test-incident-123",
        "timestamp": "2025-11-01T20:00:00Z",
        "severity": "high",
        "data": {
            "metric": "cpu_usage_percent",
            "current_value": 95.5,
            "threshold": 80.0,
            "affected_services": ["user-service", "auth-service"],
            "cluster": "prod-cluster",
            "namespace": "production",
            "pod_name": "user-service-7b9c8d-xyz"
        }
    }


@pytest.fixture
def sample_memory_incident() -> Dict[str, Any]:
    """Sample memory incident event"""
    return {
        "agent": "monitoring",
        "type": "incident_detected",
        "incident_id": "test-incident-456",
        "timestamp": "2025-11-01T20:05:00Z",
        "severity": "critical",
        "data": {
            "metric": "memory_usage_percent",
            "current_value": 92.0,
            "threshold": 85.0,
            "affected_services": ["database-service"],
            "cluster": "prod-cluster",
            "namespace": "production",
            "pod_name": "database-service-abc123"
        }
    }


@pytest.fixture
def sample_llm_analysis() -> Dict[str, Any]:
    """Sample LLM analysis response"""
    return {
        "root_cause": "High CPU usage due to inefficient database queries",
        "confidence": 85,
        "severity": "high",
        "immediate_actions": [
            "Scale user-service to 5 replicas",
            "Investigate database query performance"
        ],
        "recommendations": [
            {
                "action_type": "SCALE",
                "target_service": "user-service",
                "target_type": "deployment",
                "rationale": "Scale to handle increased load",
                "criticality": "high",
                "parameters": {
                    "replicas": 5
                }
            }
        ]
    }


@pytest.fixture
def sample_similar_incidents() -> List[Dict[str, Any]]:
    """Sample similar incidents from RAG search"""
    return [
        {
            "incident_id": "past-incident-1",
            "metric": "cpu_usage_percent",
            "resolution": "Scaled deployment to 5 replicas",
            "success_rate": 0.9,
            "score": 0.85
        },
        {
            "incident_id": "past-incident-2",
            "metric": "cpu_usage_percent",
            "resolution": "Optimized database queries",
            "success_rate": 0.95,
            "score": 0.78
        }
    ]


@pytest.fixture
def sample_logs() -> List[str]:
    """Sample log lines"""
    return [
        "2025-11-01 20:00:00 ERROR user-service: Database query timeout after 30s",
        "2025-11-01 20:00:05 WARN user-service: Connection pool exhausted",
        "2025-11-01 20:00:10 ERROR auth-service: High latency detected (2500ms)",
        "2025-11-01 20:00:15 INFO user-service: Scaling up to handle load"
    ]


@pytest.fixture
def mock_llm_analyzer():
    """Mock LLMAnalyzer"""
    analyzer = AsyncMock()
    analyzer.analyze = AsyncMock(return_value={
        "root_cause": "High CPU usage due to traffic spike",
        "confidence": 85,
        "severity": "high",
        "immediate_actions": ["Scale deployment to 5 replicas"],
        "recommendations": [
            {
                "action_type": "SCALE",
                "target_service": "user-service",
                "target_type": "deployment",
                "rationale": "Scale to handle traffic spike",
                "criticality": "high",
                "parameters": {"replicas": 5}
            }
        ]
    })
    return analyzer


@pytest.fixture
def mock_log_fetcher():
    """Mock LogFetcher"""
    fetcher = AsyncMock()
    fetcher.fetch_logs = AsyncMock(return_value=[
        "ERROR: Database connection timeout",
        "WARN: High CPU detected"
    ])
    return fetcher


@pytest.fixture
def mock_rag_search():
    """Mock RAGSearch"""
    rag = AsyncMock()
    rag.search = AsyncMock(return_value=[
        {
            "incident_id": "past-123",
            "resolution": "Scaled to 5 replicas",
            "score": 0.85
        }
    ])
    return rag


@pytest.fixture
def mock_event_consumer():
    """Mock EventConsumer"""
    consumer = AsyncMock()
    consumer.connect = AsyncMock()
    consumer.disconnect = AsyncMock()
    consumer.subscribe = AsyncMock()
    return consumer


@pytest.fixture
def mock_event_publisher():
    """Mock EventPublisher"""
    publisher = AsyncMock()
    publisher.connect = AsyncMock()
    publisher.disconnect = AsyncMock()
    publisher.publish = AsyncMock()
    return publisher


@pytest.fixture
async def analyzer_agent(
    mock_config,
    mock_llm_analyzer,
    mock_event_consumer,
    mock_event_publisher
):
    """Create AnalyzerAgent instance with mocked dependencies"""
    with patch('app.main.config', mock_config):
        with patch('app.main.LLMAnalyzer', return_value=mock_llm_analyzer):
            with patch('app.main.EventConsumer', return_value=mock_event_consumer):
                with patch('app.main.EventPublisher', return_value=mock_event_publisher):
                    from app.main import AnalyzerAgent
                    agent = AnalyzerAgent()
                    agent.llm_analyzer = mock_llm_analyzer
                    agent.event_consumer = mock_event_consumer
                    agent.event_publisher = mock_event_publisher
                    yield agent


@pytest.fixture
def mock_httpx_client():
    """Mock httpx async client"""
    client = AsyncMock()
    client.post = AsyncMock()
    client.get = AsyncMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    client = MagicMock()
    client.search = MagicMock(return_value=[])
    return client
