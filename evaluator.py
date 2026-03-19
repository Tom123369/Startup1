"""
STEP 6 – Price Action Evaluation
Deterministic Python logic to evaluate predictions as CORRECT, WRONG, or ONGOING.
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

def evaluate_prediction(prediction: Dict, market_data: Dict) -> Dict:
    """
    Evaluate based on PURE DIRECTIONAL STRATEGY.
    Ignore price targets. Use a 3% goal threshold.
    """
    price_at = market_data.get("price_at_video_time")
    highest = market_data.get("highest_price_after")
    lowest = market_data.get("lowest_price_after")
    current = market_data.get("current_price")
    
    # ───── STRATEGY SETUP ─────
    GOAL_PCT = 0.01 # 1% directional move counts as a WIN
    STOP_PCT = 0.05 # 5% move against counts as a LOSS (Short term)
    
    price_at_f = float(price_at) if price_at else 0.0
    high_f = float(highest) if highest else 0.0
    low_f = float(lowest) if lowest else 0.0
    curr_f = float(current) if current else 0.0
    
    direction = str(prediction.get("direction", "UP")).upper()
    if direction not in ["UP", "DOWN"]:
        direction = "UP"
        
    # Auto-correct direction if target price contradicts it
    target = float(prediction.get("target_price") or 0.0)
    if target > 0 and price_at_f > 0:
        if target > price_at_f and direction == "DOWN":
            direction = "UP"
            prediction["direction"] = direction
        elif target < price_at_f and direction == "UP":
            direction = "DOWN"
            prediction["direction"] = direction

    if price_at_f == 0:
        # No market data could be fetched for this coin — mark as unevaluable rather than fake ONGOING
        return {**prediction, "status": "N/A", "price_at_prediction": price_at, "highest_after": highest, "lowest_after": lowest, "current_price": current}

    status = "ONGOING"
    tf = str(prediction.get("timeframe", "short_term")).lower()
    
    # Precise days limit matching for evaluation maturity
    if "very_short" in tf or "ultra" in tf:
        days_limit = 7   # 1-7 days for ultra-short flips
    elif "long" in tf:
        days_limit = 180 # 6 months for long term
    elif "mid" in tf or "medium" in tf:
        days_limit = 30  # 1 month for medium
    else:
        days_limit = 14  # 2 weeks for standard short term calls
    
    try:
        pub_date = prediction.get("publish_date")
        days_since = 0
        if pub_date:
            try:
                dt = datetime.strptime(pub_date, "%Y-%m-%d")
                days_since = (datetime.now() - dt).days
            except: pass

        if direction == "UP":
            # Check if it hit the +1% goal (sensitive to fast touches)
            if high_f >= price_at_f * (1 + GOAL_PCT):
                status = "CORRECT"
            # Check if it hit the stop loss
            elif low_f <= price_at_f * (1 - (0.2 if "long" in tf else STOP_PCT)):
                status = "WRONG"
            # If timeframe passed, final check
            elif days_since >= days_limit:
                status = "CORRECT" if curr_f > price_at_f else "WRONG"
        else: # DOWN direction
            # Check if it hit the -1% goal
            if low_f <= price_at_f * (1 - GOAL_PCT):
                status = "CORRECT"
            # Check if it hit the stop loss (20% for long-term)
            elif high_f >= price_at_f * (1 + (0.2 if "long" in tf else STOP_PCT)):
                status = "WRONG"
            # If timeframe passed, final check
            elif days_since >= days_limit:
                status = "CORRECT" if curr_f < price_at_f else "WRONG"
    except Exception as e:
        logger.error(f"Eval error: {e}")
        status = "ONGOING"

    return {
        **prediction,
        "direction": direction,
        "price_at_prediction": price_at,
        "highest_after": highest,
        "lowest_after": lowest,
        "current_price": current,
        "status": status,
    }

def evaluate_all_predictions(predictions: List[Dict], market_data_map: Dict[str, Dict]) -> Dict:
    evaluated = []
    correct = 0
    wrong = 0
    ongoing = 0

    for pred in predictions:
        vid = pred.get("video_id", "")
        asset = str(pred.get("asset") or pred.get("coin") or "BTC").upper()
        # Robust asset-ticker conversion to match market_data.py
        CRYPTO_MAP = {
            "BITCOIN": "BTC-USD", "BTC": "BTC-USD", "XBT": "BTC-USD",
            "ETHEREUM": "ETH-USD", "ETH": "ETH-USD",
            "SOLANA": "SOL-USD", "SOL": "SOL-USD",
            "POLKADOT": "DOT-USD", "DOT": "DOT-USD",
            "INTERNET COMPUTER": "ICP-USD", "ICP": "ICP-USD",
            "NEAR PROTOCOL": "NEAR-USD", "NEAR": "NEAR-USD",
            "AVALANCHE": "AVAX-USD", "AVAX": "AVAX-USD",
            "CHAINLINK": "LINK-USD", "LINK": "LINK-USD",
            "POLYGON": "MATIC-USD", "MATIC": "MATIC-USD",
            "CARDANO": "ADA-USD", "ADA": "ADA-USD",
            "RIPPLE": "XRP-USD", "XRP": "XRP-USD",
            "DOGECOIN": "DOGE-USD", "DOGE": "DOGE-USD",
            "BINANCE": "BNB-USD", "BNB": "BNB-USD",
            "COSMOS": "ATOM-USD", "ATOM": "ATOM-USD",
            "LITECOIN": "LTC-USD", "LTC": "LTC-USD",
            "SHIB": "SHIB-USD", "AAVE": "AAVE-USD",
            "UNISWAP": "UNI-USD", "UNI": "UNI-USD",
            "STELLAR": "XLM-USD", "XLM": "XLM-USD",
            "OIL": "CL=F", "CRUDE": "CL=F",
            "GOLD": "GC=F",
            "SPY": "SPY", "S&P": "SPY", "S&P500": "SPY",
            "NDAQ": "QQQ", "NASDAQ": "QQQ",
        }
        if asset in CRYPTO_MAP:
            asset = CRYPTO_MAP[asset]
        elif asset not in ["CL=F", "GC=F", "SPY", "QQQ"] and not asset.endswith("-USD"):
            asset += "-USD"
        
        key = f"{vid}_{asset}"
        mdata = market_data_map.get(key, {})
        result = evaluate_prediction(pred, mdata)
        evaluated.append(result)

        s = result["status"]
        if s == "CORRECT": correct += 1
        elif s == "WRONG": wrong += 1
        else: ongoing += 1

    decided = correct + wrong
    accuracy = round((correct / decided * 100), 1) if decided > 0 else 0.0

    return {
        "videos_analyzed": 0,
        "predictions_found": len(evaluated),
        "correct": correct,
        "wrong": wrong,
        "ongoing": ongoing,
        "accuracy_percentage": accuracy,
        "predictions": evaluated,
    }
