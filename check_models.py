#!/usr/bin/env python3
import requests

API_KEY = "your-openrouter-api-key-here" # Replace with real key for local testing

#List models
print("Fetching OpenRouter models...")
r = requests.get("https://openrouter.ai/api/v1/models", 
                headers={"Authorization": f"Bearer {API_KEY}"}, timeout=10)
print(f"Status: {r.status_code}")

if r.status_code == 200:
    models = r.json()
    print("\n🔍 FREE models containing 'grok':")
    for m in models.get('data', []):
        if 'grok' in m['id'].lower() and m.get('pricing', {}).get('prompt') == '0':
            print(f"  - {m['id']}")
    
    print("\n🔍 ALL Grok models:")
    for m in models.get('data', []):
        if 'grok' in m['id'].lower():
            prompt_price = m.get('pricing', {}).get('prompt', 'N/A')
            print(f"  - {m['id']} (${prompt_price}/1M tokens)")
else:
    print(f"Error: {r.text[:300]}")
