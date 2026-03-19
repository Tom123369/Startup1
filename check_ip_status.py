from youtube_transcript_api import YouTubeTranscriptApi

vids = ["QvD-6F4rXWc", "G7zF1q3S-vI", "9id7-vK-D7Q"]

print("--- Testing Transcript API directly ---")
for vid in vids:
    try:
        print(f"Testing {vid}...", end=" ", flush=True)
        # Correct usage is get_transcript
        transcript = YouTubeTranscriptApi.get_transcript(vid)
        print(f"SUCCESS! Got {len(transcript)} segments")
    except Exception as e:
        msg = str(e)
        if "429" in msg or "too many requests" in msg.lower():
            print(f"BLOCKED (IP Blocked / 429)")
        elif "TranscriptsDisabled" in msg:
            print(f"FAILED (Transcripts disabled)")
        else:
            print(f"FAILED: {msg[:100]}...")
