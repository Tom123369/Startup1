import yt_dlp
import json

def test_collection(url, limit=20):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
        'playlist_items': f'1-{limit}',
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get('entries', [])
        print(f"Collected {len(entries)} entries")
        for e in entries:
            print(f"ID: {e.get('id')}, Title: {e.get('title')}, Date: {e.get('upload_date')}")

if __name__ == "__main__":
    # Test with a known channel that posts daily
    test_collection("https://www.youtube.com/@TheMoon", limit=20)
