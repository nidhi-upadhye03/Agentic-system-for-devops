"""
LLM Client - Unified interface for OpenAI, Anthropic, and Gemini APIs
Supports automatic failover and retry logic with token tracking
"""
from __future__ import annotations
import os
import time
from typing import Any, AsyncGenerator
from enum import Enum
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    MEGALLM = "megallm"


class LLMConfig(BaseSettings):
    """Configuration for LLM clients"""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key_1: str = ""
    openrouter_api_key_2: str = ""
    megallm_api_key: str = ""
    preferred_provider: LLMProvider = LLMProvider.MEGALLM
    fallback_enabled: bool = True
    openai_model: str = "gpt-4"
    anthropic_model: str = "claude-3-opus-20240229"
    gemini_model: str = "gemini-2.0-flash"
    openrouter_model: str = "x-ai/grok-3-mini-beta"
    megallm_model: str = "openai-gpt-oss-20b"
    max_tokens: int = 2000
    temperature: float = 0.7
    timeout: int = 300
    cache_enabled: bool = True

    class Config:
        env_file = ".env"


class LLMResponse:
    """Standardized response from LLM providers"""
    def __init__(
        self,
        content: str,
        provider: LLMProvider,
        model: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
        cached: bool = False
    ):
        self.content = content
        self.provider = provider
        self.model = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.latency_ms = latency_ms
        self.cached = cached


