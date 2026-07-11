# agents/agent_5_synthesizer.py
"""Agent 5: CSCO Synthesizer — LLM-generated narrative using ONLY verified claims with source citations."""
import json, re, os
from typing import Dict, Any, List
from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are the CSCO (Chief Supply Chain Officer) Synthesizer for the ARGUS system, analyzing the Iran-Israel conflict's impact on crude oil supply through the Strait of Hormuz for India.

Your task: Generate a concise risk narrative using ONLY the provided verified claims and risk analysis.

STRICT RULES:
1. Every factual claim MUST end with [source: URL] — the URL is provided next to each claim.
2. If a claim has no source, mark as [INFERRED — low confidence].
3. Do NOT invent data not in the verified claims below.
4. Be specific with numbers.
5. Maximum 5 sentences.
6. If flagged claims exist, mention the discrepancy and that those claims are quarantined."""),
    ("human", """VERIFIED CLAIMS:
{verified_claims_text}

RISK ANALYSIS:
- Risk Score: {risk_score} ({risk_level})
- Components: {risk_components}

FLAGGED CLAIMS (source discrepancies):
{flagged_claims_text}

Generate the narrative now:""")
])

def run_agent_5(verified_claims: List[Dict], risk_output: Dict, flagged_claims: List[Dict] = None) -> Dict[str, Any]:
    if not verified_claims:
        return {"narrative": "No verified claims available for analysis.", "confidence": 0.0, "citations": []}
    flagged = flagged_claims or []
    api_key = os.getenv("NVIDIA_API_KEY")
    model = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")
    if not api_key:
        return {"narrative": "LLM unavailable — no NVIDIA_API_KEY configured.", "confidence": 0.0, "citations": [], "error": "missing_api_key"}
    verified_text = "\n".join(
        f"- {c.get('claim','')[:300]} [source: {c.get('source_url','')}] [tier: {c.get('source_tier','')}]"
        for c in verified_claims
    ) or "No verified claims."
    risk_score = risk_output.get("risk_score", 0.0)
    risk_level = risk_output.get("risk_level", "UNKNOWN")
    comps = risk_output.get("components", [])
    risk_comp_text = "; ".join(f"{c['name']}={c['value']} (weight={c['weight']}, contrib={c['contribution']})" for c in comps) or "N/A"
    flagged_text = "\n".join(
        f"- {fc.get('claim','')[:200]} — {fc.get('reason','')} [source: {fc.get('source_url','')}]"
        for fc in flagged[:3]
    ) or "No flagged claims."
    try:
        llm = ChatNVIDIA(model=model, temperature=0)
        chain = SYNTHESIS_PROMPT | llm
        response = chain.invoke({
            "verified_claims_text": verified_text,
            "risk_score": f"{risk_score:.4f}",
            "risk_level": risk_level,
            "risk_components": risk_comp_text,
            "flagged_claims_text": flagged_text,
        })
        narrative = response.content.strip()
        citations = []
        for c in verified_claims:
            url = c.get("source_url", "")
            if url and url not in [x["url"] for x in citations]:
                citations.append({"text": c.get("headline", "")[:80], "url": url})
        return {
            "narrative": narrative,
            "confidence": round(0.85 - 0.1 * len(flagged), 2),
            "citations": citations,
            "model": model,
            "llm_generated": True
        }
    except Exception as e:
        return {"narrative": f"LLM generation failed: {str(e)}", "confidence": 0.0, "citations": [], "error": str(e)}
