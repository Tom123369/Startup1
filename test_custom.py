import httpx
import re
import json
from urllib.parse import quote

def get_transcript(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
    }
    
    client = httpx.Client(headers=headers, follow_redirects=True, timeout=10.0)
    resp = client.get(url)
    
    match = re.search(r'"captionTracks": *(\[.*?\])', resp.text)
    if not match:
        print("No caption tracks found.")
        return
        
    try:
        tracks = json.loads(match.group(1))
        track = tracks[0]
        for t in tracks:
            if t.get('languageCode', '').startswith('en'):
                track = t
                break
                
        # fetch the xml from baseUrl but proxy it
        track_url = track['baseUrl']
        # Try https://api.allorigins.win/raw?url=
        proxy_url = f"https://api.allorigins.win/raw?url={quote(track_url, safe='')}"
        print("Fetching Proxy URL:", proxy_url[:100])
        
        xml_resp = client.get(proxy_url)
        xml = xml_resp.text
        
        print("XML Response Status:", xml_resp.status_code)
        print("XML prefix:", xml[:100])
        
        # Simple extract
        text_match = re.findall(r'<text[^>]*>(.*?)</text>', xml)
        from html import unescape
        text = " ".join([unescape(t) for t in text_match])
        print("Text snippet:", text[:100])
        print("Text len:", len(text))
    except Exception as e:
        print("Error parsing", e)

if __name__ == "__main__":
    get_transcript("AjrSEIqun14")
