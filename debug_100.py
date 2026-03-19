import asyncio
from pipeline import run_pipeline

async def main():
    result = await run_pipeline(
        channel_url="https://www.youtube.com/@CryptoWorldJosh",
        max_videos=100
    )
    print(f"Videos Analyzed: {result['videos_analyzed']}")
    print(f"Predictions Found: {result['predictions_found']}")

asyncio.run(main())
