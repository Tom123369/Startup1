"""
Full end-to-end debug script.
Tests every stage independently.
"""
import asyncio
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def main():
    print("=" * 60)
    print("STAGE 1: Testing Video Collection")
    print("=" * 60)
    
    from video_collector import collect_videos
    videos = collect_videos("https://www.youtube.com/@CryptoWorldJosh", limit=10)
    print(f"  -> Collected {len(videos)} videos")
    if not videos:
        print("  FATAL: No videos collected! Stopping.")
        return
    for v in videos[:3]:
        print(f"     {v['video_id']} | {v['title'][:50]} | {v['publish_date']}")
    
    print()
    print("=" * 60)
    print("STAGE 2: Testing Transcript Extraction (3 videos)")
    print("=" * 60)
    
    from transcript_extractor import fetch_transcript_with_retry
    transcripts = {}
    for v in videos[:3]:
        vid = v["video_id"]
        text = fetch_transcript_with_retry(vid)
        length = len(text) if text else 0
        transcripts[vid] = text
        print(f"  {vid}: {length} chars")
        if text:
            print(f"    Preview: {text[:100]}...")
        else:
            print(f"    EMPTY - No transcript found!")
    
    print()
    print("=" * 60)
    print("STAGE 3: Testing Transcript Filter")
    print("=" * 60)
    
    from transcript_filter import filter_transcript
    filtered = {}
    for vid, text in transcripts.items():
        if text:
            filt = filter_transcript(text)
            filtered[vid] = filt
            print(f"  {vid}: {len(filt)} chars after filtering")
        else:
            filtered[vid] = ""
            print(f"  {vid}: SKIP (no transcript)")
    
    print()
    print("=" * 60)
    print("STAGE 4: Testing AI Extraction (Direct API call)")
    print("=" * 60)
    
    # First test a raw API call to each provider
    import aiohttp
    from config import GROQ_API_KEY, OPENROUTER_API_KEY, CEREBRAS_API_KEY, BYTEZ_API_KEY
    
    test_configs = [
        {"name": "Bytez/GPT-4o", "url": "https://api.bytez.com/models/v2/openai/v1/chat/completions", "key": BYTEZ_API_KEY, "model": "openai/gpt-4o"},
        {"name": "Cerebras/llama3.1-8b", "url": "https://api.cerebras.ai/v1/chat/completions", "key": CEREBRAS_API_KEY, "model": "llama3.1-8b"},
        {"name": "Groq/llama-3.1-8b-instant", "url": "https://api.groq.com/openai/v1/chat/completions", "key": GROQ_API_KEY, "model": "llama-3.1-8b-instant"},
        {"name": "OpenRouter/gemini-flash", "url": "https://openrouter.ai/api/v1/chat/completions", "key": OPENROUTER_API_KEY, "model": "google/gemini-2.0-flash-lite:free"},
        {"name": "OpenRouter/llama-3.3", "url": "https://openrouter.ai/api/v1/chat/completions", "key": OPENROUTER_API_KEY, "model": "meta-llama/llama-3.3-70b-instruct:free"},
    ]
    
    working_provider = None
    async with aiohttp.ClientSession() as session:
        for cfg in test_configs:
            if not cfg["key"]:
                print(f"  {cfg['name']}: SKIP (no API key)")
                continue
            try:
                headers = {
                    "Authorization": f"Bearer {cfg['key']}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://btc-prediction-analyzer.local",
                    "X-Title": "BTC Prediction Analyzer",
                }
                payload = {
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "Say 'HELLO' and nothing else."},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50,
                }
                async with session.post(cfg["url"], json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    status = resp.status
                    body = await resp.text()
                    if status == 200:
                        data = json.loads(body)
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        print(f"  {cfg['name']}: OK (HTTP {status}) -> '{content.strip()}'")
                        if not working_provider:
                            working_provider = cfg
                    else:
                        print(f"  {cfg['name']}: FAILED (HTTP {status}) -> {body[:200]}")
            except Exception as e:
                print(f"  {cfg['name']}: ERROR -> {e}")
    
    if not working_provider:
        print("\n  FATAL: ALL AI PROVIDERS FAILED! Cannot extract predictions.")
        print("  Check your API keys in .env file!")
        return
    
    print(f"\n  Best working provider: {working_provider['name']}")
    
    print()
    print("=" * 60)
    print("STAGE 5: Testing AI Prediction Extraction (real video)")
    print("=" * 60)
    
    # Pick first video with content
    test_video = None
    for v in videos[:3]:
        vid = v["video_id"]
        content = filtered.get(vid, "")
        if content and len(content) > 50:
            test_video = {
                "video_id": vid,
                "title": v["title"],
                "filtered_text": content,
                "text_for_ai": f"TITLE: {v['title']}\nCONTENT: {content}",
            }
            break
    
    if not test_video:
        print("  WARNING: No video had usable transcript content!")
        print("  Trying with just titles...")
        test_video = {
            "video_id": videos[0]["video_id"],
            "title": videos[0]["title"],
            "filtered_text": videos[0]["title"],
            "text_for_ai": f"TITLE: {videos[0]['title']}\nCONTENT: {videos[0]['title']}",
        }
    
    print(f"  Testing with video: {test_video['video_id']} - {test_video['title'][:50]}")
    print(f"  Content length: {len(test_video.get('text_for_ai', ''))} chars")
    
    from ai_extractor import extract_predictions_async
    predictions = await extract_predictions_async([test_video])
    print(f"  -> Got {len(predictions)} predictions")
    for p in predictions:
        print(f"     Target: ${p.get('target_price', 0)} | Direction: {p.get('direction')} | Timeframe: {p.get('timeframe')}")
        print(f"     Sentence: {p.get('sentence', '')[:80]}")
    
    print()
    print("=" * 60)
    print("STAGE 6: Testing with 5 videos through AI")
    print("=" * 60)
    
    batch = []
    for v in videos[:5]:
        vid = v["video_id"]
        content = filtered.get(vid, "") or v["title"]
        batch.append({
            "video_id": vid,
            "title": v["title"],
            "filtered_text": content,
            "text_for_ai": f"TITLE: {v['title']}\nCONTENT: {content}",
        })
    
    predictions5 = await extract_predictions_async(batch)
    print(f"  -> Got {len(predictions5)} predictions from 5 videos")
    for p in predictions5:
        tp = p.get('target_price', 0)
        print(f"     {p.get('video_id')[:8]}... | ${tp} | {p.get('direction')} | {p.get('timeframe')}")
    
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Videos collected: {len(videos)}")
    non_empty = sum(1 for t in transcripts.values() if t and len(t) > 50)
    print(f"  Transcripts with content: {non_empty}/{len(transcripts)}")
    print(f"  Working AI provider: {working_provider['name'] if working_provider else 'NONE'}")
    print(f"  Predictions from 1 video: {len(predictions)}")
    print(f"  Predictions from 5 videos: {len(predictions5)}")
    
    if len(predictions5) > 0:
        print("\n  *** PIPELINE IS WORKING! ***")
    else:
        print("\n  *** PIPELINE STILL BROKEN - SEE ERRORS ABOVE ***")

if __name__ == "__main__":
    asyncio.run(main())
