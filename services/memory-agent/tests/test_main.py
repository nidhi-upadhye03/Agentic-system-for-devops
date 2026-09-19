"""
Unit tests for memory-agent
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.unit
@pytest.mark.asyncio
class TestMemoryAgent:
    """Test MemoryAgent main class"""

    async def test_agent_initialization(self, mock_config):
        """Test memory agent initializes correctly"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool', new_callable=AsyncMock):
                with patch('app.main.QdrantClient'):
                    with patch('app.main.OpenAI'):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()

                            assert agent is not None

    async def test_store_incident(
        self,
        mock_config,
        sample_incident,
        mock_db_pool,
        mock_qdrant_client,
        mock_openai_client
    ):
        """Test storing incident in database and vector store"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool', return_value=mock_db_pool):
                with patch('app.main.QdrantClient', return_value=mock_qdrant_client):
                    with patch('app.main.OpenAI', return_value=mock_openai_client):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()
                            agent.db_pool = mock_db_pool
                            agent.qdrant_client = mock_qdrant_client
                            agent.openai_client = mock_openai_client

                            # Execute
                            await agent.store_incident(sample_incident)

                            # Verify database insert
                            assert mock_db_pool.acquire.called

                            # Verify embedding created and stored
                            assert mock_openai_client.embeddings.create.called
                            assert mock_qdrant_client.upsert.called

    async def test_retrieve_similar_incidents(
        self,
        mock_config,
        sample_similar_incidents,
        mock_db_pool,
        mock_qdrant_client,
        mock_openai_client
    ):
        """Test retrieving similar incidents"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool', return_value=mock_db_pool):
                with patch('app.main.QdrantClient', return_value=mock_qdrant_client):
                    with patch('app.main.OpenAI', return_value=mock_openai_client):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()
                            agent.qdrant_client = mock_qdrant_client
                            agent.openai_client = mock_openai_client

                            # Mock search results
                            mock_result = MagicMock()
                            mock_result.id = "past-incident-1"
                            mock_result.score = 0.92
                            mock_result.payload = {
                                "incident_id": "past-incident-1",
                                "resolution": "Scaled to 5 replicas"
                            }
                            mock_qdrant_client.search = AsyncMock(return_value=[mock_result])

                            # Execute
                            query = "High CPU usage in user-service"
                            similar = await agent.retrieve_similar_incidents(query, top_k=5)

                            # Verify
                            assert len(similar) > 0
                            assert similar[0]["incident_id"] == "past-incident-1"
                            assert mock_openai_client.embeddings.create.called

    async def test_detect_patterns(
        self,
        mock_config,
        mock_db_pool
    ):
        """Test pattern detection in incidents"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool', return_value=mock_db_pool):
                with patch('app.main.QdrantClient'):
                    with patch('app.main.OpenAI'):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()
                            agent.db_pool = mock_db_pool

                            # Mock database query for patterns
                            mock_pattern_row = {
                                "metric": "cpu_usage_percent",
                                "service": "user-service",
                                "count": 5,
                                "common_resolution": "Scaled deployment"
                            }
                            mock_db_pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
                                return_value=[mock_pattern_row]
                            )

                            # Execute
                            patterns = await agent.detect_patterns()

                            # Verify
                            assert isinstance(patterns, list)

    async def test_learn_from_resolution(
        self,
        mock_config,
        mock_db_pool,
        mock_qdrant_client
    ):
        """Test learning from successful resolution"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool', return_value=mock_db_pool):
                with patch('app.main.QdrantClient', return_value=mock_qdrant_client):
                    with patch('app.main.OpenAI'):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()
                            agent.db_pool = mock_db_pool

                            resolution_data = {
                                "incident_id": "test-incident-123",
                                "action_taken": "scale_deployment",
                                "success": True,
                                "metrics_after": {
                                    "cpu_usage": 60.0
                                }
                            }

                            # Execute
                            await agent.learn_from_resolution(resolution_data)

                            # Verify database update
                            assert mock_db_pool.acquire.called

    async def test_create_embedding(
        self,
        mock_config,
        mock_openai_client
    ):
        """Test creating embeddings from text"""
        with patch('app.main.config', mock_config):
            with patch('asyncpg.create_pool'):
                with patch('app.main.QdrantClient'):
                    with patch('app.main.OpenAI', return_value=mock_openai_client):
                        with patch('app.main.EventConsumer'):
                            from app.main import MemoryAgent
                            agent = MemoryAgent()
                            agent.openai_client = mock_openai_client

                            # Execute
                            text = "High CPU usage in user-service"
                            embedding = await agent.create_embedding(text)

                            # Verify
                            assert isinstance(embedding, list)
                            assert len(embedding) == 1536
                            assert mock_openai_client.embeddings.create.called


