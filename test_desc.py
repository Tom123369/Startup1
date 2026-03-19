import httpx
import re
import json

def get_description_via_html(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=10)
        # Search for "shortDescription":"..."
        match = re.search(r'"shortDescription":"(.+?)","isCrawlable"', resp.text)
        if match:
            desc = match.group(1).encode('utf-8').decode('unicode_escape')
            print("SUCCESS: Found description!")
            print("Size:", len(desc))
            return desc
    except Exception as e:
        print("Error:", e)
    return ""

if __name__ == "__main__":
    get_description_via_html("AjrSEIqun14")
 darkness", "duration": 4.14}, ...
