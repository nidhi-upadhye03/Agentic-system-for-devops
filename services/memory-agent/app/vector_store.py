"""
Vector Store - Qdrant Integration

Handles embedding generation and storage for semantic search.
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import AsyncOpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from app.config import config

logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector database for semantic incident search"""

    def __init__(
        self,
        qdrant_host: str,
        qdrant_port: int,
        qdrant_api_key: str,
        collection_name: str,
        vector_size: int,
        openai_api_key: str,
        openai_model: str = "text-embedding-3-small"
    ):
        """
        Initialize vector store

        Args:
            qdrant_host: Qdrant host URL
            qdrant_port: Qdrant port
            qdrant_api_key: Qdrant API key
            collection_name: Collection name
            vector_size: Embedding vector size
            openai_api_key: OpenAI API key
            openai_model: OpenAI embedding model
        """
        self.qdrant_host = qdrant_host
        self.qdrant_port = qdrant_port
        self.qdrant_api_key = qdrant_api_key
        self.collection_name = collection_name
        self.vector_size = vector_size
        self.openai_model = openai_model

        # Initialize clients
        self.qdrant_client = None
        self.openai_client = AsyncOpenAI(api_key=openai_api_key)

    async def connect(self) -> bool:
        """
        Connect to Qdrant and create collection if needed

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to Qdrant Cloud at {self.qdrant_host}")

            # Initialize Qdrant client (sync client is fine, operations are fast)
            self.qdrant_client = QdrantClient(
                url=self.qdrant_host,
                port=self.qdrant_port,
                api_key=self.qdrant_api_key,
                timeout=30
            )

            # Create collection if it doesn't exist
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ Collection created: {self.collection_name}")
            else:
                logger.info(f"✓ Collection exists: {self.collection_name}")

            # Test connection
            info = self.qdrant_client.get_collection(self.collection_name)
            logger.info(f"✓ Connected to Qdrant - Collection has {info.points_count} points")

            return True

        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
            return False

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text using OpenAI

        Args:
            text: Input text

        Returns:
            Embedding vector or None
        """
        try:
            response = await self.openai_client.embeddings.create(
                model=self.openai_model,
                input=text
            )

            embedding = response.data[0].embedding
            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}", exc_info=True)
            return None

    def _create_incident_text(self, incident: Dict[str, Any]) -> str:
        """
        Create searchable text from incident

        Args:
            incident: Incident data

        Returns:
            Formatted text for embedding
        """
        parts = [
            f"Metric: {incident.get('metric_name', 'unknown')}",
            f"Target: {incident.get('target', 'unknown')}",
            f"Severity: {incident.get('severity', 'medium')}",
            f"Value: {incident.get('current_value', 0)} (threshold: {incident.get('threshold', 0)})"
        ]

        # Add root cause if available
        if "root_cause" in incident:
            parts.append(f"Root Cause: {incident['root_cause']}")

        # Add action details if available
        if "action_type" in incident:
            parts.append(f"Action: {incident['action_type']}")
            if "action_details" in incident:
                details = incident["action_details"]
                if isinstance(details, dict):
                    parts.append(f"Details: {str(details)}")

        return " | ".join(parts)

    async def store_incident_embedding(
        self,
        incident: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None,
        resolution: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Generate and store incident embedding

        Args:
            incident: Incident data
            analysis: Analysis data (optional)
            resolution: Resolution data (optional)

        Returns:
            True if stored successfully
        """
        try:
            # Combine incident + analysis + resolution into searchable text
            incident_copy = incident.copy()
            if analysis:
                incident_copy["root_cause"] = analysis.get("root_cause", "")
                incident_copy["confidence"] = analysis.get("confidence", 0.0)

            if resolution:
                incident_copy["action_type"] = resolution.get("action_type", "")
                incident_copy["action_details"] = resolution.get("action_details", {})
                incident_copy["success"] = resolution.get("success", False)

            # Create searchable text
            text = self._create_incident_text(incident_copy)

            # Generate embedding
            embedding = await self.generate_embedding(text)
            if not embedding:
                logger.error("Failed to generate embedding")
                return False

            # Prepare metadata
            metadata = {
                "incident_id": incident.get("incident_id"),
                "metric_name": incident.get("metric_name"),
                "target": incident.get("target"),
                "severity": incident.get("severity"),
                "detected_at": incident.get("timestamp", datetime.now().isoformat()),
                "has_analysis": analysis is not None,
                "has_resolution": resolution is not None
            }

            if resolution:
                metadata["success"] = resolution.get("success", False)
                metadata["action_type"] = resolution.get("action_type", "")

            # Store in Qdrant
            point_id = incident.get("incident_id", "unknown")
            # Use hash of incident_id as numeric ID
            numeric_id = abs(hash(point_id)) % (10 ** 10)

            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=numeric_id,
                        vector=embedding,
                        payload=metadata
                    )
                ]
            )

            logger.info(f"Stored embedding for incident: {incident.get('incident_id')}")
            return True

        except Exception as e:
            logger.error(f"Failed to store embedding: {e}", exc_info=True)
            return False

    async def search_similar_incidents(
        self,
        incident: Dict[str, Any],
        limit: int = 5,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar past incidents using vector similarity

        Args:
            incident: Current incident to find matches for
            limit: Maximum results
            min_score: Minimum similarity score (0-1)

        Returns:
            List of similar incidents with scores
        """
        try:
            # Create search text
            text = self._create_incident_text(incident)

            # Generate embedding
            embedding = await self.generate_embedding(text)
            if not embedding:
                return []

            # Search Qdrant
            results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=embedding,
                limit=limit,
                score_threshold=min_score
            )

            # Format results
            similar = []
            for result in results:
                similar.append({
                    "incident_id": result.payload.get("incident_id"),
                    "metric_name": result.payload.get("metric_name"),
                    "target": result.payload.get("target"),
                    "severity": result.payload.get("severity"),
                    "similarity_score": result.score,
                    "action_type": result.payload.get("action_type"),
                    "success": result.payload.get("success", False)
                })

            logger.info(f"Found {len(similar)} similar incidents")
            return similar

        except Exception as e:
            logger.error(f"Failed to search similar incidents: {e}", exc_info=True)
            return []

    async def get_successful_patterns(
        self,
        metric_name: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get successful resolution patterns for a metric

        Args:
            metric_name: Metric to filter by
            limit: Maximum results

        Returns:
            List of successful patterns
        """
        try:
            # Search with filters
            results = self.qdrant_client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="metric_name",
                            match=MatchValue(value=metric_name)
                        ),
                        FieldCondition(
                            key="success",
                            match=MatchValue(value=True)
                        ),
                        FieldCondition(
                            key="has_resolution",
                            match=MatchValue(value=True)
                        )
                    ]
                ),
                limit=limit
            )

            patterns = []
            for point in results[0]:  # scroll returns (points, next_offset)
                patterns.append({
                    "incident_id": point.payload.get("incident_id"),
                    "metric_name": point.payload.get("metric_name"),
                    "target": point.payload.get("target"),
                    "action_type": point.payload.get("action_type"),
                    "detected_at": point.payload.get("detected_at")
                })

            logger.info(f"Found {len(patterns)} successful patterns for {metric_name}")
            return patterns

        except Exception as e:
            logger.error(f"Failed to get successful patterns: {e}", exc_info=True)
            return []

    async def batch_store_embeddings(
        self,
        incidents: List[Dict[str, Any]]
    ) -> int:
        """
        Store multiple incident embeddings in batch

        Args:
            incidents: List of incidents with analysis/resolution data

        Returns:
            Number successfully stored
        """
        stored_count = 0

        for incident in incidents:
            analysis = incident.get("analysis")
            resolution = incident.get("resolution")

            success = await self.store_incident_embedding(
                incident=incident,
                analysis=analysis,
                resolution=resolution
            )

            if success:
                stored_count += 1

            # Avoid rate limiting
            await asyncio.sleep(0.1)

        logger.info(f"Batch stored {stored_count}/{len(incidents)} embeddings")
        return stored_count

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics

        Returns:
            Collection stats
        """
        try:
            info = self.qdrant_client.get_collection(self.collection_name)

            return {
                "total_points": info.points_count,
                "vector_size": info.config.params.vectors.size,
                "distance_metric": info.config.params.vectors.distance.name
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}", exc_info=True)
            return {}
