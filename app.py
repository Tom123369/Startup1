"""
FastAPI Application – BTC Prediction Analyzer
Serves the API endpoints and the frontend dashboard.
"""

import asyncio
import logging
import json
import random
import time
from pathlib import Path
from typing import Optional, Dict

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from pipeline import run_pipeline
from config import MAX_VIDEOS, RESEND_API_KEY, RESEND_FROM_EMAIL
from ai_extractor import resolve_youtuber_name
from firebase_utils import get_firestore_db

# Initialize Persistent Storage (Cloud persistence for Render)
get_firestore_db()


# Temporary in-memory storage for codes (In production, use Redis)
verification_codes: Dict[str, dict] = {}

class VerificationRequest(BaseModel):
    email: str

class VerificationVerify(BaseModel):
    email: str
    code: str

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="BTC Prediction Analyzer",
    description="Analyze Bitcoin predictions from YouTube influencers",
    version="1.0.0",
)

# Serve static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

def get_dashboard_html():
    """Read the dashboard HTML from disk. No cache to ensure updates are reflected."""
    html_path = Path(__file__).parent / "static" / "index.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf-8")
    return None



# ── Request / Response models ─────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    channel_url: str
    max_videos: int = MAX_VIDEOS
    market: str = "bitcoin"


class SearchChannelRequest(BaseModel):
    query: str


class AnalyzeResponse(BaseModel):
    videos_analyzed: int
    predictions_found: int
    correct: int
    wrong: int
    ongoing: int
    accuracy_percentage: float
    processing_time: float = 0
    predictions: list
    error: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the frontend dashboard."""
    content = get_dashboard_html()
    if content:
        return HTMLResponse(
            content=content, 
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
        )
    return HTMLResponse(content="<h1>Dashboard not found</h1>", status_code=404)


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_channel(request: AnalyzeRequest):
    """
    Analyze a YouTube channel for Bitcoin predictions.
    This is the main REST endpoint.
    """
    if not request.channel_url.strip():
        raise HTTPException(status_code=400, detail="Channel URL is required")

    try:
        # TEMPORARY FAST TRACK FOR USER DEMO
        url_lower = request.channel_url.lower()
        if "cryptogyan8280" in url_lower or "cryptoworldjosh" in url_lower:
            from pathlib import Path
            safe_name = "cryptogyan8280" if "cryptogyan" in url_lower else "CryptoWorldJosh"
            results_dir = Path("results") / safe_name
            if results_dir.exists():
                files = sorted(results_dir.glob("evaluation_*.json"), key=os.path.getmtime, reverse=True)
                if files:
                    with open(files[0], "r", encoding="utf-8") as f:
                        result = json.load(f)
                        return result

        result = await run_pipeline(
            channel_url=request.channel_url.strip(),
            max_videos=request.max_videos,
            market_type=request.market,
        )

        return AnalyzeResponse(**result)
    except Exception as e:
        logger.exception(f"Pipeline error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search-channel")
async def search_channel(request: SearchChannelRequest):
    """
    Search for a YouTube channel by name.
    """
    query = request.query.strip()
    if not query:
        return {"results": []}

    try:
        resolved_name = await resolve_youtuber_name(query)
        logger.info(f"AI resolved '{query}' to '{resolved_name}'")

        def _search(search_query):
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'extract_flat': True,
                'force_generic_extractor': False,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch5:{search_query}", download=False)
                results = []
                seen_channels = set()
                if 'entries' in info:
                    for entry in info['entries']:
                        chan_id = entry.get('channel_id')
                        chan_name = entry.get('uploader')
                        chan_url = entry.get('channel_url') or (f"https://www.youtube.com/channel/{chan_id}" if chan_id else None)
                        
                        if chan_url and chan_url not in seen_channels:
                            results.append({
                                "name": chan_name or search_query,
                                "url": chan_url,
                                "id": chan_id
                            })
                            seen_channels.add(chan_url)
                return results

        results = await asyncio.to_thread(_search, resolved_name)
        if not results and resolved_name != query:
            results = await asyncio.to_thread(_search, query)
            
        return {"results": results, "resolved_as": resolved_name}
    except Exception as e:
        logger.exception(f"Search error: {e}")
        return {"results": [], "error": str(e)}


@app.websocket("/ws/analyze")
async def analyze_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time progress updates.
    """
    await websocket.accept()

    try:
        data = await websocket.receive_json()
        channel_url = data.get("channel_url", "")
        max_videos = data.get("max_videos", MAX_VIDEOS)
        market = data.get("market", "bitcoin")

        if not channel_url:
            await websocket.send_json({"error": "Channel URL is required"})
            await websocket.close()
            return

        async def progress_callback(stage: str, detail: str):
            try:
                await websocket.send_json({
                    "type": "progress",
                    "stage": stage,
                    "detail": detail,
                })
            except Exception:
                pass

        result = await run_pipeline(
            channel_url=channel_url,
            max_videos=max_videos,
            market_type=market,
            progress_callback=progress_callback,
        )

        await websocket.send_json({"type": "result", "data": result})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"type": "error", "detail": str(e)})
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "Reloaded", "service": "btc-prediction-analyzer"}

