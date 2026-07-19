from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import asyncio
import threading
import json
from .database import engine, Base
from .pipeline import execute_pipeline_stream
from .ais_client import start_ais_background_loop, get_ais_snapshot

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ARGUS v5.0 API", description="Deterministic Energy Supply Chain Resilience Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_ais_thread():
    loop = asyncio.new_event_loop()
    start_ais_background_loop(loop)

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=run_ais_thread, daemon=True)
    thread.start()

class SignalRequest(BaseModel):
    signal_data: str

class ChallengeRequest(BaseModel):
    claim_text: str
    claim_source: str
    math_context: str
    user_query: str = ""

class GraphRequest(BaseModel):
    math_context: str  # JSON string of the math_state

@app.get("/")
def read_root():
    return {"status": "ok", "message": "ARGUS v5.0 Backend running."}

@app.get("/api/ais")
def get_ais_data():
    return {"status": "success", "data": get_ais_snapshot()}

@app.post("/api/signal")
def process_signal(req: SignalRequest):
    return StreamingResponse(execute_pipeline_stream(req.signal_data), media_type="application/x-ndjson")

@app.post("/api/challenge")
def challenge_claim(req: ChallengeRequest):
    """D-SHIELD Claim Challenge: sends the claim to the LLM for adversarial counter-analysis."""
    from .agents import or_client, OR_MODEL_NAME
    import requests as http_requests
    import os
    
    user_objection_text = f"\nUSER'S SPECIFIC OBJECTION: {req.user_query}" if req.user_query else ""
    prompt = f"""You are an adversarial intelligence auditor for a government energy security agency. A junior analyst produced the following claim in an intelligence briefing:

CLAIM: "{req.claim_text}"
CITED SOURCE: {req.claim_source}{user_objection_text}

Your job is to rigorously fact-check this claim. Respond with a structured JSON object:
{{
  "verdict": "CONFIRMED" or "DISPUTED" or "UNVERIFIABLE",
  "confidence": float (0.0 to 1.0),
  "counter_evidence": "string — provide specific data points, dates, or statistics that support or contradict the claim",
  "source_reliability": "string — assess whether the cited source type is appropriate for this claim",
  "source_link": "string — provide a highly realistic URL link (e.g., https://www.eia.gov/..., https://www.reuters.com/...) pointing to data that verifies or refutes this claim",
  "suggested_revision": "string — if DISPUTED, provide a more accurate version of the claim. If CONFIRMED, return the original claim unchanged.",
  "reasoning": "string — step-by-step explanation of your analysis"
}}

Mathematical context for reference: {req.math_context}
"""
    try:
        # Try NVIDIA first
        NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
        MODEL_NAME = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Accept": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 4096,
            "stream": False
        }
        response = http_requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        # Fallback to Groq
        try:
            response = or_client.chat.completions.create(
                model=OR_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            content = response.choices[0].message.content
        except Exception as e2:
            return {"error": str(e2)}

    try:
        import re
        clean_json = re.sub(r'```json\n|```', '', content).strip()
        result = json.loads(clean_json)
    except Exception:
        result = {"verdict": "UNVERIFIABLE", "confidence": 0.5, "counter_evidence": content, "source_reliability": "N/A", "source_link": "#", "suggested_revision": req.claim_text, "reasoning": content}
    
    return result

@app.post("/api/graph-analysis")
def graph_analysis(req: GraphRequest):
    """Generate strategic graph datasets from the math state using LLM analysis."""
    from .agents import or_client, OR_MODEL_NAME
    import requests as http_requests
    import os
    
    prompt = f"""You are a data visualization strategist. Given this energy supply chain mathematical state, generate 3 strategic chart datasets that would be most impactful for executive decision-makers.

Math State: {req.math_context}

Return a JSON array of exactly 3 chart objects. Each chart must have:
{{
  "title": "string — chart title",
  "chart_type": "bar" or "line" or "radar" or "area",
  "x_label": "string",
  "y_label": "string",
  "data": [{{ "label": "string", "value": number }}, ...],
  "insight": "string — one sentence explaining the strategic takeaway"
}}

Focus on: cost comparisons, risk exposure over time, and supplier competitiveness. Use real numbers from the math state.
"""
    try:
        NVIDIA_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
        MODEL_NAME = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")
        headers = {
            "Authorization": f"Bearer {os.getenv('NVIDIA_API_KEY')}",
            "Accept": "application/json",
        }
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "top_p": 0.95,
            "max_tokens": 4096,
            "stream": False
        }
        response = http_requests.post(NVIDIA_API_URL, headers=headers, json=payload, timeout=15.0)
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
    except Exception:
        try:
            response = or_client.chat.completions.create(
                model=OR_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            content = response.choices[0].message.content
        except Exception as e2:
            return {"charts": []}

    try:
        charts = json.loads(content)
        if isinstance(charts, dict) and "charts" in charts:
            charts = charts["charts"]
        elif isinstance(charts, dict):
            charts = [charts]
    except Exception:
        charts = []
    
    return {"charts": charts if isinstance(charts, list) else []}

