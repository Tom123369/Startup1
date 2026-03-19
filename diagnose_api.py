from youtube_transcript_api import YouTubeTranscriptApi

def test_api():
    print("Testing YouTubeTranscriptApi.fetch('AjrSEIqun14')...")
    api = YouTubeTranscriptApi()
    try:
        data = api.fetch('AjrSEIqun14')
        print("✅ SUCCESS! Transcript fetched.")
        print("First 100 chars:", str(data)[:100])
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}")
        print(f"Details: {str(e)}")

if __name__ == "__main__":
    test_api()
