# agents/agent_4_risk.py
from typing import Dict, Any, List

WEIGHTS = {
    "Exposure_Breadth": 0.35,
    "Dependency_Ratio": 0.25,
    "Downstream_Criticality": 0.20,
    "Tier1_Centrality": 0.10,
    "Exposure_Depth": 0.10
}

THRESHOLDS = [("HIGH", 0.60), ("MEDIUM", 0.45), ("LOW", 0.0)]

DEMO_VALUES = {
    "Exposure_Breadth": 0.85,
    "Dependency_Ratio": 0.68,
    "Downstream_Criticality": 0.71,
    "Tier1_Centrality": 0.92,
    "Exposure_Depth": 0.45
}

def compute_component(name: str, verified_claims: List[Dict]) -> Dict[str, Any]:
    supporting = [c for c in verified_claims if name.lower().replace("_", " ") in c.get("claim", "").lower()]
    source_url = supporting[0].get("source_url", "https://www.eia.gov/") if supporting else "https://www.eia.gov/"
    value = DEMO_VALUES.get(name, 0.5)
    weight = WEIGHTS[name]
    contribution = round(value * weight, 4)
    return {"name": name, "value": value, "weight": weight, "contribution": contribution, "source_node": name, "source_url": source_url}

def run_agent_4(verified_claims: List[Dict], graph: Dict = None) -> Dict[str, Any]:
    components = [compute_component(name, verified_claims) for name in WEIGHTS]
    risk_score = round(sum(c["contribution"] for c in components), 4)
    risk_level = "LOW"
    for level, threshold in sorted(THRESHOLDS, key=lambda x: -x[1]):
        if risk_score >= threshold:
            risk_level = level
            break
    confidences = [c.get("confidence", 0.5) for c in verified_claims]
    confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.5
    return {
        "risk_score": risk_score, "risk_level": risk_level,
        "confidence": confidence, "components": components,
        "formula_citation": "AlMahri et al. 2026, Eq. 4 (Cambridge/Alan Turing Institute)"
    }
