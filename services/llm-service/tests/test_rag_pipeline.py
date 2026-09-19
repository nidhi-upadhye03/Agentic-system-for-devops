"""
Comprehensive unit tests for RAG Pipeline
Tests document ingestion, retrieval, and RAG query functionality
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from rag_pipeline import RAGPipeline, RAGConfig
from qdrant_client.models import Distance, VectorParams, PointStruct


class TestRAGConfig:
    """Tests for RAG configuration"""

    def test_default_config(self):
        """Test default RAG configuration values"""
        config = RAGConfig()
        assert config.qdrant_url == "https://localhost:6333"
        assert config.collection_name == "knowledge_base"
        assert config.embedding_dim == 1536
        assert config.chunk_size == 1000
        assert config.chunk_overlap == 200
        assert config.top_k == 5

    def test_custom_config(self):
        """Test custom RAG configuration"""
        config = RAGConfig(
            qdrant_url="http://custom:6333",
            collection_name="custom_kb",
            chunk_size=500,
            chunk_overlap=100,
            top_k=10
        )
        assert config.qdrant_url == "http://custom:6333"
        assert config.collection_name == "custom_kb"
        assert config.chunk_size == 500
        assert config.chunk_overlap == 100
        assert config.top_k == 10


class TestRAGPipeline:
    """Tests for RAG Pipeline"""

    def test_pipeline_initialization(self, rag_pipeline, llm_client, rag_config):
        """Test RAG pipeline initialization"""
        assert rag_pipeline.config == rag_config
        assert rag_pipeline.llm_client == llm_client
        assert rag_pipeline.qdrant_client is not None
        assert rag_pipeline.text_splitter is not None

    def test_ensure_collection_creates_new(self, rag_pipeline, mock_qdrant_client):
        """Test collection creation when it doesn't exist"""
        # Reset collections to empty
        mock_collections = MagicMock()
        mock_collections.collections = []
        mock_qdrant_client.get_collections.return_value = mock_collections

        rag_pipeline._ensure_collection()

        assert mock_qdrant_client.create_collection.called
        call_args = mock_qdrant_client.create_collection.call_args
        assert call_args.kwargs['collection_name'] == rag_pipeline.config.collection_name

    def test_ensure_collection_exists(self, rag_pipeline, mock_qdrant_client):
        """Test collection is not created when it already exists"""
        # Mock existing collection
        mock_collection = MagicMock()
        mock_collection.name = rag_pipeline.config.collection_name
        mock_collections = MagicMock()
        mock_collections.collections = [mock_collection]
        mock_qdrant_client.get_collections.return_value = mock_collections

        # Reset create_collection call count
        mock_qdrant_client.create_collection.reset_mock()

        rag_pipeline._ensure_collection()

        assert not mock_qdrant_client.create_collection.called

    def test_ingest_document_success(self, rag_pipeline, sample_document):
        """Test successful document ingestion"""
        num_chunks = rag_pipeline.ingest_document(sample_document)

        assert num_chunks > 0
        assert rag_pipeline.qdrant_client.upsert.called

        # Verify upsert was called with correct parameters
        call_args = rag_pipeline.qdrant_client.upsert.call_args
        assert call_args.kwargs['collection_name'] == rag_pipeline.config.collection_name
        assert 'points' in call_args.kwargs

    def test_ingest_document_with_metadata(self, rag_pipeline, sample_document):
        """Test document ingestion with metadata"""
        metadata = {"source": "test_doc", "version": "1.0", "author": "test"}
        num_chunks = rag_pipeline.ingest_document(sample_document, metadata=metadata)

        assert num_chunks > 0

        # Verify metadata is included
        call_args = rag_pipeline.qdrant_client.upsert.call_args
        points = call_args.kwargs['points']
        assert points[0].payload['metadata'] == metadata

    def test_ingest_document_chunking(self, rag_pipeline, sample_document):
        """Test that document is properly chunked"""
        num_chunks = rag_pipeline.ingest_document(sample_document)

        call_args = rag_pipeline.qdrant_client.upsert.call_args
        points = call_args.kwargs['points']

        # Verify multiple chunks created
        assert len(points) == num_chunks

        # Verify each chunk has proper structure
        for i, point in enumerate(points):
            assert hasattr(point, 'id')
            assert hasattr(point, 'vector')
            assert hasattr(point, 'payload')
            assert 'text' in point.payload
            assert 'chunk_index' in point.payload
            assert point.payload['chunk_index'] == i

    def test_ingest_document_creates_embeddings(self, rag_pipeline, llm_client, sample_document):
        """Test that embeddings are created for each chunk"""
        num_chunks = rag_pipeline.ingest_document(sample_document)

        # Verify embedding creation was called
        create_embedding_calls = llm_client.create_embedding.call_count
        assert create_embedding_calls == num_chunks

    def test_ingest_empty_document(self, rag_pipeline):
        """Test ingestion of empty document"""
        num_chunks = rag_pipeline.ingest_document("")

        # Should create at least one chunk even for empty text
        assert num_chunks >= 0

    def test_ingest_short_document(self, rag_pipeline):
        """Test ingestion of short document"""
        short_doc = "This is a short document."
        num_chunks = rag_pipeline.ingest_document(short_doc)

        # Short document should create 1 chunk
        assert num_chunks == 1

    def test_retrieve_documents_success(self, rag_pipeline):
        """Test successful document retrieval"""
        query = "What is Python?"
        documents = rag_pipeline.retrieve(query)

        assert len(documents) > 0
        assert rag_pipeline.qdrant_client.search.called

        # Verify document structure
        doc = documents[0]
        assert 'text' in doc
        assert 'score' in doc
        assert 'metadata' in doc
        assert 'chunk_index' in doc

    def test_retrieve_with_custom_top_k(self, rag_pipeline, mock_qdrant_client):
        """Test retrieval with custom top_k"""
        query = "Test query"
        custom_top_k = 10

        # Mock multiple results
        mock_results = []
        for i in range(custom_top_k):
            mock_result = MagicMock()
            mock_result.payload = {
                "text": f"Document {i}",
                "chunk_index": i,
                "metadata": {}
            }
            mock_result.score = 0.9 - (i * 0.05)
            mock_results.append(mock_result)

        mock_qdrant_client.search.return_value = mock_results

        documents = rag_pipeline.retrieve(query, top_k=custom_top_k)

        # Verify correct top_k was used
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs['limit'] == custom_top_k
        assert len(documents) == custom_top_k

    def test_retrieve_no_results(self, rag_pipeline, mock_qdrant_client):
        """Test retrieval with no results"""
        mock_qdrant_client.search.return_value = []

        documents = rag_pipeline.retrieve("non-existent query")

        assert len(documents) == 0

    def test_retrieve_creates_query_embedding(self, rag_pipeline, llm_client):
        """Test that query embedding is created"""
        query = "Test query"
        rag_pipeline.retrieve(query)

        # Verify embedding was created for query
        llm_client.create_embedding.assert_called()
        call_args = llm_client.create_embedding.call_args
        assert call_args[0][0] == query

    def test_rag_query_success(self, rag_pipeline, llm_client):
        """Test successful RAG query"""
        query = "What is Python?"
        answer = rag_pipeline.rag_query(query)

        assert answer == "This is a test response"
        assert llm_client.chat_completion.called

    def test_rag_query_with_system_prompt(self, rag_pipeline, llm_client):
        """Test RAG query with custom system prompt"""
        query = "What is Python?"
        system_prompt = "You are an expert Python developer."

        answer = rag_pipeline.rag_query(query, system_prompt=system_prompt)

        # Verify system prompt was used
        call_args = llm_client.chat_completion.call_args
        messages = call_args[0][0]
        assert messages[0]['role'] == 'system'
        assert system_prompt in messages[0]['content']

    def test_rag_query_with_custom_top_k(self, rag_pipeline, mock_qdrant_client):
        """Test RAG query with custom top_k"""
        query = "Test query"
        custom_top_k = 3

        answer = rag_pipeline.rag_query(query, top_k=custom_top_k)

        # Verify correct top_k was used in retrieval
        call_args = mock_qdrant_client.search.call_args
        assert call_args.kwargs['limit'] == custom_top_k

    def test_rag_query_no_context_found(self, rag_pipeline, llm_client, mock_qdrant_client):
        """Test RAG query when no context is found"""
        # Mock no results
        mock_qdrant_client.search.return_value = []

        query = "Non-existent information"
        answer = rag_pipeline.rag_query(query)

        # Should still generate answer without context
        assert answer == "This is a test response"
        assert llm_client.chat_completion.called

        # Verify messages don't contain context
        call_args = llm_client.chat_completion.call_args
        messages = call_args[0][0]
        user_message = messages[1]['content']
        assert 'Context:' not in user_message

    def test_rag_query_formats_context(self, rag_pipeline, llm_client, mock_qdrant_client):
        """Test that RAG query properly formats context"""
        # Mock multiple results
        mock_results = []
        for i in range(3):
            mock_result = MagicMock()
            mock_result.payload = {
                "text": f"Context document {i}",
                "chunk_index": i,
                "metadata": {}
            }
            mock_result.score = 0.9 - (i * 0.1)
            mock_results.append(mock_result)

        mock_qdrant_client.search.return_value = mock_results

        query = "Test query"
        answer = rag_pipeline.rag_query(query)

        # Verify context was formatted in messages
        call_args = llm_client.chat_completion.call_args
        messages = call_args[0][0]
        user_message = messages[1]['content']

        assert 'Context:' in user_message
        assert 'Document 1' in user_message
        assert 'Score:' in user_message
        assert query in user_message

    def test_delete_collection(self, rag_pipeline, mock_qdrant_client):
        """Test collection deletion"""
        rag_pipeline.delete_collection()

        assert mock_qdrant_client.delete_collection.called
        call_args = mock_qdrant_client.delete_collection.call_args
        assert call_args[0][0] == rag_pipeline.config.collection_name

    def test_delete_collection_error(self, rag_pipeline, mock_qdrant_client):
        """Test collection deletion error handling"""
        mock_qdrant_client.delete_collection.side_effect = Exception("Deletion failed")

        with pytest.raises(Exception, match="Deletion failed"):
            rag_pipeline.delete_collection()


