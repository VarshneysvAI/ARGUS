"""
Agent 7: Consensus & Conflict Detector — Semantic comparison (not math trick).
LLM compares risk narrative vs sourcing alternatives for genuine agreement/disagreement.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import json

from core.reasoning import LLMReasoner, CONFIG
from core.schemas import Citation, SourceTier, EvidenceType, Claim
from core.evidence_store import get_evidence_store


@dataclass
class ConsensusResult:
    """Semantic consensus between agents."""
    consensus_level: str  # "strong", "moderate", "weak", "conflict"
    reasoning: str
    risk_direction: str      # "improving", "stable", "worsening"
    sourcing_direction: str  # "improving", "stable", "worsening"
    key_agreements: List[str]
    key_disagreements: List[str]
    confidence: float
    requires_human_review: bool


class ConsensusReasoner(LLMReasoner):
    """LLM that semantically compares agent outputs."""
    
    def __init__(self):
        super().__init__(
            agent_name="Agent7_Consensus",
            temperature=CONFIG.TEMPERATURE_REASONING,
            system_prompt="""You are a senior analyst comparing two intelligence assessments.
Determine if they semantically agree or disagree on the severity and direction of a crisis.
Output ONLY valid JSON."""
        )
    
    def compare(self,
                risk_output: Dict,
                mcda_output: Dict,
                verified_claims: List[Dict],
                flagged_claims: List[Dict]) -> ConsensusResult:
        """Semantic comparison of risk assessment vs sourcing alternatives."""
        
        # Extract key narratives
        risk_summary = self._summarize_risk(risk_output)
        mcda_summary = self._summarize_mcda(mcda_output)
        claims_summary = self._summarize_claims(verified_claims, flagged_claims)
        
        prompt = f"""
RISK ASSESSMENT NARRATIVE:
{risk_summary}

SOURCING ALTERNATIVES ASSESSMENT:
{mcda_summary}

KEY EVIDENCE:
{claims_summary}

TASK: Do these assessments agree on the SEVERITY and DIRECTION of the crisis?

OUTPUT JSON:
{{
  "consensus_level": "strong|moderate|weak|conflict",
  "reasoning": "Detailed semantic comparison",
  "risk_direction": "improving|stable|worsening",
  "sourcing_direction": "improving|stable|worsening",
  "key_agreements": ["point1", "point2"],
  "key_disagreements": ["point1", "point2"],
  "confidence": 0.0-1.0,
  "requires_human_review": boolean
}}

