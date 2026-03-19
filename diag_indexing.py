from market_data import _get_history
import pandas as pd
from datetime import datetime
def test():
    symbol = "BTC-USD"
    hist = _get_history(symbol)
    print(f"Ticker: {symbol}")
    print(f"Dataframe rows: {len(hist)}")
    print(f"Last date in index: {hist.index[-1]}")
    print(f"First date in index: {hist.index[0]}")
    
    dates = ["2026-03-19", "2026-03-15", "2026-03-10", "2026-02-15"]
    for d in dates:
        target = pd.to_datetime(d).normalize()
        if hist.index.tz: target = target.tz_localize(hist.index.tz)
        
        idx = hist.index.searchsorted(target)
        print(f"\nDate: {d} | Search Target: {target}")
        print(f"Searchsorted index: {idx}")
        if idx < len(hist):
            print(f"Matched Date: {hist.index[idx]}")
            print(f"Open: {hist['Open'].iloc[idx]}")
        else:
            print("OUT OF BOUNDS (using latest)")
            print(f"Latest Open: {hist['Open'].iloc[-1]}")

if __name__ == "__main__":
    test()
