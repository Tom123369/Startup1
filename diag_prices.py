from market_data import get_price_range_since
import logging
logging.basicConfig(level=logging.INFO)
def test():
    dates = ["2026-03-19", "2026-03-15", "2026-03-10", "2026-02-15"]
    for d in dates:
        print(f"\n--- Testing Date: {d} ---")
        res = get_price_range_since(d, "BTC-USD")
        print(f"Entry Price: {res.get('price_at_video_time')}")
        print(f"Current Price: {res.get('current_price')}")
if __name__ == "__main__":
    test()