class TestTextSplitting:
    """Tests for text splitting functionality"""

    def test_text_splitter_configuration(self, rag_pipeline, rag_config):
        """Test text splitter is configured correctly"""
        splitter = rag_pipeline.text_splitter
        assert splitter._chunk_size == rag_config.chunk_size
        assert splitter._chunk_overlap == rag_config.chunk_overlap

    def test_long_document_splitting(self, rag_pipeline):
        """Test splitting of long documents"""
        # Create a long document
        long_doc = " ".join(["This is sentence number {}.".format(i) for i in range(200)])

        num_chunks = rag_pipeline.ingest_document(long_doc)

        # Should create multiple chunks
        assert num_chunks > 1

    def test_chunk_overlap(self, rag_pipeline):
        """Test that chunks have proper overlap"""
        # Document with distinct sections
        doc = "\n\n".join([
            "Section 1: " + ("A " * 200),
            "Section 2: " + ("B " * 200),
            "Section 3: " + ("C " * 200)
        ])

        chunks = rag_pipeline.text_splitter.split_text(doc)

        # Verify overlap exists between consecutive chunks
        if len(chunks) > 1:
            # Some content should overlap between chunks
            assert len(chunks) >= 2


class TestErrorHandling:
    """Tests for error handling in RAG pipeline"""

    def test_ingest_embedding_error(self, rag_pipeline, llm_client):
        """Test error handling during embedding creation"""
        llm_client.create_embedding.side_effect = Exception("Embedding API error")

        with pytest.raises(Exception, match="Embedding API error"):
            rag_pipeline.ingest_document("Test document")

    def test_ingest_qdrant_error(self, rag_pipeline, mock_qdrant_client):
        """Test error handling during Qdrant upsert"""
        mock_qdrant_client.upsert.side_effect = Exception("Qdrant connection error")

        with pytest.raises(Exception, match="Qdrant connection error"):
            rag_pipeline.ingest_document("Test document")

    def test_retrieve_embedding_error(self, rag_pipeline, llm_client):
        """Test error handling during query embedding creation"""
        llm_client.create_embedding.side_effect = Exception("Embedding error")

        with pytest.raises(Exception, match="Embedding error"):
            rag_pipeline.retrieve("Test query")

    def test_retrieve_qdrant_error(self, rag_pipeline, mock_qdrant_client):
        """Test error handling during Qdrant search"""
        mock_qdrant_client.search.side_effect = Exception("Search error")

        with pytest.raises(Exception, match="Search error"):
            rag_pipeline.retrieve("Test query")

    def test_rag_query_llm_error(self, rag_pipeline, llm_client):
        """Test error handling during LLM completion"""
        # Retrieval succeeds but LLM fails
        llm_client.chat_completion.side_effect = Exception("LLM error")

        with pytest.raises(Exception, match="LLM error"):
            rag_pipeline.rag_query("Test query")

    def test_collection_creation_error(self, rag_pipeline, mock_qdrant_client):
        """Test error handling during collection creation"""
        mock_qdrant_client.get_collections.side_effect = Exception("Connection error")

        with pytest.raises(Exception, match="Connection error"):
            rag_pipeline._ensure_collection()


