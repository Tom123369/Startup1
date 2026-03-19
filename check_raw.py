himport logging
from youtube_transcript_api import YouTubeTranscriptApi

def check_raw_api():
    vid = "QvD-6F4rXWc"
    print(f"Checking {vid}...")
    try:
        # This is how it's used in and documented for some versions
        from youtube_transcript_api import YouTubeTranscriptApi
        res = YouTubeTranscriptApi.get_transcript(vid)
        print("SUCCESS")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    check_raw_api()
