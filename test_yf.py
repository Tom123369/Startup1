import yfinance as yf
from datetime import datetime, timedelta

def test_yfinance():
    # Cache historical data for the last 5 years
    hist = yf.Ticker("BTC-USD").history(period="5y")
    print(f"Downloaded {len(hist)} days of BTC data")
    
    current_price = hist['Close'].iloc[-1]
    print(f"Current price: {current_price}")
    
    # 30 days ago
    date = datetime.now() - timedelta(days=30)
    # Get all prices from that date onward
    mask = hist.index >= date.strftime('%Y-%m-%d')
    subset = hist.loc[mask]
    
    if not subset.empty:
        price_at_video = subset['Close'].iloc[0]
        high = subset['High'].max()
        low = subset['Low'].min()
        print(f"30 days ago: price={price_at_video}, high={high}, low={low}")

if __name__ == "__main__":
    test_yfinance()
