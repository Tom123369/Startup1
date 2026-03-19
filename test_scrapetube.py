import scrapetube
import logging
logging.basicConfig(level=logging.INFO)

print("Testing scrapetube...")
try:
    vids = list(scrapetube.get_channel(channel_url="https://www.youtube.com/@CryptoWorldJosh", limit=5))
    print(f"Found {len(vids)} videos.")
    if vids:
        print(vids[0].get('title', 'no title'))
except Exception as e:
    print(f"Error: {e}")
