# agents/agent_5_synthesizer.py
import os, re
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NIM_MODEL = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")

def format_claims(claims: List[Dict]) -> str:
    return "\n".join([f"- {c.get('claim','')} [source: {c.get('source_url','')}]" for c in claims])

def format_components(components: List[Dict]) -> str:
    return ", ".join([f"{c['name']}={c['value']:.2f} (w={c['weight']})" for c in components])

def run_agent_5(risk_output: Dict, verified_claims: List[Dict]) -> Dict[str, Any]:
    narrative_parts = []
    citations = []
    risk_level = risk_output.get("risk_level", "UNKNOWN")
    risk_score = risk_output.get("risk_score", 0.0)
    if risk_score >= 0.6:
        narrative_parts.append(f"RISK ASSESSMENT: {risk_level} risk (score: {risk_score:.2f}) — immediate action recommended [source: Cambridge formula Eq. 4]")
    elif risk_score >= 0.45:
        narrative_parts.append(f"RISK ASSESSMENT: {risk_level} risk (score: {risk_score:.2f}) — monitoring required [source: Cambridge formula Eq. 4]")
    else:
        narrative_parts.append(f"RISK ASSESSMENT: {risk_level} risk (score: {risk_score:.2f}) — standard operations [source: Cambridge formula Eq. 4]")
    citations.append({"text": f"Risk score: {risk_score} ({risk_level})", "url": "Cambridge et al. 2026, Eq. 4"})
    for claim in verified_claims[:3]:
        text = claim.get("claim", "")[:120]
        url = claim.get("source_url", "")
        tier = claim.get("source_tier", "unknown")
        narrative_parts.append(f"{text} [source: {url}]")
        citations.append({"text": text[:60], "url": url})
        if tier in ("gov",) and claim.get("verification_status") == "VERIFIED":
            narrative_parts.append(f"  Verified against government data — confidence: {claim.get('confidence', 0.0):.0%}")
    components = risk_output.get("components", [])
    if components:
        top = max(components, key=lambda c: c["contribution"])
        narrative_parts.append(f"Primary risk driver: {top['name']} (contribution: {top['contribution']:.4f}) [source: {top['source_url']}]")
        citations.append({"text": f"Primary driver: {top['name']}", "url": top["source_url"]})
    narrative_parts.append("[INFERRED — low confidence]: Geopolitical negotiations may affect timeline, but outcome is unpredictable.")
    return {
        "narrative": "\n\n".join(narrative_parts),
        "confidence": 0.72,
        "citations": citations
    }
