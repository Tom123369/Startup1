import asyncio
import aiohttp
import json
import os
import sys

# Load .env manually to be sure
env = {}
if os.path.exists('.env'):
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                env[k] = v

OR_KEY = env.get('OPENROUTER_API_KEY', '').strip()
OR_URL = "https://openrouter.ai/api/v1/chat/completions"

# Comprehensive list of free models to find ONE that works
FREE_MODELS = [
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "deepseek/deepseek-chat:free",
    "mistralai/mistral-small-24b-instruct-2501:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "google/gemini-2.0-pro-exp-02-05:free",
    "nvidia/llama-3.1-nemotron-70b-instruct:free",
    "microsoft/phi-3-medium-128k-instruct:free",
    "openrouter/free"
]

async def test_model(session, model):
    headers = {
        "Authorization": f"Bearer {OR_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "Tester"
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Return the JSON: [{\"test\": true}]"}],
        "max_tokens": 100
    }
    try:
        async with session.post(OR_URL, json=payload, headers=headers, timeout=10) as resp:
            status = resp.status
            body = await resp.text()
            if status == 200:
                print(f"[SUCCESS] {model}")
                return model
            else:
                print(f"[FAIL   ] {model} -> Status {status}: {body[:100]}")
                return None
    except Exception as e:
        print(f"[ERROR  ] {model} -> {str(e)}")
        return None

async def main():
    if not OR_KEY:
        print("No OpenRouter Key found in .env")
        return
        
    async with aiohttp.ClientSession() as session:
        tasks = [test_model(session, m) for m in FREE_MODELS]
        results = await asyncio.gather(*tasks)
        working = [r for r in results if r]
        
        print("\nSUMMARY OF WORKING FREE MODELS:")
        if not working:
            print("NONE. All free models returned errors (likely 429 or 402).")
        else:
            for w in working:
                print(f"  - {w}")

if __name__ == "__main__":
    asyncio.run(main())
