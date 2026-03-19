import video_collector
import logging
logging.basicConfig(level=logging.INFO)

url = "https://www.youtube.com/@CryptoWorldJosh"
print(f"Testing collector with {url} and limit 100")
vids = video_collector.collect_videos(url, limit=100)
print(f"Collected: {len(vids)}")
if vids:
    print(vids[0])