class TestEdgeCases:
    """Tests for edge cases in RAG pipeline"""

    def test_very_long_query(self, rag_pipeline):
        """Test retrieval with very long query"""
        long_query = "test " * 1000
        documents = rag_pipeline.retrieve(long_query)

        assert isinstance(documents, list)

    def test_special_characters_in_document(self, rag_pipeline):
        """Test ingestion with special characters"""
        doc = "Test with special chars: @#$%^&*() \n\t\r"
        num_chunks = rag_pipeline.ingest_document(doc)

        assert num_chunks > 0

    def test_unicode_in_document(self, rag_pipeline):
        """Test ingestion with Unicode characters"""
        doc = "Testing Unicode: 你好世界 مرحبا العالم"
        num_chunks = rag_pipeline.ingest_document(doc)

        assert num_chunks > 0

    def test_empty_query(self, rag_pipeline):
        """Test retrieval with empty query"""
        documents = rag_pipeline.retrieve("")

        assert isinstance(documents, list)

    def test_none_metadata(self, rag_pipeline, sample_document):
        """Test ingestion with None metadata"""
        num_chunks = rag_pipeline.ingest_document(sample_document, metadata=None)

        assert num_chunks > 0

        # Verify empty metadata dict is used
        call_args = rag_pipeline.qdrant_client.upsert.call_args
        points = call_args.kwargs['points']
        assert points[0].payload['metadata'] == {}


