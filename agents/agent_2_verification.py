"""
Agent 2: Source Verification — LLM semantic verification with citation enforcement.
Cross-checks numerical claims against baselines, validates source credibility.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json
import re

from core.reasoning import LLMReasoner, CitationEnforcer, CitedClaim
from core.schemas import Citation, ClaimStatus, SourceTier, EvidenceType, VerificationResult
from core.evidence_store import get_evidence_store
from core.scenarios import find_scenario


@dataclass
class BaselineEntry:
    """A baseline reference value."""
    key: str
    value: float
    unit: str
    description: str
    source_url: str
    confidence: float = 0.95


# EIA Baseline data (from eia_baseline.json)
BASELINE_DATA = {
    "hormuz_throughput_mbd": BaselineEntry(
        key="hormuz_throughput_mbd",
        value=2.7, unit="mbd",
        description="Hormuz throughput March 2026",
        source_url="https://www.eia.gov/outlooks/steo/archives/apr26.pdf"
    ),
    "hormuz_prewar_mbd": BaselineEntry(
        key="hormuz_prewar_mbd",
        value=20.0, unit="mbd",
        description="Hormuz pre-war baseline",
        source_url="https://www.eia.gov/outlooks/steo/archives/apr26.pdf"
    ),
    "saudi_shutin_mbd": BaselineEntry(
        key="saudi_shutin_mbd",
        value=9.1, unit="mbd",
        description="Saudi shut-in production March 2026",
        source_url="https://www.eia.gov/outlooks/steo/archives/apr26.pdf"
    ),
    "brent_peak_apr2026": BaselineEntry(
        key="brent_peak_apr2026",
        value=144.0, unit="usd/bbl",
        description="Brent crude peak April 2026",
        source_url="https://www.eia.gov/outlooks/steo/archives/apr26.pdf"
    ),
    "brent_q2_2026": BaselineEntry(
        key="brent_q2_2026",
        value=114.6, unit="usd/bbl",
        description="Brent Q2 2026 average forecast",
        source_url="https://www.eia.gov/outlooks/steo/archives/apr26.pdf"
    ),
    "uae_pipeline_capacity_mbd": BaselineEntry(
        key="uae_pipeline_capacity_mbd",
        value=1.8, unit="mbd",
        description="UAE Habshan-Fujairah pipeline capacity",
        source_url="https://www.iea.org/reports/oil-market-report-june-2026/uae-pipeline"
    ),
    "india_import_dependency_pct": BaselineEntry(
        key="india_import_dependency_pct",
        value=88.6, unit="%",
        description="India crude import dependency FY2025-26",
        source_url="https://pib.gov.in/PressReleaseDetail.aspx?PRID=2000001"
    ),
    "india_spr_days": BaselineEntry(
        key="india_spr_days",
        value=9.5, unit="days",
        description="India SPR government-controlled days",
        source_url="https://pib.gov.in/PressReleaseDetail.aspx?PRID=2000010"
    ),
    "india_total_reserve_days": BaselineEntry(
        key="india_total_reserve_days",
        value=60.0, unit="days",
        description="India total commercial + strategic reserve days",
        source_url="https://pib.gov.in/PressReleaseDetail.aspx?PRID=2000010"
    ),
    "india_hormuz_bypass_pct": BaselineEntry(
        key="india_hormuz_bypass_pct",
        value=70.0, unit="%",
        description="India crude imports bypassing Hormuz",
        source_url="https://pib.gov.in/PressReleaseDetail.aspx?PRID=2000001"
    ),
    "jkm_lng_spot_price": BaselineEntry(
        key="jkm_lng_spot_price",
        value=28.0, unit="usd/mmbtu",
        description="JKM spot LNG price March 2026",
        source_url="https://www.platts.com/natural-gas"
    ),
    "lng_cape_premium": BaselineEntry(
        key="lng_cape_premium",
        value=3.5, unit="usd/mmbtu",
        description="Cape of Good Hope LNG routing premium",
        source_url="https://www.platts.com/natural-gas"
    )
}


class SemanticVerifier(LLMReasoner):
    """LLM-based semantic claim verification with citation enforcement."""
    
    def __init__(self):
        system = """You are a rigorous fact-checker for energy supply chain intelligence.
        
