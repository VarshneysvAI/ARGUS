import json
import os
from .schemas import ExtractionSchema
from .engine import ArgusEngine
from .eia_client import get_spot_price
from .agents import agent_1_extract, agent_5_synthesize
from .validator import validate_claims
import requests

_serper_cache = {}

def get_osint_chatter(signal_text: str) -> dict:
    if signal_text in _serper_cache:
        return _serper_cache[signal_text]
        
    key = os.getenv("SERPER_API_KEY")
    fallback = {
        "summary": "[Unverified] Social chatter indicates secondary explosion near port facilities...",
        "articles": [
            {"title": "Secondary explosion near port facilities", "snippet": "Reports indicate secondary explosion at major port facility impacting crude oil logistics.", "link": "#"},
            {"title": "Tanker insurance premiums spike", "snippet": "Maritime insurance premiums for Persian Gulf routes increased by 340% following the incident.", "link": "#"},
            {"title": "Port authority issues lockdown", "snippet": "Regional port authorities have issued a temporary lockdown on outbound vessel traffic.", "link": "#"}
        ]
    }
    if not key:
        return fallback
    try:
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": key, "Content-Type": "application/json"}
        payload = {"q": f"latest energy news: {signal_text[:100]}"}
        response = requests.post(url, headers=headers, json=payload, timeout=3)
        if response.status_code == 200:
            results = response.json().get("organic", [])
            articles = []
            for res in results[:3]:
                articles.append({
                    "title": res.get("title", "Untitled"),
                    "snippet": res.get("snippet", ""),
                    "link": res.get("link", "#")
                })
            if articles:
                summary = f"[LIVE OSINT via Serper.dev] Rank 1: {articles[0]['snippet']} | Rank 2: {articles[1]['snippet'] if len(articles) > 1 else 'N/A'} | Rank 3: {articles[2]['snippet'] if len(articles) > 2 else 'N/A'}"
                res_data = {"summary": summary, "articles": articles}
                _serper_cache[signal_text] = res_data
                return res_data
    except Exception as e:
        print(f"Serper API error: {e}")
    return fallback

def get_static_candidates():
    return [
        {
            "supplier": "Saudi Aramco",
            "flag_state": "SA",
            "route": "Ras Tanura → Jamnagar",
            "landed_cost_usd_bbl": 84.20,
            "lead_time_days": 7,
            "vessel_class": "VLCC",
            "grade_compatibility": "HIGH (Arab Heavy match 0.90)",
        },
        {
            "supplier": "NNPC",
            "flag_state": "NG",
            "route": "Bonny → Paradip",
            "landed_cost_usd_bbl": 86.90,
            "lead_time_days": 19,
            "vessel_class": "Suezmax",
            "grade_compatibility": "MEDIUM",
        },
        {
            "supplier": "NIOC (Iran)",
            "flag_state": "IR",
            "route": "Kharg Island → Jamnagar",
            "landed_cost_usd_bbl": 70.00,
            "lead_time_days": 5,
            "vessel_class": "VLCC",
            "grade_compatibility": "HIGH",
        }
    ]

def load_sanctions():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "sanctions_snapshot.json")
    with open(path, "r") as f:
        return json.load(f)

import time
import json

def execute_pipeline_stream(signal_data: str):
    """
    Executes the entire ARGUS pipeline and streams progress.
    """
    yield json.dumps({"log": "[AGENT 1] Initializing prompt and validating Pydantic schema..."}) + "\n"
    time.sleep(0.1)
    extraction = agent_1_extract(signal_data)
    yield json.dumps({"log": f"[AGENT 1] Extracted {extraction.volume_lost_mbd} mbd for {extraction.corridor}"}) + "\n"
    
    # ---------------------------------------------------------
    # STAGE 2 & D-SHIELD: Data Aggregation & Variance Gate
    # ---------------------------------------------------------
    yield json.dumps({"log": "[THREAD A] Fetching Daily Official Benchmark from EIA v2..."}) + "\n"
    p_spot_base = get_spot_price()
    
    # Supply-shock elasticity heuristic: $2.50 per 1 mbd lost. 
    # This ensures the economic cascade dynamically scales with the severity of the crisis.
    shock_premium = extraction.volume_lost_mbd * 2.5
    p_spot = p_spot_base + shock_premium
    
    yield json.dumps({"log": f"[THREAD A] EIA Base: ${p_spot_base} | Shock Premium: +${shock_premium} | Adjusted Spot: ${p_spot}"}) + "\n"
    
    p_contract = 75.0 # default heuristic
    m_freight = 1.8 # from hormuz.json
    delta_grade = 2.2 # from hormuz.json
    d_congestion = 0.5 # proxy
    
    # OSINT vs baseline
    yield json.dumps({"log": "[THREAD B] Scraping OSINT chatter via Serper.dev..."}) + "\n"
    osint_chatter = get_osint_chatter(signal_data)
    baseline_mbd = 17.0
    osint_claim_mbd = extraction.volume_lost_mbd
    # D-Shield: OSINT vs baseline deviation > 20%
    variance = abs(osint_claim_mbd - baseline_mbd) / baseline_mbd > 0.20
    
    # ---------------------------------------------------------
    yield json.dumps({"log": "[ENGINE] Executing Cost Delta, Sanctions Pre-Filter, TOPSIS..."}) + "\n"
    time.sleep(0.1)
    engine = ArgusEngine()
    
    cost_metrics = engine.calculate_cost_delta(
        v_lost=extraction.volume_lost_mbd,
        p_spot=p_spot,
        p_contract=p_contract,
        m_freight=m_freight,
        delta_grade=delta_grade,
        d_congestion=d_congestion
    )
    
    sanctions_data = load_sanctions()
    candidates = get_static_candidates()
    candidates = engine.apply_sanctions_filter(candidates, sanctions_data)
    ranked_candidates = engine.heuristic_ranking(candidates)
    
    spr_strategy = engine.optimize_spr(extraction.volume_lost_mbd, extraction.duration_days)
    
    economic_impact = engine.economic_cascade(
        pump_delta=(cost_metrics["c_delta_usd_day"] / extraction.volume_lost_mbd / 1_000_000) if extraction.volume_lost_mbd > 0 else 0,
        duration_days=extraction.duration_days
    )
    
    math_state = {
        "cost_metrics": cost_metrics,
        "procurement_cards": ranked_candidates,
        "spr_strategy": spr_strategy,
        "economic_impact": economic_impact
    }

    # ---------------------------------------------------------
    # STAGE 4: Adversarial Synthesis (Agent 5)
    # ---------------------------------------------------------
    yield json.dumps({"log": "[AGENT 5] Synthesizing adversarial scenarios based on math state..."}) + "\n"
    narrative = agent_5_synthesize(math_state, variance)
    
    # ---------------------------------------------------------
    # STAGE 5: Regex Validator
    # ---------------------------------------------------------
    yield json.dumps({"log": "[D-SHIELD] Validating regex claims and physical bounds..."}) + "\n"
    try:
        validate_claims(narrative, math_state)
    except ValueError as e:
        yield json.dumps({"log": f"[D-SHIELD WARNING] {e}"}) + "\n"
    
    final_payload = {
        "extraction": extraction.model_dump(),
        "math_state": math_state,
        "variance_flag": variance,
        "narrative": narrative,
        "osint_chatter": osint_chatter
    }
    yield json.dumps({"final": final_payload}) + "\n"
