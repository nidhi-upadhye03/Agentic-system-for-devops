"""
Quick test script for LLM Service
Tests OpenAI and Anthropic clients with the configured API keys
"""
import sys
import os

# Add app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set environment variables from .env in devops/
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / '.env'

if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

from llm_client import LLMClient, LLMProvider

def test_openai():
    """Test OpenAI chat completion"""
    print("\n" + "=" * 60)
    print("TESTING OPENAI")
    print("=" * 60)

    try:
        client = LLMClient()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from OpenAI!' and nothing else."}
        ]

        response = client.chat_completion(messages, provider=LLMProvider.OPENAI)

        print(f"Response: {response.content}")
        print(f"Provider: {response.provider}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.total_tokens} (prompt: {response.prompt_tokens}, completion: {response.completion_tokens})")
        print(f"Latency: {response.latency_ms}ms")
        print("\n✅ OpenAI test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ OpenAI test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_anthropic():
    """Test Anthropic chat completion"""
    print("\n" + "=" * 60)
    print("TESTING ANTHROPIC")
    print("=" * 60)

    try:
        client = LLMClient()

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello from Anthropic!' and nothing else."}
        ]

        response = client.chat_completion(messages, provider=LLMProvider.ANTHROPIC)

        print(f"Response: {response.content}")
        print(f"Provider: {response.provider}")
        print(f"Model: {response.model}")
        print(f"Tokens: {response.total_tokens} (prompt: {response.prompt_tokens}, completion: {response.completion_tokens})")
        print(f"Latency: {response.latency_ms}ms")
        print("\n✅ Anthropic test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ Anthropic test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_embedding():
    """Test embedding creation"""
    print("\n" + "=" * 60)
    print("TESTING EMBEDDINGS")
    print("=" * 60)

    try:
        client = LLMClient()

        text = "This is a test for embedding generation"
        embedding = client.create_embedding(text)

        print(f"Text: {text}")
        print(f"Embedding dimension: {len(embedding)}")
        print(f"First 5 values: {embedding[:5]}")
        print("\n✅ Embedding test PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ Embedding test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LLM SERVICE TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("OpenAI", test_openai()))
    results.append(("Anthropic", test_anthropic()))
    results.append(("Embeddings", test_embedding()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)
