import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

logger = logging.getLogger(__name__)

_db = None

def get_firestore_db():
    global _db
    if _db is not None:
        return _db

    # Try to initialize from environment variable
    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    if not service_account_json:
        # Fallback: check for a local file (e.g., during development)
        local_path = "service-account.json"
        if os.path.exists(local_path):
            try:
                with open(local_path, "r") as f:
                    service_account_json = f.read()
            except Exception:
                pass

    if service_account_json:
        try:
            # Parse strictly to ensure it's valid JSON
            sa_info = json.loads(service_account_json)
            cred = credentials.Certificate(sa_info)
            firebase_admin.initialize_app(cred)
            _db = firestore.client()
            logger.info("Firebase Firestore initialized successfully via Service Account.")
            return _db
        except Exception as e:
            logger.error(f"Failed to initialize Firebase with Service Account: {e}")
            return None
    else:
        logger.warning("FIREBASE_SERVICE_ACCOUNT_JSON not found. Persistent results will be disabled.")
        return None

def save_analysis_to_firestore(youtuber_name: str, result: dict):
    """Save the final analysis report to a persistent Firestore collection."""
    db = get_firestore_db()
    if not db: return

    try:
        # Sanitize name for document ID
        doc_id = "".join(c for c in youtuber_name if c.isalnum()).strip().lower()
        if not doc_id: doc_id = "unknown_youtuber"

        # Limit large objects if necessary (Firestore has a 1MB limit per document)
        # Our predictions are usually small enough, but let's be safe.
        doc_ref = db.collection("evaluations").document(doc_id)
        
        # Add a server-side timestamp for freshness check
        result["stored_at"] = datetime.utcnow().isoformat()
        
        doc_ref.set(result)
        logger.info(f"Analysis for {youtuber_name} persisted to Firestore.")
    except Exception as e:
        logger.error(f"Firestore Save Error: {e}")

async def load_analysis_from_firestore(youtuber_name: str) -> dict:
    """Check Firestore for a recent analysis of this YouTuber."""
    db = get_firestore_db()
    if not db: return None

    try:
        doc_id = "".join(c for c in youtuber_name if c.isalnum()).strip().lower()
        doc_ref = db.collection("evaluations").document(doc_id)
        doc = doc_ref.get()

        if doc.exists:
            data = doc.to_dict()
            # Check freshness? (e.g., less than 48 hours old)
            stored_at_str = data.get("stored_at")
            if stored_at_str:
                stored_at = datetime.fromisoformat(stored_at_str)
                age_hours = (datetime.utcnow() - stored_at).total_seconds() / 3600
                if age_hours < 48: # 2 days persistence
                    logger.info(f"FIRESTORE CACHE HIT: Found persistent data for {youtuber_name} (Age: {age_hours:.1f}h)")
                    return data
        
        return None
    except Exception as e:
        logger.warning(f"Firestore Load Error: {e}")
        return None
