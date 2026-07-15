"""
Agent 1: Research & Retrieval — Hybrid local documents + user uploads + semantic search.
Every claim extracted MUST have a source citation.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
import json
import hashlib
from datetime import datetime
import fitz  # pymupdf
from PIL import Image
import io
import os
import requests

from core.reasoning import StructuredExtractor
from core.schemas import Citation, SourceTier, EvidenceType, ClaimStatus, Claim
from core.evidence_store import get_evidence_store
from core.scenarios import find_scenario, generate_articles_for_scenario


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "articles"
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "data" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


class DocumentProcessor:
    """Process various document types into extractable text."""
    
    @staticmethod
    def load_local_articles() -> List[Dict]:
        """Load all local article JSONs."""
        articles = []
        if not DATA_DIR.exists():
            return articles
        
        for f in sorted(DATA_DIR.glob("*.json")):
            try:
                doc = json.loads(f.read_text(encoding="utf-8"))
                doc["_filename"] = f.name
                articles.append(doc)
            except (json.JSONDecodeError, IOError):
                continue
        return articles
    
    @staticmethod
    def load_scenario_articles(scenario) -> List[Dict]:
        """Generate articles from scenario templates."""
        return generate_articles_for_scenario(scenario)
    
    @staticmethod
    def process_pdf(file_path: Path) -> Dict[str, Any]:
        """Extract text from PDF."""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            
            return {
                "text": text,
                "pages": len(doc) if 'doc' in dir() else 0,
                "source_type": "pdf",
                "file_hash": hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
            }
        except Exception as e:
            return {"error": str(e), "text": ""}
    
    @staticmethod
    def process_image(file_path: Path) -> Dict[str, Any]:
        """Extract text from image (OCR placeholder)."""
        try:
            img = Image.open(file_path)
            # In production: use pytesseract or cloud OCR
            # For now: return metadata
            return {
                "text": f"[Image: {file_path.name}, {img.size[0]}x{img.size[1]}] OCR not implemented in demo",
                "source_type": "image",
                "file_hash": hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
            }
        except Exception as e:
            return {"error": str(e), "text": ""}
    
    @staticmethod
    def process_csv(file_path: Path) -> Dict[str, Any]:
        """Extract data summary from CSV."""
        try:
            import pandas as pd
            df = pd.read_csv(file_path)
            text = f"CSV Data Summary:\nShape: {df.shape}\nColumns: {list(df.columns)}\n\nSample rows:\n{df.head(10).to_string()}"
            return {
                "text": text,
                "source_type": "csv",
                "file_hash": hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
            }
        except Exception as e:
            return {"error": str(e), "text": ""}


class SourceTierClassifier:
    """Classify source tier from URL or metadata."""
    
    TIER_MAP = {
        "eia.gov": SourceTier.OFFICIAL_GOV,
        "iea.org": SourceTier.INTERNATIONAL_ORG,
        "pib.gov.in": SourceTier.OFFICIAL_GOV,
        "reuters.com": SourceTier.MAJOR_NEWS,
        "apnews.com": SourceTier.MAJOR_NEWS,
        "bloomberg.com": SourceTier.MAJOR_NEWS,
        "ft.com": SourceTier.MAJOR_NEWS,
        "wsj.com": SourceTier.MAJOR_NEWS,
        "argusmedia.com": SourceTier.SPECIALIZED_PRESS,
        "spglobal.com": SourceTier.INDUSTRY_REPORT,
        "rystadenergy.com": SourceTier.INDUSTRY_REPORT,
        "aljazeera.com": SourceTier.MAJOR_NEWS,
        "cnbc.com": SourceTier.MAJOR_NEWS,
    }
    
    @classmethod
    def get_tier(cls, url: str) -> SourceTier:
        for domain, tier in cls.TIER_MAP.items():
            if domain in url:
                return tier
        return SourceTier.UNKNOWN


class ClaimExtractor:
    """LLM-based claim extraction with citations."""
    
    def __init__(self):
        self.extractor = StructuredExtractor(
            agent_name="Agent1_ClaimExtractor",
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "claim_type": {"type": "string", "enum": ["numerical", "categorical", "trend", "event", "policy", "forecast"]},
                        "value": {"type": ["number", "null"]},
                        "unit": {"type": ["string", "null"]},
                        "date": {"type": ["string", "null"]},
                        "location": {"type": ["string", "null"]},
                        "evidence_type": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "excerpt": {"type": "string"}
                    },
                    "required": ["text", "claim_type", "excerpt"]
                }
            },
            temperature=0.1
        )
    
    def extract(self, document: Dict[str, Any], source_url: str, source_tier: SourceTier) -> List[Dict[str, Any]]:
        """Extract claims from document text."""
        text = document.get("text", "") or document.get("body", "") or document.get("headline", "")
        if not text:
            return []
        
        # Combine headline + body for extraction
        full_text = f"SOURCE: {document.get('headline', '')}\n\nBODY: {document.get('body', text)}"
        
        result = self.extractor.extract(full_text, source_url, source_tier.value)
        
        if "_error" in result:
            return []
        
        if isinstance(result, dict):
            claims = result.get("claims", [])
            if not claims and "claims" not in result:
                # If the schema extraction returned the dictionary of properties directly (instead of a list)
                claims = [result]
        elif isinstance(result, list):
            claims = result
        else:
            claims = []
        
        # Add source metadata to each claim
        for claim in claims:
            claim["source_url"] = document.get("source_url", source_url)
            claim["source_tier"] = document.get("source_tier", source_tier.value)
            claim["source_headline"] = document.get("headline", "")
            claim["retrieved_at"] = datetime.utcnow().isoformat() + "Z"
        
        return claims


def perform_serper_search(query: str) -> List[Dict]:
    """Perform real web search using Serper API to get live news and data."""
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return []
        
    url = "https://google.serper.dev/search"
    # Force news/recent context by appending 'news latest'
    payload = json.dumps({"q": query + " latest news", "num": 8})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
        res_json = response.json()
        
        docs = []
        for item in res_json.get("organic", []):
            docs.append({
                "headline": item.get("title", ""),
                "body": item.get("snippet", ""),
                "source_url": item.get("link", ""),
                "source_type": "web_search"
            })
        return docs
    except Exception as e:
        print(f"Serper API error: {e}")
        return []


def run_agent_1(
    corridor: str, 
    commodity: str, 
    economy: str,
    uploaded_files: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """Run Agent 1: Research & Retrieval."""
    
    store = get_evidence_store()
    processor = DocumentProcessor()
    classifier = SourceTierClassifier()
    extractor = ClaimExtractor()
    
    # Find matching scenario
    scenario = find_scenario(corridor, commodity, economy)
    
    # Collect all documents
    documents = []
    
    # 1. Local articles
    local_articles = processor.load_local_articles()
    for doc in local_articles:
        url = doc.get("source_url", "")
        tier = classifier.get_tier(url) if url else SourceTier.UNKNOWN
        doc["source_tier"] = tier.value
        documents.append(doc)
    
    # 2. Scenario articles (if scenario matches)
    if scenario:
        scenario_articles = processor.load_scenario_articles(scenario)
        for doc in scenario_articles:
            tier = classifier.get_tier(doc.get("source_url", ""))
            doc["source_tier"] = tier.value
            documents.append(doc)
            
    # 2.5 Real Web Search (Serper API)
    search_query = f"{corridor} {commodity} disruption supply chain"
    web_articles = perform_serper_search(search_query)
    for doc in web_articles:
        tier = classifier.get_tier(doc.get("source_url", ""))
        doc["source_tier"] = tier.value
        documents.append(doc)
    
    # 3. User uploads
    uploaded_docs = []
    if uploaded_files:
        for upload in uploaded_files:
            file_path = UPLOADS_DIR / upload["filename"]
            if file_path.exists():
                if upload["type"] == "pdf":
                    processed = processor.process_pdf(file_path)
                elif upload["type"] == "image":
                    processed = processor.process_image(file_path)
                elif upload["type"] == "csv":
                    processed = processor.process_csv(file_path)
                else:
                    processed = {"text": upload.get("text", ""), "source_type": "text"}
                
                if "text" in processed and processed["text"]:
                    doc = {
                        "headline": f"User Upload: {upload['filename']}",
                        "body": processed["text"],
                        "source_url": f"upload://{upload['filename']}",
                        "source_tier": SourceTier.USER_PROVIDED.value,
                        "source_type": processed.get("source_type", "upload"),
                        "is_upload": True
                    }
                    documents.append(doc)
                    uploaded_docs.append(doc)
    
    # Filter relevant documents
    keywords = []
    if corridor: keywords.append(corridor.lower())
    if commodity: keywords.append(commodity.lower())
    if economy: keywords.append(economy.lower())
    
    claims = []
    quarantined = []
    relevant_docs = 0
    
    for doc in documents:
        text = str((doc.get("headline", "") or "") + " " + (doc.get("body", "") or "")).lower()
        
        if keywords and not any(kw in text for kw in keywords) and doc.get("source_type") != "web_search":
            continue
        
        relevant_docs += 1
        
        # Extract claims
        source_url = doc.get("source_url", "")
        source_tier = SourceTier(doc.get("source_tier", "unknown"))
        
        extracted = extractor.extract(doc, source_url, source_tier)
        
        for claim_data in extracted:
            # Create proper Claim object for evidence store
            raw_evidence_type = claim_data.get("evidence_type", "news_report")
            try:
                evidence_type = EvidenceType(raw_evidence_type)
            except ValueError:
                evidence_type = EvidenceType.NEWS_REPORT

            citation = Citation(
                source_tier=SourceTier(claim_data.get("source_tier", "unknown")),
                source_name=claim_data.get("source_headline", "Unknown"),
                source_url=claim_data.get("source_url", ""),
                evidence_type=evidence_type,
                excerpt=str(claim_data.get("excerpt") or "")[:200],
                confidence=float(claim_data.get("confidence") if claim_data.get("confidence") is not None else 0.5)
            )
            
            claim = Claim(
                text=claim_data.get("text", ""),
                claim_type=str(claim_data.get("claim_type") or "categorical"),
                value=claim_data.get("value"),
                unit=claim_data.get("unit"),
                date=claim_data.get("date"),
                location=claim_data.get("location"),
                citations=[citation],
                status=ClaimStatus.VERIFIED_SINGLE_SOURCE,
                confidence=float(claim_data.get("confidence") if claim_data.get("confidence") is not None else 0.5),
                extracted_by="Agent1_ClaimExtractor",
                metadata={"source_doc": doc.get("headline", "")[:50]}
            )
            
            # Store in evidence store
            store.store_claim(claim)
            claims.append({
                "claim": claim.text,
                "claim_type": claim.claim_type,
                "value": claim.value,
                "unit": claim.unit,
                "date": claim.date,
                "location": claim.location,
                "source_url": claim_data.get("source_url", ""),
                "source_tier": claim_data.get("source_tier", "unknown"),
                "source_headline": claim_data.get("source_headline", ""),
                "retrieval_confidence": round(claim.confidence * 0.95, 2),
                "retrieved_at": claim_data.get("retrieved_at", datetime.utcnow().isoformat() + "Z"),
                "citations": [citation.model_dump()],
                "_filename": doc.get("_filename", doc.get("source_url", ""))
            })
    
    # Quarantine unmatched
    total_docs = len(documents)
    if total_docs > relevant_docs:
        quarantined.append({
            "claim": f"{total_docs - relevant_docs} documents did not match query keywords",
            "reason": "relevance_filter",
            "status": "QUARANTINED"
        })
    
    # Store stats
    stats = {
        "total_documents": total_docs,
        "relevant_documents": relevant_docs,
        "claims_extracted": len(claims),
        "scenario_used": scenario.id if scenario else "none",
        "uploads_processed": len(uploaded_docs)
    }
    
    stats_claim = Claim(
        text=f"Agent1 retrieved {len(claims)} claims from {relevant_docs} relevant documents",
        claim_type="categorical",
        status=ClaimStatus.VERIFIED_SINGLE_SOURCE,
        confidence=0.9,
        extracted_by="Agent1"
    )
    store.store_claim(stats_claim)
    
    return {
        "claims": claims,
        "quarantined": quarantined,
        "total_documents": total_docs,
        "relevant_documents": relevant_docs,
        "stats": stats,
        "reasoning_trace": extractor.extractor.get_trace()
    }


if __name__ == "__main__":
    # Test with Hormuz scenario
    result = run_agent_1("hormuz", "crude oil", "india")
    print(f"Claims extracted: {len(result['claims'])}")
    print(f"Relevant docs: {result['relevant_documents']}/{result['total_documents']}")
    for c in result['claims'][:3]:
        print(f"  - [{c['source_tier']}] {c['claim'][:80]}... [source: {c['source_url'][:60]}]")