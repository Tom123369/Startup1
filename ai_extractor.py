"""
STEP 4 – AI Extraction (REFACTORED - BULLETPROOF)
Implements:
- Free-tier fallback system (OpenRouter + Cerebras)
- Sequential processing to avoid 429 Rate Limits
- Automatic ID injection if AI forgets it
- Resilient JSON parsing (handles arrays and objects)
"""

import logging
import json
import re
import random
import aiohttp
import asyncio
from typing import List, Dict, Optional

from config import GROQ_API_KEY, OPENROUTER_API_KEY, CEREBRAS_API_KEY, BYTEZ_API_KEY, ACTIVE_AI_KEY, ACTIVE_AI_MODEL, ACTIVE_AI_BASE_URL

import os

OR_URL = "https://openrouter.ai/api/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# confirmed SUCCESS on user's machine: "openrouter/free"
# Other free models added for redundancy
FALLBACK_CONFIGS = [
    {"url": OR_URL, "key": OPENROUTER_API_KEY, "model": "openrouter/free", "provider": "openrouter"},
    {"url": OR_URL, "key": OPENROUTER_API_KEY, "model": "meta-llama/llama-3.3-70b-instruct:free", "provider": "openrouter"},
    {"url": OR_URL, "key": OPENROUTER_API_KEY, "model": "google/gemini-2.0-flash-lite-preview-02-05:free", "provider": "openrouter"},
    {"url": OR_URL, "key": OPENROUTER_API_KEY, "model": "mistralai/mistral-small-24b-instruct-2501:free", "provider": "openrouter"},
    {"url": GROQ_URL, "key": GROQ_API_KEY, "model": "llama-3.1-8b-instant", "provider": "groq"},
]

def heuristic_title_extraction(title: str, market_type: str = "bitcoin") -> Dict:
    """
    Zero-brain emergency fallback. Pulls a number from the title if AI is dead.
    """
    title_lower = title.lower()
    
    # S01: Better asset detection using the master keyword list
    asset = "BTC"
    found_coins = _detect_coins_in_title(title)
    if found_coins:
        asset = found_coins[0] # Pick primary coin from title
    elif market_type != "bitcoin":
        asset = "NDAQ"
    
    # Try to find a target price like "$100k", "85,000", "75000"
    num_match = re.search(r'\$?(\d{1,3}(?:,\d{3})*k?|\d+k)', title_lower)
    target = 0
    if num_match:
        val_str = num_match.group(1).replace('$', '').replace(',', '')
        if 'k' in val_str:
            try: target = float(val_str.replace('k', '')) * 1000
            except: pass
        else:
            try: target = float(val_str)
            except: pass
            
    # Direction
    direction = "UP"
    if any(w in title_lower for w in ["crash", "dump", "bear", "warning", "danger", "drop", "down", "sell"]):
        direction = "DOWN"
    elif any(w in title_lower for w in ["moon", "pump", "bull", "rally", "skyrocket", "next", "new", "all time high", "buy", "long"]):
        direction = "UP"
        
    return {
        "coin": asset,
        "asset": asset,
        "target_price": target,
        "direction": direction,
        "confidence": 0.4,
        "proof_quote": f"Heuristic extraction from title: {title}",
        "timeframe": "short_term"
    }


logger = logging.getLogger(__name__)

def _get_system_prompt(market_type: str = "bitcoin") -> str:
    return """You are a directional crypto prediction engine. 
Your job is to extract EVERY SINGLE prediction made by the influencer for EACH cryptocurrency or asset mentioned in the transcript.

CORE RULES:
1. MULTIPLE COINS: If the influencer mentions Bitcoin, Ethereum, Solana, and XRP, you MUST return a separate object for EACH one.
2. DIRECTION (Bullish/Bearish):
   - "UP" (Bullish, the price is expected to go higher)
   - "DOWN" (Bearish, the price is expected to go lower)

3. TIMEFRAME (Duration of the predicted move): 
   Classify strictly as:
   - "very_short_term" -> Move happens in 1 to 7 days
   - "short_term"      -> Move happens in 1 to 2 weeks
   - "medium_term"     -> Move happens in about 1 month
   - "long_term"       -> Move is a macro projection for 2 to 6 months+

4. PRICE TARGETS: Try to extract the specific price level target if mentioned (e.g. 75000, 2.50, 4800). 
5. NO NEUTRALITY: Pick the most likely direction from the context.

OUTPUT FORMAT (JSON ARRAY ONLY):
[
  {
    "video_id": "string",
    "coin": "BTCTICKER", 
    "direction": "UP",
    "target_price": 75000,
    "timeframe": "short_term",
    "confidence": 0.8,
    "proof_quote": "Bitcoin heading to 75k soon"
  },
  {
    "video_id": "string",
    "coin": "SOL", 
    "direction": "DOWN",
    "target_price": 140,
    "timeframe": "very_short_term",
    "confidence": 0.7,
    "proof_quote": "Solana likely to drop to 140"
  }
]
"""

