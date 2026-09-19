"""
Pytest configuration and fixtures for LLM Service tests
"""
import pytest
from unittest.mock import Mock, MagicMock
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from llm_client import LLMClient, LLMConfig, LLMProvider
from rag_pipeline import RAGPipeline, RAGConfig


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    mock_client = MagicMock()

    # Mock chat completion response
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "This is a test response"
    mock_client.chat.completions.create.return_value = mock_response

    # Mock embedding response
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock()]
    mock_embedding_response.data[0].embedding = [0.1] * 1536
    mock_client.embeddings.create.return_value = mock_embedding_response

    return mock_client


@pytest.fixture
def mock_async_openai_client():
    """Mock AsyncOpenAI client for testing"""
    mock_client = MagicMock()

    # Mock streaming response
    async def mock_stream():
        chunks = ["Hello", " ", "world", "!"]
        for chunk_text in chunks:
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = chunk_text
            yield chunk

    mock_client.chat.completions.create.return_value = mock_stream()
    return mock_client


@pytest.fixture
def llm_config():
    """Create test LLM configuration"""
    return LLMConfig(
        openai_api_key="test-openai-key",
        gemini_api_key="test-gemini-key",
        preferred_provider=LLMProvider.OPENAI,
        openai_model="gpt-4o",
        gemini_model="gemini-2.0-flash-exp",
        max_tokens=2000,
        temperature=0.7
    )


@pytest.fixture
def llm_client(llm_config, mock_openai_client, monkeypatch):
    """Create test LLM client with mocked OpenAI client"""
    def mock_openai_init(api_key, base_url=None):
        return mock_openai_client

    monkeypatch.setattr("llm_client.OpenAI", mock_openai_init)
    return LLMClient(llm_config)


@pytest.fixture
def rag_config():
    """Create test RAG configuration"""
    return RAGConfig(
        qdrant_url="http://localhost:6333",
        qdrant_api_key="test-qdrant-key",
        collection_name="test_knowledge_base",
        embedding_dim=1536,
        chunk_size=1000,
        chunk_overlap=200,
        top_k=5
    )


@pytest.fixture
def mock_qdrant_client():
    """Mock Qdrant client for testing"""
    mock_client = MagicMock()

    # Mock get_collections
    mock_collections = MagicMock()
    mock_collections.collections = []
    mock_client.get_collections.return_value = mock_collections

    # Mock create_collection
    mock_client.create_collection.return_value = None

    # Mock upsert
    mock_client.upsert.return_value = None

    # Mock search
    mock_search_result = MagicMock()
    mock_search_result.payload = {
        "text": "Test document chunk",
        "chunk_index": 0,
        "metadata": {"source": "test"}
    }
    mock_search_result.score = 0.95
    mock_client.search.return_value = [mock_search_result]

    return mock_client


@pytest.fixture
def rag_pipeline(llm_client, rag_config, mock_qdrant_client, monkeypatch):
    """Create test RAG pipeline with mocked dependencies"""
    monkeypatch.setattr("rag_pipeline.QdrantClient", lambda url, api_key: mock_qdrant_client)
    pipeline = RAGPipeline(llm_client, rag_config)
    pipeline.qdrant_client = mock_qdrant_client
    return pipeline


@pytest.fixture
def sample_messages():
    """Sample messages for testing"""
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is Python?"}
    ]


@pytest.fixture
def sample_document():
    """Sample document for testing RAG ingestion"""
    return """
    Python is a high-level, interpreted programming language.
    It was created by Guido van Rossum and first released in 1991.
    Python emphasizes code readability with its notable use of significant indentation.
    It supports multiple programming paradigms, including structured, object-oriented, and functional programming.
    """


@pytest.fixture
def sample_chunks():
    """Sample document chunks for testing"""
    return [
        "Python is a high-level, interpreted programming language.",
        "It was created by Guido van Rossum and first released in 1991.",
        "Python emphasizes code readability with its notable use of significant indentation."
    ]


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration between tests"""
    import logging
    logging.getLogger().handlers = []
    yield
    logging.getLogger().handlers = []


@pytest.fixture
def mock_uuid(monkeypatch):
    """Mock uuid generation for predictable IDs"""
    counter = 0

    def mock_uuid4():
        nonlocal counter
        counter += 1
        mock_id = MagicMock()
        mock_id.__str__ = lambda self: f"test-uuid-{counter}"
        return mock_id

    import uuid
    monkeypatch.setattr(uuid, "uuid4", mock_uuid4)


# Pytest configuration
def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