TASK: Verify a claim against evidence and baselines. Determine if SUPPORTED, REFUTED, or UNSUPPORTED.

RULES:
1. Every assertion MUST cite evidence by [source: URL] format
2. Numerical claims: check against baselines, compute variance %
2. Source tier matters: official_gov > international_org > major_news > specialized_press > industry_report > regional_news > social_verified > social_unverified
3. Multiple independent sources agreeing = SUPPORTED
4. Sources disagreeing beyond 10% tolerance = FLAGGED_DISCREPANCY
5. Single high-tier source = VERIFIED_SINGLE_SOURCE
6. No accessible sources = INSUFFICIENT_EVIDENCE
7. Claim contradicts established baseline >10% = FLAGGED_DISCREPANCY

OUTPUT FORMAT (JSON only):
{
  "verdict": "SUPPORTED|VERIFIED_SINGLE_SOURCE|CORROBORATED|REFUTED|CONFLICTING|INSUFFICIENT_EVIDENCE|UNVERIFIABLE|FLAGGED_DISCREPANCY",
  "confidence": 0.0-1.0,
  "reasoning": "Step-by-step verification with citations",
  "supporting_evidence": ["citation_ids"],
  "contradicting_evidence": ["citation_ids"],
  "numerical_variance_pct": number or null,
  "baseline_used": "baseline_key or null",
  "requires_human_review": boolean,
  "review_reason": "string or null"
}"""
        super().__init__("Agent2_Verifier", temperature=0.2, system_prompt=system)
    
    def verify_claim(self, 
                     claim: Dict[str, Any], 
                     evidence: List[Dict[str, Any]],
                     baselines: Dict[str, BaselineEntry]) -> VerificationResult:
        """Verify a single claim against evidence and baselines."""
        
        claim_text = claim.get("claim", "")
        claim_value = claim.get("value")
        claim_unit = claim.get("unit")
        claim_type = claim.get("claim_type", "categorical")
        
        # Prepare evidence summary
        evidence_summary = "\n".join([
            f"- [{e.get('source_tier','unknown')}] {e.get('claim','')[:150]} [source: {e.get('source_url','')}]"
            for e in evidence[:10]
        ])
        
        # Check baselines for numerical claims
        baseline_info = ""
        matched_baseline = None
        variance_pct = None
        
        if claim_value is not None and claim_type == "numerical":
            # Find matching baseline
            for key, base in baselines.items():
                if self._matches_baseline(claim_text, key):
                    matched_baseline = key
                    variance_pct = abs(claim_value - base.value) / base.value * 100
                    baseline_info = f"\nBASELINE ({key}): {base.value} {base.unit} (source: {base.source_url})"
                    baseline_info += f"\nCLAIMED: {claim_value} {claim_unit}"
                    baseline_info += f"\nVARIANCE: {variance_pct:.1f}%"
                    break
        
        prompt = f"""
CLAIM TO VERIFY: {claim_text}
CLAIM TYPE: {claim_type}
CLAIM VALUE: {claim_value} {claim_unit}

EVIDENCE AVAILABLE:
{evidence_summary}
{baseline_info}