SOLO_SYSTEM_PROMPT = """Extract the specific asset and its price target from this transcript. 
You MUST return a JSON array with exactly one object. 
Be precise about whether it's Bitcoin (BTC), Ethereum (ETH), Solana (SOL), or another asset mentioned."""

def _build_user_prompt(videos: List[Dict]) -> str:
    blocks = []
    for v in videos:
        text = v.get("text_for_ai", "")[:12000] # Cap text length
        blocks.append(f"VIDEO ID: {v['video_id']}\nTRANSCRIPT: {text}")
    return "\n\n---\n\n".join(blocks)

def _build_solo_prompt(video: Dict) -> str:
    vid = video["video_id"]
    title = video.get("title", "")
    # Use more transcript (up to 15k) to ensure the target isn't cut off
    text = video.get("text_for_ai", "")[:15000]
    return f"""VIDEO: {title}
ID: {vid}

TRANSCRIPT:
{text}

TITLE AGAIN: {title}

TASK: Find the price target for the main asset mentioned in the video (e.g. BTC, ETH, OIL, SPY, etc).
OUTPUT FORMAT: [{"asset":"TICKER", "direction":"UP", "target_price":150, "timeframe":"short-term", "sentence":"quote here"}]"""

async def _call_ai(session: aiohttp.ClientSession, system_prompt: str, user_prompt: str, label: str) -> str:
    valid_configs = [c for c in FALLBACK_CONFIGS if c["key"]]
    if not valid_configs: return ""

    import random
    configs = valid_configs.copy()
    random.shuffle(configs)
    
    # Always prioritize the user's explicitly configured model from .env first
    primary_config = {"url": ACTIVE_AI_BASE_URL, "key": ACTIVE_AI_KEY, "model": ACTIVE_AI_MODEL, "provider": "primary"}
    
    if primary_config["key"] and primary_config["model"]:
        # Put primary at the beginning
        configs = [primary_config] + [c for c in configs if c["model"] != primary_config["model"]]
    
    # Cap to max 4 models per call to avoid endless 429 looping taking 30 minutes
    configs = configs[:4]

    for config in configs:
        m_id = config["model"]
        headers = {
            "Authorization": f"Bearer {config['key']}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://btc-prediction-analyzer.local",
            "X-Title": "BTC Prediction Analyzer",
        }
        payload = {
            "model": m_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2000,
        }
        
        # Retry logic: rigorous exponential backoff for 429s, fast fail for 403
        for attempt in range(4):
            try:
                async with session.post(config["url"], json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                    if resp.status == 429:
                        # Massive 429s hit free models -> chill out exponentially giving the API a chance
                        await asyncio.sleep(1.5 ** attempt + random.uniform(0.5, 2.0))
                        continue
                        
                    if resp.status in (403, 404, 402):
                        logger.warning(f"AI: {m_id} returned {resp.status} (FATAL ERROR). Skipping to next provider. ({label})")
                        break # Break loop to move exactly to the NEXT config
                        
                    if resp.status != 200:
                        logger.warning(f"AI: {m_id} returned {resp.status} for {label}. Retry attempt {attempt+1}")
                        await asyncio.sleep(2)
                        continue
                        
                    data = await resp.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content and content.strip(): 
                        return content
                break
            except Exception as e:
                logger.debug(f"AI: config {m_id} failed for {label}: {e}")
                await asyncio.sleep(2)
                continue
    return ""

def _parse_ai_response(content: str, label: str, market_type: str = "bitcoin", max_per_video: int = 2) -> List[Dict]:
    content = content.replace("```json", "").replace("```", "").strip()
    
    # Identify JSON blocks using regex
    match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
    if not match:
        # Try finding a single object instead
        match = re.search(r'\{.*?\}', content, re.DOTALL)
        
    if match:
        json_str = match.group(0)
    else:
        # Fallback to the old heuristic but more strictly bounded
        start_array = content.find("[")
        start_obj = content.find("{")
        if start_array == -1 and start_obj == -1:
            logger.error(f"[{label}] No JSON markers found in AI response: {content[:100]}...")
            return []

        idx = start_array if (start_array != -1 and (start_obj == -1 or start_array < start_obj)) else start_obj
        char_open = content[idx]
        char_close = "]" if char_open == "[" else "}"
        end = content.rfind(char_close)
        
        if end == -1:
            return []
        json_str = content[idx:end + 1]

    try:
        predictions = json.loads(json_str)
        if isinstance(predictions, dict): predictions = [predictions]
        if not isinstance(predictions, list): return []
    except Exception as e:
        logger.error(f"[{label}] JSON Decode Error: {e} | Content: {json_str[:200]}")
        return []


    valid = []
    
    for p in predictions:
        if not isinstance(p, dict): continue
        
        # ID Handling
        ai_returned_vid = str(p.get("video_id", "")).strip()
        if not ai_returned_vid or ai_returned_vid.lower() in {"video_id_here", "...", "null", "none", "undefined", label}:
            vid = label
        else:
            vid = ai_returned_vid
        p["video_id"] = vid

        # Price Extraction (Internal: target_price)
        raw_target = p.get("target_price")
        val = 0.0
        if raw_target is not None:
            try:
                # Midpoint calculation if range provided as [a, b] or similar
                if isinstance(raw_target, (list, tuple)) and len(raw_target) >= 2:
                    val = (float(raw_target[0]) + float(raw_target[1])) / 2
                else:
                    s = str(raw_target).lower().replace('k', '000').replace(',', '')
                    nums = re.findall(r'\d+(?:\.\d+)?', s)
                    if nums:
                        val = float(nums[0])
                        if (p.get("coin") == "BTC" or market_type == "bitcoin") and val < 500:
                            val *= 1000
            except: 
                val = 0.0
        
        p["asset"] = p.get("coin") or p.get("asset") or ("BTC" if market_type == "bitcoin" else "CRYPTO")
        p["sentence"] = p.get("proof_quote") or p.get("sentence") or "Extracted from context."
        
        # Ensure only UP or DOWN, never NEUTRAL
        direction = str(p.get("direction", "UP")).upper()
        if direction not in ["UP", "DOWN"]:
            direction = "UP" # Default to Bullish/UP per user request
        p["direction"] = direction
        
        p.setdefault("timeframe", "short_term")
        p.setdefault("confidence", 0.5)
        
        # Stringify target for prediction display
        ticker = p["asset"].upper()
        if val > 0:
            p["prediction"] = f"{ticker} at ${val:,.0f}"
        else:
            p["prediction"] = f"{ticker} {p['direction']} (No Target)"

        valid.append(p)
    return valid


# Priority-ordered coin detection from title. First match wins for single-coin titles.
_TITLE_COIN_KEYWORDS = [
    (["bitcoin", "btc", "xbt"], "BTC"),
    (["ethereum", "eth"], "ETH"),
    (["solana", "sol"], "SOL"),
    (["ripple", "xrp"], "XRP"),
    (["cardano", "ada"], "ADA"),
    (["dogecoin", "doge"], "DOGE"),
    (["polkadot", "dot"], "DOT"),
    (["chainlink", "link"], "LINK"),
    (["avalanche", "avax"], "AVAX"),
    (["near protocol", "near"], "NEAR"),
    (["internet computer", "icp"], "ICP"),
    (["shiba", "shib"], "SHIB"),
    (["pepe"], "PEPE"),
    (["floki"], "FLOKI"),
    (["bnb", "binance coin"], "BNB"),
    (["litecoin", "ltc"], "LTC"),
    (["polygon", "matic", "pol"], "POL"),
    (["cosmos", "atom"], "ATOM"),
    (["render", "rndr"], "RNDR"),
    (["fantom", "ftm"], "FTM"),
    (["arbitrum", "arb"], "ARB"),
    (["optimism", "op"], "OP"),
    (["sui"], "SUI"),
    (["aptos", "apt"], "APT"),
    (["jupiter", "jup"], "JUP"),
    (["inj", "injective"], "INJ"),
    (["sei"], "SEI"),
    (["tia", "celestia"], "TIA"),
    (["oil", "crude"], "OIL"),
    (["gold", "xau"], "GOLD"),
    (["s&p", "spy", "s&p500"], "SPY"),
    (["nasdaq", "ndaq", "qqq"], "NDAQ"),
]

def _detect_coins_in_title(title: str) -> list:
    """Return list of all coins explicitly mentioned in the title using word boundaries."""
    title_lower = title.lower()
    found = []
    for keywords, coin in _TITLE_COIN_KEYWORDS:
        # Check every keyword for a word-boundary match (regex \b)
        for kw in keywords:
            clean_kw = kw.strip().lower()
            if not clean_kw: continue
            # Handle cases where keyword is already regex-like (e.g. with slashes)
            pattern = rf"\b{re.escape(clean_kw)}\b"
            if re.search(pattern, title_lower):
                if coin not in found:
                    found.append(coin)
                break
    return found
    
def _validate_coin_against_title(prediction: dict, video_title: str) -> list:
    """
    Cross-check the AI's extracted coin against the video title.
    - If title has one coin, and AI is vague/wrong, correct it.
    - If title has multiple coins, ensure AI has a prediction for each.
    - If title has no coins, trust the AI.
    """
    title_coins = _detect_coins_in_title(video_title)
    if not title_coins:
        return [prediction]
    
    ai_coin = str(prediction.get("asset") or prediction.get("coin") or "").upper()
    
    # RELAXED: Only overwrite if the AI extraction is clearly generic or vague.
    # If the AI extracted a specific coin like "SOL" or "ETH" and it's not in the title,
    # it might still be a valid secondary prediction from the transcript.
    if len(title_coins) == 1:
        correct_coin = title_coins[0]
        # If AI found a specific ticker that's NOT the title coin, we trust the AI more than the title
        # unless the AI coin is very likely a "default" or "hallucination".
        # We only overwrite if the AI-coin is generic or if it's the wrong primary coin but the AI was shaky.
        if ai_coin in ["BTC", "CRYPTO", "COIN", "UNKNOWN"] and ai_coin != correct_coin:
            prediction = dict(prediction)
            prediction["coin"] = correct_coin
            prediction["asset"] = correct_coin
    
    # For multiple coins in title, the main loop in extract_predictions_async covers the rest.
    return [prediction]

async def extract_predictions_async(videos: List[Dict], market_type: str = "bitcoin", progress_callback=None) -> List[Dict]:
    """
    Strategy 2 & 4: Batched and Parallelized AI Calls.
    Sends multiple video transcripts in one prompt and runs all batches concurrently.
    """
    batch_size = 3 # 3 videos per AI call prevents smaller AI models from getting lazy and skipping objects
    batches = [videos[i:i + batch_size] for i in range(0, len(videos), batch_size)]
    
    all_predictions = []
    processed_count = [0]
    total = len(videos)
    
    system_prompt = _get_system_prompt(market_type)
    
    async def process_batch(session: aiohttp.ClientSession, i, batch):
        prompts = []
        for v in batch:
            vid = v['video_id']
            title = v.get('title', 'Unknown')
            text = v.get('text_for_ai', '')[:6000]
            prompts.append(f"--- VIDEO ID: {vid} ---\nTITLE: {title}\nTRANSCRIPT: {text}")
        
        user_prompt = "\n\n".join(prompts) + "\n\nCRITICAL TASK: For EVERY VIDEO ID above, extract predictions for EVERY cryptocurrency or stock mentioned (BTC, ETH, SOL, etc). If 5 coins are discussed in one video, return 5 objects for that video. DO NOT skip any altcoins."
        label = batch[0]['video_id']
        raw = await _call_ai(session, system_prompt, user_prompt, f"Batch_{i}_{label}")
        
        batch_results = []
        parsed = []
        if raw:
            parsed = _parse_ai_response(raw, label, market_type)
        
        # We need a quick way to look up parsed predictions by video_id
        parsed_by_vid = {}
        for p in parsed:
            vid = p.get('video_id', '')
            if vid not in parsed_by_vid:
                parsed_by_vid[vid] = []
            parsed_by_vid[vid].append(p)
            
        # Process each video in the batch
        for v in batch:
            vid = v['video_id']
            title = v.get('title', '')
            title_coins = _detect_coins_in_title(title)
            
            ai_preds = parsed_by_vid.get(vid, [])
            
            # TRACKER: Which coins from title already have an AI prediction?
            represented_coins = set()
            for p in ai_preds:
                # Basic validation for AI predictions
                validated = _validate_coin_against_title(p, title)
                for vp in validated:
                    batch_results.append(vp)
                    asset_name = str(vp.get("asset") or vp.get("coin") or "").upper()
                    represented_coins.add(asset_name)
            
            # COVERAGE ENFORCEMENT: If title mentions coins that AI missed, add fallbacks for them.
            for t_coin in title_coins:
                if t_coin.upper() not in represented_coins:
                    h = heuristic_title_extraction(title, market_type=market_type)
                    h["video_id"] = vid
                    h["coin"] = t_coin
                    h["asset"] = t_coin
                    batch_results.append(h)
                    represented_coins.add(t_coin.upper())
            
            # If nothing was found at all, use the simple heuristic fallback
            if not represented_coins and not ai_preds:
                h = heuristic_title_extraction(title, market_type=market_type)
                h["video_id"] = vid
                batch_results.append(h)
            
        if progress_callback:
            processed_count[0] += len(batch)
            await progress_callback("ai_extraction", f"AI processed {processed_count[0]}/{total} videos")
            
        return batch_results
    

    # Use a Semaphore to prevent blasting 429 rate limits on fallback free models
    ai_semaphore = asyncio.Semaphore(4)

    async def _safe_process_batch(session, i, batch):
        async with ai_semaphore:
            # Add subtle jitter to smooth out arrival rate
            await asyncio.sleep(i * 0.1)
            return await process_batch(session, i, batch)

    async with aiohttp.ClientSession() as session:
        tasks = [_safe_process_batch(session, i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks)
        for r in results:
            all_predictions.extend(r)
            
    return all_predictions

def _finalize_prediction_data(p: Dict, market_type: str) -> Dict:
    raw_target = p.get("target_price")
    val = 0.0
    if raw_target:
        try:
            s = str(raw_target).lower().replace('k', '000').replace(',', '')
            nums = re.findall(r'\d+(?:\.\d+)?', s)
            if nums:
                val = float(nums[0])
                if market_type == "bitcoin" and val < 500:
                    val *= 1000
            else:
                val = 0.0
        except: 
            val = 0.0
    
    if val == 0 and p.get("sentence"):
        nums = re.findall(r'\d+(?:,\d{3})*(?:\.\d+)?k?', str(p["sentence"]).lower().replace('k', '000').replace(',', ''))
        if nums:
            try: val = float(nums[0])
            except: pass
    
    p["target_price"] = val
    # Only default to BTC if no coin was found at all
    if not p.get("asset") and not p.get("coin"):
        p["asset"] = "BTC" if market_type == "bitcoin" else "CRYPTO"
    
    p.setdefault("direction", "UP")
    p.setdefault("timeframe", "short-term")
    p.setdefault("sentence", "Found in video context.")
    return p

async def resolve_youtuber_name(query: str) -> str:
    system_prompt = "You are a YouTube expert. Identify the most likely YouTube channel handle or exact name for the given YouTuber."
    user_prompt = f"Identify the YouTube handle (e.g. @TheMoonCarl) for the YouTuber: '{query}'. Output ONLY the handle or most accurate name, nothing else."
    try:
        async with aiohttp.ClientSession() as session:
            result = await _call_ai(session, system_prompt, user_prompt, "NameResolution")
            return result.strip().strip("'\"") if result else query
    except Exception: return query
