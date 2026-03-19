"""
Pipeline Orchestrator (REFACTORED - VERSION 4)
Implements:
- ULTRA FAST fallback for blocked IPs
- Controlled concurrency (Semaphore = 5)
- Multi-stage worker pool
- Strategy 6: Supports capping via `max_videos`.
"""

import asyncio
import logging
import time
import random
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from config import MAX_VIDEOS
from video_collector import collect_videos
from transcript_extractor import fetch_transcript_async
from transcript_filter import filter_transcript
from ai_extractor import extract_predictions_async
from market_data import get_batch_price_ranges_async
from evaluator import evaluate_all_predictions

from firebase_utils import save_analysis_to_firestore, load_analysis_from_firestore

logger = logging.getLogger(__name__)

# ── Global Semaphore ─────────────────────────────────────────────────────────
transcript_semaphore = asyncio.Semaphore(15) # Optimized concurrency for Render CPU


async def _run_stage_2_3(video: Dict) -> Dict:
    """
    Stage 2: Transcript Fetch (or Fallback)
    Stage 3: Transcript Filtering
    """
    vid = video["video_id"]
    
    async with transcript_semaphore:
        # Fully async fetch (Strategy 1)
        content = await fetch_transcript_async(vid)
        
        # Stage 3: Filter (Fast)
        filtered = filter_transcript(content) if content else ""
        
        return {**video, "transcript": content or "", "filtered_text": filtered}


def _save_results_to_disk(youtuber_name: str, result: Dict):
    """Save the analysis results into a dedicated folder for the YouTuber."""
    try:
        # Sanitize folder name
        safe_name = "".join(c for c in youtuber_name if c.isalnum() or c in (" ", "-", "_")).strip()
        safe_name = safe_name.replace(" ", "_")
        if not safe_name: safe_name = "Unknown_Youtuber"
        
        # Create directory
        results_dir = Path("results") / safe_name
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = results_dir / f"evaluation_{timestamp}.json"
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
            
        logger.info(f"Results saved to: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save results to disk: {e}")


