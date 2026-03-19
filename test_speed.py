"""Speed test: 100 videos, fresh cache."""
import asyncio
import sys
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)

from pipeline import run_pipeline


async def test():
    print("=" * 60)
    print("SPEED TEST: 100 videos from @CryptoWorldJosh (FRESH)")
    print("=" * 60)

    start = time.time()
    result = await run_pipeline(
        "https://www.youtube.com/@CryptoWorldJosh", max_videos=100
    )
    total = time.time() - start

    print("\n" + "=" * 60)
    print(f"RESULT: {total:.1f} seconds total")
    print(f"  Videos analyzed:   {result['videos_analyzed']}")
    print(f"  Predictions found: {result['predictions_found']}")
    print(f"  Correct:           {result['correct']}")
    print(f"  Wrong:             {result['wrong']}")
    print(f"  Ongoing:           {result['ongoing']}")
    print(f"  Accuracy:          {result['accuracy_percentage']}%")

    if result.get("error"):
        print(f"  ERROR: {result['error']}")

    for i, p in enumerate(result["predictions"][:10]):
        title = p.get("video_title", "")[:40]
        print(f"  {i+1}. {p['prediction']:>15} | {p['status']:>7} | {title}")

    print("=" * 60)
    if total < 30:
        print(f"PASS - Under 30s target ({total:.1f}s)")
    elif total < 60:
        print(f"CLOSE - Under 60s ({total:.1f}s)")
    else:
        print(f"NEEDS WORK - Over 60s ({total:.1f}s)")


if __name__ == "__main__":
    asyncio.run(test())
