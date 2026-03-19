import yt_dlp
import json

ydl_opts = {'quiet': True, 'extract_flat': True, 'playlistend': 5}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info("https://www.youtube.com/@TheMoonCarl", download=False)
    
if 'entries' in info:
    vids = list(info['entries'])
    print(f"Found {len(vids)} entries from root")
    for v in vids[:2]: print(v.get('title'))
else:
    print("No entries")
