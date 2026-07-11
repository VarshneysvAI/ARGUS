# graph/argus_graph.py
import json, asyncio
from typing import Dict, Any, TypedDict
from langgraph.graph import StateGraph, END

from agents.agent_0_search_quality import run_agent_0
from agents.agent_1_research import run_agent_1
from agents.agent_2_verification import run_agent_2
from agents.agent_4_risk import run_agent_4
from agents.agent_7_consensus import run_agent_7
from agents.agent_5_synthesizer import run_agent_5
from agents.agent_8_eraser import run_agent_8

class ArgusState(TypedDict):
    user_input: str
    agent_0: Dict[str, Any]
    agent_1: Dict[str, Any]
    agent_2: Dict[str, Any]
    agent_4: Dict[str, Any]
    agent_7: Dict[str, Any]
    agent_5: Dict[str, Any]
    agent_8: Dict[str, Any]
    status: str
    graph_data: Dict[str, Any]

def node_0(state: ArgusState) -> ArgusState:
    result = run_agent_0(state["user_input"])
    state["agent_0"] = result
    if result.get("status") == "REJECT":
        state["status"] = "REJECTED"
    return state

def node_1(state: ArgusState) -> ArgusState:
    a0 = state["agent_0"]
    result = run_agent_1(
        a0.get("corridor", ""),
        a0.get("commodity", ""),
        a0.get("economy", "")
    )
    state["agent_1"] = result
    return state

def node_2(state: ArgusState) -> ArgusState:
    claims = state["agent_1"].get("claims", [])
    result = run_agent_2(claims)
    state["agent_2"] = result
    return state

def node_4(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    graph = state.get("graph_data", {})
    result = run_agent_4(verified, graph)
    state["agent_4"] = result
    return state

def node_7(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    result = run_agent_7(state["agent_4"], verified)
    state["agent_7"] = result
    state["status"] = result.get("status", "UNKNOWN")
    return state

def node_5(state: ArgusState) -> ArgusState:
    if state.get("status") == "HALTED":
        a2_flagged = state["agent_2"].get("flagged_claims", [])
        narrative_parts = ["⚠️ SYSTEM HALTED: Agent conflict detected. Human review required."]
        citations = []
        if a2_flagged:
            for c in a2_flagged[:2]:
                narrative_parts.append(f"FLAGGED: {c.get('claim','')[:80]}... [source: {c.get('source_url','')}]")
                citations.append({"text": "Flagged claim", "url": c.get("source_url", "")})
            narrative_parts.append(f"Reason: {a2_flagged[0].get('reason', 'Variance exceeds threshold')}")
        state["agent_5"] = {
            "narrative": "\n\n".join(narrative_parts),
            "confidence": 0.0,
            "citations": citations
        }
        return state
    verified = state["agent_2"].get("verified_claims", [])
    result = run_agent_5(state["agent_4"], verified)
    state["agent_5"] = result
    return state

def node_8(state: ArgusState) -> ArgusState:
    final_output = {
        "agent_2": state.get("agent_2", {}),
        "agent_4": state.get("agent_4", {}),
        "agent_5": state.get("agent_5", {}),
        "agent_7": state.get("agent_7", {})
    }
    risk_score = state.get("agent_4", {}).get("risk_score", 0.0)
    variance = state.get("agent_7", {}).get("variance", 0.0)
    result = run_agent_8(final_output, risk_score, variance)
    state["agent_8"] = result
    state["status"] = "COMPLETE"
    return state

def should_continue(state: ArgusState) -> str:
    s = state.get("status", "")
    if s in ("REJECTED", "HALTED"):
        return "skip_synthesis"
    return "continue"

workflow = StateGraph(ArgusState)
workflow.add_node("agent_0", node_0)
workflow.add_node("agent_1", node_1)
workflow.add_node("agent_2", node_2)
workflow.add_node("agent_4", node_4)
workflow.add_node("agent_7", node_7)
workflow.add_node("agent_5", node_5)
workflow.add_node("agent_8", node_8)

workflow.set_entry_point("agent_0")
workflow.add_edge("agent_0", "agent_1")
workflow.add_edge("agent_1", "agent_2")
workflow.add_edge("agent_2", "agent_4")
workflow.add_edge("agent_4", "agent_7")
workflow.add_conditional_edges("agent_7", should_continue, {
    "continue": "agent_5",
    "skip_synthesis": "agent_8"
})
workflow.add_edge("agent_5", "agent_8")
workflow.add_edge("agent_8", END)

argus_app = workflow.compile()
