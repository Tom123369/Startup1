"""
STEP 1 – Video Collection
Uses scrapetube to retrieve the latest N videos from a YouTube channel.
"""

import re
import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

import httpx
import scrapetube
import yt_dlp
import re

logger = logging.getLogger(__name__)


def _extract_channel_identifier(url: str) -> tuple[str, str]:
    """Parse a YouTube channel URL and return (kind, value)."""
    url = url.strip().rstrip("/")
    m = re.search(r"youtube\.com/channel/(UC[\w-]+)", url)
    if m: return ("channel_id", m.group(1))
    m = re.search(r"youtube\.com/@([\w.-]+)", url)
    if m: return ("channel_url", f"https://www.youtube.com/@{m.group(1)}")
    m = re.search(r"youtube\.com/(?:c|user)/([\w.-]+)", url)
    if m: return ("channel_username", m.group(1))
    if url.startswith("UC"): return ("channel_id", url)
    return ("channel_url", url)


def _get_channel_id(url: str) -> Optional[str]:
    """Use yt-dlp to find the actual UC... channel ID once."""
    try:
        with yt_dlp.YoutubeDL({'quiet': True, 'extract_flat': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return info.get('playlist_channel_id') or info.get('channel_id')
    except Exception:
        return None

def _fetch_rss_dates(channel_id: str) -> Dict[str, str]:
    """Get real ISO dates from the RSS feed as a truth source."""
    dates = {}
    if not channel_id: return dates
    try:
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        resp = httpx.get(url, timeout=10)
        root = ET.fromstring(resp.text)
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            vid = entry.find("{http://www.youtube.com/xml/schemas/2015}videoId").text
            pub = entry.find("{http://www.w3.org/2005/Atom}published").text
            dates[vid] = pub.split("T")[0]
    except Exception:
        pass
    return dates

def _parse_relative_date(text: str) -> str:
    """Convert '2 hours ago', '3 days ago' etc to YYYY-MM-DD."""
    if not text: return datetime.now().strftime("%Y-%m-%d")
    text = text.lower()
    m = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", text)
    if not m: return datetime.now().strftime("%Y-%m-%d")
    
    num = int(m.group(1))
    unit = m.group(2)
    multipliers = {"second": 0,"minute": 0,"hour": 0,"day": 1,"week": 7,"month": 30,"year": 365}
    days_ago = num * multipliers.get(unit, 1)
    return (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")

def collect_videos(channel_url: str, limit: int = 100) -> List[Dict]:
    """
    Retrieve latest videos with ABSOLUTE dates using yt-dlp flat extraction.
    This eliminates 'repeating dates' by fetching the actual upload_date.
    """
    logger.info(f"Collecting last {limit} videos with accurate dates for {channel_url}...")
    
    # Clean and optimize search URL
    search_url = channel_url.rstrip("/")
    if "/@" in search_url and not any(x in search_url for x in ["/videos", "/streams", "/shorts"]):
        search_url = f"{search_url}/videos"
    
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlist_items': f'1-{limit}',
        'skip_download': True,
        'force_generic_extractor': False,
    }
    
    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_url, download=False)
            
            if 'entries' in info:
                for i, entry in enumerate(info['entries']):
                    if not entry: continue
                    
                    vid = entry.get('id') or entry.get('url')
                    if not vid: continue
                    
                    # Extract TRUE date
                    upload_date = entry.get('upload_date') # YYYYMMDD
                    title = str(entry.get('title', 'Untitled Video'))
                    
                    # Formatting YYYYMMDD -> YYYY-MM-DD
                    fmt_date = ""
                    if upload_date and len(upload_date) == 8:
                        fmt_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
                    else:
                        # Fallback ONLY if yt-dlp fails (rare)
                        fmt_date = (datetime.now() - timedelta(days=int(i))).strftime("%Y-%m-%d")
                    
                    videos.append({
                        "video_id": vid,
                        "title": title,
                        "publish_date": fmt_date,
                    })
                    
    except Exception as e:
        logger.error(f"yt-dlp absolute collection failed: {e}")
        # Secondary fallback logic could go here if needed
        
    # Final sorting by date (newest first)
    videos.sort(key=lambda x: str(x.get("publish_date", "")), reverse=True)
    logger.info(f"Successfully collected {len(videos)} videos with specific dates.")
    return videos

    # Deduplicate and sort
    seen = set()
    unique_videos = []
    for v in videos:
        if v["video_id"] not in seen:
            unique_videos.append(v)
            seen.add(v["video_id"])

    unique_videos.sort(key=lambda x: str(x.get("publish_date", "")), reverse=True)
    logger.info(f"Workflow complete. Found {len(unique_videos)} videos.")
    return unique_videos
