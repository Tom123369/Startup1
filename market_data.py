"""
STEP 5 – Market Data Collection
Fetches price data using yfinance (primary) with CoinGecko as fallback for obscure tokens.
"""

import logging
import requests
import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio

import yfinance as yf

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Map ticker symbols to CoinGecko coin IDs for the fallback
COINGECKO_ID_MAP = {
    "RIVER-USD": "river-protocol",
    "NEAR-USD": "near",
    "ICP-USD": "internet-computer",
    "DOT-USD": "polkadot",
    "AVAX-USD": "avalanche-2",
    "LINK-USD": "chainlink",
    "MATIC-USD": "matic-network",
    "ADA-USD": "cardano",
    "XRP-USD": "ripple",
    "DOGE-USD": "dogecoin",
    "BNB-USD": "binancecoin",
    "ATOM-USD": "cosmos",
    "LTC-USD": "litecoin",
    "SHIB-USD": "shiba-inu",
    "UNI-USD": "uniswap",
    "XLM-USD": "stellar",
    "FIL-USD": "filecoin",
    "AAVE-USD": "aave",
    "GRT-USD": "the-graph",
    "ALGO-USD": "algorand",
    "VET-USD": "vechain",
    "TRX-USD": "tron",
    "XMR-USD": "monero",
    "EOS-USD": "eos",
    "XTZ-USD": "tezos",
    "HBAR-USD": "hedera-hashgraph",
    "APT-USD": "aptos",
    "SUI-USD": "sui",
    "PEPE-USD": "pepe",
    "FLOKI-USD": "floki",
    "BCH-USD": "bitcoin-cash",
    "ETC-USD": "ethereum-classic",
    "BTC-USD": "bitcoin",
    "ETH-USD": "ethereum",
    "SOL-USD": "solana",
}

