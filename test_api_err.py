import urllib.request, urllib.error, json, os

key = open('.env').read().split('OPENROUTER_API_KEY=')[1].split('\n')[0].strip()
headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
req = urllib.request.Request(
    'https://openrouter.ai/api/v1/chat/completions',
    data=json.dumps({'model': 'google/gemini-2.0-flash-lite-preview-02-05:free', 'messages': [{'role':'user','content':'hi'}]}).encode(),
    headers=headers
)

try:
    resp = urllib.request.urlopen(req)
    print("SUCCESS", resp.read())
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print("BODY:", e.read().decode())
