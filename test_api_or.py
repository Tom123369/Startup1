import asyncio
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv('OPENROUTER_API_KEY')

async def test():
    headers = {'Authorization': f'Bearer {KEY}', 'Content-Type': 'application/json'}
    payload = {'model': 'openai/gpt-4o-mini', 'messages': [{'role': 'user', 'content': 'hi'}]}
    async with aiohttp.ClientSession() as s:
        async with s.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=payload) as r:
            with open('real_err3.txt', 'w', encoding='utf-8') as f:
                f.write(str(r.status) + '\n')
                f.write(await r.text())
asyncio.run(test())