def _get_history_coingecko(ticker: str):
    """Fallback: fetch historical OHLC from CoinGecko for coins yfinance doesn't know."""
    coin_id = COINGECKO_ID_MAP.get(ticker)
    if not coin_id:
        # Try to derive a coin_id from the ticker (e.g. RIVER-USD -> river)
        coin_id = ticker.replace("-USD", "").lower()
    
    try:
        # Fetch 5 years of daily price data
        url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": "1825", "interval": "daily"}
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        prices = data.get("prices", [])
        if not prices:
            logger.warning(f"CoinGecko returned no price data for {coin_id}")
            return None
        
        # Build a pandas DataFrame matching yfinance format
        dates = [datetime.utcfromtimestamp(p[0] / 1000) for p in prices]
        closes = [p[1] for p in prices]
        
        df = pd.DataFrame({
            "Close": closes,
            "Open": closes,
            "High": closes,
            "Low": closes,
            "Volume": [0] * len(closes),
        }, index=pd.to_datetime(dates))
        
        logger.info(f"CoinGecko fallback successful for {ticker} ({coin_id}): {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"CoinGecko fallback failed for {ticker} ({coin_id}): {e}")
        return None

# Cache historical dataframes per symbol
_historical_caches = {}
_fetch_times = {}
CACHE_TTL = 3600  # 1 hour

def _get_history(symbol: str):
    global _historical_caches, _fetch_times
    now = datetime.now().timestamp()
    
    # Comprehensive Crypto/Asset Mapping
    ticker = symbol.upper().strip()
    
    CRYPTO_MAP = {
        # Bitcoin variants
        "BITCOIN": "BTC-USD", "BTC": "BTC-USD", "XBT": "BTC-USD",
        # Ethereum
        "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
        # Solana
        "SOLANA": "SOL-USD", "SOL": "SOL-USD",
        # Polkadot
        "POLKADOT": "DOT-USD", "DOT": "DOT-USD",
        # Internet Computer
        "INTERNET COMPUTER": "ICP-USD", "ICP": "ICP-USD",
        # NEAR Protocol
        "NEAR PROTOCOL": "NEAR-USD", "NEAR": "NEAR-USD",
        # Avalanche
        "AVALANCHE": "AVAX-USD", "AVAX": "AVAX-USD",
        # Chainlink
        "CHAINLINK": "LINK-USD", "LINK": "LINK-USD",
        # Polygon
        "POLYGON": "MATIC-USD", "MATIC": "MATIC-USD", "POL": "POL-USD",
        # Cardano
        "CARDANO": "ADA-USD", "ADA": "ADA-USD",
        # Ripple
        "RIPPLE": "XRP-USD", "XRP": "XRP-USD",
        # Dogecoin
        "DOGECOIN": "DOGE-USD", "DOGE": "DOGE-USD",
        # Binance Coin
        "BINANCE": "BNB-USD", "BNB": "BNB-USD",
        # Cosmos
        "COSMOS": "ATOM-USD", "ATOM": "ATOM-USD",
        # Litecoin
        "LITECOIN": "LTC-USD", "LTC": "LTC-USD",
        # Shiba Inu
        "SHIBA": "SHIB-USD", "SHIB": "SHIB-USD",
        # Uniswap
        "UNISWAP": "UNI-USD", "UNI": "UNI-USD",
        # Stellar
        "STELLAR": "XLM-USD", "XLM": "XLM-USD",
        # Filecoin
        "FILECOIN": "FIL-USD", "FIL": "FIL-USD",
        # Aave
        "AAVE": "AAVE-USD",
        # The Graph
        "THE GRAPH": "GRT-USD", "GRT": "GRT-USD",
        # Algorand
        "ALGORAND": "ALGO-USD", "ALGO": "ALGO-USD",
        # VeChain
        "VECHAIN": "VET-USD", "VET": "VET-USD",
        # Tron
        "TRON": "TRX-USD", "TRX": "TRX-USD",
        # Monero
        "MONERO": "XMR-USD", "XMR": "XMR-USD",
        # EOS
        "EOS": "EOS-USD",
        # Tezos
        "TEZOS": "XTZ-USD", "XTZ": "XTZ-USD",
        # Hedera
        "HEDERA": "HBAR-USD", "HBAR": "HBAR-USD",
        # Aptos
        "APTOS": "APT-USD", "APT": "APT-USD",
        # Sui
        "SUI": "SUI-USD",
        # Pepe
        "PEPE": "PEPE-USD",
        # Floki
        "FLOKI": "FLOKI-USD",
        # Bitcoin Cash
        "BITCOIN CASH": "BCH-USD", "BCH": "BCH-USD",
        # Ethereum Classic
        "ETHEREUM CLASSIC": "ETC-USD", "ETC": "ETC-USD",
        # River - no real yfinance ticker, skip
        "RIVER": None,
        # Stocks/Indices
        "OIL": "CL=F", "CRUDE": "CL=F",
        "GOLD": "GC=F",
        "SPY": "SPY", "S&P": "SPY", "S&P500": "SPY",
        "NDAQ": "QQQ", "NASDAQ": "QQQ",
    }
    
    if ticker in CRYPTO_MAP:
        mapped = CRYPTO_MAP[ticker]
        if mapped is None:
            return None  # Unknown coin, no data available
        ticker = mapped
    elif not ticker.endswith("-USD") and ticker not in ["CL=F", "GC=F", "SPY", "QQQ"]:
        # Generic: append -USD for anything we don't explicitly know
        ticker = ticker + "-USD"
    
    cached = _historical_caches.get(ticker)
    last_fetch = _fetch_times.get(ticker, 0)
    
    if cached is None or (now - last_fetch > CACHE_TTL):
        logger.info(f"Downloading {ticker} historical data via yfinance...")
        data = None
        try:
            data = yf.Ticker(ticker).history(period="5y")
            if data.empty:
                logger.warning(f"yfinance: no data for {ticker}, trying CoinGecko fallback...")
                data = None
        except Exception as e:
            logger.error(f"yfinance download error for {ticker}: {e}")
            data = None
        
        # CoinGecko fallback for coins yfinance doesn't cover
        if data is None:
            data = _get_history_coingecko(ticker)
        
        if data is None:
            logger.error(f"All data sources failed for {ticker}")
            return None
        
        _historical_caches[ticker] = data
        _fetch_times[ticker] = now
            
    return _historical_caches.get(ticker)

def get_current_price(symbol: str = "BTC-USD") -> Optional[float]:
    """Get the current price for a symbol."""
    try:
        hist = _get_history(symbol)
        if hist is not None and not hist.empty:
            return float(hist['Close'].iloc[-1])
    except Exception as e:
        logger.error(f"Failed to fetch current price for {symbol}: {e}")
    return None

def _estimate_days_ago(date_text: str) -> Optional[int]:
    """
    Estimate how many days ago a video was published from:
    - Relative text like "2 days ago", "3 weeks ago"
    - ISO date strings
    """
    if not date_text:
        return 7  # default fallback

    text = date_text.lower().strip()
    # Try ISO parse first
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            dt = datetime.strptime(text, fmt)
            if dt.tzinfo:
                 dt = dt.replace(tzinfo=None)
            delta = datetime.now() - dt
            return max(0, delta.days)
        except ValueError:
            continue

    import re
    m = re.search(r"(\d+)\s*(second|minute|hour|day|week|month|year)s?\s*ago", text)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        multipliers = {"second": 0,"minute": 0,"hour": 0,"day": 1,"week": 7,"month": 30,"year": 365}
        return max(0, num * multipliers.get(unit, 1))
    
    m = re.search(r"streamed\s+(\d+)\s*(day|week|month|year)s?\s*ago", text)
    if m:
        num = int(m.group(1))
        unit = m.group(2)
        multipliers = {"day": 1, "week": 7, "month": 30, "year": 365}
        return max(0, num * multipliers.get(unit, 1))

    return 7
def get_price_range_since(publish_date: str, symbol: str = "BTC-USD", timeframe: str = "short_term") -> dict:
    """Fetch entry price, and the high/low capped to the prediction's actual timeframe window."""
    # Determine window size based on timeframe
    tf_lower = timeframe.lower()
    if "very_short" in tf_lower or "ultra" in tf_lower:
        window_days = 7    # 1 week for very-short-term calls
    elif "long" in tf_lower:
        window_days = 180  # 6 months for long-term calls
    elif "mid" in tf_lower or "medium" in tf_lower:
        window_days = 30   # 1 month for medium-term
    else:
        window_days = 14   # 2 weeks for short-term (generous but bounded)
    
    result = {
        "price_at_video_time": None,
        "highest_price_after": None,
        "lowest_price_after": None,
        "current_price": None,
    }
    try:
        hist = _get_history(symbol)
        if hist is None or hist.empty:
            return result
            
        current = float(hist['Close'].iloc[-1])
        result["current_price"] = current
        
        import pandas as pd
        # S01: HIGH PRECISION DATE PARSE
        try:
            # First try direct parse (RSS/ISO)
            if not publish_date or str(publish_date).strip() == "":
                raise ValueError("Empty date")
            target_date = pd.to_datetime(publish_date).normalize()
            if pd.isna(target_date):
                raise ValueError("NaT result")
        except:
            # Fallback to smart relative estimation
            days_ago = _estimate_days_ago(publish_date)
            target_date = pd.to_datetime(datetime.now() - timedelta(days=days_ago)).normalize()

        # S02: TZ MATCHING
        if hist.index.tz:
            if target_date.tzinfo is None:
                target_date = target_date.tz_localize(hist.index.tz)
            else:
                target_date = target_date.tz_convert(hist.index.tz)
        
        # S03: EXACT INDEX MATCHING
        # Use searchsorted to find the earliest entry >= target_date in the index
        idx_pos = hist.index.searchsorted(target_date)
        
        logger.info(f"Price search for {symbol} on {target_date}: idx_pos={idx_pos}, hist_len={len(hist)}")
        
        if idx_pos < len(hist):
            # We use the Open of the day found (the first available trading candle after publication)
            entry_price = float(hist['Open'].iloc[idx_pos])
            result["price_at_video_time"] = entry_price
            
            # Cap subset to timeframe window — critical for fair short-term evaluation
            end_pos = min(idx_pos + window_days, len(hist))
            subset = hist.iloc[idx_pos:end_pos]
            result["highest_price_after"] = float(subset['High'].max())
            result["lowest_price_after"] = float(subset['Low'].min())
            
            # Backwards compatibility for evaluator
            result["highest_future"] = result["highest_price_after"]
            result["lowest_future"] = result["lowest_price_after"]
        else:
            # Prediction too new? Use latest
            logger.warning(f"Date {target_date} for {symbol} is beyond history (idx_pos {idx_pos} >= {len(hist)}). Using latest.")
            val = float(hist['Open'].iloc[-1])
            result["price_at_video_time"] = val
            result["highest_price_after"] = float(hist['High'].iloc[-1])
            result["lowest_price_after"] = float(hist['Low'].iloc[-1])
                
    except Exception as e:
        logger.error(f"yfinance range error for {publish_date} on {symbol}: {e}")
        
    return result


async def get_batch_price_ranges_async(videos: list, market_type: str = "bitcoin") -> Dict[str, Dict]:
    # Strategy 3: Global Fetch for the main symbol to avoid per-video calls
    base_symbol = "BTC-USD" if market_type == "bitcoin" else "SPY"
    
    # Pre-fetch the main history once to ensure it's in cache
    _get_history(base_symbol)
    
    results = {}
    for v in videos:
        vid = v.get("video_id", "")
        pub = v.get("publish_date", "")
        asset = str(v.get("asset") or v.get("coin") or base_symbol).upper()
        
        logger.info(f"Processing Market Data: VID={vid} PUB={pub} ASSET={asset}")
        
        # Mapping common names to tickers
        if asset in ["BITCOIN", "BTC"]: asset = "BTC-USD"
        if asset in ["ETHEREUM", "ETH"]: asset = "ETH-USD"
        if asset in ["SOLANA", "SOL"]: asset = "SOL-USD"
        
        # S02: Robust Currency Differentiator
        if market_type == "bitcoin":
            # If it's a known crypto but missing -USD, append it
            if asset in ["OIL", "SPY", "NDAQ", "CL=F", "GOLD", "GC=F"]:
                pass # Leave as is
            elif not asset.endswith("-USD") and asset in ["BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "LINK", "MATIC"]:
                asset += "-USD"
            elif not asset.endswith("-USD") and len(asset) <= 10: # Likely a crypto ticker
                asset += "-USD"

        # Pass timeframe so price range is capped correctly per prediction type
        timeframe = str(v.get("timeframe") or "short_term")
        key = f"{vid}_{asset}"
        results[key] = get_price_range_since(pub, asset, timeframe=timeframe)
        
    return results

def get_batch_price_ranges(videos: list, market_type: str = "bitcoin") -> Dict[str, Dict]:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return {} 
        return asyncio.run(get_batch_price_ranges_async(videos, market_type))
    except Exception:
        return {}
# Aggressive cache purge on load to ensure stale ETF data is gone
_historical_caches.clear()
_fetch_times.clear()
logger.info("Market Data module loaded - Cache Purged")
