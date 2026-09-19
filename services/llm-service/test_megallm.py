from openai import OpenAI
import os

# Use the key directly as requested by the user for testing
api_key = "sk-mega-b94d3ed547bcfbd47679d8596aa112a4091c7a479f168872f21a54f42444a77c"

print(f"Testing MegaLLM with key: {api_key[:10]}...")

try:
    client = OpenAI(
        base_url="https://ai.megallm.io/v1",
        api_key=api_key
    )

    response = client.chat.completions.create(
        model="openai-gpt-oss-20b",
        messages=[
            {"role": "user", "content": "Hello, test if you are alive"}
        ]
    )

    print("\nResponse received:")
    print("-" * 50)
    print(response.choices[0].message.content)
    print("-" * 50)
    print("\n✅ MegaLLM connection successful!")

except Exception as e:
    print(f"\n❌ MegaLLM connection failed: {e}")
