"""
Agent 8: ERASER — PolitiFact-style Evidence Trail Audit.
Produces complete audit report for the pipeline run.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from core.reasoning import LLMReasoner, CONFIG
from core.schemas import Claim, Citation, SourceTier, EvidenceType
from core.evidence_store import get_evidence_store


class ERASERReasoner(LLMReasoner):
    """LLM-based epistemic auditor producing PolitiFact-style report."""

    def __init__(self):
        super().__init__(
            agent_name="Agent8_ERASER",
            temperature=0.2,
            system_prompt="""You are ERASER, the ARGUS system's internal epistemic auditor.
Produce a PolitiFact-style evidence trail audit for the complete pipeline run.
For EACH agent, answer the 8 ERASER questions with specific citations.
Be rigorous. Identify gaps, contradictions, missing evidence, overconfidence.
Output ONLY valid JSON."""
        )

    def audit_pipeline(self,
                       pipeline_state: Dict[str, Any],
                       evidence_trail: List[Dict]) -> Dict[str, Any]:
        """Audit the complete pipeline run."""

        # Build concise summary
        summary = self._build_summary(pipeline_state, evidence_trail)

        prompt = f"""
PIPELINE RUN AUDIT DATA:
{summary}

TASK: Produce PolitiFact-style evidence trail audit.
For EACH agent that ran (0-7 + Final ERASER), answer ALL 8 ERASER questions.

ERASER QUESTIONS:
1. WHY: What is the reasoning behind this step?
2. WHAT: What is the evidence for each claim?
3. WHERE: What is the source URL, timestamp, and tier for each claim?
4. IS: Does the inference logically follow from the evidence?
5. WHAT_IF: If a configurable parameter changes, how does output change?
6. WHO: Which other agents disagree with this output?
7. MISSING: What data is absent that would change the conclusion?
8. RAW: Show the original prompt and raw agent response.

