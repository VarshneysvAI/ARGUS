# agents/agent_1_research.py
"""Agent 1: Research & Retrieval — loads pre-fetched documents, extracts claims with mandatory source URLs."""
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "articles"

TIER_MAP = {
    "eia.gov": "gov", "iea.org": "gov", "pib.gov.in": "gov",
    "reuters.com": "major_media", "bbc.com": "major_media", "apnews.com": "major_media",
    "aljazeera.com": "major_media", "cnbc.com": "major_media",
}

SOURCE_TIER_WEIGHTS = {"gov": 1.0, "major_media": 0.8, "regional": 0.5, "social": 0.2, "internal": 0.3}

def get_source_tier(url: str) -> str:
    for domain, tier in TIER_MAP.items():
        if domain in url:
            return tier
    return "social"

def filter_relevant(doc: Dict, corridor: str, commodity: str, economy: str) -> bool:
    body = ((doc.get("body") or "") + " " + (doc.get("headline") or "")).lower()
    keywords = []
    if corridor:
        keywords.append(corridor.lower())
    if commodity:
        keywords.append(commodity.lower())
    if economy:
        keywords.append(economy.lower())
    if not keywords:
        return True
    return any(kw in body for kw in keywords)

def run_agent_1(corridor: str, commodity: str, economy: str) -> Dict[str, Any]:
    claims = []
    quarantined = []
    if not DATA_DIR.exists():
        return {"claims": [], "quarantined": [{"claim": "No data directory found", "reason": "data_dir_missing", "status": "QUARANTINED"}], "total_documents": 0}
    doc_files = sorted(DATA_DIR.glob("*.json"))
    for f in doc_files:
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            doc["_filename"] = f.name
        except (json.JSONDecodeError, IOError):
            quarantined.append({"claim": f"Failed to parse {f.name}", "reason": "parse_error", "status": "QUARANTINED"})
            continue
        if not filter_relevant(doc, corridor, commodity, economy):
            continue
        source_url = doc.get("source_url", "")
        source_tier = doc.get("source_tier") or get_source_tier(source_url)
        body = doc.get("body", "")
        headline = doc.get("headline", "")
        text = f"{headline}. {body}".strip()
        if not text or len(text) < 10:
            quarantined.append({"claim": f"Empty content in {f.name}", "reason": "no_content", "status": "QUARANTINED"})
            continue
        if not source_url.startswith(("http://", "https://", "file://")):
            quarantined.append({"claim": f"Article '{headline}' — no valid source URL", "reason": "missing_source_url", "status": "REJECTED"})
            continue
        tier_weight = SOURCE_TIER_WEIGHTS.get(source_tier, 0.2)
        claims.append({
            "claim": text,
            "headline": headline,
            "source_url": source_url,
            "source_tier": source_tier,
            "retrieval_confidence": round(tier_weight * 0.95, 2),
            "retrieved_at": doc.get("retrieved_at", datetime.utcnow().isoformat() + "Z"),
            "_filename": f.name
        })
    return {
        "claims": claims,
        "quarantined": quarantined,
        "total_documents": len(doc_files),
        "relevant_documents": len(claims)
    }
