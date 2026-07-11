# graph/argus_graph.py
"""ARGUS — 8-agent LangGraph orchestration with ERASER audit after EVERY agent."""
import json, asyncio
from typing import Dict, Any, TypedDict, List
from langgraph.graph import StateGraph, END

from agents.agent_0_search_quality import run_agent_0
from agents.agent_1_research import run_agent_1
from agents.agent_2_verification import run_agent_2
from agents.agent_3_graph_builder import run_agent_3
from agents.agent_4_risk import run_agent_4
from agents.agent_5_synthesizer import run_agent_5
from agents.agent_6_mcda import run_agent_6
from agents.agent_7_consensus import run_agent_7
from agents.agent_8_eraser import run_agent_8

class ArgusState(TypedDict):
    user_input: str
    status: str
    agent_0: Dict[str, Any]
    agent_0_eraser: Dict[str, Any]
    agent_1: Dict[str, Any]
    agent_1_eraser: Dict[str, Any]
    agent_2: Dict[str, Any]
    agent_2_eraser: Dict[str, Any]
    agent_3: Dict[str, Any]
    agent_3_eraser: Dict[str, Any]
    agent_4_risk: Dict[str, Any]
    agent_4_eraser: Dict[str, Any]
    agent_5: Dict[str, Any]
    agent_5_eraser: Dict[str, Any]
    agent_6: Dict[str, Any]
    agent_6_eraser: Dict[str, Any]
    agent_7: Dict[str, Any]
    agent_7_eraser: Dict[str, Any]
    human_decision: Dict[str, Any]
    graph_data: Dict[str, Any]

def initial_state(user_input: str) -> ArgusState:
    return {
        "user_input": user_input, "status": "RUNNING",
        "agent_0": {}, "agent_0_eraser": {},
        "agent_1": {}, "agent_1_eraser": {},
        "agent_2": {}, "agent_2_eraser": {},
        "agent_3": {}, "agent_3_eraser": {},
        "agent_4_risk": {}, "agent_4_eraser": {},
        "agent_5": {}, "agent_5_eraser": {},
        "agent_6": {}, "agent_6_eraser": {},
        "agent_7": {}, "agent_7_eraser": {},
        "human_decision": {}, "graph_data": {}
    }

def node_0(state: ArgusState) -> ArgusState:
    result = run_agent_0(state["user_input"])
    state["agent_0"] = result
    state["agent_0_eraser"] = run_agent_8(0, result)
    if result.get("status") == "REJECT":
        state["status"] = "REJECTED"
    return state

def node_1(state: ArgusState) -> ArgusState:
    a0 = state["agent_0"]
    result = run_agent_1(a0.get("corridor", ""), a0.get("commodity", ""), a0.get("economy", ""))
    state["agent_1"] = result
    state["agent_1_eraser"] = run_agent_8(1, result)
    return state

def node_2(state: ArgusState) -> ArgusState:
    claims = state["agent_1"].get("claims", [])
    result = run_agent_2(claims)
    state["agent_2"] = result
    state["agent_2_eraser"] = run_agent_8(2, result)
    return state

def node_3(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    result = run_agent_3(verified)
    state["agent_3"] = result
    state["graph_data"] = result.get("graph_data", {})
    state["agent_3_eraser"] = run_agent_8(3, result)
    return state

def node_4(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    graph = state.get("graph_data", {})
    result = run_agent_4(verified, graph)
    state["agent_4_risk"] = result
    state["agent_4_eraser"] = run_agent_8(4, result)
    return state

def node_5(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    flagged = state["agent_2"].get("flagged_claims", [])
    result = run_agent_5(verified, state["agent_4_risk"], flagged)
    state["agent_5"] = result
    state["agent_5_eraser"] = run_agent_8(5, result)
    return state

def node_6(state: ArgusState) -> ArgusState:
    verified = state["agent_2"].get("verified_claims", [])
    result = run_agent_6(verified, state.get("graph_data", {}))
    state["agent_6"] = result
    state["agent_6_eraser"] = run_agent_8(6, result)
    return state

def node_7(state: ArgusState) -> ArgusState:
    result = run_agent_7(state["agent_4_risk"], state["agent_2"].get("verified_claims", []), state.get("agent_6", {}))
    state["agent_7"] = result
    state["agent_7_eraser"] = run_agent_8(7, result)
    state["status"] = result.get("status", "UNKNOWN")
    return state

def should_halt(state: ArgusState) -> str:
    s = state.get("status", "")
    if s in ("REJECTED", "HALTED"):
        return "halt"
    return "continue"

workflow = StateGraph(ArgusState)

workflow.add_node("agent_0", node_0)
workflow.add_node("agent_1", node_1)
workflow.add_node("agent_2", node_2)
workflow.add_node("agent_3", node_3)
workflow.add_node("agent_4", node_4)
workflow.add_node("agent_5", node_5)
workflow.add_node("agent_6", node_6)
workflow.add_node("agent_7", node_7)

workflow.set_entry_point("agent_0")
workflow.add_edge("agent_0", "agent_1")
workflow.add_edge("agent_1", "agent_2")
workflow.add_edge("agent_2", "agent_3")
workflow.add_edge("agent_3", "agent_4")
workflow.add_edge("agent_4", "agent_5")
workflow.add_edge("agent_5", "agent_6")
workflow.add_edge("agent_6", "agent_7")
workflow.add_conditional_edges("agent_7", should_halt, {"halt": END, "continue": END})

argus_app = workflow.compile()
