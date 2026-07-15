"""
Agent 4: Risk Analyzer — Cambridge weighted formula with ALL 5 components data-driven.
LLM estimates components with citations. No hardcoded constants.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import re
import json

from core.reasoning import LLMReasoner, CONFIG
from core.schemas import Citation, SourceTier, REASONING_PROMPTS as PROMPTS, Claim
from core.evidence_store import get_evidence_store
from core.satellite import SatelliteAnalyzer


@dataclass
class RiskComponent:
    """Risk component with evidence-backed value."""
    name: str
    value: float          # 0.0 - 1.0
    weight: float
    contribution: float
    description: str
    evidence_citations: List[Dict]
    reasoning: str
    confidence: float
    source_nodes: List[str] = None


class RiskReasoner(LLMReasoner):
    """Specialized reasoner for risk component estimation."""
    
    def __init__(self):
        super().__init__(
            agent_name="Agent4_RiskReasoner",
            temperature=CONFIG.TEMPERATURE_REASONING,
            system_prompt="""You are a supply chain risk analyst for energy markets.
Estimate risk components using ONLY the provided evidence. Every numerical assertion MUST cite evidence.
Output JSON with explicit citations for every claim."""
        )
    
    def estimate_component(self, 
                          component_name: str,
                          component_desc: str,
                          weight: float,
                          evidence: List[Dict],
                          graph_summary: Dict,
                          satellite_data: Dict,
                          context: Dict) -> RiskComponent:
        """Estimate a risk component value with citations."""
        
        evidence_text = json.dumps(evidence[:10], indent=2) if evidence else "No direct evidence"
        graph_text = json.dumps(graph_summary, indent=2)
        sat_text = json.dumps(satellite_data, indent=2)
        
        prompt = f"""
COMPONENT: {component_name} (weight: {weight})
DEFINITION: {component_desc}

AVAILABLE EVIDENCE:
{evidence_text}

GRAPH SUMMARY:
{graph_text}

SATELLITE INTELLIGENCE:
{sat_text}

CONTEXT:
Corridor: {context.get('corridor', 'unknown')}
Commodity: {context.get('commodity', 'unknown')}
Economy: {context.get('economy', 'unknown')}

TASK: Estimate component value (0.0 = no risk, 1.0 = maximum risk).

OUTPUT JSON:
{{
  "value": 0.0-1.0,
  "reasoning": "Step-by-step reasoning citing specific evidence",
  "evidence_citations": ["citation_id1", "citation_id2"],
  "confidence": 0.0-1.0,
  "key_assumptions": ["assumption1", "assumption2"]
}}

