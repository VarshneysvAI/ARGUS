# agents/agent_3_graph_builder.py
"""Agent 3: Graph Builder — constructs NetworkX graph from verified claims.
Every node/edge REQUIRES source_url, retrieved_at, verification_status, agent_confidence.
Claims without source_url are REJECTED — never enter graph."""
import networkx as nx
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

GRAPH_PERSIST_PATH = Path(__file__).resolve().parent.parent / "data" / "argus_graph.graphml"
GRAPH_JSON_PATH = Path(__file__).resolve().parent.parent / "data" / "argus_graph.json"

NODE_TYPE_KEYWORDS = {
    "Supplier": ["supplier", "country", "producer", "exporter", "saudi", "iraq", "uae", "iran", "kuwait", "russia"],
    "Refinery": ["refinery", "paradip", "jamnagar", "kochi", "mangalore", "bina", "bathinda", "panipat"],
    "Corridor": ["hormuz", "strait", "malacca", "suez", "red sea", "pipeline", "bab el mandeb"],
    "PortTerminal": ["port", "terminal", "fujairah", "habshan", "shipping", "vessel"],
    "SPR_Facility": ["spr", "strategic petroleum", "reserve", "storage", "cavern"],
    "Contract": ["contract", "agreement", "deal", "supply", "purchase"]
}

REL_TYPE_KEYWORDS = {
    "SUPPLIES_VIA": {"from": "Supplier", "to": "Corridor", "keywords": ["supplies", "exports", "ships", "flows"]},
    "ROUTES_TO": {"from": "Corridor", "to": "Refinery", "keywords": ["imports", "receives", "routes", "delivers"]},
    "HAS_CONTRACT": {"from": "Supplier", "to": "Contract", "keywords": ["agreed", "signed", "contracted", "deal"]},
    "STORES_AT": {"from": "Contract", "to": "SPR_Facility", "keywords": ["stored", "reserve", "stockpile"]},
}

def classify_node_type(text: str) -> str:
    text_lower = text.lower()
    for node_type, keywords in NODE_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return node_type
    return "Generic"

def classify_rel_type(text: str, source_type: str, target_type: str) -> str:
    text_lower = text.lower()
    for rel_type, spec in REL_TYPE_KEYWORDS.items():
        if spec["from"] == source_type and spec["to"] == target_type:
            if any(kw in text_lower for kw in spec["keywords"]):
                return rel_type
    return "RELATES_TO"

def build_graph(verified_claims: List[Dict]) -> Dict[str, Any]:
    G = nx.MultiDiGraph()
    stats = {"nodes_created": 0, "edges_created": 0, "rejected_no_url": 0, "node_types": {}}
    for claim in verified_claims:
        source_url = claim.get("source_url", "")
        if not source_url:
            stats["rejected_no_url"] += 1
            continue
        claim_text = claim.get("claim", "")
        headline = claim.get("headline", "")
        confidence = claim.get("confidence", 0.5)
        node_type = classify_node_type(claim_text + " " + headline)
        node_type = claim.get("verification_status", "Verified") + "_" + node_type
        node_id = f"node_{stats['nodes_created']}"
        G.add_node(node_id, type=node_type, label=headline[:50] if headline else f"Claim {stats['nodes_created']}", claim=claim_text[:200], source_url=source_url,
                   retrieved_at=claim.get("retrieved_at", datetime.utcnow().isoformat() + "Z"),
                   verification_status="VERIFIED", agent_confidence=confidence)
        stats["nodes_created"] += 1
        stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1
    if len(verified_claims) >= 2:
        for i in range(len(verified_claims) - 1):
            src_claim = verified_claims[i]
            for j in range(i + 1, len(verified_claims)):
                tgt_claim = verified_claims[j]
                src_type = classify_node_type(src_claim.get("claim", ""))
                tgt_type = classify_node_type(tgt_claim.get("claim", ""))
                combined_text = src_claim.get("claim", "") + " " + tgt_claim.get("claim", "")
                rel_type = classify_rel_type(combined_text, src_type, tgt_type)
                G.add_edge(f"node_{i}", f"node_{j}", rel_type=rel_type, source_url=src_claim.get("source_url", ""),
                           agent_confidence=min(src_claim.get("confidence", 0.5), tgt_claim.get("confidence", 0.5)))
                stats["edges_created"] += 1
    if G.number_of_nodes() > 0:
        stats["graph_analytics"] = {
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "density": round(nx.density(G), 4),
            "connected_components": nx.number_weakly_connected_components(G),
        }
        try:
            stats["graph_analytics"]["avg_clustering"] = round(nx.average_clustering(G.to_undirected()), 4) if G.number_of_nodes() > 1 else 0
        except Exception:
            stats["graph_analytics"]["avg_clustering"] = 0
    graph_data = nx.node_link_data(G)
    GRAPH_JSON_PATH.write_text(json.dumps(graph_data, indent=2, default=str), encoding="utf-8")
    return {
        "graph": G,
        "graph_data": graph_data,
        "stats": stats,
        "graph_persisted": str(GRAPH_JSON_PATH)
    }

def run_agent_3(verified_claims: List[Dict]) -> Dict[str, Any]:
    result = build_graph(verified_claims)
    return {
        "stats": result["stats"],
        "graph_data": result["graph_data"],
        "graph_summary": {
            "total_nodes": result["stats"]["nodes_created"],
            "total_edges": result["stats"]["edges_created"],
            "node_types": result["stats"]["node_types"],
            "analytics": result["stats"].get("graph_analytics", {}),
        },
        "graph_persisted": result["graph_persisted"]
    }

def load_graph() -> nx.MultiDiGraph:
    if GRAPH_JSON_PATH.exists():
        data = json.loads(GRAPH_JSON_PATH.read_text(encoding="utf-8"))
        return nx.node_link_graph(data, multigraph=True)
    return nx.MultiDiGraph()
