import asyncio
import aiohttp
import json
from config import OPENROUTER_API_KEY

OR_URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-pro-exp-02-05:free",
    "google/gemini-2.0-flash-lite-preview-02-05:free",
    "deepseek/deepseek-chat:free",
    "mistralai/mistral-nemo:free",
    "liquid/lfm-7b-color:free"
]

async def test():
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        for model in MODELS:
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": "hi"}]
            }
            async with session.post(OR_URL, json=payload, headers=headers) as resp:
                print(f"Model: {model} -> Status: {resp.status}")
                if resp.status == 200:
                    data = await resp.json()
                    print("  SUCCESS!")
                    return  # Stop if we find a working one
                else:
                    text = await resp.text()
                    print("  FAILED:", text[:100])

asyncio.run(test())
