import httpx
import json
import re

def get_transcript_via_html(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }
    
    try:
        resp = httpx.get(url, headers=headers, timeout=10)
        # Search for ytInitialPlayerResponse
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', resp.text)
        if not match:
            # Try without the semicolon
            match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*<', resp.text)
            
        if match:
            data = json.loads(match.group(1))
            captions = data.get('captions', {}).get('playerCaptionsTracklistRenderer', {}).get('captionTracks', [])
            if captions:
                print(f"SUCCESS: Found {len(captions)} tracks")
                track_url = captions[0]['baseUrl']
                xml_resp = httpx.get(track_url, headers=headers)
                print("XML Status:", xml_resp.status_code)
                if xml_resp.status_code == 200:
                    print("Transcript Sample:", xml_resp.text[:100])
                    return xml_resp.text
            else:
                print("No caption tracks in player response.")
        else:
            print("Could not find ytInitialPlayerResponse.")
            
    except Exception as e:
        print("Error:", e)
    return None

if __name__ == "__main__":
    get_transcript_via_html("AjrSEIqun14")
