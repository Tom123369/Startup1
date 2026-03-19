import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()
GROQ_KEY = os.getenv('GROQ_API_KEY')

async def test():
    headers = {'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'}
    payload = {'model': 'llama-3.1-8b-instant', 'messages': [{'role': 'user', 'content': 'hi'}]}
    async with aiohttp.ClientSession() as s:
        async with s.post('https://api.groq.com/openai/v1/chat/completions', headers=headers, json=payload) as r:
            with open('real_err.txt', 'w', encoding='utf-8') as f:
                f.write(str(r.status) + '\n')
                f.write(await r.text())
asyncio.run(test())
