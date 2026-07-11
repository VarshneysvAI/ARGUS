# agents/agent_0_search_quality.py
import re
from typing import Dict, Any, List

CRISIS_KEYWORDS = {
    "corridor": ["hormuz", "malacca", "suez", "bab el mandeb", "red sea", "gibraltar", "panama", "bab-el-mandeb"],
    "commodity": ["crude oil", "lng", "petroleum", "natural gas", "oil", "lpg"],
    "economy": ["india", "china", "japan", "south korea", "europe", "us", "usa", "japan"],
    "crisis_type": ["conflict", "blockade", "piracy", "closure", "disruption", "war", "attack", "sanctions"]
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
    corridor = entities.get("corridor", [None])[0]
    commodity = entities.get("commodity", [None])[0]
    economy = entities.get("economy", [None])[0]
    if corridor and commodity:
        queries.append(f"{corridor} {commodity} disruption 2026 EIA")
    if economy and commodity:
        queries.append(f"{economy} {commodity} imports 2026")
    if corridor:
        queries.append(f"{corridor} shipping disruption 2026")
    if economy and corridor:
        queries.append(f"{economy} {corridor} oil supply risk 2026")
    return queries

def run_agent_0(user_input: str) -> Dict[str, Any]:
    entities = extract_entities(user_input)
    specificity = calculate_specificity(entities)
    if specificity < 0.5:
        return {
            "status": "REJECT",
            "reason": "Input too vague. Please specify corridor, commodity, economy, and crisis type.",
            "specificity_score": round(specificity, 2),
            "entities": entities
        }
    return {
        "corridor": (entities.get("corridor") or [None])[0],
        "commodity": (entities.get("commodity") or [None])[0],
        "economy": (entities.get("economy") or [None])[0],
        "crisis_type": (entities.get("crisis_type") or [None])[0],
        "specificity_score": round(specificity, 2),
        "status": "PASS",
        "generated_queries": generate_queries(entities)
    }
