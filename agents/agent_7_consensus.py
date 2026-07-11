# agents/agent_7_consensus.py
from typing import Dict, Any, List

def compute_sourcing_proxy(verified_claims: List[Dict]) -> float:
    alt_keywords = ["bypass", "alternative", "pipeline", "route", "diversif", "uae", "red sea", "fujairah"]
    score = 0.0
    for claim in verified_claims:
        claim_lower = claim.get("claim", "").lower()
        for kw in alt_keywords:
            if kw in claim_lower:
                score += 0.15
    return min(score, 1.0)

def run_agent_7(risk_output: Dict, verified_claims: List[Dict]) -> Dict[str, Any]:
    risk_score = risk_output["risk_score"]
    sourcing_proxy = compute_sourcing_proxy(verified_claims)
    sourcing_risk = round(1.0 - sourcing_proxy, 2)
    variance = round(abs(risk_score - sourcing_risk), 2)
    threshold = 0.30
    if variance < 0.15:
        status = "CONSENSUS"
    elif variance < threshold:
        status = "FLAGGED"
    else:
        status = "HALTED"
    return {
        "consensus_status": "CONFLICT" if status == "HALTED" else status,
        "variance": variance, "threshold": threshold,
        "agent_opinions": {"Agent_4_Risk": risk_score, "Agent_6_Sourcing_Proxy": sourcing_risk},
        "status": status,
        "recommendation": "Human review required" if status == "HALTED" else "Proceed to synthesis"
    }
