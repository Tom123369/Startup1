import asyncio
import aiohttp
import logging
from config import GROQ_API_KEY

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

async def test():
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": "hi"}],
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(GROQ_URL, json=payload, headers=headers) as resp:
            print("Status:", resp.status)
            txt = await resp.text()
            print("Response:", txt)

asyncio.run(test())
