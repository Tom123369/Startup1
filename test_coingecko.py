import asyncio
import logging
from market_data import get_batch_price_ranges_async

logging.basicConfig(level=logging.INFO)

async def test():
    videos = [
        {"video_id": f"vid{i}", "publish_date": f"{i} days ago"} for i in range(1, 40)
    ]
    res = await get_batch_price_ranges_async(videos)
    print("Fetched", len([v for v in res.values() if v.get("price_at_video_time")]))

if __name__ == "__main__":
    asyncio.run(test())
