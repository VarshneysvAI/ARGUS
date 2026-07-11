# agents/agent_1_research.py
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "articles"

TIER_MAP = {
    "eia.gov": "gov", "iea.org": "gov", "pib.gov.in": "gov",
    "reuters.com": "major_media", "bbc.com": "major_media", "apnews.com": "major_media",
    "aljazeera.com": "major_media", "cnbc.com": "major_media",
}

def get_source_tier(url: str) -> str:
    for domain, tier in TIER_MAP.items():
        if domain in url:
            return tier
    return "social"

def load_documents(corridor: str, commodity: str, economy: str) -> List[Dict]:
    docs = []
    if not DATA_DIR.exists():
        return docs
    for f in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.name
            body = (data.get("body") or "") + " " + (data.get("headline") or "")
            body_lower = body.lower()
            relevant = True
            if corridor and corridor not in body_lower:
                relevant = False
            docs.append(data)
        except (json.JSONDecodeError, IOError):
            continue
    if not docs:
        return [{
            "source": "ARGUS Internal Note",
            "source_url": "file://data/articles/internal_note.md",
            "source_tier": "internal",
            "headline": "No matching documents found",
            "body": "The data directory is empty or no documents matched the query.",
            "_filename": "internal_note.json"
        }]
    return docs

def run_agent_1(corridor: str, commodity: str, economy: str) -> Dict[str, Any]:
    docs = load_documents(corridor, commodity, economy)
    claims = []
    quarantined = []
    for d in docs:
        source_url = d.get("source_url", "file://data/articles/unknown")
        source_tier = d.get("source_tier") or get_source_tier(source_url)
        body = d.get("body", "")
        headline = d.get("headline", "")
        text = f"{headline} {body}"
        if not text.strip():
            quarantined.append({"claim": "Empty document content", "reason": "no_content", "status": "QUARANTINED"})
            continue
        if not source_url.startswith(("http://", "https://", "file://")):
            quarantined.append({"claim": f"Article: {headline}", "reason": "missing_source_url", "status": "REJECTED"})
            continue
        tier_mult = {"gov": 1.0, "major_media": 0.8, "regional": 0.5, "social": 0.2}.get(source_tier, 0.2)
        claim = {
            "claim": text.strip(),
            "source_url": source_url,
            "source_tier": source_tier,
            "retrieval_confidence": round(tier_mult * 0.95, 2),
            "retrieved_at": d.get("retrieved_at", datetime.utcnow().isoformat() + "Z"),
            "_filename": d.get("_filename", "unknown")
        }
        claims.append(claim)
    return {"claims": claims, "quarantined": quarantined}
