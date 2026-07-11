# agents/agent_0_search_quality.py
"""Agent 0: Search Quality Gate — validates input specificity, extracts crisis entities."""
import re
from typing import Dict, Any, List

CRISIS_KEYWORDS = {
    "corridor": ["hormuz", "malacca", "suez", "bab el mandeb", "red sea", "gibraltar", "panama", "bab-el-mandeb", "bosphorus", "dover"],
    "commodity": ["crude oil", "lng", "petroleum", "natural gas", "oil", "lpg", "coal", "iron ore"],
    "economy": ["india", "china", "japan", "south korea", "europe", "us", "usa", "japan", "germany", "uk"],
    "crisis_type": ["conflict", "blockade", "piracy", "closure", "disruption", "war", "attack", "sanctions", "natural disaster", "earthquake"]
}

def extract_entities(text: str) -> Dict[str, List[str]]:
    text_lower = text.lower()
    entities = {k: [] for k in CRISIS_KEYWORDS}
    for cat, keywords in CRISIS_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                entities[cat].append(kw)
    entities = {k: list(dict.fromkeys(v)) for k, v in entities.items()}
    return entities

def calculate_specificity(entities: Dict) -> float:
    filled = sum(1 for v in entities.values() if v)
    return filled / len(entities)

def generate_queries(entities: Dict) -> List[str]:
    queries = []
    corridor = (entities.get("corridor") or [None])[0]
    commodity = (entities.get("commodity") or [None])[0]
    economy = (entities.get("economy") or [None])[0]
    crisis = (entities.get("crisis_type") or [None])[0]
    if corridor and commodity:
        queries.append(f"{corridor} {commodity} disruption 2026 EIA")
    if economy and commodity:
        queries.append(f"{economy} {commodity} imports 2026 PIB")
    if corridor:
        queries.append(f"{corridor} shipping AIS disruption 2026")
    if economy and corridor:
        queries.append(f"{economy} {corridor} oil supply risk 2026")
    if crisis and corridor:
        queries.append(f"{crisis} {corridor} impact energy 2026")
    return queries

def run_agent_0(user_input: str) -> Dict[str, Any]:
    entities = extract_entities(user_input)
    specificity = calculate_specificity(entities)
    if specificity < 0.3:
        return {
            "status": "REJECT",
            "reason": "Input too vague. Specify corridor (e.g., Hormuz, Malacca), commodity (e.g., crude oil, LNG), economy (e.g., India, Japan), and crisis type (e.g., conflict, blockade).",
            "specificity_score": round(specificity, 2),
            "entities": entities,
            "input": user_input
        }
    return {
        "status": "PASS",
        "specificity_score": round(specificity, 2),
        "corridor": (entities.get("corridor") or [None])[0],
        "commodity": (entities.get("commodity") or [None])[0],
        "economy": (entities.get("economy") or [None])[0],
        "crisis_type": (entities.get("crisis_type") or [None])[0],
        "input": user_input,
        "entities": entities,
        "generated_queries": generate_queries(entities)
    }
