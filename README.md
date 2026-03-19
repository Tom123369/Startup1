# BTC Prediction Analyzer

A production-ready Python web application that analyzes Bitcoin price predictions made by YouTube influencers and evaluates their accuracy using real market data.

## Features

- ⚡ **Fast** – Analyzes 100 videos in under 30 seconds
- 🎯 **Accurate** – Uses real CoinGecko market data for deterministic evaluation
- 🤖 **AI-Powered** – Extracts predictions using OpenRouter LLMs
- 📊 **Premium Dashboard** – Real-time WebSocket progress tracking
- 🔄 **Cached** – Predictions cached to avoid re-processing

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  YouTube    │────▶│  Transcripts │────▶│  Filter (90%+  │
│  Scrapetube │     │  YT API /    │     │  token saving)  │
│  (100 vids) │     │  Whisper     │     │                │
└─────────────┘     └──────────────┘     └────────┬───────┘
                                                   │
┌─────────────┐     ┌──────────────┐     ┌────────▼───────┐
│  Dashboard  │◀────│  Evaluator   │◀────│  OpenRouter AI │
│  (FastAPI)  │     │  (CORRECT /  │     │  (Batch × 5)   │
│             │     │  WRONG /     │     │                │
│             │     │  ONGOING)    │     └────────────────┘
└─────────────┘     └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │  CoinGecko   │
                    │  Market Data │
                    └──────────────┘
```

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API key** in `.env`:
   ```env
   OPENROUTER_API_KEY=sk-or-v1-your-key-here
   OPENROUTER_MODEL=z-ai/glm-4.5-air
   ```

3. **Run the server:**
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port 8000
   ```

4. **Open the dashboard** at `http://localhost:8000`

## Project Structure

```
├── app.py                  # FastAPI server (REST + WebSocket)
├── pipeline.py             # Orchestrator (coordinates all steps)
├── video_collector.py      # Step 1: YouTube video collection
├── transcript_extractor.py # Step 2: Transcript extraction
├── transcript_filter.py    # Step 3: Smart filtering (90%+ reduction)
├── ai_extractor.py         # Step 4: AI prediction extraction
├── market_data.py          # Step 5: CoinGecko market data
├── evaluator.py            # Step 6: Deterministic evaluation
├── config.py               # Configuration & constants
├── static/
│   └── index.html          # Frontend dashboard
├── cache/                  # Prediction cache (auto-created)
├── requirements.txt
├── .env
└── README.md
```

## Evaluation Logic

- **CORRECT**: Target price was reached (UP: highest ≥ target, DOWN: lowest ≤ target)
- **WRONG**: Price moved 3.5%+ against the prediction direction
- **ONGOING**: Target not yet reached, price hasn't moved significantly against prediction

## Performance

- ThreadPoolExecutor (10 workers) for parallel transcript fetching
- Async AI batch requests (5 videos per batch, 3 concurrent)
- Transcript filtering reduces AI token usage by 90%+
- File-based prediction caching (same video never analyzed twice)
- CoinGecko data cached & grouped by publish date
