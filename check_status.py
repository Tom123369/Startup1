import httpx
from youtube_transcript_api import YouTubeTranscriptApi

def check():
    api = YouTubeTranscriptApi()
    try:
        # Fetching a tiny transcript to check status
        api.fetch("AjrSEIqun14")
        print("STATUS: UNBLOCKED")
    except Exception as e:
        print(f"STATUS: STILL_BLOCKED ({type(e).__name__})")

if __name__ == "__main__":
    check()