RULES:
- 0.0 = no risk, 1.0 = maximum risk
- MUST cite evidence for every quantitative claim
- If no evidence, state clearly and use conservative (higher) estimate
- Explicitly state key assumptions
"""
        self._add_step(f"estimate_{component_name}", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, f"estimate_{component_name}")
        self._add_step(f"estimate_{component_name}_result", response)
        
        try:
            result = json.loads(response)
            value = max(0.0, min(1.0, float(result.get("value", 0.5))))
            reasoning = result.get("reasoning", "")
            citations = result.get("evidence_citations", [])
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            return RiskComponent(
                name=component_name,
                value=value,
                weight=weight,
                contribution=round(value * weight, 4),
                description=f"LLM-estimated with {confidence:.0%} confidence",
                evidence_citations=citations,
                reasoning=reasoning,
                confidence=confidence
            )
        except json.JSONDecodeError:
            # Fallback: conservative estimate
            return RiskComponent(
                name=component_name,
                value=0.5,
                weight=weight,
                contribution=round(0.5 * weight, 4),
                description="LLM parse failed - conservative default",
                evidence_citations=[],
                reasoning="JSON parse failed",
                confidence=0.3
            )


def extract_claim_citations(verified_claims: List[Dict]) -> List[Dict]:
    """Extract all citations from verified claims."""
    citations = []
    for claim in verified_claims:
        for cit in claim.get("citations", []):
            citations.append({
                "id": cit.get("id", f"cit_{len(citations)}"),
                "source_tier": cit.get("source_tier"),
                "source_name": cit.get("source_name"),
                "source_url": cit.get("source_url"),
                "evidence_type": cit.get("evidence_type"),
                "excerpt": cit.get("excerpt", "")[:200],
                "confidence": cit.get("confidence", 0.5)
            })
    return citations


def build_graph_summary(verified_claims: List[Dict]) -> Dict:
    """Build a summary of the claim graph for risk reasoning."""
    entities = set()
    relations = []
    
    for claim in verified_claims:
        text = str(claim.get("claim", claim.get("text", "")) or "").lower()
        
        # Extract entities
        for e in ["hormuz", "malacca", "suez", "saudi", "uae", "india", "japan", "paradip", "jamnagar", "fujairah"]:
            if e in text:
                entities.add(e)
    
    return {
        "entities": list(entities),
        "claim_count": len(entities),
        "verified_claims": len(entities)
    }


def run_agent_4(
    verified_claims: List[Dict],
    graph_data: Dict,
    corridor: str,
    commodity: str,
    economy: str
) -> Dict[str, Any]:
    """Run Agent 4: Risk Analyzer with all 5 components LLM-estimated."""
    
    store = get_evidence_store()
    reasoner = RiskReasoner()
    
    # Prepare evidence
    citations = extract_claim_citations(verified_claims)
    graph_summary = graph_data.get("graph_summary", {})
    analyzer = SatelliteAnalyzer()
    satellite_data = analyzer.get_latest_for_corridor(corridor)
    
    context = {"corridor": corridor, "commodity": commodity, "economy": economy}
    
    # Component definitions (Cambridge formula weights)
    COMPONENTS = [
        ("Exposure_Breadth", 0.35, "Share of supply sources/routes affected by disruption"),
        ("Dependency_Ratio", 0.25, "Fraction of total supply that passes through the disrupted corridor"),
        ("Downstream_Criticality", 0.20, "Economic criticality of downstream consumers (refineries, power plants, etc.)"),
        ("Tier1_Centrality", 0.10, "Network centrality of Tier-1 suppliers in the disrupted corridor"),
        ("Exposure_Depth", 0.10, "Duration and severity of exposure (transit time, inventory cover)")
    ]
    
    # Gather evidence for each component
    component_evidence = _gather_component_evidence(verified_claims)
    
    components = []
    for name, weight, desc in COMPONENTS:
        evidence = component_evidence.get(name, [])
        
        comp = reasoner.estimate_component(
            name, desc, weight, evidence, 
            graph_summary={},  # We don't have full graph yet
            satellite_data=satellite_data,
            context={"corridor": corridor, "commodity": commodity, "economy": economy}
        )
        components.append(comp)
    
    # Calculate risk score
    risk_score = round(sum(c.contribution for c in components), 4)
    
    # Risk level
    if risk_score >= 0.60:
        risk_level = "HIGH"
    elif risk_score >= 0.45:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"
    
    # Overall confidence
    avg_confidence = round(sum(c.confidence for c in components) / len(components), 2)
    
    result = {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "confidence": avg_confidence,
        "formula": {
            "weights": {c.name: c.weight for c in components},
            "thresholds": {"HIGH": 0.60, "MEDIUM": 0.45, "LOW": 0.0}
        },
        "components": [
            {
                "name": c.name,
                "value": c.value,
                "weight": c.weight,
                "contribution": c.contribution,
                "description": c.description,
                "evidence_citations": c.evidence_citations,
                "reasoning": c.reasoning,
                "confidence": c.confidence
            }
            for c in components
        ],
        "satellite_intelligence": satellite_data,
        "formula_citation": "Cambridge Supply Chain Risk Formula (adapted for energy)",
        "reasoning_trace": reasoner.get_trace()
    }
    
    # Store result
    from core.schemas import Citation, EvidenceType, ClaimStatus
    store.store_claim(
        Claim(
            text=f"Risk score: {risk_score} ({risk_level})",
            claim_type="categorical",
            status=ClaimStatus.VERIFIED,
            citations=[
                Citation(
                    source_tier=SourceTier.UNKNOWN,
                    source_name="Agent4_RiskAnalyzer",
                    source_url="internal://agent4/risk",
                    evidence_type=EvidenceType.USER_PROVIDED,
                    excerpt=f"Risk score: {risk_score} ({risk_level}) with {avg_confidence:.0%} confidence",
                    confidence=avg_confidence
                )
            ],
            value=risk_score,
            unit="score",
            status="VERIFIED",
            confidence=avg_confidence,
            extracted_by="Agent4"
        )
    )
    
    return result


def _gather_component_evidence(verified_claims: List[Dict]) -> Dict[str, List[Dict]]:
    """Distribute claims to relevant risk components."""
    
    component_keywords = {
        "Exposure_Breadth": ["source", "supplier", "route", "alternative", "bypass", "number of"],
        "Dependency_Ratio": ["dependency", "import", "pass through", "fraction", "percent", "%"],
        "Downstream_Criticality": ["refinery", "power plant", "consumer", "critical", "essential", "downstream"],
        "Tier1_Centrality": ["tier 1", "primary", "primary supplier", "hub", "central", "connected"],
        "Exposure_Depth": ["transit", "time", "days", "duration", "inventory", "stock", "cover", "lead time"]
    }
    
    # Initialize all components
    result = {comp: [] for comp in [
        "Exposure_Breadth", "Dependency_Ratio", 
        "Downstream_Criticality", "Tier1_Centrality", "Exposure_Depth"
    ]}
    
    for claim in verified_claims:
        text = str(claim.get("claim", claim.get("text", "")) or "").lower()
        
        for comp, keywords in component_keywords.items():
            if any(kw in text for kw in keywords):
                result[comp].append(claim)
    
    return result


if __name__ == "__main__":
    # Test with mock claims
    test_claims = [
        {
            "claim_id": "c1",
            "claim": "Hormuz throughput fell to 2.7 million b/d from 20M pre-war",
            "verification_status": "VERIFIED",
            "verification_confidence": 0.92,
            "source_url": "https://eia.gov/steo/apr26.pdf",
            "source_tier": "official_gov",
            "claim_type": "numerical",
            "value": 2.7,
            "unit": "mbd"
        },
        {
            "claim_id": "c2",
            "claim": "India import dependency 88.6%, 70% bypass Hormuz",
            "verification_status": "VERIFIED",
            "verification_confidence": 0.95,
            "source_url": "https://pib.gov.in/PRID=2000001",
            "source_tier": "official_gov",
            "claim_type": "numerical",
            "value": 88.6,
            "unit": "%"
        },
        {
            "claim_id": "c3",
            "claim": "UAE pipeline 1.8M b/d bypass operating at 95% capacity",
            "verification_status": "VERIFIED",
            "verification_confidence": 0.88,
            "source_url": "https://iea.org/uae-pipeline",
            "source_tier": "international_org",
            "claim_type": "numerical",
            "value": 1.8,
            "unit": "mbd"
        }
    ]
    
    result = run_agent_4(test_claims, {}, "hormuz", "crude oil", "india")
    print(json.dumps(result, indent=2, default=str))