from youtubesearchpython import Transcript

def check_search_python(video_id):
    try:
        data = Transcript.get(video_id)
        if data and 'segments' in data:
            print("SUCCESS: Search-Python worked!")
            print("Segments count:", len(data['segments']))
        else:
            print("FAILED: Search-Python returned empty or invalid structure")
    except Exception as e:
        print(f"FAILED: Search-Python error: {type(e).__name__} - {str(e)}")

if __name__ == "__main__":
    check_search_python("AjrSEIqun14")
