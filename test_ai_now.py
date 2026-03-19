import asyncio
import aiohttp
from ai_extractor import _call_ai, _parse_ai_response, _build_solo_prompt
from config import ACTIVE_AI_BASE_URL, ACTIVE_AI_KEY, ACTIVE_AI_MODEL
import logging

logging.basicConfig(level=logging.DEBUG)


async def test():
    video = {
        "video_id": "test_id_123",
        "title": "BITCOIN WARNING: Price Squeeze",
        "text_for_ai": "Bitcoin is looking very bullish right now. We are going to see a huge squeeze up to the 85,000 level very soon. I am super excited!"
    }
    
    prompt = _build_solo_prompt(video)
    system = "Extract the Bitcoin price target from this transcript. You MUST return a JSON array with exactly one object."
    
    async with aiohttp.ClientSession() as session:
        headers = {
            "Authorization": f"Bearer {ACTIVE_AI_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://btc-prediction-analyzer.local",
            "X-Title": "BTC Prediction Analyzer",
        }
        payload = {
            "model": ACTIVE_AI_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }
        try:
            async with session.post(ACTIVE_AI_BASE_URL, json=payload, headers=headers) as resp:
                text = await resp.text()
                with open("api_test.txt", "w", encoding="utf-8") as f:
                    f.write(f"Status: {resp.status}\n")
                    f.write(text)
        except Exception as e:
            pass


if __name__ == "__main__":
    asyncio.run(test())