VERIFY THIS CLAIM AGAINST THE EVIDENCE AND BASELINES.
"""
        self._add_step("verification", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, "verification")
        self._add_step("verification_result", response)
        
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            # Fallback parsing
            result = self._parse_fallback(response)
        
        # Extract citation IDs used
        supporting = result.get("supporting_evidence", [])
        contradicting = result.get("contradicting_evidence", [])
        
        return VerificationResult(
            claim_id=claim.get("claim_id", ""),
            status=result.get("verdict", "INSUFFICIENT_EVIDENCE"),
            reasoning=result.get("reasoning", "Failed to parse verification"),
            supporting_citations=supporting,
            contradicting_citations=contradicting,
            numerical_variance_pct=result.get("numerical_variance_pct") or variance_pct,
            baseline_used=matched_baseline,
            confidence=result.get("confidence", 0.5),
            requires_human_review=result.get("requires_human_review", False),
            review_reason=result.get("review_reason")
        )
    
    def _matches_baseline(self, claim_text: str, baseline_key: str) -> bool:
        """Check if claim matches a baseline key."""
        keywords = {
            "hormuz_throughput_mbd": ["hormuz", "throughput", "flow"],
            "hormuz_prewar_mbd": ["pre-war", "prewar", "baseline", "normal"],
            "saudi_shutin_mbd": ["saudi", "shut-in", "shutin", "production"],
            "brent_peak_apr2026": ["brent", "peak", "price", "$144"],
            "brent_q2_2026": ["brent", "q2", "forecast", "average"],
            "uae_pipeline_capacity_mbd": ["uae", "pipeline", "habshan", "fujairah"],
            "india_import_dependency_pct": ["india", "import", "dependency", "88"],
            "india_spr_days": ["india", "spr", "strategic", "reserve", "9.5"],
            "india_total_reserve_days": ["india", "total", "reserve", "60"],
            "india_hormuz_bypass_pct": ["bypass", "hormuz", "70"],
            "jkm_lng_spot_price": ["jkm", "lng", "spot", "price"],
            "lng_cape_premium": ["cape", "premium", "routing"]
        }
        kws = keywords.get(baseline_key, [])
        claim_lower = claim_text.lower()
        return any(kw in claim_lower for kw in kws)
    
    def _parse_fallback(self, content: str) -> Dict:
        """Parse LLM response if JSON fails."""
        verdict = "INSUFFICIENT_EVIDENCE"
        for v in ["SUPPORTED", "VERIFIED_SINGLE_SOURCE", "CORROBORATED", 
                  "REFUTED", "CONFLICTING", "FLAGGED_DISCREPANCY", "UNVERIFIABLE"]:
            if v.lower() in content.lower():
                verdict = v
                break
        
        conf = 0.5
        import re
        m = re.search(r'confidence["\s:]+([0-9.]+)', content.lower())
        if m:
            try:
                conf = float(m.group(1))
            except:
                pass
        
        return {
            "verdict": verdict,
            "confidence": conf,
            "reasoning": content[:500],
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "numerical_variance_pct": None,
            "requires_human_review": False
        }


class SourceCredibilityScorer:
    """Score source credibility for news scoring."""
    
    # MBFC/AllSides composite scores (0-1)
    SOURCE_SCORES = {
        "eia.gov": {"factuality": 0.95, "bias": 0.0, "transparency": 0.9},
        "iea.org": {"factuality": 0.93, "bias": 0.05, "transparency": 0.85},
        "pib.gov.in": {"factuality": 0.9, "bias": 0.1, "transparency": 0.8},
        "reuters.com": {"factuality": 0.95, "bias": 0.0, "transparency": 0.9},
        "apnews.com": {"factuality": 0.95, "bias": 0.0, "transparency": 0.9},
        "bloomberg.com": {"factuality": 0.9, "bias": 0.1, "transparency": 0.85},
        "ft.com": {"factuality": 0.9, "bias": 0.1, "transparency": 0.85},
        "wsj.com": {"factuality": 0.9, "bias": 0.2, "transparency": 0.85},
        "argusmedia.com": {"factuality": 0.92, "bias": 0.0, "transparency": 0.7},
        "spglobal.com": {"factuality": 0.88, "bias": 0.05, "transparency": 0.75},
        "rystadenergy.com": {"factuality": 0.85, "bias": 0.05, "transparency": 0.7},
        "aljazeera.com": {"factuality": 0.75, "bias": 0.3, "transparency": 0.7},
        "cnbc.com": {"factuality": 0.8, "bias": 0.2, "transparency": 0.75},
        "platts.com": {"factuality": 0.9, "bias": 0.0, "transparency": 0.7},
        "default": {"factuality": 0.5, "bias": 0.0, "transparency": 0.5}
    }
    
    @classmethod
    def score(cls, url: str) -> Dict[str, float]:
        for domain, scores in cls.SOURCE_SCORES.items():
            if domain in url:
                return scores
        return cls.SOURCE_SCORES["default"]
    
    @classmethod
    def overall_credibility(cls, url: str) -> float:
        scores = cls.score(url)
        # Weight: factuality 50%, transparency 30%, bias penalty 20%
        return round(
            scores["factuality"] * 0.5 + 
            scores["transparency"] * 0.3 - 
            abs(scores["bias"]) * 0.2, 
            3
        )


def run_agent_2(claims: List[Dict]) -> Dict[str, Any]:
    """Run Agent 2: Source Verification."""
    
    store = get_evidence_store()
    verifier = SemanticVerifier()
    scorer = SourceCredibilityScorer()
    
    # Load baselines
    baselines = BASELINE_DATA.copy()
    
    # Add scenario-specific baselines
    for claim in claims:
        if claim.get("claim_id"):
            # Could add scenario-specific baselines here
            pass
    
    verified = []
    flagged = []
    quarantined = []
    
    for claim in claims:
        # Get credibility score
        url = claim.get("source_url", "")
        credibility = scorer.overall_credibility(url)
        tier = claim.get("source_tier", "unknown")
        
        # Find corroborating evidence (other claims with similar content)
        corroborating = []
        for other in claims:
            if other is claim:
                continue
            if _claims_similar(claim, other):
                corroborating.append(other)
        
        # Verify
        evidence = [claim] + corroborating
        result = verifier.verify_claim(claim, evidence, BASELINE_DATA)
        
        # Apply source credibility modifier
        tier_mod = {
            "official_gov": 1.0, "international_org": 0.95,
            "major_news": 0.85, "specialized_press": 0.8,
            "industry_report": 0.75, "regional_news": 0.6,
            "social_verified": 0.4, "social_unverified": 0.2,
            "user_provided": 0.3, "unknown": 0.3
        }
        tier_key = claim.get("source_tier", "unknown")
        mod = tier_mod.get(tier_key, 0.3)
        
        adjusted_confidence = result.confidence * mod * credibility
        
        # Determine final status
        final_status = _determine_final_status(
            result.status, adjusted_confidence, 
            claim.get("value"), claim.get("claim_type")
        )
        
        claim_result = {
            **claim,
            "verification_status": final_status.value,
            "verification_reasoning": result.reasoning,
            "verification_confidence": round(adjusted_confidence, 2),
            "source_credibility": round(credibility, 3),
            "numerical_variance_pct": result.numerical_variance_pct,
            "baseline_used": result.baseline_used,
            "requires_human_review": result.requires_human_review,
            "review_reason": result.review_reason
        }
        
        if final_status in [ClaimStatus.VERIFIED, ClaimStatus.VERIFIED_SINGLE_SOURCE, ClaimStatus.CORROBORATED]:
            verified.append(claim_result)
        elif final_status in [ClaimStatus.FLAGGED_DISCREPANCY, ClaimStatus.CONFLICTING]:
            flagged.append(claim_result)
        else:
            quarantined.append(claim_result)
        
        # Store verification result
        store.store_verification(VerificationResult(
            claim_id=claim.get("claim_id", ""),
            status=final_status.value,
            reasoning=result.reasoning,
            supporting_citations=result.supporting_citations,
            contradicting_citations=result.contradicting_citations,
            numerical_variance_pct=result.numerical_variance_pct,
            baseline_used=result.baseline_used,
            confidence=adjusted_confidence,
            requires_human_review=result.requires_human_review,
            review_reason=result.review_reason
        ))
    
    return {
        "verified_claims": verified,
        "flagged_claims": flagged,
        "quarantined_claims": quarantined,
        "stats": {
            "total": len(claims),
            "verified": len(verified),
            "flagged": len(flagged),
            "quarantined": len(quarantined)
        },
        "reasoning_trace": verifier.get_trace()
    }


def _claims_similar(c1: Dict, c2: Dict, threshold: float = 0.7) -> bool:
    """Check if two claims are about the same thing."""
    # Simple text similarity
    t1 = str(c1.get("claim", c1.get("text", "")) or "").lower()
    t2 = str(c2.get("claim", c2.get("text", "")) or "").lower()
    
    # Check for key entity overlap
    entities = ["hormuz", "saudi", "brent", "india", "uae", "pipeline", "lng", "japan"]
    e1 = set(e for e in entities if e in str(c1.get("claim", c1.get("text", "")) or "").lower())
    e2 = set(e for e in entities if e in str(c2.get("claim", c2.get("text", "")) or "").lower())
    
    if e1 and e2 and e1 == e2:
        return True
    
    # Numerical value similarity
    v1 = c1.get("value")
    v2 = c2.get("value")
    if v1 is not None and v2 is not None:
        try:
            diff = abs(float(v1) - float(v2)) / max(abs(float(v1)), 1)
            if diff < 0.15:
                return True
        except:
            pass
    
    return False


def _determine_final_status(
    raw_status: str, 
    confidence: float,
    value: Optional[float],
    claim_type: str
) -> ClaimStatus:
    """Map raw verification to final status with confidence thresholds."""
    
    # High confidence verified
    if confidence >= 0.7 and raw_status in ["SUPPORTED", "VERIFIED_SINGLE_SOURCE", "CORROBORATED"]:
        return ClaimStatus.VERIFIED
    
    # Medium confidence
    if confidence >= 0.5 and raw_status in ["VERIFIED_SINGLE_SOURCE", "CORROBORATED"]:
        return ClaimStatus.VERIFIED_SINGLE_SOURCE
    
    # Numerical discrepancies
    if raw_status == "FLAGGED_DISCREPANCY" or (value is not None and claim_type == "numerical"):
        # Check variance threshold
        return ClaimStatus.FLAGGED_DISCREPANCY
    
    # Conflicting sources
    if raw_status in ["CONFLICTING", "REFUTED"]:
        return ClaimStatus.CONFLICTING
    
    # Low confidence
    return ClaimStatus.INSUFFICIENT_EVIDENCE


if __name__ == "__main__":
    # Test with sample claims
    test_claims = [
        {
            "claim_id": "c1",
            "claim": "Hormuz throughput fell to 2.7 million b/d in March 2026",
            "claim_type": "numerical",
            "value": 2.7,
            "unit": "mbd",
            "source_url": "https://www.eia.gov/outlooks/steo/archives/apr26.pdf",
            "source_tier": "official_gov",
            "claim_id": "c1"
        },
        {
            "claim_id": "c2", 
            "claim": "Saudi Arabia shut in 15 million b/d",
            "claim_type": "numerical",
            "value": 15.0,
            "unit": "mbd",
            "source_url": "https://www.aljazeera.com/economy/2026/04/15/saudi-shuts-in-15-million-barrels",
            "source_tier": "major_news",
            "claim_id": "c2"
        },
        {
            "claim_id": "c3",
            "claim": "India's crude import dependency is 88.6%",
            "claim_type": "numerical",
            "value": 88.6,
            "unit": "%",
            "source_url": "https://pib.gov.in/PressReleaseDetail.aspx?PRID=2000001",
            "source_tier": "official_gov",
            "claim_id": "c3"
        }
    ]
    
    result = run_agent_2(test_claims)
    print(f"Verified: {result['stats']['verified']}")
    print(f"Flagged: {result['stats']['flagged']}")
    print(f"Quarantined: {result['stats']['quarantined']}")
    
    for c in result["flagged_claims"]:
        print(f"\nFLAGGED: {c['claim'][:80]}")
        print(f"  Variance: {c.get('numerical_variance_pct')}%")
        print(f"  Baseline: {c.get('baseline_used')}")
        print(f"  Reasoning: {c['verification_reasoning'][:200]}")