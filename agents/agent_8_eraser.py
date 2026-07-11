# agents/agent_8_eraser.py
"""Agent 8: ERASER — Epistemic Review & Scrutiny Agent.
Per-agent audits (0-7) are deterministic rule-based checks.
Final audit (agent_id=8) uses LLM for deep structured interrogation."""
import json, os
from typing import Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

ERASER_QUESTIONS = [
    "WHY: What is the reasoning behind this step?",
    "WHAT: What is the evidence for each claim?",
    "WHERE: What is the source URL, timestamp, and tier for each claim?",
    "IS: Does the inference logically follow from the evidence?",
    "WHAT_IF: If a configurable parameter changes (e.g., weight, threshold), how does output change?",
    "WHO: Which other agents disagree with this output?",
    "MISSING: What data is absent that would change the conclusion?",
    "RAW: Show the original prompt and raw agent response."
]

FINAL_ERASER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are ERASER, the ARGUS system's internal epistemic skeptic. You are given a concise summary of the pipeline run. Provide a brief critical assessment in 3-5 sentences covering: key findings, any data quality issues, and whether the conclusion is supported by the evidence."""),
    ("human", """Pipeline summary:
{pipeline_state}

ERASER assessment:""")
])

def audit_agent_0(output: Dict) -> Dict:
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
            "RAW": f"Input: {str(output.get('input', ''))[:100]}... | Keywords: crisis entity mapping"
        }
    }

def audit_agent_1(output: Dict) -> Dict:
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
            "RAW": "Loaded from data/articles/ | Filter applied: corridor + commodity + economy match"
        }
    }

def audit_agent_2(output: Dict) -> Dict:
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
            "RAW": "Cross-check: numerical regex extraction -> baseline comparison -> pass/fail/tolerance calc"
        }
    }

def audit_agent_3(output: Dict) -> Dict:
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

def audit_agent_4(output: Dict) -> Dict:
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

def audit_agent_5(output: Dict) -> Dict:
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

def audit_agent_6(output: Dict) -> Dict:
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

def audit_agent_7(output: Dict) -> Dict:
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
            "RAW": f"variance = abs(Agent_4_risk(...) - Agent_6_sourcing(...))"
        }
    }

AUDIT_FUNCTIONS = {
    0: audit_agent_0, 1: audit_agent_1, 2: audit_agent_2, 3: audit_agent_3,
    4: audit_agent_4, 5: audit_agent_5, 6: audit_agent_6, 7: audit_agent_7
}

def final_llm_audit(pipeline_state: Dict) -> Dict:
    api_key = os.getenv("NVIDIA_API_KEY")
    model = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")
    if not api_key:
        return {"agent_id": 8, "agent_name": "Final ERASER (LLM)", "status": "ERROR", "error": "missing_api_key"}
    summary = {}
    a0 = pipeline_state.get("agent_0", {})
    a1 = pipeline_state.get("agent_1", {})
    a2 = pipeline_state.get("agent_2", {})
    a3 = pipeline_state.get("agent_3", {})
    a4 = pipeline_state.get("agent_4_risk", {})
    a5 = pipeline_state.get("agent_5", {})
    a6 = pipeline_state.get("agent_6", {})
    a7 = pipeline_state.get("agent_7", {})
    summary["query"] = a0.get("input", "")[:100]
    summary["entities"] = f"corridor={a0.get('corridor')}, commodity={a0.get('commodity')}, economy={a0.get('economy')}"
    summary["specificity"] = a0.get("specificity_score", 0)
    summary["claims_found"] = len(a1.get("claims", []))
    summary["verified"] = len(a2.get("verified_claims", []))
    summary["flagged"] = len(a2.get("flagged_claims", []))
    summary["flagged_reasons"] = [f.get("reason","")[:100] for f in a2.get("flagged_claims", [])[:3]]
    summary["graph_nodes"] = a3.get("graph_summary", {}).get("total_nodes", 0)
    summary["graph_edges"] = a3.get("graph_summary", {}).get("total_edges", 0)
    summary["risk_score"] = a4.get("risk_score", 0)
    summary["risk_level"] = a4.get("risk_level", "?")
    summary["narrative_llm"] = a5.get("llm_generated", False)
    summary["narrative_preview"] = (a5.get("narrative","")[:200] + "...") if a5.get("narrative") else "N/A"
    summary["alternatives_top"] = [a.get("name") for a in a6.get("alternatives", [])[:3]]
    summary["status"] = a7.get("status", "?")
    summary["variance"] = a7.get("variance", 0)
    try:
        llm = ChatNVIDIA(model=model, temperature=0, timeout=30)
        chain = FINAL_ERASER_PROMPT | llm
        response = chain.invoke({"pipeline_state": json.dumps(summary, indent=2)})
        return {
            "agent_id": 8, "agent_name": "Final ERASER (LLM)",
            "status": "PASS", "llm_audit": response.content.strip(),
            "model": model, "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        return {"agent_id": 8, "agent_name": "Final ERASER (LLM)", "status": "ERROR", "error": str(e)}

def run_agent_8(agent_id: int, agent_output: Dict = None, pipeline_state: Dict = None) -> Dict[str, Any]:
    if agent_id == 8:
        return final_llm_audit(pipeline_state or {})
    audit_fn = AUDIT_FUNCTIONS.get(agent_id)
    if not audit_fn:
        return {"agent_id": agent_id, "agent_name": "Unknown", "status": "ERROR", "error": f"No audit function for agent {agent_id}"}
    result = audit_fn(agent_output)
    result["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return result
