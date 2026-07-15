"""
Agent 5: CSCO Synthesizer — Dynamic narrative generation with MANDATORY citation enforcement.
Every factual sentence MUST end with [source: URL]. Temperature tuned for coherent narrative.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from core.reasoning import CitationEnforcedSynthesizer, CONFIG, CitationEnforcer
from core.schemas import Citation, SourceTier, EvidenceType, Claim
from core.evidence_store import get_evidence_store


class CSCOSynthesizer:
    """CSCO Synthesizer with enforced citation format."""
    
    def __init__(self):
        self.synthesizer = CitationEnforcedSynthesizer("Agent5_CSCO")
        self.enforcer = CitationEnforcer()
    
    def build_context(self, 
                      verified_claims: List[Dict],
                      risk_output: Dict,
                      flagged_claims: List[Dict],
                      corridor: str,
                      commodity: str,
                      economy: str) -> Dict[str, Any]:
        """Build rich context for narrative generation."""
        
        # Format verified claims as cited bullets
        claims_text = "\n".join([
            f"- {c['claim'][:250]} [source: {c['source_url']}] "
            f"(tier: {c.get('source_tier','?')}, conf: {c.get('verification_confidence',0):.0%})"
            for c in verified_claims
        ]) or "No verified claims available."
        
        # Format risk components
        risk_components = risk_output.get("components", [])
        risk_text = "\n".join([
            f"- {c['name']}: {c['value']:.2f} (weight {c['weight']}, contrib {c['contribution']:.4f}) "
            f"[evidence: {len(c.get('evidence_citations',[]))} citations]"
            for c in risk_components
        ])
        
        # Format flagged claims
        flagged_text = "\n".join([
            f"- {fc['claim'][:150]}... CONFLICT: {fc.get('verification_reasoning','')[:100]} "
            f"[source: {fc.get('source_url','')}]"
            for fc in flagged_claims[:3]
        ]) or "No flagged claims."
        
        # Risk summary
        risk_score = risk_output.get("risk_score", 0)
        risk_level = risk_output.get("risk_level", "UNKNOWN")
        
        return {
            "corridor": corridor,
            "commodity": commodity,
            "economy": economy,
            "verified_claims_text": claims_text,
            "risk_score": f"{risk_score:.4f}",
            "risk_level": risk_level,
            "risk_components_text": risk_text,
            "flagged_claims_text": flagged_text,
            "citations_available": len(set(
                c.get('source_url') 
                for c in verified_claims 
                if c.get('source_url')
            ))
        }
    
    def synthesize(self,
                   verified_claims: List[Dict],
                   risk_output: Dict,
                   flagged_claims: List[Dict],
                   corridor: str,
                   commodity: str,
                   economy: str) -> Dict[str, Any]:
        """Generate CSCO narrative with enforced citations."""
        
        context = self.build_context(
            verified_claims, risk_output, flagged_claims,
            corridor, commodity, economy
        )
        
        # Build the synthesis prompt
        prompt = f"""You are the CSCO (Chief Supply Chain Officer) for {economy.upper()}, 
analyzing the {str(corridor or 'GLOBAL').upper()} {str(commodity or 'SUPPLY').upper()} supply disruption.

VERIFIED EVIDENCE (use ONLY these facts):
{context['verified_claims_text']}

RISK ASSESSMENT:
- Overall Risk: {context['risk_score']} ({context['risk_level']})
- Components:
{context['risk_components_text']}

FLAGGED DISCREPANCIES (must mention):
{context['flagged_claims_text']}

STRICT RULES:
1. EVERY factual sentence MUST end with [source: URL]
2. If a statement has no source, mark as [INFERRED — low confidence]
3. Do NOT invent data not in VERIFIED EVIDENCE above
4. Be specific with numbers, dates, locations
5. Maximum 5 sentences
6. Flag discrepancies explicitly
7. End with 2 actionable recommendations

