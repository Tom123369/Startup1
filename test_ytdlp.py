import yt_dlp
import sys
import time

url = "https://www.youtube.com/@CryptoWorldJosh/videos"

try:
    start = time.time()
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlistend': 100
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get('entries', [])
        print(f"Found {len(entries)} videos in {time.time() - start:.2f} seconds.")
except Exception as e:
    print(e)
