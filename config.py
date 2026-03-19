"""
Configuration module – loads environment variables and defines constants.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── AI Provider Configuration ────────────────────────────────────────────────
AI_PROVIDER = os.getenv("AI_PROVIDER", "openrouter").lower()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "z-ai/glm-4.5-air:free")

BYTEZ_API_KEY = os.getenv("BYTEZ_API_KEY", "")
BYTEZ_MODEL = os.getenv("BYTEZ_MODEL", "openai/gpt-4o")

CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.getenv("CEREBRAS_MODEL", "llama3.1-8b")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

if AI_PROVIDER == "bytez":
    ACTIVE_AI_KEY = BYTEZ_API_KEY
    ACTIVE_AI_MODEL = BYTEZ_MODEL
    ACTIVE_AI_BASE_URL = "https://api.bytez.com/models/v2/openai/v1/chat/completions"
elif AI_PROVIDER == "cerebras":
    ACTIVE_AI_KEY = CEREBRAS_API_KEY
    ACTIVE_AI_MODEL = CEREBRAS_MODEL
    ACTIVE_AI_BASE_URL = "https://api.cerebras.ai/v1/chat/completions"
elif AI_PROVIDER == "groq":
    ACTIVE_AI_KEY = GROQ_API_KEY
    ACTIVE_AI_MODEL = GROQ_MODEL
    ACTIVE_AI_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
else:
    ACTIVE_AI_KEY = OPENROUTER_API_KEY
    ACTIVE_AI_MODEL = OPENROUTER_MODEL
    ACTIVE_AI_BASE_URL = "https://openrouter.ai/api/v1/chat/completions"

# ── Processing ────────────────────────────────────────────────────────────────
MAX_VIDEOS = 100
MAX_WORKERS = 10
AI_BATCH_SIZE = 4            # Smaller batches for higher accuracy and reliability
MAX_RETRIES = 5
RETRY_BASE_DELAY = 1.0       # Fast retry base

# ── Transcript ────────────────────────────────────────────────────────────────
TRANSCRIPT_HEAD_SECONDS = 300   # first 5 minutes
TRANSCRIPT_TAIL_SECONDS = 300   # last 5 minutes
TRANSCRIPT_CONCURRENCY = 3      # max concurrent transcript requests
TRANSCRIPT_DELAY_MIN = 0.15     # randomization min delay
TRANSCRIPT_DELAY_MAX = 0.35     # randomization max delay
TRANSCRIPT_CACHE_DIR = "cache/transcripts"
TRANSCRIPT_MAX_RETRIES = 5

# ── Evaluation thresholds ─────────────────────────────────────────────────────
WRONG_MARGIN = 0.035            # 3.5 %

# ── CoinGecko ─────────────────────────────────────────────────────────────────
COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# ── Resend Configuration ──────────────────────────────────────────────────────
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
