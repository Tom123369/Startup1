import logging
import json
import time
import re
import httpx
import asyncio
from pathlib import Path
from typing import Optional, List, Dict

from youtube_transcript_api import YouTubeTranscriptApi
from config import (
    TRANSCRIPT_HEAD_SECONDS, 
    TRANSCRIPT_TAIL_SECONDS,
    TRANSCRIPT_CACHE_DIR
)

logger = logging.getLogger(__name__)

# Ensure cache directory exists
CACHE_PATH = Path(TRANSCRIPT_CACHE_DIR)
CACHE_PATH.mkdir(parents=True, exist_ok=True)

_api = YouTubeTranscriptApi()
_LANG_PRIORITY = ["en", "en-US", "en-GB"]

# ── Global Circuit Breaker ──────────────────────────────────────────────
_CONSECUTIVE_429 = 0
_MAX_CONSECUTIVE_429 = 4
_IP_BLOCKED_MODE = False


def _get_cache_path(video_id: str) -> Path:
    return CACHE_PATH / f"{video_id}.json"


def _load_from_cache(video_id: str) -> Optional[str]:
    path = _get_cache_path(video_id)
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("text")
        except Exception:
            pass
    return None


def _save_to_cache(video_id: str, text: str):
    path = _get_cache_path(video_id)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id, "text": text, "timestamp": time.time()}, f)
    except Exception:
        pass


async def _get_description_fallback_async(video_id: str) -> str:
    """Scrape description if transcript is blocked. Returns description text."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=5.0) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                match = re.search(r'"shortDescription":"(.+?)","isCrawlable"', resp.text)
                if match:
                    return match.group(1).encode('utf-8').decode('unicode_escape')
                match2 = re.search(r'\\\"description\\\":\{\\\"simpleText\\\":\\\"(.+?)\\\"\}', resp.text)
                if match2:
                    return match2.group(1).encode('utf-8').decode('unicode_escape')
    except Exception as e:
        logger.error(f"Scraper error for {video_id}: {e}")
    return ""


async def _get_yt_dlp_transcript_fallback_async(video_id: str) -> Optional[str]:
    """Fallback to use yt-dlp to download auto-subtitles."""
    import yt_dlp
    
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['en'],
        'quiet': True,
        'no_warnings': True,
    }
    
    def _extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    try:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, _extract)
        subs = info.get('requested_subtitles', {})
        if subs and 'en' in subs:
            sub_url = subs['en']['url']
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(sub_url)
                if resp.status_code == 200:
                    lines = []
                    last_text = ""
                    for line in resp.text.split('\n'):
                        if '-->' in line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:') or not line.strip():
                            continue
                        line = re.sub(r'<[^>]+>', '', line).strip()
                        if line and line != last_text:
                            lines.append(line)
                            last_text = line
                    return " ".join(lines)
    except Exception as e:
        logger.warning(f"yt-dlp subtitle extraction failed for {video_id}: {e}")
    return None


async def fetch_transcript_async(video_id: str) -> Optional[str]:
    """
    Fetch transcript with caching. Fully async with fast failure fallbacks.
    """
    global _CONSECUTIVE_429, _IP_BLOCKED_MODE

    # 1. Check cache first (Instant)
    cached = _load_from_cache(video_id)
    if cached is not None:
        return cached

    # 2. If blocked, jump straight to fallbacks
    if _IP_BLOCKED_MODE:
        subs = await _get_yt_dlp_transcript_fallback_async(video_id)
        if subs:
            _save_to_cache(video_id, subs)
            return subs
        return await _get_description_fallback_async(video_id)

    # 3. Attempt youtube_transcript_api (Wrap in thread pool since it's blocking)
    loop = asyncio.get_event_loop()
    try:
        def _call_api():
            try:
                return _api.fetch(video_id, languages=_LANG_PRIORITY)
            except:
                t_list = _api.list(video_id)
                available = list(t_list)
                if not available: return None
                return available[0].fetch()

        transcript_obj = await loop.run_in_executor(None, _call_api)
        
        if transcript_obj:
            segments = transcript_obj
            text = " ".join(s.get("text", "") for s in segments)
            if text.strip():
                _CONSECUTIVE_429 = 0
                _save_to_cache(video_id, text)
                return text

    except Exception as e:
        msg = str(e)
        # S02: Distinguish between "Blocked" and "Not Available"
        if "429" in msg or "IpBlocked" in type(e).__name__ or "Too Many Requests" in msg:
            _CONSECUTIVE_429 += 1
            if _CONSECUTIVE_429 >= _MAX_CONSECUTIVE_429:
                if not _IP_BLOCKED_MODE:
                    _IP_BLOCKED_MODE = True
                    logger.error("!!! YouTube IP Blocked - Switching to Fallbacks !!!")
        elif "TranscriptsDisabled" in msg or "No transcript found" in msg or "Could not find a transcript" in msg:
            # This is a normal failure, don't trigger circuit breaker
            _CONSECUTIVE_429 = 0
        else:
            logger.debug(f"Transcript fetch error for {video_id}: {e}")

    # Final Fallbacks
    subs = await _get_yt_dlp_transcript_fallback_async(video_id)
    if subs:
        _save_to_cache(video_id, subs)
        return subs

    desc = await _get_description_fallback_async(video_id)
    if desc:
        return desc

    return None
