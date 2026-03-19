import asyncio, json, os, logging
from ai_extractor import extract_predictions_async

logging.basicConfig(level=logging.INFO)

async def test_bulk():
    # Load some real transcripts from cache
    transcripts = []
    files = os.listdir('cache/transcripts')[:10]
    for f in files:
        if not f.endswith('.json'): continue
        data = json.load(open(os.path.join('cache/transcripts', f), encoding='utf-8'))
        transcripts.append({
            'video_id': data['video_id'],
            'title': f"Real Video Test {data['video_id']}",
            'filtered_text': data['text'][:4000] # Use first 4000 chars roughly
        })
    
    # Combined titles/filtered_text into text_for_ai like pipeline does
    with_text = []
    for v in transcripts:
        v["text_for_ai"] = f"TITLE: {v['title']}\nCONTENT: {v['filtered_text']}"
        with_text.append(v)
        
    print(f"Testing with {len(with_text)} real videos...")
    
    res = await extract_predictions_async(with_text)
    print("--- EXTRACTED RESULTS ---")
    print(json.dumps(res, indent=2))
    print(f"Successfully extracted: {len(res)} predictions")

if __name__ == "__main__":
    asyncio.run(test_bulk())