@pytest.mark.unit
class TestIncidentStore:
    """Test incident storage functionality"""

    async def test_store_incident_success(self, sample_incident, mock_db_pool):
        """Test successful incident storage"""
        from app.incident_store import IncidentStore

        store = IncidentStore(mock_db_pool)

        # Mock successful insert
        mock_db_pool.acquire.return_value.__aenter__.return_value.execute = AsyncMock()

        await store.store_incident(sample_incident)

        # Verify execute was called
        assert mock_db_pool.acquire.called

    async def test_get_incident_by_id(self, mock_db_pool):
        """Test retrieving incident by ID"""
        from app.incident_store import IncidentStore

        store = IncidentStore(mock_db_pool)

        # Mock database row
        mock_row = {
            "incident_id": "test-123",
            "metric": "cpu_usage",
            "service": "user-service"
        }
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow = AsyncMock(
            return_value=mock_row
        )

        incident = await store.get_incident_by_id("test-123")

        assert incident is not None
        assert incident["incident_id"] == "test-123"

    async def test_get_recent_incidents(self, mock_db_pool):
        """Test retrieving recent incidents"""
        from app.incident_store import IncidentStore

        store = IncidentStore(mock_db_pool)

        # Mock multiple rows
        mock_rows = [
            {"incident_id": "inc-1", "timestamp": "2025-11-01T20:00:00Z"},
            {"incident_id": "inc-2", "timestamp": "2025-11-01T19:00:00Z"}
        ]
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
            return_value=mock_rows
        )

        incidents = await store.get_recent_incidents(limit=10)

        assert len(incidents) == 2
        assert incidents[0]["incident_id"] == "inc-1"


@pytest.mark.unit
@pytest.mark.asyncio
class TestPatternDetector:
    """Test pattern detection"""

    async def test_detect_recurring_patterns(self, mock_db_pool):
        """Test detecting recurring incident patterns"""
        from app.pattern_detector import PatternDetector

        detector = PatternDetector(
            db_pool=mock_db_pool,
            min_occurrences=3,
            time_window_hours=168
        )

        # Mock pattern results
        mock_patterns = [
            {
                "metric": "cpu_usage_percent",
                "service": "user-service",
                "count": 5,
                "avg_confidence": 85.0
            }
        ]
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetch = AsyncMock(
            return_value=mock_patterns
        )

        patterns = await detector.detect_recurring_patterns()

        assert len(patterns) > 0
        assert patterns[0]["count"] >= 3

    async def test_calculate_success_rate(self, mock_db_pool):
        """Test calculating resolution success rate"""
        from app.pattern_detector import PatternDetector

        detector = PatternDetector(
            db_pool=mock_db_pool,
            min_occurrences=3,
            time_window_hours=168
        )

        # Mock success rate query
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchval = AsyncMock(
            return_value=0.85
        )

        success_rate = await detector.calculate_success_rate(
            metric="cpu_usage_percent",
            resolution="scale_deployment"
        )

        assert success_rate == 0.85


@pytest.mark.unit
@pytest.mark.asyncio
class TestVectorStore:
    """Test vector store operations"""

    async def test_upsert_embedding(self, mock_qdrant_client):
        """Test upserting embedding to Qdrant"""
        from app.vector_store import VectorStore

        vector_store = VectorStore(
            client=mock_qdrant_client,
            collection_name="test_incidents"
        )

        embedding = [0.1] * 1536
        metadata = {
            "incident_id": "test-123",
            "metric": "cpu_usage"
        }

        await vector_store.upsert_embedding(
            id="test-123",
            embedding=embedding,
            metadata=metadata
        )

        assert mock_qdrant_client.upsert.called

    async def test_search_similar(self, mock_qdrant_client):
        """Test searching for similar embeddings"""
        from app.vector_store import VectorStore

        vector_store = VectorStore(
            client=mock_qdrant_client,
            collection_name="test_incidents"
        )

        # Mock search result
        mock_result = MagicMock()
        mock_result.id = "similar-1"
        mock_result.score = 0.9
        mock_result.payload = {"incident_id": "similar-1"}
        mock_qdrant_client.search = AsyncMock(return_value=[mock_result])

        query_embedding = [0.1] * 1536
        results = await vector_store.search_similar(
            query_embedding=query_embedding,
            top_k=5,
            score_threshold=0.7
        )

        assert len(results) > 0
        assert results[0]["score"] == 0.9
