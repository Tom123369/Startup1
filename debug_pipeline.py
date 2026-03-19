"""
Simulate the EXACT pipeline flow for 10 videos, step by step.
"""
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def main():
    from video_collector import collect_videos
    from transcript_extractor import fetch_transcript_with_retry
    from transcript_filter import filter_transcript
    from ai_extractor import extract_predictions_async
    from market_data import get_batch_price_ranges_async
    from evaluator import evaluate_all_predictions
    
    # Stage 1: Collect
    loop = asyncio.get_event_loop()
    videos = await loop.run_in_executor(None, lambda: collect_videos("https://www.youtube.com/@CryptoWorldJosh", limit=10))
    print(f"\n=== COLLECTED {len(videos)} VIDEOS ===")
    
    # Stage 2+3: Transcripts + Filter (exactly like pipeline.py)
    videos_with_content = []
    for v in videos:
        vid = v["video_id"]
        content = fetch_transcript_with_retry(vid)
        filtered = filter_transcript(content) if content else ""
        result = {**v, "transcript": content or "", "filtered_text": filtered}
        
        # Build text_for_ai (exactly like pipeline.py line 108-109)
        text_content = result.get('filtered_text', '') or result.get('description', '')
        result["text_for_ai"] = f"TITLE: {result.get('title', '')}\nCONTENT: {text_content}"
        
        videos_with_content.append(result)
        print(f"  {vid}: transcript={len(content) if content else 0} chars, filtered={len(filtered)} chars, text_for_ai={len(result['text_for_ai'])} chars")
    
    # Stage 4: AI Extraction
    print(f"\n=== AI EXTRACTION ({len(videos_with_content)} videos) ===")
    predictions = await extract_predictions_async(videos_with_content)
    print(f"  -> Raw predictions: {len(predictions)}")
    for p in predictions:
        print(f"     {p['video_id'][:11]} | ${p.get('target_price',0)} | {p.get('direction')} | {p.get('timeframe')}")
    
    # Stage 5: Market Data
    print(f"\n=== MARKET DATA ===")
    market_map = await get_batch_price_ranges_async(videos)
    print(f"  -> Got market data for {len(market_map)} videos")
    
    # Link metadata
    title_map = {v["video_id"]: v.get("title", "") for v in videos}
    date_map = {v["video_id"]: v.get("publish_date", "") for v in videos}
    for p in predictions:
        p["video_title"] = title_map.get(p["video_id"], "")
        p["publish_date"] = date_map.get(p["video_id"], "")
    
    # Stage 6: Evaluate
    print(f"\n=== EVALUATION ===")
    eval_result = evaluate_all_predictions(predictions, market_map)
    
    valid = [p for p in eval_result["predictions"] if p.get("status") != "N/A"]
    na = [p for p in eval_result["predictions"] if p.get("status") == "N/A"]
    print(f"  Valid predictions: {len(valid)}")
    print(f"  N/A predictions: {len(na)}")
    
    for p in valid:
        print(f"     {p.get('video_title','')[:40]} | ${p.get('target_price',0)} | {p.get('status')} | {p.get('direction')}")
    
    for p in na:
        print(f"     [N/A] {p.get('video_title','')[:40]} | ${p.get('target_price',0)}")
    
    # Final format (like pipeline.py)
    formatted = []
    for p in valid:
        formatted.append({
            "video_title": p.get("video_title", ""),
            "prediction": f"BTC to {int(p.get('target_price', 0))} ({p.get('timeframe', 'short-term')})" if p.get('target_price',0) > 0 else "N/A",
            "direction": p.get("direction", ""),
            "target_price": p.get("target_price", 0),
            "status": p.get("status", "ONGOING"),
        })
    
    print(f"\n=== FINAL OUTPUT: {len(formatted)} predictions ===")
    for f in formatted:
        print(f"  {f['video_title'][:40]} | {f['prediction']} | {f['status']}")

if __name__ == "__main__":
    asyncio.run(main())