@app.post("/api/auth/send-code")
async def send_verification_code(req: VerificationRequest):
    """
    Generate a verification code and send it via Resend.
    """
    email = req.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    
    code = f"{random.randint(100000, 999999)}"
    verification_codes[email] = {
        "code": code,
        "expires_at": time.time() + 600 # 10 minutes
    }
    
    # CLEAR LOGGING FOR DEVELOPMENT
    logger.info(f"VERIFICATION_CODE_FOR_{email}: {code}")
    
    if not RESEND_API_KEY:
        logger.warning(f"No Resend API Key found. Use code in logs: {code}")
        # during development, we return success so the developer can just check logs
        return {"message": "Development mode: Code logged to terminal", "dev": True}

    # Send email via Resend
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {RESEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": f"PredictIQ <{RESEND_FROM_EMAIL}>",
                    "to": [email],
                    "subject": "Your Verification Code - PredictIQ",
                    "html": f"""
                        <div style="font-family: 'Inter', sans-serif; padding: 40px; background: #12131a; color: #e8eaf0; border-radius: 20px; border: 1px solid #2a2d3e;">
                            <h1 style="color: #f7931a; margin-bottom: 24px;">Verification Code</h1>
                            <p style="font-size: 16px; margin-bottom: 32px;">Please use the following code to complete your login or registration at PredictIQ:</p>
                            <div style="background: rgba(247, 147, 26, 0.1); border: 1.5px solid #f7931a; padding: 20px; text-align: center; border-radius: 12px; margin-bottom: 32px;">
                                <span style="font-size: 32px; font-weight: 800; letter-spacing: 8px; color: #f7931a;">{code}</span>
                            </div>
                            <p style="font-size: 14px; color: #8b8fa4;">This code will expire in 10 minutes. If you did not request this code, you can ignore this email.</p>
                            <div style="text-align: center; margin-top: 20px;">
                                <a href="https://startup1-4.onrender.com/" style="color: #f7931a; text-decoration: none; font-size: 14px; font-weight: 600;">← Return to PredictIQ</a>
                            </div>
                            <hr style="border: 0; border-top: 1px solid #2a2d3e; margin: 32px 0;">
                            <p style="font-size: 12px; color: #5c6078; text-align: center;">© 2025 PredictIQ. AI-powered crypto tracker.</p>
                            <p style="font-size: 10px; color: #3a3d4f; text-align: center;">Sent from startup1-4.onrender.com</p>
                        </div>
                    """,
                }
            )
            
            if resp.status_code != 200:
                err_data = resp.json()
                msg = err_data.get('message', '')
                logger.error(f"Resend API error: {resp.text}")
                
                if "onboarding@resend.dev" in resp.text:
                    raise HTTPException(
                        status_code=403, 
                        detail="Resend Onboarding Restriction: Use your Resend account email or verify your domain."
                    )
                
                raise HTTPException(status_code=resp.status_code, detail=f"Email service error: {msg}")
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Error sending email: {e}")
            raise HTTPException(status_code=500, detail="Error sending email")
            
    return {"message": "Verification code sent successfully"}


@app.post("/api/auth/verify-code")
async def verify_code(req: VerificationVerify):
    """
    Verify the code against the cached one.
    """
    email = req.email.strip().lower()
    if email not in verification_codes:
        raise HTTPException(status_code=400, detail="No verification code sent for this email")
    
    record = verification_codes[email]
    if record["expires_at"] < time.time():
        del verification_codes[email]
        raise HTTPException(status_code=400, detail="Verification code expired")
    
    if record["code"] != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Success, clear the code
    del verification_codes[email]
    return {"message": "Code verified successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)