async def run_pipeline(
    channel_url: str,
    max_videos: int = MAX_VIDEOS,
    market_type: str = "bitcoin",
    progress_callback=None,
) -> Dict:
    """
    Run the multi-stage analysis pipeline.
    Strategy 6: Supports capping via `max_videos`.
    """
    start_time = time.time()
    max_videos = int(max_videos)
    
    # SXX: FAST CACHE CHECK
    # Check if we already have a recent result for this influencer to avoid redundant work
    # Sanitize inputs
    clean_url = channel_url.strip().lower()
    
    # Resolve name FIRST to check cache folders
    from ai_extractor import resolve_youtuber_name
    potential_handle = clean_url.split('/')[-1] if '/' in clean_url else clean_url
    yt_name = await resolve_youtuber_name(potential_handle)
    
    # Sanitize filename
    safe_name = "".join(c for c in yt_name if c.isalnum() or c in (" ", "-", "_")).strip().replace(" ", "_")
    results_dir = Path("results") / safe_name
    
    if results_dir.exists():
        # Look for the absolute newest file in results dir
        try:
            files = sorted(results_dir.glob("evaluation_*.json"), key=os.path.getmtime, reverse=True)
            if files:
                newest = files[0]
                # If the file is less than 6 hours old, return it instantly!
                if (time.time() - os.path.getmtime(newest)) < 3600 * 6:
                    logger.info(f"CACHE HIT: Found recent analysis for {yt_name} - loading instantly.")
                    with open(newest, "r", encoding="utf-8") as f:
                        cached_data = json.load(f)
                        if progress_callback: await progress_callback("done", f"Loaded previous analysis for {yt_name} (Cached)")
                        return cached_data
        except Exception as e:
            logger.debug(f"Local cache hit skipped: {e}")

    # SXY: CLOUD PERSISTENCE (Firestore)
    # Check if we have this cached in the cloud (survives Render redeploys)
    cloud_data = await load_analysis_from_firestore(yt_name)
    if cloud_data:
        if progress_callback: await progress_callback("done", f"Loaded persistent analysis for {yt_name} (Cloud)")
        return cloud_data

    # Not in cache, proceed with full analysis
    all_valid_predictions = []
    all_na_predictions = []

    processed_video_ids = set()
    videos_metadata_cache = []
    
    fetch_limit = max_videos + 10 # Slight buffer
    max_attempts = 1 # We just do one pass through the newest videos now

    async def _progress(stage: str, detail: str = ""):
        if progress_callback:
            try:
                await progress_callback(stage, detail)
            except Exception:
                pass
        logger.info(f"[PIPELINE] {stage.upper()}: {detail}")

    for attempt in range(max_attempts):
        await _progress("collecting", f"Fetching newest videos (limit {fetch_limit})...")
        loop = asyncio.get_event_loop()
        new_batch = await loop.run_in_executor(
            None, lambda: collect_videos(channel_url, limit=fetch_limit)
        )
        
        for v in new_batch:
            if v["video_id"] not in [m["video_id"] for m in videos_metadata_cache]:
                videos_metadata_cache.append(v)

        unprocessed = [v for v in new_batch if v["video_id"] not in processed_video_ids]
        if not unprocessed:
            logger.info("No more new videos found.")
            break
            
        unprocessed = unprocessed[:max_videos] # Hard cap at Strategy 6
        await _progress("collecting", f"Found {len(unprocessed)} new videos. Starting parallel extraction...")

        # Strategy 4: Full Streaming Parallelization
        tasks = [_run_stage_2_3(v) for v in unprocessed]
        
        await _progress("transcripts", f"Extracting metadata and transcripts (Streaming)...")
        
        batch_predictions = []
        current_batch = []
        ai_tasks = []
        
        for stage_task in asyncio.as_completed(tasks):
            v = await stage_task
            v["text_for_ai"] = v["filtered_text"] or v.get("title", "")
            processed_video_ids.add(v["video_id"])
            
            current_batch.append(v)
            if len(current_batch) >= 10: 
                batch_to_process = current_batch[:]
                current_batch = []
                ai_tasks.append(extract_predictions_async(batch_to_process, market_type, _progress))
        
        if current_batch:
            ai_tasks.append(extract_predictions_async(current_batch, market_type, _progress))
            
        if ai_tasks:
            all_results = await asyncio.gather(*ai_tasks)
            for sublist in all_results:
                batch_predictions.extend(sublist)

        # Link metadata (REQUIRED before market data fetch for correct dates)
        title_map = {v["video_id"]: v.get("title", "") for v in videos_metadata_cache}
        date_map = {v["video_id"]: v.get("publish_date", "") for v in videos_metadata_cache}
        for p in batch_predictions:
            p["video_title"] = title_map.get(p["video_id"], "")
            p["publish_date"] = date_map.get(p["video_id"], "")

        # Market Data (Strategy 5)
        await _progress("market_data", "Retrieving historical price data for evaluation...")
        market_map = await get_batch_price_ranges_async(batch_predictions, market_type)

        # Evaluate
        await _progress("evaluation", "Analyzing results against market movements...")
        eval_result = evaluate_all_predictions(batch_predictions, market_map)
        
        # Sort into Real vs N/A
        logger.info(f"PIPELINE: Batch analyzed.")

        for p in eval_result["predictions"]:
            if p.get("status") == "N/A":
                all_na_predictions.append(p)
            else:
                all_valid_predictions.append(p)
        
        await _progress("status", f"Summary: {len(all_valid_predictions)} valid + {len(all_na_predictions)} N/A")
        
        # If we still need more videos to analyze, increase fetch_limit
        if len(processed_video_ids) < max_videos:
            fetch_limit += max_videos - len(processed_video_ids) + 10
        else:
            break

    # Show EVERYTHING found by AI (Valid + N/A) so the user doesn't wonder where data went
    final_list = all_valid_predictions + all_na_predictions

    # Re-calculate overall stats for the final chosen list
    current_prices = {p["video_id"]: p["current_price"] for p in (all_valid_predictions + all_na_predictions) if "current_price" in p}
    final_market_map = {vid: {"current_price": cp} for vid, cp in current_prices.items()} # Minimal map for re-eval
    
    # We already have evaluated objects, just re-aggregate totals
    correct = sum(1 for p in final_list if p["status"] == "CORRECT")
    wrong = sum(1 for p in final_list if p["status"] == "WRONG")
    ongoing = sum(1 for p in final_list if p["status"] == "ONGOING")
    decided = correct + wrong
    accuracy = round((correct / decided * 100), 1) if decided > 0 else 0.0

    total_time = round(time.time() - start_time, 1)
    
    # Final Format
    formatted = []
    for p in final_list:
        tp = float(p.get('target_price') or 0)
        asset = p.get('asset', 'BTC').upper()
        # Format the prediction string bulletproof explicitly
        if p.get("prediction"):
            pred_text = str(p["prediction"])
            
            # If the parser returned N/A (e.g., from an old cache or failure), override it intelligently
            if pred_text == "N/A" or pred_text == "Skipped (AI Fault)":
                if tp > 0:
                    pred_text = f"{asset} to {int(tp) if tp > 10 else round(tp, 2)}"
                else:
                    pred_text = f"{asset} {p.get('direction', 'NEUTRAL')} (No Target)"
                    
        else:
            if tp > 0:
                pred_text = f"{asset} to {int(tp) if tp > 10 else round(tp, 2)}"
            else:
                pred_text = f"{asset} {p.get('direction', 'NEUTRAL')} (No Target)"

        formatted.append({
            "video_title": p.get("video_title", ""),
            "video_id": p.get("video_id", ""),
            "publish_date": p.get("publish_date", ""),
            "coin": str(p.get("coin") or asset),
            "prediction": pred_text,
            "direction": p.get("direction", ""),
            "confidence": p.get("confidence", 0.0),
            "target_price": tp,
            "timeframe": p.get("timeframe", "short_term"),
            "price_at_prediction": p.get("price_at_prediction"),
            "highest_after": p.get("highest_after"),
            "lowest_after": p.get("lowest_after"),
            "current_price": p.get("current_price"),
            "status": p.get("status", "ONGOING"),
            "sentence": p.get("sentence", p.get("proof_quote", "")),
            "reasoning": p.get("reasoning", ""),
        })
    formatted.sort(key=lambda x: str(x.get("publish_date", "")), reverse=True)

    await _progress("done", f"Found {len(all_valid_predictions)} valid + {len(all_na_predictions)} N/A predictions from {len(processed_video_ids)} videos.")

    response = {
        "videos_analyzed": len(processed_video_ids),
        "predictions_found": len(formatted),
        "correct": correct,
        "wrong": wrong,
        "ongoing": ongoing,
        "accuracy_percentage": accuracy,
        "predictions": formatted,
        "processing_time": total_time
    }

    # S08: SAVE TO DISK & CLOUD
    try:
        response["influencer_name"] = yt_name
        _save_results_to_disk(yt_name, response)
        # Persistent Storage Backup
        save_analysis_to_firestore(yt_name, response)
    except Exception as e:
        logger.error(f"Save failed: {e}")
        response["influencer_name"] = "Channel_Analysis"
        _save_results_to_disk("Channel_Analysis", response)

    return response



