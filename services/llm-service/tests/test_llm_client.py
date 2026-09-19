"""
Comprehensive unit tests for LLM Client
Tests OpenAI and Gemini integration with mocking
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from llm_client import LLMClient, LLMConfig, LLMProvider
from openai import OpenAI, AsyncOpenAI


class TestLLMConfig:
    """Tests for LLM configuration"""

    def test_default_config(self):
        """Test default configuration values"""
        config = LLMConfig()
        assert config.preferred_provider == LLMProvider.OPENAI
        assert config.openai_model == "gpt-4o"
        assert config.gemini_model == "gemini-2.0-flash-exp"
        assert config.max_tokens == 2000
        assert config.temperature == 0.7

    def test_custom_config(self):
        """Test custom configuration"""
        config = LLMConfig(
            openai_api_key="custom-key",
            preferred_provider=LLMProvider.GEMINI,
            max_tokens=4000,
            temperature=0.5
        )
        assert config.openai_api_key == "custom-key"
        assert config.preferred_provider == LLMProvider.GEMINI
        assert config.max_tokens == 4000
        assert config.temperature == 0.5


class TestLLMClient:
    """Tests for LLM Client"""

    def test_client_initialization_with_openai(self, llm_config, monkeypatch):
        """Test client initialization with OpenAI"""
        mock_openai = MagicMock()
        monkeypatch.setattr("llm_client.OpenAI", mock_openai)

        client = LLMClient(llm_config)

        assert LLMProvider.OPENAI in client.clients
        assert client.config == llm_config

    def test_client_initialization_without_api_keys(self, monkeypatch):
        """Test client initialization without API keys"""
        config = LLMConfig(openai_api_key="", gemini_api_key="")
        monkeypatch.setattr("llm_client.OpenAI", MagicMock())

        client = LLMClient(config)

        assert len(client.clients) == 0

    def test_chat_completion_success(self, llm_client, sample_messages):
        """Test successful chat completion"""
        response = llm_client.chat_completion(sample_messages)

        assert response == "This is a test response"
        assert llm_client.clients[LLMProvider.OPENAI].chat.completions.create.called

    def test_chat_completion_with_custom_params(self, llm_client, sample_messages):
        """Test chat completion with custom parameters"""
        response = llm_client.chat_completion(
            sample_messages,
            max_tokens=1000,
            temperature=0.9
        )

        call_args = llm_client.clients[LLMProvider.OPENAI].chat.completions.create.call_args
        assert call_args.kwargs['max_tokens'] == 1000
        assert call_args.kwargs['temperature'] == 0.9

    def test_chat_completion_with_specific_provider(self, llm_client, sample_messages):
        """Test chat completion with specific provider"""
        response = llm_client.chat_completion(
            sample_messages,
            provider=LLMProvider.OPENAI
        )

        assert response == "This is a test response"

    def test_chat_completion_provider_not_configured(self, llm_config):
        """Test chat completion with unconfigured provider"""
        config = LLMConfig(openai_api_key="", gemini_api_key="")
        client = LLMClient(config)

        with pytest.raises(ValueError, match="Provider .* not configured"):
            client.chat_completion(
                [{"role": "user", "content": "test"}],
                provider=LLMProvider.OPENAI
            )

    def test_chat_completion_with_fallback(self, llm_config, monkeypatch):
        """Test automatic fallback to Gemini when OpenAI fails"""
        # Create mocks for both providers
        mock_openai = MagicMock()
        mock_gemini = MagicMock()

        # OpenAI fails
        mock_openai.chat.completions.create.side_effect = Exception("OpenAI error")

        # Gemini succeeds
        mock_gemini_response = MagicMock()
        mock_gemini_response.choices = [MagicMock()]
        mock_gemini_response.choices[0].message.content = "Gemini response"
        mock_gemini.chat.completions.create.return_value = mock_gemini_response

        # Mock OpenAI constructor
        def mock_openai_init(api_key, base_url=None):
            if base_url and "generativelanguage" in base_url:
                return mock_gemini
            return mock_openai

        monkeypatch.setattr("llm_client.OpenAI", mock_openai_init)

        client = LLMClient(llm_config)
        response = client.chat_completion([{"role": "user", "content": "test"}])

        assert response == "Gemini response"
        assert mock_gemini.chat.completions.create.called

    def test_chat_completion_empty_response(self, llm_client, sample_messages):
        """Test chat completion with empty response"""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        llm_client.clients[LLMProvider.OPENAI].chat.completions.create.return_value = mock_response

        response = llm_client.chat_completion(sample_messages)

        assert response == ""

    def test_create_embedding_success(self, llm_client):
        """Test successful embedding creation"""
        embedding = llm_client.create_embedding("Test text")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)
        assert llm_client.clients[LLMProvider.OPENAI].embeddings.create.called

    def test_create_embedding_with_openai(self, llm_client):
        """Test embedding creation specifically with OpenAI"""
        embedding = llm_client.create_embedding("Test text", provider=LLMProvider.OPENAI)

        call_args = llm_client.clients[LLMProvider.OPENAI].embeddings.create.call_args
        assert call_args.kwargs['model'] == "text-embedding-ada-002"
        assert call_args.kwargs['input'] == "Test text"

    def test_create_embedding_gemini_fallback(self, llm_config, monkeypatch):
        """Test Gemini embedding falls back to OpenAI"""
        mock_openai = MagicMock()
        mock_gemini = MagicMock()

        # Setup OpenAI embeddings
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1] * 1536
        mock_openai.embeddings.create.return_value = mock_embedding_response

        def mock_openai_init(api_key, base_url=None):
            if base_url and "generativelanguage" in base_url:
                return mock_gemini
            return mock_openai

        monkeypatch.setattr("llm_client.OpenAI", mock_openai_init)

        client = LLMClient(llm_config)
        embedding = client.create_embedding("Test", provider=LLMProvider.GEMINI)

        # Should fall back to OpenAI
        assert len(embedding) == 1536
        assert mock_openai.embeddings.create.called

    def test_create_embedding_error(self, llm_client):
        """Test embedding creation error handling"""
        llm_client.clients[LLMProvider.OPENAI].embeddings.create.side_effect = Exception("API error")

        with pytest.raises(Exception, match="API error"):
            llm_client.create_embedding("Test text")

    @pytest.mark.asyncio
    async def test_stream_completion_success(self, llm_config, monkeypatch):
        """Test successful streaming completion"""
        mock_async_client = MagicMock()

        # Create async generator for streaming
        async def mock_stream():
            chunks = ["Hello", " ", "world", "!"]
            for chunk_text in chunks:
                chunk = MagicMock()
                chunk.choices = [MagicMock()]
                chunk.choices[0].delta.content = chunk_text
                yield chunk

        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_stream())
        monkeypatch.setattr("llm_client.AsyncOpenAI", lambda api_key, base_url: mock_async_client)

        # Also mock sync OpenAI for initialization
        mock_sync_client = MagicMock()
        monkeypatch.setattr("llm_client.OpenAI", lambda api_key, base_url=None: mock_sync_client)

        client = LLMClient(llm_config)

        messages = [{"role": "user", "content": "Hello"}]
        result = []

        async for chunk in client.stream_completion(messages):
            result.append(chunk)

        assert "".join(result) == "Hello world!"

    @pytest.mark.asyncio
    async def test_stream_completion_with_gemini(self, llm_config, monkeypatch):
        """Test streaming with Gemini provider"""
        mock_async_client = MagicMock()

        async def mock_stream():
            chunk = MagicMock()
            chunk.choices = [MagicMock()]
            chunk.choices[0].delta.content = "Gemini response"
            yield chunk

        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        created_base_url = None

        def capture_async_openai(api_key, base_url):
            nonlocal created_base_url
            created_base_url = base_url
            return mock_async_client

        monkeypatch.setattr("llm_client.AsyncOpenAI", capture_async_openai)

        # Mock sync OpenAI
        mock_sync_client = MagicMock()
        monkeypatch.setattr("llm_client.OpenAI", lambda api_key, base_url=None: mock_sync_client)

        client = LLMClient(llm_config)

        messages = [{"role": "user", "content": "Hello"}]
        result = []

        async for chunk in client.stream_completion(messages, provider=LLMProvider.GEMINI):
            result.append(chunk)

        assert created_base_url == "https://generativelanguage.googleapis.com/v1beta/openai/"

    @pytest.mark.asyncio
    async def test_stream_completion_provider_not_configured(self, llm_config):
        """Test streaming with unconfigured provider"""
        config = LLMConfig(openai_api_key="", gemini_api_key="")
        client = LLMClient(config)

        with pytest.raises(ValueError, match="Provider .* not configured"):
            async for chunk in client.stream_completion(
                [{"role": "user", "content": "test"}],
                provider=LLMProvider.OPENAI
            ):
                pass


class TestLLMProviderEnum:
    """Tests for LLM Provider enum"""

    def test_provider_values(self):
        """Test provider enum values"""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.GEMINI.value == "gemini"

    def test_provider_string_comparison(self):
        """Test provider string comparison"""
        assert LLMProvider.OPENAI == "openai"
        assert LLMProvider.GEMINI == "gemini"


class TestRetryLogic:
    """Tests for retry logic in LLM client"""

    def test_chat_completion_retry_on_failure(self, llm_client, sample_messages):
        """Test retry logic on temporary failures"""
        mock_client = llm_client.clients[LLMProvider.OPENAI]

        # Fail first two times, succeed third time
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Success after retry"

        mock_client.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            Exception("Temporary error"),
            mock_response
        ]

        response = llm_client.chat_completion(sample_messages)

        assert response == "Success after retry"
        assert mock_client.chat.completions.create.call_count == 3

    def test_chat_completion_max_retries_exceeded(self, llm_client, sample_messages):
        """Test that retries stop after max attempts"""
        mock_client = llm_client.clients[LLMProvider.OPENAI]
        mock_client.chat.completions.create.side_effect = Exception("Persistent error")

        # Remove Gemini to avoid fallback
        if LLMProvider.GEMINI in llm_client.clients:
            del llm_client.clients[LLMProvider.GEMINI]

        with pytest.raises(Exception, match="Persistent error"):
            llm_client.chat_completion(sample_messages)


class TestEdgeCases:
    """Tests for edge cases and error conditions"""

    def test_empty_messages_list(self, llm_client):
        """Test chat completion with empty messages"""
        response = llm_client.chat_completion([])

        # Should still call the API
        assert llm_client.clients[LLMProvider.OPENAI].chat.completions.create.called

    def test_very_long_message(self, llm_client):
        """Test chat completion with very long message"""
        long_content = "a" * 10000
        messages = [{"role": "user", "content": long_content}]

        response = llm_client.chat_completion(messages)

        assert response == "This is a test response"

    def test_special_characters_in_message(self, llm_client):
        """Test chat completion with special characters"""
        messages = [{"role": "user", "content": "Test with \n\t special chars: @#$%^&*()"}]

        response = llm_client.chat_completion(messages)

        assert response == "This is a test response"

    def test_embedding_empty_text(self, llm_client):
        """Test embedding creation with empty text"""
        embedding = llm_client.create_embedding("")

        assert len(embedding) == 1536
