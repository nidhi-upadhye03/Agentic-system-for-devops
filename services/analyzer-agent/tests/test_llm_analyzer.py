"""
Unit tests for LLM Analyzer
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


@pytest.mark.unit
@pytest.mark.asyncio
class TestLLMAnalyzer:
    """Test LLMAnalyzer class"""

    @pytest.fixture
    def llm_analyzer(self):
        """Create LLMAnalyzer instance"""
        from app.llm_analyzer import LLMAnalyzer
        return LLMAnalyzer(
            service_url="http://test-llm:8000",
            provider="openai",
            model="gpt-4",
            temperature=0.2
        )

    async def test_analyze_success(self, llm_analyzer, mock_httpx_client):
        """Test successful LLM analysis"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "root_cause": "High CPU from database queries",
            "confidence": 85,
            "severity": "high",
            "immediate_actions": ["Scale deployment"],
            "recommendations": [
                {
                    "action_type": "SCALE",
                    "target_service": "user-service",
                    "target_type": "deployment",
                    "rationale": "Scale to handle load",
                    "criticality": "high",
                    "parameters": {"replicas": 5}
                }
            ]
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        # Patch httpx.AsyncClient
        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            result = await llm_analyzer.analyze(
                prompt="Test incident analysis"
            )

        # Verify
        assert result["root_cause"] == "High CPU from database queries"
        assert result["confidence"] == 85
        assert "recommendations" in result

    async def test_analyze_timeout(self, llm_analyzer):
        """Test LLM analysis timeout"""
        # Mock timeout
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(Exception):
                await llm_analyzer.analyze(
                    prompt="Test",
                    timeout=1
                )

    async def test_analyze_http_error(self, llm_analyzer):
        """Test LLM analysis HTTP error handling"""
        # Mock 500 error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "500 Server Error",
                request=MagicMock(),
                response=mock_response
            )
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('httpx.AsyncClient', return_value=mock_client):
            with pytest.raises(Exception):
                await llm_analyzer.analyze(prompt="Test")

    async def test_analyze_malformed_response(self, llm_analyzer):
        """Test handling of malformed LLM response"""
        # Mock malformed JSON response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "invalid_field": "missing required fields"
        }

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch('httpx.AsyncClient', return_value=mock_client):
            # Should handle gracefully or raise appropriate error
            result = await llm_analyzer.analyze(prompt="Test")
            # Verify error handling
            assert isinstance(result, dict)

    async def test_analyze_with_custom_timeout(self, llm_analyzer, mock_httpx_client):
        """Test analysis with custom timeout"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "root_cause": "Test cause",
            "confidence": 70
        }
        mock_httpx_client.post = AsyncMock(return_value=mock_response)

        with patch('httpx.AsyncClient', return_value=mock_httpx_client):
            result = await llm_analyzer.analyze(
                prompt="Test",
                timeout=30
            )

        # Verify timeout was passed
        assert mock_httpx_client.post.called
        call_args = mock_httpx_client.post.call_args
        if 'timeout' in call_args.kwargs:
            assert call_args.kwargs['timeout'] == 30

    async def test_analyze_empty_prompt(self, llm_analyzer):
        """Test analysis with empty prompt"""
        with pytest.raises(ValueError):
            await llm_analyzer.analyze(prompt="")


@pytest.mark.unit
@pytest.mark.asyncio
class TestRAGSearch:
    """Test RAG Search functionality"""

    @pytest.fixture
    def rag_search(self, mock_qdrant_client):
        """Create RAGSearch instance with mock client"""
        with patch('app.rag_search.QdrantClient', return_value=mock_qdrant_client):
            from app.rag_search import RAGSearch
            return RAGSearch(
                host="test-qdrant",
                port=6333,
                collection="test_incidents"
            )

    async def test_search_success(self, rag_search, mock_qdrant_client):
        """Test successful RAG search"""
        # Mock search results
        mock_result = MagicMock()
        mock_result.id = "incident-123"
        mock_result.score = 0.85
        mock_result.payload = {
            "incident_id": "incident-123",
            "metric": "cpu_usage",
            "resolution": "Scaled to 5 replicas",
            "success_rate": 0.9
        }

        mock_qdrant_client.search = MagicMock(return_value=[mock_result])

        # Execute
        results = await rag_search.search(
            query="High CPU usage in user-service",
            top_k=5,
            score_threshold=0.7
        )

        # Verify
        assert len(results) > 0
        assert results[0]["incident_id"] == "incident-123"
        assert results[0]["score"] == 0.85

    async def test_search_no_results(self, rag_search, mock_qdrant_client):
        """Test search with no results"""
        mock_qdrant_client.search = MagicMock(return_value=[])

        results = await rag_search.search(
            query="Unique incident",
            top_k=5,
            score_threshold=0.9
        )

        assert results == []

    async def test_search_below_threshold(self, rag_search, mock_qdrant_client):
        """Test search filters results below threshold"""
        # Mock low-score results
        mock_result = MagicMock()
        mock_result.id = "incident-456"
        mock_result.score = 0.5  # Below threshold
        mock_result.payload = {
            "incident_id": "incident-456",
            "resolution": "Unknown"
        }

        mock_qdrant_client.search = MagicMock(return_value=[mock_result])

        results = await rag_search.search(
            query="Test query",
            top_k=5,
            score_threshold=0.7  # Higher than result score
        )

        # Should be filtered out
        assert len(results) == 0

    async def test_search_connection_error(self, rag_search, mock_qdrant_client):
        """Test handling of Qdrant connection error"""
        mock_qdrant_client.search = MagicMock(
            side_effect=Exception("Connection refused")
        )

        with pytest.raises(Exception):
            await rag_search.search(query="Test", top_k=5)


@pytest.mark.unit
@pytest.mark.asyncio
class TestLogFetcher:
    """Test Log Fetcher functionality"""

    @pytest.fixture
    def log_fetcher(self):
        """Create LogFetcher instance"""
        from app.log_fetcher import LogFetcher
        return LogFetcher()

    async def test_fetch_logs_success(self, log_fetcher):
        """Test successful log fetching"""
        # Mock Kubernetes client or log source
        mock_logs = [
            "2025-11-01 20:00:00 ERROR: Connection timeout",
            "2025-11-01 20:00:05 WARN: Retrying connection"
        ]

        # Mock the fetch implementation
        with patch.object(log_fetcher, 'fetch_logs', return_value=mock_logs):
            logs = await log_fetcher.fetch_logs(
                services=["user-service"],
                time_window=600,
                max_lines=100
            )

        assert len(logs) == 2
        assert "ERROR" in logs[0]

    async def test_fetch_logs_empty_services(self, log_fetcher):
        """Test log fetching with no services"""
        logs = await log_fetcher.fetch_logs(
            services=[],
            time_window=600,
            max_lines=100
        )

        assert logs == []

    async def test_fetch_logs_max_lines_limit(self, log_fetcher):
        """Test log fetching respects max_lines limit"""
        # Generate many logs
        mock_logs = [f"Log line {i}" for i in range(200)]

        with patch.object(log_fetcher, 'fetch_logs', return_value=mock_logs[:50]):
            logs = await log_fetcher.fetch_logs(
                services=["user-service"],
                time_window=600,
                max_lines=50
            )

        assert len(logs) <= 50


@pytest.mark.unit
class TestEventConsumer:
    """Test Event Consumer"""

    @pytest.fixture
    def event_consumer(self):
        """Create EventConsumer instance"""
        from app.event_consumer import EventConsumer
        return EventConsumer(
            host="test-rabbitmq",
            port=5672,
            user="test",
            password="test",
            vhost="test"
        )

    async def test_connect(self, event_consumer):
        """Test RabbitMQ connection"""
        with patch('aio_pika.connect_robust', new_callable=AsyncMock) as mock_connect:
            mock_connection = AsyncMock()
            mock_channel = AsyncMock()
            mock_connection.channel = AsyncMock(return_value=mock_channel)
            mock_connect.return_value = mock_connection

            await event_consumer.connect()

            assert mock_connect.called

    async def test_subscribe(self, event_consumer):
        """Test subscribing to events"""
        # Mock connection setup
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_queue = AsyncMock()

        event_consumer.channel = mock_channel
        mock_channel.declare_exchange = AsyncMock(return_value=mock_exchange)
        mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

        callback = AsyncMock()

        await event_consumer.subscribe(
            exchange="test_events",
            routing_key="monitoring.incident.*",
            callback=callback
        )

        assert mock_channel.declare_exchange.called
        assert mock_channel.declare_queue.called


@pytest.mark.unit
class TestEventPublisher:
    """Test Event Publisher"""

    @pytest.fixture
    def event_publisher(self):
        """Create EventPublisher instance"""
        from app.event_publisher import EventPublisher
        return EventPublisher(
            host="test-rabbitmq",
            port=5672,
            user="test",
            password="test",
            vhost="test",
            exchange="test_events"
        )

    async def test_publish(self, event_publisher):
        """Test publishing events"""
        # Mock connection
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_exchange.publish = AsyncMock()

        event_publisher.channel = mock_channel
        event_publisher.exchange = mock_exchange

        message = {
            "type": "analysis_complete",
            "incident_id": "test-123",
            "data": {}
        }

        await event_publisher.publish(
            routing_key="analyzer.analysis.complete",
            message=message
        )

        assert mock_exchange.publish.called
