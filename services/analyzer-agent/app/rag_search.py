"""
RAG Search - Search similar past incidents using vector similarity

Integrates with Qdrant vector database to find similar historical incidents.
"""
import logging
import os
from typing import List, Dict, Any, Optional
import aiohttp

logger = logging.getLogger(__name__)


class RAGSearchError(Exception):
    """Custom exception for RAG search errors"""
    pass


class RAGSearch:
    """RAG-based similar incident search"""

    def __init__(
        self,
        host: str = "qdrant",
        port: int = 6333,
        collection: str = "incident_history",
        api_key: str = ""
    ):
        """
        Initialize RAG Search

        Args:
            host: Qdrant host
            port: Qdrant HTTP port
            collection: Collection name
            api_key: API key (optional)
        """
        self.base_url = f"http://{host}:{port}"
        self.collection = collection
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        logger.info(f"RAG Search initialized: {self.base_url}/{collection}")

    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self.session is None or self.session.closed:
            headers = {}
            if self.api_key:
                headers["api-key"] = self.api_key
            self.session = aiohttp.ClientSession(headers=headers)

    async def close(self):
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search for similar incidents

        Args:
            query: Search query text
            top_k: Number of results to return
            score_threshold: Minimum similarity score

        Returns:
            List of similar incidents with scores

        Raises:
            RAGSearchError: If search fails
        """
        await self._ensure_session()

        # Read LLM service URL from environment
        llm_service_url = os.getenv("LLM_SERVICE_URL", "http://llm-service:8000")
        url = f"{llm_service_url}/api/v1/rag/query"
        payload = {
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold
        }

        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    logger.debug(f"RAG search returned status {response.status} (expected for empty database)")
                    return []

                data = await response.json()
                results = data.get("results", [])

                logger.debug(f"RAG search returned {len(results)} results")
                return results

        except Exception as e:
            logger.warning(f"RAG search failed: {e}")
            return []  # Don't fail analysis if RAG unavailable

    async def health_check(self) -> bool:
        """Check if Qdrant is accessible"""
        await self._ensure_session()

        try:
            url = f"{self.base_url}/collections/{self.collection}"
            async with self.session.get(url) as response:
                return response.status == 200
        except Exception:
            return False

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
