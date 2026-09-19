"""
RAG Pipeline - Retrieval-Augmented Generation using Qdrant vector store
Supports document ingestion, chunking, vector search, and context-enhanced responses
"""
from __future__ import annotations
from typing import Any, List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from pydantic_settings import BaseSettings
import logging
import uuid
import time
import re

logger = logging.getLogger(__name__)


class RAGConfig(BaseSettings):
    """Configuration for RAG pipeline"""
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""
    collection_name: str = "knowledge_base"
    embedding_dim: int = 1536  # OpenAI ada-002 dimension
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    max_context_tokens: int = 4000  # Maximum tokens to include in context

    @property
    def qdrant_url(self) -> str:
        """Build Qdrant URL from host and port"""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    class Config:
        env_file = ".env"


class DocumentChunk:
    """Represents a chunk of a document"""
    def __init__(
        self,
        text: str,
        chunk_index: int,
        total_chunks: int,
        metadata: Dict[str, Any]
    ):
        self.text = text
        self.chunk_index = chunk_index
        self.total_chunks = total_chunks
        self.metadata = metadata


class RAGPipeline:
    """RAG pipeline for document ingestion and retrieval"""

    def __init__(self, llm_client, config: RAGConfig | None = None):
        self.config = config or RAGConfig()
        self.llm_client = llm_client

        # Initialize Qdrant client
        self.qdrant_client = QdrantClient(
            url=self.config.qdrant_url,
            api_key=self.config.qdrant_api_key if self.config.qdrant_api_key else None
        )

        # Create collection if it doesn't exist
        self._ensure_collection()
        logger.info("RAG Pipeline initialized")

    def _ensure_collection(self):
        """Ensure the vector collection exists with retry logic"""
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                collections = self.qdrant_client.get_collections().collections
                collection_names = [c.name for c in collections]

                if self.config.collection_name not in collection_names:
                    self.qdrant_client.create_collection(
                        collection_name=self.config.collection_name,
                        vectors_config=VectorParams(
                            size=self.config.embedding_dim,
                            distance=Distance.COSINE
                        )
                    )
                    logger.info(f"Created collection: {self.config.collection_name}")
                else:
                    logger.info(f"Collection {self.config.collection_name} already exists")
                return  # Success!

            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1}/{max_retries} failed to connect to Qdrant: {e}. Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"Failed to connect to Qdrant after {max_retries} attempts: {e}")
                    raise

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks with overlap while preserving sentence boundaries

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        # Split into sentences (simple approach)
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_length = len(sentence)

            # If adding this sentence would exceed chunk_size
            if current_length + sentence_length > self.config.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(' '.join(current_chunk))

                # Start new chunk with overlap
                # Calculate how many sentences to keep for overlap
                overlap_text = ' '.join(current_chunk)
                overlap_length = len(overlap_text)

                # Keep removing sentences from the start until we're within overlap size
                while overlap_length > self.config.chunk_overlap and current_chunk:
                    removed = current_chunk.pop(0)
                    overlap_length -= len(removed) + 1  # +1 for space

                current_length = overlap_length

            current_chunk.append(sentence)
            current_length += sentence_length + 1  # +1 for space

        # Add final chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def ingest_document(
        self,
        text: str,
        metadata: Dict[str, Any] | None = None,
        document_id: str | None = None
    ) -> Dict[str, Any]:
        """
        Ingest a document into the vector store

        Args:
            text: Document text to ingest
            metadata: Optional metadata for the document
            document_id: Optional unique document ID (auto-generated if not provided)

        Returns:
            Dictionary with ingestion results
        """
        start_time = time.time()
        doc_id = document_id or str(uuid.uuid4())

        try:
            # Split text into chunks
            chunks = self._chunk_text(text)
            total_chunks = len(chunks)
            logger.info(f"Split document {doc_id} into {total_chunks} chunks")

            if not chunks:
                logger.warning(f"No chunks created for document {doc_id}")
                return {
                    "document_id": doc_id,
                    "chunks_created": 0,
                    "status": "empty",
                    "duration_ms": int((time.time() - start_time) * 1000)
                }

            # Create embeddings and upload in batches
            points = []
            batch_size = 10  # Process 10 chunks at a time

            for i in range(0, len(chunks), batch_size):
                batch_chunks = chunks[i:i + batch_size]

                for j, chunk in enumerate(batch_chunks):
                    chunk_index = i + j

                    # Create embedding
                    embedding = self.llm_client.create_embedding(chunk)

                    # Create point with enhanced metadata
                    point_metadata = {
                        "text": chunk,
                        "chunk_index": chunk_index,
                        "total_chunks": total_chunks,
                        "document_id": doc_id,
                        "ingested_at": time.time(),
                        **(metadata or {})
                    }

                    point = PointStruct(
                        id=str(uuid.uuid4()),
                        vector=embedding,
                        payload=point_metadata
                    )
                    points.append(point)

                # Upload batch to Qdrant
                self.qdrant_client.upsert(
                    collection_name=self.config.collection_name,
                    points=points
                )
                points.clear()  # Clear for next batch

            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Successfully ingested document {doc_id} with {total_chunks} chunks in {duration_ms}ms")

            return {
                "document_id": doc_id,
                "chunks_created": total_chunks,
                "status": "success",
                "duration_ms": duration_ms
            }

        except Exception as e:
            logger.error(f"Error ingesting document {doc_id}: {e}")
            raise

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        filter_metadata: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents for a query

        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of retrieved documents with text, score, and metadata
        """
        try:
            # Create query embedding
            query_embedding = self.llm_client.create_embedding(query)

            # Build filter if metadata provided
            query_filter = None
            if filter_metadata:
                conditions = []
                for key, value in filter_metadata.items():
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    query_filter = Filter(must=conditions)

            # Search in Qdrant
            results = self.qdrant_client.search(
                collection_name=self.config.collection_name,
                query_vector=query_embedding,
                limit=top_k or self.config.top_k,
                query_filter=query_filter
            )

            # Format results
            documents = []
            for result in results:
                documents.append({
                    "text": result.payload["text"],
                    "score": result.score,
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "total_chunks": result.payload.get("total_chunks", 1),
                    "document_id": result.payload.get("document_id", "unknown"),
                    "metadata": {k: v for k, v in result.payload.items()
                               if k not in ["text", "chunk_index", "total_chunks", "document_id", "ingested_at"]}
                })

            logger.info(f"Retrieved {len(documents)} documents for query")
            return documents

        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            raise

    def rag_query(
        self,
        query: str,
        system_prompt: str | None = None,
        top_k: int | None = None,
        filter_metadata: Dict[str, Any] | None = None,
        provider: str | None = None
    ) -> Dict[str, Any]:
        """
        Perform RAG query: retrieve context and generate answer

        Args:
            query: User question
            system_prompt: Optional system prompt
            top_k: Number of documents to retrieve
            filter_metadata: Optional metadata filters
            provider: LLM provider to use

        Returns:
            Dictionary with answer, context, and metadata
        """
        try:
            # Retrieve relevant documents
            documents = self.retrieve(query, top_k, filter_metadata)

            if not documents:
                # No context found, answer directly
                logger.warning("No relevant context found, answering without RAG")
                messages = [
                    {"role": "system", "content": system_prompt or "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ]
                response = self.llm_client.chat_completion(messages, provider=provider)

                return {
                    "answer": response.content,
                    "context_used": False,
                    "num_documents": 0,
                    "documents": [],
                    "llm_response": {
                        "provider": str(response.provider),
                        "model": response.model,
                        "total_tokens": response.total_tokens,
                        "latency_ms": response.latency_ms
                    }
                }

            # Build context from retrieved documents
            context_parts = []
            for i, doc in enumerate(documents):
                context_parts.append(
                    f"[Document {i+1}] (Relevance: {doc['score']:.3f})\n{doc['text']}"
                )
            context = "\n\n".join(context_parts)

            # Create prompt with context
            system_msg = system_prompt or "You are a helpful assistant. Answer questions based on the provided context. If the context doesn't contain enough information, say so."
            user_msg = f"Context:\n{context}\n\n---\n\nQuestion: {query}\n\nPlease answer the question based on the context above. Include relevant details and cite which document(s) you used."

            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ]

            # Generate answer
            response = self.llm_client.chat_completion(messages, provider=provider)
            logger.info(f"Successfully generated RAG answer using {len(documents)} documents")

            return {
                "answer": response.content,
                "context_used": True,
                "num_documents": len(documents),
                "documents": documents,
                "llm_response": {
                    "provider": str(response.provider),
                    "model": response.model,
                    "total_tokens": response.total_tokens,
                    "latency_ms": response.latency_ms
                }
            }

        except Exception as e:
            logger.error(f"Error in RAG query: {e}")
            raise

    def delete_document(self, document_id: str) -> int:
        """
        Delete all chunks of a specific document

        Args:
            document_id: Document ID to delete

        Returns:
            Number of chunks deleted
        """
        try:
            # Search for all chunks with this document_id
            filter_condition = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )

            # Delete matching points
            result = self.qdrant_client.delete(
                collection_name=self.config.collection_name,
                points_selector=filter_condition
            )

            logger.info(f"Deleted document {document_id}")
            return result

        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection

        Returns:
            Dictionary with collection stats
        """
        try:
            collection_info = self.qdrant_client.get_collection(self.config.collection_name)

            return {
                "collection_name": self.config.collection_name,
                "vectors_count": collection_info.vectors_count,
                "points_count": collection_info.points_count,
                "status": collection_info.status,
                "config": {
                    "embedding_dim": self.config.embedding_dim,
                    "chunk_size": self.config.chunk_size,
                    "chunk_overlap": self.config.chunk_overlap
                }
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            raise

    def delete_collection(self):
        """Delete the entire collection (use with caution)"""
        try:
            self.qdrant_client.delete_collection(self.config.collection_name)
            logger.info(f"Deleted collection: {self.config.collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise


# Example usage
if __name__ == "__main__":
    from llm_client import LLMClient
    import json

    # Initialize
    llm_client = LLMClient()
    rag_pipeline = RAGPipeline(llm_client)

    print("=" * 60)
    print("RAG Pipeline Example")
    print("=" * 60)

    # Get collection stats
    stats = rag_pipeline.get_collection_stats()
    print(f"\nCollection: {stats['collection_name']}")
    print(f"Vectors: {stats['vectors_count']}, Points: {stats['points_count']}")

    # Ingest a document
    document_text = """
    Kubernetes is an open-source container orchestration platform.
    It automates the deployment, scaling, and management of containerized applications.
    Kubernetes was originally developed by Google and is now maintained by the Cloud Native Computing Foundation (CNCF).

    Key features include:
    - Automated rollouts and rollbacks
    - Service discovery and load balancing
    - Storage orchestration
    - Self-healing
    - Secret and configuration management

    Kubernetes uses a declarative approach to manage infrastructure. You describe the desired state
    of your application using YAML configuration files, and Kubernetes works to maintain that state.
    """

    print("\n" + "=" * 60)
    print("Ingesting Document...")
    print("=" * 60)

    result = rag_pipeline.ingest_document(
        document_text,
        metadata={"source": "kubernetes_intro", "version": "1.0", "category": "infrastructure"}
    )
    print(f"Document ID: {result['document_id']}")
    print(f"Chunks created: {result['chunks_created']}")
    print(f"Status: {result['status']}")
    print(f"Duration: {result['duration_ms']}ms")

    # Perform RAG query
    print("\n" + "=" * 60)
    print("Performing RAG Query...")
    print("=" * 60)

    question = "What is Kubernetes and what are its main features?"
    rag_result = rag_pipeline.rag_query(question)

    print(f"\nQuestion: {question}")
    print(f"\nAnswer: {rag_result['answer']}")
    print(f"\nContext Used: {rag_result['context_used']}")
    print(f"Documents Retrieved: {rag_result['num_documents']}")
    print(f"LLM Provider: {rag_result['llm_response']['provider']}")
    print(f"Model: {rag_result['llm_response']['model']}")
    print(f"Total Tokens: {rag_result['llm_response']['total_tokens']}")
    print(f"Latency: {rag_result['llm_response']['latency_ms']}ms")

    # Retrieve documents
    print("\n" + "=" * 60)
    print("Direct Document Retrieval...")
    print("=" * 60)

    docs = rag_pipeline.retrieve("container orchestration", top_k=3)
    print(f"\nRetrieved {len(docs)} documents for 'container orchestration'")

    for i, doc in enumerate(docs):
        print(f"\n[Document {i+1}]")
        print(f"  Score: {doc['score']:.4f}")
        print(f"  Document ID: {doc['document_id']}")
        print(f"  Chunk: {doc['chunk_index'] + 1}/{doc['total_chunks']}")
        print(f"  Text: {doc['text'][:150]}...")
        if doc['metadata']:
            print(f"  Metadata: {json.dumps(doc['metadata'], indent=4)}")

    print("\n" + "=" * 60)
    print("RAG Pipeline Example Complete!")
    print("=" * 60)
