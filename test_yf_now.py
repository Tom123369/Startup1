import yfinance as yf
from datetime import datetime
def test():
    tickers = ["BTC-USD", "BTC", "BTCS"]
    for t in tickers:
        print(f"\n--- Ticker: {t} ---")
        try:
            data = yf.Ticker(t).history(period="5d")
            if data.empty:
                print("No data found")
            else:
                print("Last Close:", data['Close'].iloc[-1])
                print("Open at:", data['Open'].iloc[0])
        except Exception as e:
            print(f"Error: {e}")
if __name__ == "__main__":
    test()