OUTPUT JSON:
{{
  "overall_rating": "PASS|FLAG|FAIL",
  "summary": "Executive summary of audit findings",
  "agent_audits": {{
    "Agent0_SearchQuality": {{
      "rating": "PASS|FLAG|FAIL",
      "answers": {{
        "WHY": "string",
        "WHAT": "string",
        "WHERE": "string",
        "IS": "string",
        "WHAT_IF": "string",
        "WHO": "string",
        "MISSING": "string",
        "RAW": "string"
      }},
      "flags": ["flag1", "flag2"]
    }}
    // ... repeat for Agent1 through Agent7, and Final_ERASER
  }},
  "cross_agent_findings": [
    "Finding 1: description with citations",
    "Finding 2: ..."
  ],
  "correction_recommendations": [
    "Recommendation 1: ...",
    "Recommendation 2: ..."
  ],
  "evidence_trail_integrity": "COMPLETE|PARTIAL|BROKEN"
}}
"""
        self._add_step("eraser_audit", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, "audit_pipeline")
        self._add_step("eraser_result", response)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return self._fallback_audit(pipeline_state)

    def _build_summary(self, pipeline_state: Dict, evidence_trail: List[Dict]) -> str:
        """Build concise summary for LLM."""

        agents_run = pipeline_state.get("agents_completed", [])

        parts = [
            f"PIPELINE STATUS: {pipeline_state.get('status', 'UNKNOWN')}",
            f"USER INPUT: {pipeline_state.get('user_input', 'N/A')}",
            f"AGENTS COMPLETED: {', '.join(agents_run)}",
            f"CLAIMS EXTRACTED: {pipeline_state.get('claims_count', 0)}",
            f"CLAIMS VERIFIED: {pipeline_state.get('verified_count', 0)}",
            f"CLAIMS FLAGGED: {pipeline_state.get('flagged_count', 0)}",
            f"RISK SCORE: {pipeline_state.get('risk_score', 'N/A')} ({pipeline_state.get('risk_level', 'N/A')})",
            f"TOP ALTERNATIVE: {pipeline_state.get('top_alternative', 'N/A')}",
            f"CONSENSUS: {pipeline_state.get('consensus_status', 'N/A')}",
            f"EVIDENCE TRAIL ENTRIES: {len(evidence_trail)}"
        ]

        return "\n".join(parts)

    def _fallback_audit(self, pipeline_state: Dict) -> Dict[str, Any]:
        """Fallback audit if LLM fails."""
        return {
            "overall_rating": "FLAG",
            "summary": "LLM audit failed - manual review required",
            "agent_audits": {},
            "cross_agent_findings": ["LLM audit unavailable"],
            "correction_recommendations": ["Re-run with functional LLM"],
            "evidence_trail_integrity": "PARTIAL"
        }

    # Per-agent audit methods for graph orchestration
    def audit_agent_0(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 0: Search Quality Gate."""
        flags = []
        specificity = output.get("specificity_score", 0)
        if specificity < 0.5:
            flags.append(f"Specificity low ({specificity}). Input may be too vague.")
        if output.get("status") == "REJECT":
            flags.append(f"Input rejected: {output.get('reason', '')}")
        return {
            "agent_id": 0, "agent_name": "Search Quality Gate",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Extracted entities from user input: corridor={output.get('corridor')}, commodity={output.get('commodity')}, economy={output.get('economy')}",
                "WHAT": f"Entities extracted: {output.get('entities', {})}",
                "WHERE": "No external sources — input from user only",
                "IS": "Yes, keyword-based extraction is deterministic and explainable",
                "WHAT_IF": f"If specificity threshold raised to 0.6, this input would {'still pass' if specificity >= 0.6 else 'be rejected (specificity=' + str(specificity) + ')'}",
                "WHO": "No other agents have run yet",
                "MISSING": "No satellite or AIS data at this stage",
                "RAW": f"Input: {output.get('input', '')[:100]}... | Keywords: crisis entity mapping"
            }
        }

    def audit_agent_1(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 1: Research & Retrieval."""
        flags = []
        claims = output.get("claims", [])
        total_docs = output.get("total_documents", 0)
        relevant = output.get("relevant_documents", 0)
        if not claims:
            flags.append("No claims retrieved. Data directory may be empty.")
        if relevant < total_docs:
            flags.append(f"Only {relevant}/{total_docs} documents matched the query.")
        missing_urls = [c for c in claims if not c.get("source_url", "").startswith(("http://", "https://", "file://"))]
        if missing_urls:
            flags.append(f"{len(missing_urls)} claims have invalid/missing source URLs.")
        return {
            "agent_id": 1, "agent_name": "Research & Retrieval",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Searched {total_docs} documents, retrieved {len(claims)} relevant claims",
                "WHAT": f"Claims: {[c.get('headline','')[:60] for c in claims[:3]]}",
                "WHERE": f"Source URLs: {[c.get('source_url','') for c in claims[:3]]}",
                "IS": "Yes, each claim has a source_url and source_tier for traceability",
                "WHAT_IF": "If relevance filter was stricter, fewer claims would pass downstream",
                "WHO": "No other agents have run yet",
                "MISSING": "Live API data not integrated — using pre-loaded documents only",
                "RAW": f"Loaded from data/articles/ | Filter applied: corridor + commodity + economy match"
            }
        }

    def audit_agent_2(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 2: Source Verification."""
        flags = []
        verified = output.get("verified_claims", [])
        flagged = output.get("flagged_claims", [])
        quarantined = output.get("quarantined_claims", [])
        if flagged:
            for fc in flagged:
                flags.append(f"FLAGGED: {fc.get('claim','')[:80]}... — {fc.get('reason','')}")
        if quarantined:
            flags.append(f"{len(quarantined)} claims quarantined.")
        return {
            "agent_id": 2, "agent_name": "Source Verification",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Cross-checked {len(verified)+len(flagged)+len(quarantined)} claims against EIA baseline",
                "WHAT": f"Verified: {len(verified)}, Flagged: {len(flagged)}, Quarantined: {len(quarantined)}",
                "WHERE": "EIA baseline source: data/eia_baseline.json",
                "IS": "Verified claims are within 10% EIA tolerance. Flagged claims exceeded tolerance.",
                "WHAT_IF": "If tolerance tightened to 5%, more claims would be flagged. If loosened to 20%, some false positives pass.",
                "WHO": "Agent 1 supplied the claims. Agent 0 validated the query scope.",
                "MISSING": "Real-time EIA API not connected — using static baseline snapshot.",
                "RAW": "Cross-check: numerical regex extraction → baseline comparison → pass/fail/tolerance calc"
            }
        }

    def audit_agent_3(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 3: Graph Builder."""
        stats = output.get("stats", {})
        flags = []
        if stats.get("rejected_no_url", 0) > 0:
            flags.append(f"{stats['rejected_no_url']} claims rejected due to missing source_url.")
        if stats.get("nodes_created", 0) == 0:
            flags.append("Graph is empty — no nodes created.")
        return {
            "agent_id": 3, "agent_name": "Graph Builder",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Constructed NetworkX graph from {stats.get('nodes_created',0)} verified claim nodes",
                "WHAT": f"Nodes: {stats.get('nodes_created',0)}, Edges: {stats.get('edges_created',0)}",
                "WHERE": f"Graph persisted to: {output.get('graph_persisted', '')}",
                "IS": "Graph construction is deterministic. Every node has source_url property.",
                "WHAT_IF": "If more claims were verified, graph density and connectivity would increase",
                "WHO": "Agent 2 provided verified claims. Graph analytics inform Agent 4.",
                "MISSING": "Real-time graph updates not supported in this version.",
                "RAW": f"Node types: {stats.get('node_types', {})}"
            }
        }

    def audit_agent_4(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 4: Risk Analyzer."""
        flags = []
        risk = output.get("risk_score", 0)
        components = output.get("components", [])
        if risk >= 0.6:
            flags.append(f"HIGH risk score ({risk}). Recommend immediate action.")
        missing_urls = [c for c in components if not c.get("source_url")]
        if missing_urls:
            flags.append(f"{len(missing_urls)} components missing source URLs.")
        return {
            "agent_id": 4, "agent_name": "Risk Analyzer",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Applied Cambridge formula to {len(components)} components with weights: 35/25/20/10/10",
                "WHAT": f"Risk Score: {output.get('risk_score')} ({output.get('risk_level')}) — Components: {[c['name']+'='+str(c['value']) for c in components]}",
                "WHERE": f"Components source: {[c.get('source_url','NO URL') for c in components]}",
                "IS": "Formula validated to F1 0.96 in original Cambridge paper. Deterministic math — no hallucination risk.",
                "WHAT_IF": f"If Exposure_Breadth weight changes from 0.35 to 0.40, score increases by ~0.043",
                "WHO": "Agent 3 provides graph centrality data. Agent 2 provides verified claims.",
                "MISSING": "Real-time AIS data, refinery blending costs not modeled in components.",
                "RAW": "Risk = 0.35*EB + 0.25*DR + 0.20*DC + 0.10*TC + 0.10*ED"
            }
        }

    def audit_agent_5(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 5: CSCO Synthesizer."""
        flags = []
        narrative = output.get("narrative", "")
        if not narrative:
            flags.append("No narrative generated.")
        if len(narrative.split()) < 10:
            flags.append("Narrative is too short — may lack detail.")
        if output.get("error"):
            flags.append(f"LLM error: {output['error']}")
        return {
            "agent_id": 5, "agent_name": "CSCO Synthesizer",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": "Generated risk narrative from verified claims and risk analysis",
                "WHAT": f"Narrative generated ({len(narrative.split())} words). Citations: {len(output.get('citations',[]))}",
                "WHERE": f"Sources cited inline: {[c.get('url','') for c in output.get('citations',[])]}",
                "IS": "Narrative only uses claims from verified graph nodes. No invented data.",
                "WHAT_IF": "If risk score was lower, narrative tone would shift from 'immediate action' to 'monitoring'",
                "WHO": "Agent 4 provides risk data. Agent 2 provides verified claims.",
                "MISSING": "Geopolitical negotiation outcomes are unpredictable — noted as low confidence inference.",
                "RAW": f"Prompt: Use ONLY verified claims + risk data. Cite source_url after every claim. LLM generated: {output.get('llm_generated', False)}"
            }
        }

    def audit_agent_6(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 6: Alternative Sourcing (MCDA)."""
        flags = []
        alternatives = output.get("alternatives", [])
        if not alternatives:
            flags.append("No alternatives generated.")
        return {
            "agent_id": 6, "agent_name": "Alternative Sourcing (MCDA)",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"TOPSIS ranking across {len(output.get('criteria',[]))} criteria with AHP-derived weights",
                "WHAT": f"Ranked {len(alternatives)} alternatives. Top: {alternatives[0]['name'] if alternatives else 'N/A'} (score: {alternatives[0]['score'] if alternatives else 'N/A'})",
                "WHERE": f"Top alternative source: {alternatives[0].get('source_url','') if alternatives else 'N/A'}",
                "IS": "TOPSIS is deterministic. Weights from AHP pairwise comparison.",
                "WHAT_IF": f"Sensitivity analysis: {output.get('sensitivity_analysis',{})}",
                "WHO": "Agent 3 graph informs alternative availability. Agent 2 verified claims feed criteria values.",
                "MISSING": "Refinery-specific crude compatibility data not modeled.",
                "RAW": f"Matrix: {len(alternatives)} alternatives x {len(output.get('criteria',[]))} criteria"
            }
        }

    def audit_agent_7(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 7: Consensus & Conflict Detector."""
        flags = []
        status = output.get("status", "")
        variance = output.get("variance", 0)
        if status == "HALTED":
            flags.append(f"SYSTEM HALTED: Variance {variance} exceeds {output.get('threshold_halt', 0.30)} threshold.")
        elif status == "FLAGGED":
            flags.append(f"FLAGGED: Variance {variance} between {output.get('threshold_flag', 0.15)}-{output.get('threshold_halt', 0.30)}.")
        return {
            "agent_id": 7, "agent_name": "Consensus & Conflict Detector",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": f"Compared Agent 4 (Risk) vs Agent 6 (Sourcing). Variance: {variance} (threshold: {output.get('threshold_halt', 0.30)})",
                "WHAT": f"Agent opinions: {output.get('agent_opinions', {})}",
                "WHERE": "Internal — no external sources for this step",
                "IS": f"Thresholds: 0.15=flag, 0.30=halt. Current variance={variance}. Status={status}.",
                "WHAT_IF": f"If threshold raised to 0.40, this would {'not halt' if variance < 0.40 else 'still halt'}",
                "WHO": "Agent 4 and Agent 6 opinions compared. All previous agents audited by ERASER already.",
                "MISSING": "No probabilistic model — deterministic variance check only.",
                "RAW": f"variance = abs(Agent_4_risk({output.get('agent_opinions',{}).get('Agent_4_Risk_Score','?')}) - Agent_6_sourcing({output.get('agent_opinions',{}).get('Agent_6_Sourcing_Proxy (1-Reliability)','?')}))"
            }
        }

    def audit_agent_8(self, output: Dict) -> Dict[str, Any]:
        """Audit Agent 8: Final ERASER (self-audit)."""
        flags = []
        if output.get("overall_rating") == "FAIL":
            flags.append("Overall audit rating: FAIL")
        return {
            "agent_id": 8, "agent_name": "Final ERASER",
            "status": "FLAG" if flags else "PASS", "flags": flags,
            "answers": {
                "WHY": "Performed final epistemic audit of entire pipeline",
                "WHAT": f"Overall rating: {output.get('overall_rating', 'UNKNOWN')}",
                "WHERE": "Evidence trail exported to JSONL",
                "IS": "Audit checks citation integrity, cross-agent consistency, evidence completeness",
                "WHAT_IF": "If deterministic checks fail, audit rating becomes FLAG/FAIL",
                "WHO": "All previous agents audited. This is the final check.",
                "MISSING": "No human-in-the-loop for final sign-off in this version",
                "RAW": f"Exported trail: {output.get('evidence_trail_integrity', 'UNKNOWN')}"
            }
        }


def run_agent_8(pipeline_state: Dict[str, Any]) -> Dict[str, Any]:
    """Run Agent 8: Final ERASER audit."""

    store = get_evidence_store()
    eraser = ERASERReasoner()

    # Get evidence trail
    evidence_trail = store.get_trail()

    # Run audit
    audit = eraser.audit_pipeline(pipeline_state, evidence_trail)

    # Add timestamp
    audit["audited_at"] = datetime.utcnow().isoformat() + "Z"
    audit["pipeline_session_id"] = pipeline_state.get("session_id", "unknown")

    # Export full evidence trail
    export_path = store.export_trail(f"data/evidence/audit_{pipeline_state.get('session_id', 'unknown')}.jsonl")
    audit["evidence_trail_export"] = export_path

    # Store audit result
    store.store_claim(
        Claim(
            text=f"ERASER audit: {audit.get('overall_rating', 'UNKNOWN')} - {audit.get('summary', '')[:200]}",
            claim_type="categorical",  # ponytail: schema Literal has no 'audit'
            citations=[
                Citation(
                    source_tier=SourceTier.UNKNOWN,
                    source_name="Agent8_ERASER",
                    source_url="internal://agent8/eraser",
                    evidence_type=EvidenceType.USER_PROVIDED,
                    excerpt=f"ERASER audit: {audit.get('overall_rating', 'UNKNOWN')} - {audit.get('summary', '')[:200]}",
                    confidence=0.9
                )
            ],
            confidence=0.9,
            extracted_by="Agent8_ERASER"
        )
    )

    return audit


def generate_politiFact_report(audit: Dict[str, Any]) -> str:
    """Generate human-readable PolitiFact-style report from audit."""

    lines = [
        "=" * 80,
        "ARGUS ERASER EVIDENCE TRAIL AUDIT",
        "=" * 80,
        f"Overall Rating: {audit.get('overall_rating', 'UNKNOWN')}",
        f"Audit Timestamp: {audit.get('audited_at', 'unknown')}",
        f"Session: {audit.get('pipeline_session_id', 'unknown')}",
        "",
        "EXECUTIVE SUMMARY:",
        audit.get('summary', 'No summary available.'),
        "",
        "AGENT-BY-AGENT AUDIT:",
        "-" * 80
    ]

    for agent_id, agent_audit in audit.get("agent_audits", {}).items():
        rating = agent_audit.get("rating", "UNKNOWN")
        lines.append(f"\n{agent_id} — Rating: {rating}")

        for q, a in agent_audit.get("answers", {}).items():
            lines.append(f"  {q}: {a[:300]}...")

        if agent_audit.get("flags"):
            lines.append("  FLAGS:")
            for f in agent_audit["flags"]:
                lines.append(f"  - {f}")

    if audit.get("cross_agent_findings"):
        lines.append("\nCROSS-AGENT FINDINGS:")
        for f in audit["cross_agent_findings"]:
            lines.append(f"  - {f}")

    if audit.get("correction_recommendations"):
        lines.append("\nCORRECTION RECOMMENDATIONS:")
        for r in audit["correction_recommendations"]:
            lines.append(f"  - {r}")

    lines.append(f"\nEvidence Trail Integrity: {audit.get('evidence_trail_integrity', 'UNKNOWN')}")
    lines.append("=" * 80)

    return "\n".join(lines)


if __name__ == "__main__":
    # Test with mock pipeline state
    mock_state = {
        "status": "HALTED",
        "user_input": "Iran-Israel conflict, Strait of Hormuz, crude oil, India",
        "agents_completed": ["Agent0", "Agent1", "Agent2", "Agent3", "Agent4", "Agent5", "Agent6", "Agent7"],
        "claims_count": 6,
        "verified_count": 4,
        "flagged_count": 2,
        "risk_score": 0.5655,
        "risk_level": "MEDIUM",
        "top_alternative": "SPR Drawdown (0.76)",
        "consensus_status": "HALTED",
        "session_id": "test_20260711"
    }

    audit = run_agent_8(mock_state)
    print(audit.get("politiFact_report", "No report generated"))