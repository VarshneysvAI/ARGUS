# agents/agent_7_consensus.py
"""Agent 7: Consensus & Conflict Detector — detects when agents disagree, halts if variance > 0.30 threshold."""
from typing import Dict, Any, List

THRESHOLD_HALT = 0.30
THRESHOLD_FLAG = 0.15

def compute_sourcing_proxy(verified_claims: List[Dict]) -> float:
    alt_keywords = ["bypass", "alternative", "pipeline", "route", "diversif", "uae", "red sea", "fujairah",
                    "reserve", "spr", "drawdown", "contract", "spot", "import"]
    score = 0.0
    for claim in verified_claims:
        text = claim.get("claim", "").lower()
        for kw in alt_keywords:
            if kw in text:
                score += 0.12
    return min(score, 1.0)

def run_agent_7(risk_output: Dict, verified_claims: List[Dict], mcda_output: Dict = None) -> Dict[str, Any]:
    risk_score = risk_output.get("risk_score", 0.0)
    sourcing_proxy = compute_sourcing_proxy(verified_claims)
    sourcing_risk = round(1.0 - sourcing_proxy, 2)
    mcda_score = None
    if mcda_output and mcda_output.get("alternatives"):
        mcda_score = round(1.0 - mcda_output["alternatives"][0]["score"], 2) if mcda_output["alternatives"][0]["score"] > 0.5 else round(mcda_output["alternatives"][0]["score"], 2)
    primary_variance = round(abs(risk_score - sourcing_risk), 2)
    variance_used = primary_variance
    if primary_variance < THRESHOLD_FLAG:
        status = "CONSENSUS"
        message = f"All agents agree within {THRESHOLD_FLAG} variance. Auto-proceeding."
    elif primary_variance < THRESHOLD_HALT:
        status = "FLAGGED"
        message = f"Variance {primary_variance} between {THRESHOLD_FLAG}-{THRESHOLD_HALT}. Flagged for human review."
    else:
        status = "HALTED"
        message = f"Variance {primary_variance} exceeds {THRESHOLD_HALT} threshold. SYSTEM HALTED. Human intervention required."
    return {
        "consensus_status": "CONFLICT" if status == "HALTED" else status,
        "variance": variance_used,
        "primary_variance": primary_variance,
        "threshold_halt": THRESHOLD_HALT,
        "threshold_flag": THRESHOLD_FLAG,
        "agent_opinions": {
            "Agent_4_Risk_Score": risk_score,
            "Agent_4_Risk_Level": risk_output.get("risk_level", "UNKNOWN"),
            "Agent_6_Sourcing_Proxy (1-Reliability)": sourcing_risk,
            "Agent_6_MCDA_Top_Score": mcda_score or "N/A"
        },
        "status": status,
        "recommendation": message
    }
