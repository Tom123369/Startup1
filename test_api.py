import requests
import json

resp = requests.post("http://localhost:8000/api/analyze", json={
    "channel_url": "@DiscoverCrypto_",
    "max_videos": 1,
    "market": "bitcoin"
})

with open('debug_json.json', 'w') as f:
    json.dump(resp.json(), f, indent=2)
print("Saved to debug_json.json")
