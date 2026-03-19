import asyncio
import json
import os
import aiohttp
from dotenv import load_dotenv

load_dotenv()
GROQ_KEY = os.getenv('GROQ_API_KEY')

async def test_groq():
    url = 'https://api.groq.com/openai/v1/chat/completions'
    headers = {
        'Authorization': f'Bearer {GROQ_KEY}',
        'Content-Type': 'application/json'
    }
    
    system_prompt = "You are a price extractor. For each video, return a JSON object: {'video_id': '...', 'asset': '...', 'direction': 'UP'/'DOWN', 'target_price': <NUMBER>, 'timeframe': '...', 'sentence': '...'}. Return ONLY an array of these objects."
    user_prompt = "--- VIDEO ID: 123 ---\nTITLE: Bitcoin Next Target\nTRANSCRIPT: I think Bitcoin will go up to 75000 next month!\n\n--- VIDEO ID: 456 ---\nTITLE: Ethereum falling?\nTRANSCRIPT: Ethereum is looking weak. Next stop 2000 in short-term."
    
    payload = {
        'model': 'llama-3.1-8b-instant',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        'temperature': 0.1,
        'max_tokens': 2000
    }
    
    print('Sending prompt to Groq...')
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            print('Status:', resp.status)
            if resp.status == 200:
                data = await resp.json()
                print('Response:', data['choices'][0]['message']['content'])
            else:
                print('Error:', await resp.text())

asyncio.run(test_groq())
