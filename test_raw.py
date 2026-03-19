import httpx
import re

url = "https://www.youtube.com/@TheMoonCarl"
resp = httpx.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}, timeout=10)
print("Status Code:", resp.status_code)

match = re.search(r'"channelId":"(UC[^"]+)"', resp.text)
if match:
    print("Found ID:", match.group(1))
else:
    print("Could not find UC id.")
