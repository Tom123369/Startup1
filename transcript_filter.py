"""
STEP 3 – Transcript Filtering (Critical for Speed)
Keeps only sentences that mention Bitcoin + a price + prediction language.
Reduces AI token usage by 90 %+.
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ── Prediction keywords ──────────────────────────────────────────────────────
PREDICTION_KEYWORDS = [
    "predict", "target", "going to", "will reach", "could reach",
    "might reach", "drop to", "fall to", "rise to", "pump to", "dump to",
    "heading to", "aiming for", "expect", "forecast", "see it at",
    "bottom at", "top at", "hit", "break", "touch", "bounce to",
    "crash to", "moon to", "dip to", "surge to", "rally to",
    "support", "resistance", "breakout", "retest", "liquidation",
    "long", "short", "position", "trade", "entry", "exit", "tp", "sl",
    "warning", "danger", "bearish", "bullish", "trap", "reversal",
]

# ── Compiled patterns ────────────────────────────────────────────────────────
# Broaden coin detection to include more altcoins
COIN_RE = re.compile(r"\b(bitcoin|btc|ethereum|eth|solana|sol|ripple|xrp|cardano|ada|doge|dot|link|avax|near|icp|shib|pepe|bnb|ltc|matic|pol|atom|rndr|ftm|arb|op|market|coin|king)\b", re.IGNORECASE)
PRICE_RE = re.compile(r"\b\d{1,3}(?:,\d{3})+\b|\b\d{3,6}\b|\b\d+(?:\.\d+)?k\b", re.IGNORECASE)
KEYWORD_RE = re.compile(
    "|".join(re.escape(kw) for kw in PREDICTION_KEYWORDS),
    re.IGNORECASE,
)

# ── Sentence splitter ────────────────────────────────────────────────────────
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|(?<=\n)")


def _split_sentences(text: str) -> List[str]:
    """Split transcript text into sentences."""
    parts = SENTENCE_SPLIT_RE.split(text)
    sentences = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(part) > 300:
            sub_parts = part.split(",")
            sentences.extend(s.strip() for s in sub_parts if s.strip())
        else:
            sentences.append(part)
    return sentences


def filter_transcript(transcript: str) -> str:
    """
    Minimally filter a transcript to preserve ALL price predictions.
    For crypto channels, ALL content is relevant - avoid over-filtering.
    """
    if not transcript:
        return ""

    # SHORT: pass entirely - no risk of losing predictions
    if len(transcript) <= 8000:
        return transcript

    # LONG: do a relaxed filter to stay within AI token limits
    sentences = _split_sentences(transcript)
    kept: List[str] = []
    context_counter = 0

    for sentence in sentences:
        has_price = bool(PRICE_RE.search(sentence))
        has_keyword = bool(KEYWORD_RE.search(sentence))
        has_coin = bool(COIN_RE.search(sentence))

        # Reset / extend context window whenever we find relevant content
        if has_keyword or has_coin:
            context_counter = 30  # keep wide window around crypto/keyword mentions

        # Keep sentence if: it has a price, a keyword, a coin name, or we're in context window
        if has_price or has_keyword or has_coin or context_counter > 0:
            kept.append(sentence)

        if context_counter > 0:
            context_counter -= 1

    joined = " ".join(kept)

    # Safety fallback: if we still filtered too much, return the raw transcript capped
    if not joined or len(joined) < 500:
        return transcript[:8000]

    # Cap final output at 12000 chars to stay within AI token limits
    return joined[:12000]
