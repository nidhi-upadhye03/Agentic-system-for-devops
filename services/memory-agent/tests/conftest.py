"""
Pytest fixtures for memory-agent tests
"""
import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime


@pytest.fixture
def mock_config():
    """Mock configuration"""
    config = MagicMock()
    config.log_level = "INFO"
    config.agent_name = "memory-test"
    config.agent_version = "1.0.0-test"
    config.postgres_host = "test-postgres"
    config.postgres_port = 5432
    config.postgres_db = "test_db"
    config.postgres_user = "test"
    config.postgres_password = "test"
    config.qdrant_host = "test-qdrant"
    config.qdrant_http_port = 6333
    config.qdrant_collection_name = "test_incidents"
    config.qdrant_vector_size = 1536
    config.openai_api_key = "test-key"
    config.openai_model = "text-embedding-3-small"
    config.pattern_detection_enabled = True
    config.pattern_similarity_threshold = 0.85
    config.pattern_min_occurrences = 3
    config.pattern_time_window_hours = 168
    config.learning_enabled = True
    config.successful_resolution_threshold = 0.8
    config.embedding_batch_size = 10
    config.rabbitmq_host = "test-rabbitmq"
    config.rabbitmq_port = 5672
    config.rabbitmq_user = "test"
    config.rabbitmq_password = "test"
    config.rabbitmq_vhost = "test"
    return config


@pytest.fixture
def sample_incident():
    """Sample incident for storage"""
    return {
        "incident_id": "test-incident-123",
        "timestamp": "2025-11-01T20:00:00Z",
        "severity": "high",
        "metric": "cpu_usage_percent",
        "service": "user-service",
        "current_value": 95.0,
        "threshold": 80.0,
        "root_cause": "High traffic spike",
        "resolution": "Scaled to 5 replicas",
        "success": True
    }


@pytest.fixture
def sample_pattern():
    """Sample incident pattern"""
    return {
        "pattern_id": "pattern-123",
        "description": "High CPU during peak hours",
        "occurrences": 5,
        "success_rate": 0.9,
        "common_resolution": "Scale deployment",
        "affected_services": ["user-service", "auth-service"]
    }


@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()
    conn.fetch = AsyncMock(return_value=[])
    conn.fetchrow = AsyncMock(return_value=None)
    conn.fetchval = AsyncMock(return_value=1)
    pool.acquire = AsyncMock(return_value=conn)
    pool.__aenter__ = AsyncMock(return_value=conn)
    pool.__aexit__ = AsyncMock()
    return pool


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client"""
    client = AsyncMock()
    client.upsert = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.get_collection = AsyncMock()
    return client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    client = AsyncMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    client.embeddings.create = AsyncMock(return_value=mock_response)
    return client


@pytest.fixture
def sample_similar_incidents():
    """Sample similar incidents from vector search"""
    return [
        {
            "incident_id": "past-incident-1",
            "metric": "cpu_usage_percent",
            "resolution": "Scaled to 5 replicas",
            "success": True,
            "score": 0.92
        },
        {
            "incident_id": "past-incident-2",
            "metric": "cpu_usage_percent",
            "resolution": "Optimized queries",
            "success": True,
            "score": 0.87
        }
    ]


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors"""
    return {
        "incident-123": [0.1, 0.2, 0.3] * 512,  # 1536 dimensions
        "incident-456": [0.2, 0.3, 0.4] * 512
    }