RULES:
- "conflict" = fundamentally different severity/direction assessment
- "weak" = same direction but significantly different severity
- "moderate" = same direction, minor severity differences
- "strong" = aligned on both severity and direction
- Check if risk says "immediate action needed" but sourcing says "alternatives adequate"
- Check if sourcing alternatives are actually feasible given flagged claims
"""
        self._add_step("consensus", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, "consensus")
        self._add_step("consensus_result", response)
        
        try:
            result = json.loads(response)
            return ConsensusResult(
                consensus_level=result.get("consensus_level", "weak"),
                reasoning=result.get("reasoning", ""),
                risk_direction=result.get("risk_direction", "unknown"),
                sourcing_direction=result.get("sourcing_direction", "unknown"),
                key_agreements=result.get("key_agreements", []),
                key_disagreements=result.get("key_disagreements", []),
                confidence=float(result.get("confidence", 0.5)),
                requires_human_review=bool(result.get("requires_human_review", False))
            )
        except json.JSONDecodeError:
            return ConsensusResult(
                consensus_level="weak",
                reasoning="LLM parse failed - using fallback",
                risk_direction="unknown",
                sourcing_direction="unknown",
                key_agreements=[],
                key_disagreements=[],
                confidence=0.3,
                requires_human_review=True
            )
    
    def _summarize_risk(self, risk: Dict) -> str:
        parts = [f"Risk Score: {risk.get('risk_score', 'N/A')} ({risk.get('risk_level', 'N/A')})"]
        for c in risk.get('components', []):
            parts.append(f"  {c['name']}: {c['value']:.2f} (weight {c['weight']}, contrib {c['contribution']:.4f})")
        return "\n".join(parts)
    
    def _summarize_mcda(self, mcda: Dict) -> str:
        alts = mcda.get('alternatives', [])
        if not alts:
            return "No alternatives available."
        parts = [f"Top alternative: {alts[0]['name']} (score: {alts[0]['score']:.4f})"]
        for a in alts[:3]:
            parts.append(f"  {a['name']}: score {a['score']:.4f}, {a.get('criteria_scores', {})}")
        return "\n".join(parts)
    
    def _summarize_claims(self, verified: List, flagged: List) -> str:
        parts = [f"Verified: {len(verified)} claims", f"Flagged: {len(flagged)} claims"]
        for c in flagged[:3]:
            parts.append(f"  FLAG: {c.get('claim','')[:100]}... var={c.get('numerical_variance_pct','?')}%")
        return "\n".join(parts)


def run_agent_7(
    risk_output: Dict,
    verified_claims: List[Dict],
    mcda_output: Dict,
    flagged_claims: List[Dict],
    corridor: str,
    commodity: str,
    economy: str
) -> Dict[str, Any]:
    """Run Agent 7: Semantic Consensus Detector."""
    
    store = get_evidence_store()
    reasoner = ConsensusReasoner()
    
    consensus = reasoner.compare(risk_output, mcda_output, verified_claims, flagged_claims)
    
    # Determine status
    if consensus.consensus_level == "conflict":
        status = "HALTED"
        message = f"Semantic conflict detected: {consensus.reasoning}"
    elif consensus.consensus_level == "weak":
        status = "FLAGGED"
        message = f"Weak consensus: {consensus.reasoning}"
    elif consensus.requires_human_review:
        status = "FLAGGED"
        message = f"Review required: {consensus.reasoning}"
    else:
        status = "CONSENSUS"
        message = f"{consensus.consensus_level.title()} consensus: {consensus.reasoning}"
    
    # Variance proxy (for backward compat)
    direction_map = {"improving": 0.2, "stable": 0.5, "worsening": 0.8}
    risk_dir_val = direction_map.get(consensus.risk_direction, 0.5)
    sourcing_dir_val = direction_map.get(consensus.sourcing_direction, 0.5)
    variance = abs(risk_dir_val - sourcing_dir_val)
    
    result = {
        "consensus_status": "CONFLICT" if consensus.consensus_level == "conflict" else consensus.consensus_level.upper(),
        "status": status,
        "message": message,
        "variance": round(variance, 2),
        "semantic_consensus": {
            "consensus_level": consensus.consensus_level,
            "reasoning": consensus.reasoning,
            "risk_direction": consensus.risk_direction,
            "sourcing_direction": consensus.sourcing_direction,
            "key_agreements": consensus.key_agreements,
            "key_disagreements": consensus.key_disagreements,
            "confidence": consensus.confidence,
            "requires_human_review": consensus.requires_human_review
        },
        "agent_opinions": {
            "Agent_4_Risk_Score": risk_output.get("risk_score", 0),
            "Agent_4_Risk_Level": risk_output.get("risk_level", "UNKNOWN"),
            "Agent_6_Sourcing_Direction": consensus.sourcing_direction,
            "Agent_6_MCDA_Top_Score": mcda_output.get("alternatives", [{}])[0].get("score", 0) if mcda_output.get("alternatives") else 0
        },
        "threshold_halt": 0.30,
        "threshold_flag": 0.15,
        "recommendation": message
    }
    
    # Store
    store.store_claim(
        Claim(
            text=f"Semantic consensus: {consensus.consensus_level} - {consensus.reasoning[:200]}",
            claim_type="categorical",  # ponytail: schema Literal has no 'consensus'
            citations=[
                Citation(
                    source_tier=SourceTier.UNKNOWN,
                    source_name="Agent7_Consensus",
                    source_url="internal://agent7/consensus",
                    evidence_type=EvidenceType.USER_PROVIDED,
                    excerpt=f"Semantic consensus: {consensus.consensus_level} - {consensus.reasoning[:200]}",
                    confidence=consensus.confidence
                )
            ],
            confidence=consensus.confidence,
            extracted_by="Agent7_Consensus"
        )
    )
    
    result["reasoning_trace"] = reasoner.get_trace()
    return result


def _fallback_consensus(risk_output: Dict, mcda_output: Dict) -> ConsensusResult:
    """Fallback if LLM fails."""
    risk_score = risk_output.get("risk_score", 0.5)
    mcda_top = mcda_output.get("alternatives", [{}])[0].get("score", 0.5) if mcda_output.get("alternatives") else 0.5
    
    # Simple heuristic
    if risk_score > 0.6 and mcda_top < 0.6:
        return ConsensusResult(
            consensus_level="conflict",
            reasoning="High risk score but low alternative scores - risk says crisis, sourcing says inadequate alternatives",
            risk_direction="worsening",
            sourcing_direction="worsening",
            key_agreements=["Both indicate supply stress"],
            key_disagreements=["Risk severity vs alternative adequacy mismatch"],
            confidence=0.6,
            requires_human_review=True
        )
    elif risk_score < 0.45 and mcda_top > 0.6:
        return ConsensusResult(
            consensus_level="moderate",
            reasoning="Low risk score but good alternatives available",
            risk_direction="improving",
            sourcing_direction="improving",
            key_agreements=["Situation manageable"],
            key_disagreements=[],
            confidence=0.7,
            requires_human_review=False
        )
    else:
        return ConsensusResult(
            consensus_level="weak",
            reasoning="Moderate risk, moderate alternatives - alignment unclear",
            risk_direction="stable",
            sourcing_direction="stable",
            key_agreements=[],
            key_disagreements=[],
            confidence=0.5,
            requires_human_review=True
        )


if __name__ == "__main__":
    test_risk = {"risk_score": 0.565, "risk_level": "MEDIUM", "components": [
        {"name": "Exposure_Breadth", "value": 0.8, "weight": 0.35, "contribution": 0.28}
    ]}
    test_mcda = {"alternatives": [{"name": "SPR Drawdown", "score": 0.74, "criteria_scores": {}}]}
    test_verified = [{"claim": "Hormuz throughput 2.7M b/d"}]
    test_flagged = [{"claim": "Saudi 15M shut-in", "numerical_variance_pct": 65}]
    
    result = run_agent_7(test_risk, test_verified, test_mcda, test_flagged, "hormuz", "crude oil", "india")
    print(json.dumps(result, indent=2, default=str))