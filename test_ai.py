import asyncio
import json
from ai_extractor import _call_openrouter, extract_predictions_async
from config import ACTIVE_AI_KEY

import logging
logging.basicConfig(level=logging.INFO)

async def test_ai():
    print("Using key:", ACTIVE_AI_KEY[:10] + "...")
    # Load 1 cache file
    data = json.load(open('cache/transcripts/-_kbKeCAELg.json', encoding='utf-8'))
    from transcript_filter import filter_transcript
    filtered = filter_transcript(data['text'])
    
    test_video = {
        'video_id': data['video_id'],
        'title': 'Test Title',
        'filtered_text': filtered,
        'text_for_ai': f"TITLE: Test Title\nCONTENT: {filtered[:2000]}"
    }
    
    # Process it
    res = await extract_predictions_async([test_video])
    print("AI Results:")
    print(res)

if __name__ == "__main__":
    asyncio.run(test_ai())