class LLMClient:
    """Unified LLM client supporting OpenAI, Anthropic, and Gemini"""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self.openai_client: OpenAI | None = None
        self.anthropic_client: Anthropic | None = None
        self.gemini_client: OpenAI | None = None
        self.openrouter_client_1: OpenAI | None = None
        self.openrouter_client_2: OpenAI | None = None
        self.megallm_client: OpenAI | None = None
        self.current_openrouter_key = 1  # Track which key to use

        # Initialize OpenAI client
        if self.config.openai_api_key:
            self.openai_client = OpenAI(
                api_key=self.config.openai_api_key,
                timeout=self.config.timeout
            )
            logger.info("OpenAI client initialized")

        # Initialize Anthropic client
        if self.config.anthropic_api_key:
            self.anthropic_client = Anthropic(
                api_key=self.config.anthropic_api_key,
                timeout=self.config.timeout
            )
            logger.info("Anthropic client initialized")

        # Initialize Gemini client (via OpenAI-compatible API)
        if self.config.gemini_api_key:
            self.gemini_client = OpenAI(
                api_key=self.config.gemini_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=self.config.timeout
            )
            logger.info("Gemini client initialized")

        # Initialize OpenRouter clients (via OpenAI-compatible API) with dual keys
        if self.config.openrouter_api_key_1:
            self.openrouter_client_1 = OpenAI(
                api_key=self.config.openrouter_api_key_1,
                base_url="https://openrouter.ai/api/v1",
                timeout=self.config.timeout
            )
            logger.info("OpenRouter client #1 initialized")
        
        if self.config.openrouter_api_key_2:
            self.openrouter_client_2 = OpenAI(
                api_key=self.config.openrouter_api_key_2,
                base_url="https://openrouter.ai/api/v1",
                timeout=self.config.timeout
            )
            logger.info("OpenRouter client #2 initialized")

        # Initialize MegaLLM client (OpenAI-compatible)
        if self.config.megallm_api_key:
            self.megallm_client = OpenAI(
                api_key=self.config.megallm_api_key,
                base_url="https://ai.megallm.io/v1",
                timeout=self.config.timeout
            )
            logger.info("MegaLLM client initialized")

        # Track available providers
        self.available_providers = []
        if self.openai_client:
            self.available_providers.append(LLMProvider.OPENAI)
        if self.anthropic_client:
            self.available_providers.append(LLMProvider.ANTHROPIC)
        if self.gemini_client:
            self.available_providers.append(LLMProvider.GEMINI)
        if self.openrouter_client_1 or self.openrouter_client_2:
            self.available_providers.append(LLMProvider.OPENROUTER)
        if self.megallm_client:
            self.available_providers.append(LLMProvider.MEGALLM)

        if not self.available_providers:
            logger.warning("No LLM providers configured!")

    @retry(
        stop=stop_after_attempt(2),  # Reduced from 3 to 2 attempts
        wait=wait_exponential(multiplier=2, min=5, max=60)  # Longer backoff: 5s, 10s, 20s, 40s, 60s max
    )
    def chat_completion(
        self,
        messages: list[dict[str, str]],
        provider: LLMProvider | None = None,
        **kwargs: Any
    ) -> LLMResponse:
        """
        Get chat completion from LLM with automatic failover

        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: Which provider to use (defaults to config preference)
            **kwargs: Additional arguments to pass to the API

        Returns:
            LLMResponse object with content, token counts, and metadata
        """
        provider = provider or self.config.preferred_provider
        start_time = time.time()

        # Check if provider is available
        if provider not in self.available_providers:
            if not self.config.fallback_enabled or not self.available_providers:
                raise ValueError(f"Provider {provider} not configured and no fallback available")
            # Use first available provider as fallback
            provider = self.available_providers[0]
            logger.warning(f"Requested provider not available, using {provider}")

        try:
            if provider == LLMProvider.OPENAI:
                response = self.openai_client.chat.completions.create(
                    model=kwargs.get("model", self.config.openai_model),
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )
                latency_ms = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    provider=provider,
                    model=response.model,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    latency_ms=latency_ms,
                    cached=False
                )

            elif provider == LLMProvider.ANTHROPIC:
                # Extract system message if present (Anthropic requires separate system parameter)
                system_message = None
                anthropic_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

                response = self.anthropic_client.messages.create(
                    model=kwargs.get("model", self.config.anthropic_model),
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                    system=system_message,
                    messages=anthropic_messages
                )
                latency_ms = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    content=response.content[0].text,
                    provider=provider,
                    model=response.model,
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    latency_ms=latency_ms,
                    cached=False
                )

            elif provider == LLMProvider.GEMINI:
                response = self.gemini_client.chat.completions.create(
                    model=kwargs.get("model", self.config.gemini_model),
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )
                latency_ms = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    provider=provider,
                    model=response.model,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    latency_ms=latency_ms,
                    cached=False
                )

            elif provider == LLMProvider.OPENROUTER:
                # Try first OpenRouter key, rotate to second if it fails
                client = self.openrouter_client_1 if self.current_openrouter_key == 1 else self.openrouter_client_2
                
                try:
                    response = client.chat.completions.create(
                        model=kwargs.get("model", self.config.openrouter_model),
                        messages=messages,
                        max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                        temperature=kwargs.get("temperature", self.config.temperature),
                    )
                    latency_ms = int((time.time() - start_time) * 1000)

                    return LLMResponse(
                        content=response.choices[0].message.content or "",
                        provider=provider,
                        model=response.model,
                        prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                        completion_tokens=response.usage.completion_tokens if response.usage else 0,
                        latency_ms=latency_ms,
                        cached=False
                    )
                except Exception as key_error:
                    # Rotate to other key
                    logger.warning(f"OpenRouter key #{self.current_openrouter_key} failed, rotating to backup")
                    self.current_openrouter_key = 2 if self.current_openrouter_key == 1 else 1
                    backup_client = self.openrouter_client_2 if self.current_openrouter_key == 2 else self.openrouter_client_1
                    
                    if backup_client:
                        response = backup_client.chat.completions.create(
                            model=kwargs.get("model", self.config.openrouter_model),
                            messages=messages,
                            max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                            temperature=kwargs.get("temperature", self.config.temperature),
                        )
                        latency_ms = int((time.time() - start_time) * 1000)

                        return LLMResponse(
                            content=response.choices[0].message.content or "",
                            provider=provider,
                            model=response.model,
                            prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                            completion_tokens=response.usage.completion_tokens if response.usage else 0,
                            latency_ms=latency_ms,
                            cached=False
                        )
                    else:
                        raise key_error  # No backup available

            elif provider == LLMProvider.MEGALLM:
                response = self.megallm_client.chat.completions.create(
                    model=kwargs.get("model", self.config.megallm_model),
                    messages=messages,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )
                latency_ms = int((time.time() - start_time) * 1000)

                return LLMResponse(
                    content=response.choices[0].message.content or "",
                    provider=provider,
                    model=response.model,
                    prompt_tokens=response.usage.prompt_tokens if response.usage else 0,
                    completion_tokens=response.usage.completion_tokens if response.usage else 0,
                    latency_ms=latency_ms,
                    cached=False
                )

        except Exception as e:
            logger.error(f"Error with {provider}: {e}")

            # Try fallback if enabled
            if self.config.fallback_enabled and len(self.available_providers) > 1:
                # Try next available provider (prevent infinite recursion)
                for fallback_provider in self.available_providers:
                    if fallback_provider != provider:
                        logger.info(f"Falling back from {provider} to {fallback_provider}")
                        try:
                            # Use direct provider call instead of recursion
                            if fallback_provider == LLMProvider.OPENAI:
                                response = self.openai_client.chat.completions.create(
                                    model=kwargs.get("model", self.config.openai_model),
                                    messages=messages,
                                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                                    temperature=kwargs.get("temperature", self.config.temperature),
                                )
                                latency_ms = int((time.time() - start_time) * 1000)
                                return LLMResponse(
                                    content=response.choices[0].message.content or "",
                                    provider=fallback_provider,
                                    model=response.model,
                                    prompt_tokens=response.usage.prompt_tokens,
                                    completion_tokens=response.usage.completion_tokens,
                                    latency_ms=latency_ms,
                                    cached=False
                                )
                            elif fallback_provider == LLMProvider.ANTHROPIC:
                                system_message = None
                                anthropic_messages = []
                                for msg in messages:
                                    if msg["role"] == "system":
                                        system_message = msg["content"]
                                    else:
                                        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})
                                response = self.anthropic_client.messages.create(
                                    model=kwargs.get("model", self.config.anthropic_model),
                                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                                    temperature=kwargs.get("temperature", self.config.temperature),
                                    system=system_message,
                                    messages=anthropic_messages
                                )
                                latency_ms = int((time.time() - start_time) * 1000)
                                return LLMResponse(
                                    content=response.content[0].text,
                                    provider=fallback_provider,
                                    model=response.model,
                                    prompt_tokens=response.usage.input_tokens,
                                    completion_tokens=response.usage.output_tokens,
                                    latency_ms=latency_ms,
                                    cached=False
                                )
                        except Exception as fallback_error:
                            logger.error(f"Fallback to {fallback_provider} also failed: {fallback_error}")
                            continue

            raise

    def create_embedding(self, text: str, provider: LLMProvider | None = None) -> list[float]:
        """
        Create embeddings for RAG (currently only OpenAI supported)

        Args:
            text: Text to embed
            provider: Which provider to use (defaults to OpenAI for embeddings)

        Returns:
            Embedding vector (1536 dimensions for OpenAI)
        """
        # For embeddings, we primarily use OpenAI
        # Anthropic doesn't provide embeddings, Gemini support can be added later
        if not self.openai_client:
            raise ValueError("OpenAI client not configured. Embeddings require OpenAI API key.")

        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=text
            )
            logger.info(f"Successfully created embedding, dimension: {len(response.data[0].embedding)}")
            return response.data[0].embedding

        except Exception as e:
            logger.error(f"Error creating embedding: {e}")
            raise

    async def stream_completion(
        self,
        messages: list[dict[str, str]],
        provider: LLMProvider | None = None,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat completions for real-time responses

        Args:
            messages: List of message dicts with 'role' and 'content'
            provider: Which provider to use (defaults to config preference)
            **kwargs: Additional arguments to pass to the API

        Yields:
            Content chunks as they arrive from the LLM
        """
        provider = provider or self.config.preferred_provider

        # Check if provider is available
        if provider not in self.available_providers:
            if not self.config.fallback_enabled or not self.available_providers:
                raise ValueError(f"Provider {provider} not configured and no fallback available")
            provider = self.available_providers[0]
            logger.warning(f"Requested provider not available, using {provider}")

        try:
            if provider == LLMProvider.OPENAI:
                async_client = AsyncOpenAI(
                    api_key=self.config.openai_api_key,
                    timeout=self.config.timeout
                )
                stream = await async_client.chat.completions.create(
                    model=kwargs.get("model", self.config.openai_model),
                    messages=messages,
                    stream=True,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            elif provider == LLMProvider.ANTHROPIC:
                # Extract system message for Anthropic
                system_message = None
                anthropic_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

                async_client = AsyncAnthropic(
                    api_key=self.config.anthropic_api_key,
                    timeout=self.config.timeout
                )

                async with async_client.messages.stream(
                    model=kwargs.get("model", self.config.anthropic_model),
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                    system=system_message,
                    messages=anthropic_messages
                ) as stream:
                    async for text in stream.text_stream:
                        yield text

            elif provider == LLMProvider.GEMINI:
                async_client = AsyncOpenAI(
                    api_key=self.config.gemini_api_key,
                    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                    timeout=self.config.timeout
                )
                stream = await async_client.chat.completions.create(
                    model=kwargs.get("model", self.config.gemini_model),
                    messages=messages,
                    stream=True,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

            elif provider == LLMProvider.MEGALLM:
                async_client = AsyncOpenAI(
                    api_key=self.config.megallm_api_key,
                    base_url="https://api.megallm.com/v1",
                    timeout=self.config.timeout
                )
                stream = await async_client.chat.completions.create(
                    model=kwargs.get("model", self.config.megallm_model),
                    messages=messages,
                    stream=True,
                    max_tokens=kwargs.get("max_tokens", self.config.max_tokens),
                    temperature=kwargs.get("temperature", self.config.temperature),
                )

                async for chunk in stream:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"Error streaming from {provider}: {e}")
            raise


# Example usage
if __name__ == "__main__":
    import asyncio

    # Initialize client
    client = LLMClient()

    # Simple completion
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "What is Kubernetes?"}
    ]

    response = client.chat_completion(messages)
    print(f"Response: {response.content}")
    print(f"Provider: {response.provider}, Model: {response.model}")
    print(f"Tokens: {response.total_tokens} (prompt: {response.prompt_tokens}, completion: {response.completion_tokens})")
    print(f"Latency: {response.latency_ms}ms")

    # Create embedding
    embedding = client.create_embedding("Hello, world!")
    print(f"Embedding dimension: {len(embedding)}")

    # Streaming (async)
    async def test_stream():
        print("\nStreaming response:")
        async for chunk in client.stream_completion(messages):
            print(chunk, end="", flush=True)
        print()

    asyncio.run(test_stream())
