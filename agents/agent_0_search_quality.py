"""
Agent 0: Search Quality Gate — LLM-powered entity extraction + ReAct query planning.
Every extraction must cite the input text span.
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from core.reasoning import LLMReasoner, StructuredExtractor, CitationEnforcer, CitedClaim, CONFIG, PROMPTS
from core.schemas import ClaimStatus
from core.evidence_store import get_evidence_store


class Agent0Reasoner(LLMReasoner):
    """Specialized reasoner for entity extraction and query planning."""
    
    def __init__(self):
        super().__init__(
            agent_name="Agent0_SearchQuality",
            temperature=CONFIG.TEMPERATURE_EXTRACTION,
            system_prompt=PROMPTS["entity_extraction"]
        )
    
    def extract_entities(self, user_input: str) -> Dict[str, Any]:
        """Extract corridor, commodity, economy, crisis_type from user input."""
        
        prompt = f"""
USER INPUT: "{user_input}"

Extract the four entities. If not explicitly stated, infer from context but mark confidence accordingly.

OUTPUT JSON:
{{
  "corridor": "string or null",
  "commodity": "string or null",
  "economy": "string or null", 
  "crisis_type": "string or null",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation of extraction",
  "source_spans": {{"corridor": "...", "commodity": "...", "economy": "...", "crisis_type": "..."}}
}}
"""
        self._add_step("extraction", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, "extract_entities")
        self._add_step("extraction_result", response)
        
        try:
            result = json.loads(response)
            
            # If all APIs failed and returned deterministic fallback
            if result.get("fallback") or not any(result.get(k) for k in ["corridor", "commodity", "economy"]):
                return self._fallback_extraction(user_input)
                
            # Validate required fields
            for key in ["corridor", "commodity", "economy", "crisis_type"]:
                if key not in result:
                    result[key] = None
            
            # Ensure confidence is valid
            result["confidence"] = max(0.0, min(1.0, float(result.get("confidence", 0.5))))
            
            # Store source spans as citations
            if "source_spans" in result:
                result["citations"] = {
                    k: v for k, v in result["source_spans"].items() if v
                }
            
            return result
        except Exception:
            return self._fallback_extraction(user_input)
    
    def _fallback_extraction(self, user_input: str) -> Dict[str, Any]:
        """Simple keyword fallback if LLM fails."""
        text = user_input.lower()
        
        corridor_keywords = ["hormuz", "malacca", "suez", "bab el mandeb", "panama", "gibraltar", "dover"]
        commodity_keywords = ["crude oil", "lng", "petroleum", "natural gas", "oil", "lpg", "coal", "iron ore"]
        economy_keywords = ["india", "china", "japan", "south korea", "europe", "us", "usa", "germany", "uk"]
        crisis_keywords = ["conflict", "blockade", "piracy", "closure", "disruption", "war", "attack", "sanctions", "natural disaster", "earthquake", "drought"]
        
        def find_first(keywords):
            for kw in keywords:
                if kw in text:
                    return kw
            return None
        
        return {
            "corridor": find_first(corridor_keywords),
            "commodity": find_first(commodity_keywords),
            "economy": find_first(economy_keywords),
            "crisis_type": find_first(crisis_keywords),
            "confidence": 0.4,
            "reasoning": "Keyword fallback extraction",
            "citations": {}
        }
    
    def plan_queries(self, entities: Dict[str, Any]) -> List[str]:
        """Generate search queries using ReAct planning."""
        corridor = entities.get("corridor") or ""
        commodity = entities.get("commodity") or ""
        economy = entities.get("economy") or ""
        crisis = entities.get("crisis_type") or ""
        
        prompt = f"""
ENTITIES: corridor={corridor}, commodity={commodity}, economy={economy}, crisis_type={crisis}

Generate 3-5 specific search queries for research agents. Each query should target a specific data need.

OUTPUT JSON ARRAY:
[
  "query1",
  "query2", 
  "query3"
]

Focus on: EIA/IEA reports, government statistics, shipping data, price forecasts.
"""
        self._add_step("query_planning", prompt)
        messages = self._build_messages(prompt)
        response = self._invoke_with_retry(messages, "query_planning")
        self._add_step("queries_generated", response)
        
        try:
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries[:5]
        except json.JSONDecodeError:
            pass
        
        # Fallback queries
        fallback = []
        if corridor and commodity:
            fallback.append(f"{corridor} {commodity} disruption 2026 EIA")
        if economy and commodity:
            fallback.append(f"{economy} {commodity} imports 2026 government")
        if corridor:
            fallback.append(f"{corridor} shipping AIS disruption 2026")
        return fallback[:3]


def run_agent_0(user_input: str) -> Dict[str, Any]:
    """Run Agent 0: Extract entities and plan queries."""
    reasoner = Agent0Reasoner()
    store = get_evidence_store()
    
    # Extract entities
    entities = reasoner.extract_entities(user_input)
    
    # Calculate specificity score
    filled = sum(1 for v in entities.values() if v and v not in [None, ""] and not isinstance(v, dict))
    specificity = filled / 4.0  # 4 entity types
    
    # Plan queries
    queries = reasoner.plan_queries(entities)
    
    # Determine status
    if specificity < 0.3:
        status = "REJECT"
        reason = "Input too vague. Specify corridor (e.g., Hormuz), commodity (e.g., crude oil), economy (e.g., India), crisis type (e.g., conflict)."
    else:
        status = "PASS"
        reason = ""
    
    # Prepare output
    output = {
        "status": status,
        "reason": reason,
        "specificity_score": round(specificity, 2),
        "input": user_input,
        "corridor": entities.get("corridor"),
        "commodity": entities.get("commodity"),
        "economy": entities.get("economy"),
        "crisis_type": entities.get("crisis_type"),
        "entities": {k: v for k, v in entities.items() if k not in ["citations", "source_spans"]},
        "generated_queries": queries,
        "extraction_confidence": entities.get("confidence", 0.5),
        "reasoning": entities.get("reasoning", ""),
        "reasoning_trace": reasoner.get_trace()
    }
    # Store in evidence store (simplified - no need for internal tracking claim)
    # store.store_claim(
    #     CitedClaim(
    #         text=f"User query: {user_input} -> Entities: {entities}",
    #         claim_type="categorical",
    #         citations=[],
    #         status=ClaimStatus.VERIFIED_SINGLE_SOURCE,
    #         confidence=specificity,
    #         extracted_by="Agent0",
    #         metadata={"specificity": specificity}
    #     )
    # )
    
    return output


if __name__ == "__main__":
    # Test
    test_inputs = [
        "Iran-Israel conflict, Strait of Hormuz, crude oil, India",
        "Red Sea shipping attacks, LNG, Japan",
        "Panama Canal drought, petroleum products, US East Coast",
        "vague query"
    ]
    
    for inp in test_inputs:
        print(f"\n{'='*60}")
        print(f"INPUT: {inp}")
        result = run_agent_0(inp)
        print(f"Status: {result['status']}")
        print(f"Entities: corridor={result['corridor']}, commodity={result['commodity']}, economy={result['economy']}, crisis={result['crisis_type']}")
        print(f"Specificity: {result['specificity_score']}")
        print(f"Queries: {result['generated_queries']}")