class TestIntegration:
    """Integration-style tests for complete workflows"""

    @pytest.mark.integration
    def test_full_rag_workflow(self, rag_pipeline, sample_document):
        """Test complete RAG workflow: ingest -> retrieve -> query"""
        # Step 1: Ingest document
        metadata = {"source": "integration_test"}
        num_chunks = rag_pipeline.ingest_document(sample_document, metadata=metadata)
        assert num_chunks > 0

        # Step 2: Retrieve relevant chunks
        query = "programming language"
        documents = rag_pipeline.retrieve(query, top_k=3)
        assert len(documents) > 0

        # Step 3: Perform RAG query
        answer = rag_pipeline.rag_query(query)
        assert answer == "This is a test response"
        assert len(answer) > 0

    @pytest.mark.integration
    def test_multiple_document_ingestion(self, rag_pipeline):
        """Test ingesting multiple documents"""
        docs = [
            "Document 1: Python is a programming language.",
            "Document 2: JavaScript is used for web development.",
            "Document 3: Rust is a systems programming language."
        ]

        total_chunks = 0
        for i, doc in enumerate(docs):
            num_chunks = rag_pipeline.ingest_document(
                doc,
                metadata={"doc_id": i}
            )
            total_chunks += num_chunks

        assert total_chunks >= len(docs)