Generate the narrative now:"""
        
        # Use synthesizer
        self.synthesizer._add_step("synthesis", prompt)
        messages = self.synthesizer._build_messages(prompt)
        response = self.synthesizer._invoke_with_retry(messages, "synthesis")
        self.synthesizer._add_step("synthesis_result", response)
        
        narrative = response.strip()
        
        # Enforce citations
        citation_check = CitationEnforcer.verify_citations(narrative, required=True)
        
        # Extract citations from narrative
        citations = []
        for url in CitationEnforcer.extract_citations(narrative):
            # Find matching claim
            for claim in verified_claims:
                if claim.get("source_url") == url:
                    citations.append({
                        "text": claim.get("claim", "")[:80],
                        "url": url,
                        "tier": claim.get("source_tier", "unknown"),
                        "confidence": claim.get("verification_confidence", 0.5)
                    })
                    break
            else:
                citations.append({
                    "text": "Synthesized statement",
                    "url": url,
                    "tier": "synthesis",
                    "confidence": 0.6
                })
        
        # Count flags
        flagged_count = len(flagged_claims)
        confidence = round(0.85 - 0.1 * flagged_count, 2)
        
        # Add citation warning if needed
        if not citation_check["passes"]:
            narrative += f"\n\n[WARNING: {citation_check['uncited_factual']} factual claims lack citations]"
        
        result = {
            "narrative": narrative,
            "confidence": max(confidence, 0.0),
            "citations": citations,
            "citations_count": len(citations),
            "citation_check": citation_check,
            "llm_generated": True,
            "model": CONFIG.NIM_MODEL,
            "reasoning_trace": self.synthesizer.get_trace()
        }
        
        # Store in evidence
        store = get_evidence_store()
        claim_citations = []
        for c in citations:
            try:
                tier = SourceTier(c['tier']) if c['tier'] in [t.value for t in SourceTier] else SourceTier.UNKNOWN
            except:
                tier = SourceTier.UNKNOWN
            claim_citations.append(
                Citation(
                    source_tier=tier,
                    source_name='Synthesized',
                    source_url=c['url'],
                    evidence_type=EvidenceType.NEWS_REPORT,
                    excerpt=c['text'][:200],
                    confidence=c['confidence']
                )
            )
        
        store.store_claim(
            Claim(
                text=narrative,
                claim_type="categorical",  # ponytail: schema Literal has no 'narrative', using closest match
                citations=claim_citations,
                confidence=confidence,
                extracted_by="Agent5_CSCO"
            )
        )
        
        return result


def run_agent_5(
    verified_claims: List[Dict],
    risk_output: Dict,
    flagged_claims: List[Dict],
    corridor: str,
    commodity: str,
    economy: str
) -> Dict[str, Any]:
    """Run Agent 5: CSCO Synthesizer."""
    
    synthesizer = CSCOSynthesizer()
    return synthesizer.synthesize(
        verified_claims, risk_output, flagged_claims,
        corridor, commodity, economy
    )


if __name__ == "__main__":
    # Test
    test_verified = [
        {
            "claim": "Hormuz throughput fell to 2.7 million b/d in March 2026 from 20M pre-war",
            "verification_status": "VERIFIED",
            "verification_confidence": 0.92,
            "source_url": "https://eia.gov/steo/apr26.pdf",
            "source_tier": "official_gov"
        },
        {
            "claim": "India's crude import dependency reached 88.6%",
            "verification_status": "VERIFIED", 
            "verification_confidence": 0.95,
            "source_url": "https://pib.gov.in/PRID=2000001",
            "source_tier": "official_gov"
        }
    ]
    
    test_risk = {
        "risk_score": 0.5655,
        "risk_level": "MEDIUM",
        "components": [
            {"name": "Exposure_Breadth", "value": 0.8, "weight": 0.35, "contribution": 0.28, "evidence_citations": []},
            {"name": "Dependency_Ratio", "value": 0.3, "weight": 0.25, "contribution": 0.075, "evidence_citations": []}
        ]
    }
    
    test_flagged = [
        {
            "claim": "Saudi Arabia shuts in 15 million b/d amid Hormuz crisis",
            "verification_reasoning": "EIA baseline 9.1M vs claimed 15M = 65% variance",
            "source_url": "https://aljazeera.com/fake-article"
        }
    ]
    
    result = run_agent_5(test_verified, test_risk, test_flagged, "hormuz", "crude oil", "india")
    print("=" * 80)
    print("CSCO NARRATIVE:")
    print(result['narrative'])
    print("\nCITATION CHECK:", result['citation_check'])
    print("\nCITATIONS:")
    for c in result['citations']:
        print(f"  - {c['text']} -> {c['url']}")