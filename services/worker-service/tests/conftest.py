"""
Pytest configuration and fixtures for Worker Service tests
"""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock
from pika.spec import BasicProperties
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.tasks import Base, TaskContext


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_channel():
    """Mock RabbitMQ channel."""
    channel = Mock()
    channel.basic_ack = Mock()
    channel.basic_nack = Mock()
    channel.basic_publish = Mock()
    return channel


@pytest.fixture
def mock_properties():
    """Mock message properties."""
    properties = BasicProperties()
    properties.headers = {}
    return properties


@pytest.fixture
def sample_llm_message():
    """Sample LLM request message."""
    return {
        'request_id': 'req_123',
        'user_id': 'user_456',
        'model': 'gpt-3.5-turbo',
        'prompt': 'Test prompt',
        'parameters': {
            'temperature': 0.7,
            'max_tokens': 100
        }
    }


@pytest.fixture
def sample_approval_message():
    """Sample approval message."""
    return {
        'request_id': 'approval_123',
        'user_id': 'user_456',
        'request_type': 'deployment',
        'request_data': {'environment': 'production'},
        'approvers': ['approver@example.com']
    }


@pytest.fixture
def sample_notification_message():
    """Sample notification message."""
    return {
        'notification_id': 'notif_123',
        'recipient': 'user@example.com',
        'subject': 'Test Subject',
        'body': 'Test body',
        'html': False
    }


@pytest.fixture
def task_context(mock_properties):
    """Create a task context."""
    def _create_context(routing_key: str, message: dict, retry_count: int = 0):
        return TaskContext(
            routing_key=routing_key,
            message=message,
            retry_count=retry_count,
            properties=mock_properties
        )
    return _create_context


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    # Use in-memory SQLite for testing
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def mock_httpx_client(monkeypatch):
    """Mock httpx client for HTTP requests."""
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")

    class MockAsyncClient:
        def __init__(self, *args, **kwargs):
            self.responses = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, url, **kwargs):
            return MockResponse({'response': 'Test response', 'tokens_used': 50})

        async def get(self, url, **kwargs):
            return MockResponse({'status': 'ok'})

    return MockAsyncClient


@pytest.fixture
def mock_smtp(monkeypatch):
    """Mock SMTP server for email testing."""
    class MockSMTP:
        def __init__(self, host, port):
            self.host = host
            self.port = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def starttls(self):
            pass

        def login(self, user, password):
            pass

        def send_message(self, msg):
            pass

    monkeypatch.setattr('smtplib.SMTP', MockSMTP)
    return MockSMTP
